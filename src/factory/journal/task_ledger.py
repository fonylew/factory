"""Step-by-Step Task Conversation & Design Ledger Manager with Secret Redaction & Atomic Trello Linking."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from factory.graph.models import EdgeType, FeatureNode, ProblemNode, SystemSpecNode, TaskJournalNode
from factory.graph.store import TraceabilityGraphStore
from factory.graph.validator import GraphValidator

if TYPE_CHECKING:
    from factory.kanban.card_parser import CardParser
    from factory.kanban.trello_client import LocalKanbanAdapter


class SecretRedactor:
    """Redacts API keys, tokens, and private keys before writing to Task Ledgers or Trello."""

    PATTERNS = [
        # GitHub Personal Access Tokens / Fine-grained tokens
        (re.compile(r"\b(gh[pousr]_[A-Za-z0-9_]{20,})\b"), "[REDACTED_GITHUB_TOKEN]"),
        # Generic Bearer / API Key assignments
        (
            re.compile(
                r"(?i)(trello_token|trello_api_key|github_token|api_key|secret_key|bearer)\s*[:=]\s*['\"]?([A-Za-z0-9_\-\.]{16,})['\"]?"
            ),
            r"\1=[REDACTED_SECRET]",
        ),
        # OpenAI / Anthropic / Google style keys
        (re.compile(r"\b(sk-[A-Za-z0-9_\-]{20,}|AIza[0-9A-Za-z_\-]{30,})\b"), "[REDACTED_API_KEY]"),
        # Private key PEM blocks
        (
            re.compile(
                r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
                re.DOTALL,
            ),
            "[REDACTED_PRIVATE_KEY]",
        ),
    ]

    @classmethod
    def sanitize(cls, text: str) -> str:
        sanitized = text
        for pattern, replacement in cls.PATTERNS:
            sanitized = pattern.sub(replacement, sanitized)
        return sanitized


class TaskLedgerManager:
    """Manages `specs/tasks/<YYYY-MM-DD>_<TASK-ID>_<slug>/` step-by-step markdown ledgers and Trello links."""

    def __init__(self, tasks_base_dir: Path, graph_store: Optional[TraceabilityGraphStore] = None) -> None:
        self.tasks_base_dir = Path(tasks_base_dir)
        self.tasks_base_dir.mkdir(parents=True, exist_ok=True)
        self.graph_store = graph_store

    @staticmethod
    def slugify(text: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
        return slug[:48] or "task"

    def get_task_folder_name(self, task_id: str, date_str: str, description: str) -> str:
        slug = self.slugify(description)
        return f"{date_str}_{task_id}_{slug}"

    def init_task_ledger(
        self,
        task_id: str,
        description: str,
        date_str: Optional[str] = None,
        problem_id: str = "PROB-001",
        spec_id: str = "SPEC-001",
        feature_ids: Optional[List[str]] = None,
        trello_card_id: Optional[str] = None,
        trello_card_url: Optional[str] = None,
    ) -> Path:
        date_val = date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        folder_name = self.get_task_folder_name(task_id, date_val, description)
        task_dir = self.tasks_base_dir / folder_name
        task_dir.mkdir(parents=True, exist_ok=True)

        features_list = feature_ids or []
        features_yaml = "\n".join(f'  - "{fid}"' for fid in features_list) or "  []"
        card_url = trello_card_url or (f"https://trello.com/c/{trello_card_id}" if trello_card_id else "")

        readme_path = task_dir / "README.md"
        safe_desc = SecretRedactor.sanitize(description)
        readme_content = f"""---
task_id: "{task_id}"
date: "{date_val}"
description: "{safe_desc}"
problem_id: "{problem_id}"
spec_id: "{spec_id}"
features:
{features_yaml}
trello_card_id: "{trello_card_id or ''}"
trello_card_url: "{card_url}"
status: "IN_PROGRESS"
---

# [{task_id}] {safe_desc}

## Task Overview
- **Task ID**: `{task_id}`
- **Date**: `{date_val}`
- **Description**: {safe_desc}
- **Problem Anchor**: `{problem_id}`
- **System Spec**: `{spec_id}`
- **Trello Card ID**: `{trello_card_id or 'UNLINKED'}`
- **Trello Card URL**: {card_url or 'N/A'}

## Step Execution Ledger
"""
        readme_path.write_text(readme_content, encoding="utf-8")

        if self.graph_store is not None:
            node = TaskJournalNode(
                id=task_id,
                task_id=task_id,
                title=f"{task_id}: {safe_desc}",
                date=date_val,
                description=safe_desc,
                journal_dir=str(task_dir),
                problem_id=problem_id,
                steps_completed=[],
                trello_card_id=trello_card_id,
                metadata={"trello_card_url": card_url},
            )
            self.graph_store.upsert_node(node)
            for fid in features_list:
                if self.graph_store.get_node(fid):
                    self.graph_store.add_edge(fid, task_id, EdgeType.LOGGED_IN)

        return task_dir

    def create_and_link_task_with_trello(
        self,
        task_id: str,
        feature_id: str,
        title: str,
        problem_context: str,
        system_design: str,
        scenarios: List[str],
        features_dir: Path,
        kanban_adapter: "LocalKanbanAdapter",
        target_column: str = "4. Ready for Dev (Spec Locked)",
        date_str: Optional[str] = None,
        problem_id: str = "PROB-001",
        spec_id: str = "SPEC-001",
    ) -> Dict[str, Any]:
        """Atomically creates the Task Ledger, Gherkin `.feature` file, Graph nodes, and linked Trello Card."""
        from factory.kanban.card_parser import CardParser
        from factory.kanban.trello_client import KanbanCard, TrelloKanbanAdapter

        slug = self.slugify(title)
        features_dir = Path(features_dir)
        features_dir.mkdir(parents=True, exist_ok=True)
        feat_file = features_dir / f"{feature_id}-{slug}.feature"
        if not feat_file.exists():
            scenario_blocks = "\n\n".join(
                f"  Scenario: {sc}\n    Given the {feature_id} subsystem is initialized\n    When {sc.lower()}\n    Then the acceptance criteria for {feature_id} are satisfied"
                for sc in (scenarios or [f"Verify {title}"])
            )
            feat_file.write_text(
                f"@{problem_id} @{spec_id} @{feature_id}\n"
                f"Feature: {title}\n"
                f"  As a Technical Lead or System Analyst\n"
                f"  I want {title}\n"
                f"  So that {problem_context}\n\n"
                f"{scenario_blocks}\n",
                encoding="utf-8",
            )

        checksum = GraphValidator.compute_file_sha256(feat_file)
        card_id = f"CARD-{feature_id}"

        if self.graph_store is not None:
            if not self.graph_store.get_node(problem_id):
                self.graph_store.upsert_node(
                    ProblemNode(id=problem_id, title=f"Root Problem {problem_id}")
                )
            if not self.graph_store.get_node(spec_id):
                self.graph_store.upsert_node(
                    SystemSpecNode(id=spec_id, title=f"System Spec {spec_id}", problem_id=problem_id)
                )
            feat_node = FeatureNode(
                id=feature_id,
                title=title,
                spec_id=spec_id,
                feature_file_path=str(feat_file),
                scenarios=scenarios or [f"Verify {title}"],
                spec_checksum=checksum,
                trello_card_id=card_id,
                status="READY_FOR_DEV",
            )
            self.graph_store.upsert_node(feat_node)

        card_desc = CardParser.render_card_template(
            feature_id=feature_id,
            title=title,
            problem_id=problem_id,
            spec_id=spec_id,
            problem_context=problem_context,
            system_design=system_design,
            feature_file_path=str(feat_file),
            scenarios=scenarios or [f"Verify {title}"],
            spec_sha256=checksum,
        )
        card = KanbanCard(
            card_id=card_id,
            feature_id=feature_id,
            title=f"[{feature_id}] {title}",
            description=card_desc,
            column=target_column,
            labels=["spec-driven", task_id],
            last_modified_by="agy",
            task_id=task_id,
        )
        if isinstance(kanban_adapter, TrelloKanbanAdapter):
            sync_info = kanban_adapter.sync_card_to_trello_remote(card)
            final_card_id = str(sync_info["card_id"])
            final_card_url = str(sync_info["url"])
        else:
            saved_card = kanban_adapter.upsert_card(card)
            final_card_id = saved_card.card_id
            final_card_url = saved_card.url

        task_dir = self.init_task_ledger(
            task_id=task_id,
            description=title,
            date_str=date_str,
            problem_id=problem_id,
            spec_id=spec_id,
            feature_ids=[feature_id],
            trello_card_id=final_card_id,
            trello_card_url=final_card_url,
        )

        # Update FeatureNode if remote Trello card ID changed
        if self.graph_store is not None:
            fnode = self.graph_store.get_node(feature_id)
            if isinstance(fnode, FeatureNode):
                fnode.trello_card_id = final_card_id
                self.graph_store.upsert_node(fnode)

        return {
            "task_id": task_id,
            "feature_id": feature_id,
            "task_dir": str(task_dir),
            "feature_file": str(feat_file),
            "spec_sha256": checksum,
            "trello_card_id": final_card_id,
            "trello_card_url": final_card_url,
            "column": target_column,
        }

    def link_existing_task_to_trello(
        self,
        task_id: str,
        feature_id: str,
        trello_card_id: str,
        trello_card_url: Optional[str] = None,
    ) -> Path:
        """Links an existing Task Ledger folder and Graph nodes to a Trello card ID."""
        task_dir = self._find_task_dir(task_id)
        readme_path = task_dir / "README.md"
        url_val = trello_card_url or f"https://trello.com/c/{trello_card_id}"

        if readme_path.exists():
            text = readme_path.read_text(encoding="utf-8")
            text = re.sub(
                r'trello_card_id:\s*"[^"]*"',
                f'trello_card_id: "{trello_card_id}"',
                text,
            )
            text = re.sub(
                r'trello_card_url:\s*"[^"]*"',
                f'trello_card_url: "{url_val}"',
                text,
            )
            readme_path.write_text(text, encoding="utf-8")

        if self.graph_store is not None:
            tnode = self.graph_store.get_node(task_id)
            if isinstance(tnode, TaskJournalNode):
                tnode.trello_card_id = trello_card_id
                tnode.metadata["trello_card_url"] = url_val
                self.graph_store.upsert_node(tnode)
            fnode = self.graph_store.get_node(feature_id)
            if isinstance(fnode, FeatureNode):
                fnode.trello_card_id = trello_card_id
                self.graph_store.upsert_node(fnode)
                self.graph_store.add_edge(feature_id, task_id, EdgeType.LOGGED_IN)

        return readme_path

    def append_step_output(
        self,
        task_id: str,
        step_name: str,
        markdown_content: str,
        actor: str = "agy (Gemini 4 Argon)",
    ) -> Path:
        task_dir = self._find_task_dir(task_id)
        filename = step_name if step_name.endswith(".md") else f"{step_name}.md"
        step_path = task_dir / filename
        timestamp = datetime.now(timezone.utc).isoformat()
        sanitized_body = SecretRedactor.sanitize(markdown_content)

        header = (
            f"# Step Output: `{step_name}` (`{task_id}`)\n\n"
            f"- **Task ID**: `{task_id}`\n"
            f"- **Recorded At**: `{timestamp}`\n"
            f"- **Actor**: `{actor}`\n\n---\n\n"
        )
        if step_path.exists():
            existing = step_path.read_text(encoding="utf-8")
            step_path.write_text(
                existing + f"\n\n---\n### Update ({timestamp} by `{actor}`)\n\n" + sanitized_body + "\n",
                encoding="utf-8",
            )
        else:
            step_path.write_text(header + sanitized_body + "\n", encoding="utf-8")

        readme_path = task_dir / "README.md"
        if readme_path.exists():
            readme_txt = readme_path.read_text(encoding="utf-8")
            entry_line = f"- **{step_name}** ([{filename}](./{filename})) — Recorded by `{actor}` at `{timestamp}`\n"
            if filename not in readme_txt:
                readme_path.write_text(readme_txt + entry_line, encoding="utf-8")

        if self.graph_store is not None:
            node = self.graph_store.get_node(task_id)
            if isinstance(node, TaskJournalNode):
                if filename not in node.steps_completed:
                    node.steps_completed.append(filename)
                    self.graph_store.upsert_node(node)

        return step_path

    def _find_task_dir(self, task_id: str) -> Path:
        matches = sorted(self.tasks_base_dir.glob(f"*_{task_id}_*"))
        if not matches:
            raise FileNotFoundError(f"No task ledger directory found for task_id '{task_id}' in {self.tasks_base_dir}")
        return matches[0]
