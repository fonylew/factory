"""Step-by-Step Task Conversation & Design Ledger Manager with Secret Redaction."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re
from typing import List, Optional

from factory.graph.models import EdgeType, TaskJournalNode
from factory.graph.store import TraceabilityGraphStore


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
    """Manages `specs/tasks/<YYYY-MM-DD>_<TASK-ID>_<slug>/` step-by-step markdown ledgers."""

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
    ) -> Path:
        date_val = date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        folder_name = self.get_task_folder_name(task_id, date_val, description)
        task_dir = self.tasks_base_dir / folder_name
        task_dir.mkdir(parents=True, exist_ok=True)

        features_list = feature_ids or []
        features_yaml = "\n".join(f'  - "{fid}"' for fid in features_list) or "  []"

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
status: "IN_PROGRESS"
---

# [{task_id}] {safe_desc}

## Task Overview
- **Task ID**: `{task_id}`
- **Date**: `{date_val}`
- **Description**: {safe_desc}
- **Problem Anchor**: `{problem_id}`
- **System Spec**: `{spec_id}`

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
            )
            self.graph_store.upsert_node(node)
            for fid in features_list:
                if self.graph_store.get_node(fid):
                    self.graph_store.add_edge(fid, task_id, EdgeType.LOGGED_IN)

        return task_dir

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
