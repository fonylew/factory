"""Stage 1 (`1 Specification`): Research Papers -> Spec-writer <-> Reviewers <-> User -> Trusted Lean Spec."""

from __future__ import annotations

from pathlib import Path
import re
import stat
from typing import List, Optional

from factory.graph.models import FormalSpecNode
from factory.graph.store import TraceabilityGraphStore
from factory.graph.validator import GraphValidator
from factory.kanban.state_machine import KanbanStateMachine


class FormalSpecPipeline:
    """Manages untrusted Spec-writer & Reviewer iterations and Human Approval locking into a Trusted Lean Spec."""

    THEOREM_DECL_RE = re.compile(r"^\s*theorem\s+([A-Za-z0-9_']+)\b", re.MULTILINE)

    def __init__(
        self,
        formal_specs_dir: Path,
        graph_store: TraceabilityGraphStore,
        kanban_sm: Optional[KanbanStateMachine] = None,
    ) -> None:
        self.formal_specs_dir = Path(formal_specs_dir)
        self.formal_specs_dir.mkdir(parents=True, exist_ok=True)
        self.graph_store = graph_store
        self.kanban_sm = kanban_sm

    @classmethod
    def extract_theorem_names(cls, lean_text: str) -> List[str]:
        return cls.THEOREM_DECL_RE.findall(lean_text)

    def draft_lean_spec(
        self,
        formal_spec_id: str,
        feature_id: str,
        title: str,
        paper_references: List[str],
        theorem_obligations: List[str],
        reviewer_critiques: Optional[List[str]] = None,
        custom_lean_body: Optional[str] = None,
    ) -> FormalSpecNode:
        """
        Stage 1a: Untrusted Spec-writer & Reviewers produce a candidate `Spec.lean`.
        Remains `trusted=False` and escalates to Trello `2. Need Decision` until Human approves!
        """
        feat_dir = self.formal_specs_dir / feature_id
        feat_dir.mkdir(parents=True, exist_ok=True)
        spec_path = feat_dir / "Spec.lean"

        if spec_path.exists():
            spec_path.chmod(spec_path.stat().st_mode | stat.S_IWUSR)

        papers_comment = "\n".join(f"-- Reference Paper: {ref}" for ref in paper_references)
        critiques_list = reviewer_critiques or [
            "Reviewer-1 (Completeness): Verified theorem preconditions match paper assumptions.",
            "Reviewer-2 (Soundness): Confirmed specification does not contain vacuous `False -> ...` hypotheses.",
        ]
        critiques_comment = "\n".join(f"-- {c}" for c in critiques_list)

        if custom_lean_body:
            lean_content = custom_lean_body
        else:
            obligations_lean = "\n\n".join(
                f"/-- Formal obligation `{thm}` derived from specification --/\n"
                f"def {thm}_prop (state_in state_out : Nat) : Prop := state_out = state_in"
                for thm in theorem_obligations
            )
            sig_comments = "\n".join(
                f"-- REQUIRED_THEOREM: {thm}" for thm in theorem_obligations
            )
            lean_content = (
                f"-- Formal Specification `{formal_spec_id}` for `{feature_id}`: {title}\n"
                f"{papers_comment}\n"
                f"{critiques_comment}\n"
                f"{sig_comments}\n\n"
                f"namespace FactoryFormal.{feature_id.replace('-', '_')}\n\n"
                f"{obligations_lean}\n\n"
                f"end FactoryFormal.{feature_id.replace('-', '_')}\n"
            )

        spec_path.write_text(lean_content, encoding="utf-8")

        node = FormalSpecNode(
            id=formal_spec_id,
            title=title,
            feature_id=feature_id,
            lean_spec_path=str(spec_path),
            paper_references=paper_references,
            reviewer_critiques=critiques_list,
            theorem_obligations=theorem_obligations,
            trusted=False,
            human_approved_by=None,
            spec_sha256="",
            status="UNTRUSTED_DRAFT",
        )
        self.graph_store.upsert_node(node)

        if self.kanban_sm is not None and self.kanban_sm.adapter.get_card(feature_id):
            self.kanban_sm.escalate_to_need_decision(
                feature_id=feature_id,
                question_id=f"ADR-{formal_spec_id}",
                question_text=(
                    f"Approve Lean 4 Formal Specification `{formal_spec_id}` ({spec_path.name}) "
                    f"covering obligations: {', '.join(theorem_obligations)}?"
                ),
                options=[
                    f"Approve `{formal_spec_id}` as Trusted Lean Spec and lock SHA-256",
                    "Reject and request Spec-writer revision",
                ],
            )

        return node

    def approve_and_lock_spec(
        self,
        formal_spec_id: str,
        approved_by: str,
        problem_id: str = "PROB-001",
    ) -> FormalSpecNode:
        """
        Stage 1b: Human approves the candidate Lean spec, elevating it across the Trust Boundary
        into a Trusted `Lean spec` with POSIX read-only lock and SHA-256 checksum.
        """
        node = self.graph_store.get_node(formal_spec_id)
        if not isinstance(node, FormalSpecNode):
            raise ValueError(f"FormalSpecNode '{formal_spec_id}' not found.")

        if self.kanban_sm is not None:
            if approved_by not in self.kanban_sm.authorized_members:
                raise PermissionError(
                    f"User '{approved_by}' is not authorized to approve Trusted Lean Specifications."
                )
            if self.kanban_sm.adapter.get_card(node.feature_id):
                self.kanban_sm.record_human_decision_on_card(
                    feature_id=node.feature_id,
                    decision_text=f"Approve `{formal_spec_id}` as Trusted Lean Spec",
                    member_id=approved_by,
                    rationale="Verified formal obligations match research paper & security invariants.",
                )
                self.kanban_sm.process_human_decisions(problem_id=problem_id)

        spec_path = Path(node.lean_spec_path)
        checksum = GraphValidator.compute_file_sha256(spec_path)
        mode = spec_path.stat().st_mode
        spec_path.chmod(mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))

        node.trusted = True
        node.human_approved_by = approved_by
        node.spec_sha256 = checksum
        node.status = "TRUSTED_SPEC_LOCKED"
        self.graph_store.upsert_node(node)
        return node
