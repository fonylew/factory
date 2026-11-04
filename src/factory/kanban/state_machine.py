"""7-Column Trello Kanban State Machine & Human Decision Processor."""

from __future__ import annotations

import hashlib
from typing import List, Optional, Set

from factory.config import KanbanColumnsConfig
from factory.graph.models import DecisionNode, IssueNode
from factory.graph.store import TraceabilityGraphStore
from factory.journal.task_ledger import TaskLedgerManager
from factory.kanban.card_parser import CardParser, CardValidationError
from factory.kanban.trello_client import KanbanCard, LocalKanbanAdapter


class KanbanTransitionError(Exception):
    """Raised when an invalid or unauthorized Kanban state transition is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message


class KanbanStateMachine:
    """Orchestrates card transitions across the 7 Kanban columns with idempotency & HITL checks."""

    def __init__(
        self,
        adapter: LocalKanbanAdapter,
        graph_store: TraceabilityGraphStore,
        columns: Optional[KanbanColumnsConfig] = None,
        authorized_members: Optional[Set[str]] = None,
        task_ledger: Optional[TaskLedgerManager] = None,
    ) -> None:
        self.adapter = adapter
        self.graph_store = graph_store
        self.columns = columns or KanbanColumnsConfig()
        self.parser = CardParser()
        self.authorized_members = authorized_members or {"tech_lead_01", "system_analyst_01", "aimet"}
        self.task_ledger = task_ledger
        self._processed_idempotency_keys: Set[str] = set()

    @staticmethod
    def compute_transition_key(feature_id: str, target_column: str, desc_hash: str) -> str:
        raw = f"{feature_id}:{target_column}:{desc_hash}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def transition_card(
        self,
        feature_id: str,
        target_column: str,
        actor: str = "system",
    ) -> KanbanCard:
        card = self.adapter.get_card(feature_id)
        if not card:
            raise KanbanTransitionError("CARD_NOT_FOUND", f"Card '{feature_id}' does not exist.")

        # Validate mandatory System Analysis, Design, and Acceptance Criteria before Ready for Dev
        if target_column in (
            self.columns.ready_for_dev,
            self.columns.in_progress,
            self.columns.pr_review,
            self.columns.done,
        ):
            try:
                self.parser.assert_ready_for_dev(card.description)
            except CardValidationError as exc:
                self.adapter.add_comment(
                    feature_id,
                    f"Blocked transition to '{target_column}': {exc.message} ({', '.join(exc.missing_sections)})",
                )
                raise KanbanTransitionError(exc.code, str(exc)) from exc

        desc_hash = hashlib.sha256(card.description.encode("utf-8")).hexdigest()
        idem_key = self.compute_transition_key(feature_id, target_column, desc_hash)
        if idem_key in self._processed_idempotency_keys and card.column == target_column:
            return card

        card.column = target_column
        card.last_modified_by = actor
        self.adapter.upsert_card(card)
        self._processed_idempotency_keys.add(idem_key)
        return card

    def escalate_to_need_decision(
        self,
        feature_id: str,
        question_id: str,
        question_text: str,
        options: List[str],
    ) -> KanbanCard:
        card = self.adapter.get_card(feature_id)
        if not card:
            raise KanbanTransitionError("CARD_NOT_FOUND", f"Card '{feature_id}' does not exist.")

        card.description = CardParser.inject_open_question(
            card.description,
            question_id=question_id,
            question_text=question_text,
            options=options,
        )
        card.column = self.columns.need_decision
        card.last_modified_by = "agy"
        self.adapter.upsert_card(card)
        return card

    def record_human_decision_on_card(
        self,
        feature_id: str,
        decision_text: str,
        member_id: str,
        rationale: str = "",
    ) -> KanbanCard:
        """Simulates or applies a Tech Lead writing their decision & moving the card to '3. Human Decision'."""
        card = self.adapter.get_card(feature_id)
        if not card:
            raise KanbanTransitionError("CARD_NOT_FOUND", f"Card '{feature_id}' does not exist.")
        card.description = CardParser.update_human_decision_section(
            card.description,
            decision_text=decision_text,
            rationale=rationale,
        )
        card.column = self.columns.human_decision
        card.last_modified_by = member_id
        self.adapter.upsert_card(card)
        return card

    def process_human_decisions(self, problem_id: str = "PROB-001", task_id: Optional[str] = None) -> List[DecisionNode]:
        """Polls the '3. Human Decision' column, validates member auth, records ADR DecisionNodes, and unlocks Dev."""
        cards_in_decision = self.adapter.list_cards(column=self.columns.human_decision)
        recorded_decisions: List[DecisionNode] = []

        for card in cards_in_decision:
            if card.last_modified_by not in self.authorized_members:
                self.adapter.add_comment(
                    card.feature_id,
                    f"SECURITY BLOCK: Unauthorized member '{card.last_modified_by}' attempted to approve Human Decision.",
                )
                raise KanbanTransitionError(
                    "UNAUTHORIZED_DECISION_AUTHOR",
                    f"Member '{card.last_modified_by}' is not in authorized_members allowlist.",
                )

            parsed = CardParser.parse_human_decision(
                card.description, decided_by=card.last_modified_by
            )
            if not parsed:
                self.adapter.add_comment(
                    card.feature_id,
                    "Human Decision column requires a non-empty '**Decision**:' entry in '## 5. Human Decision'.",
                )
                continue

            adr_node = DecisionNode(
                id=parsed.question_id,
                title=f"Decision {parsed.question_id} for {card.feature_id}",
                problem_id=problem_id,
                question=f"Architectural decision for {card.feature_id}",
                chosen_option=parsed.decision_text,
                rationale=parsed.rationale,
                decided_by=parsed.decided_by,
                trello_card_id=card.card_id,
                metadata={"wrapped_safe_input": parsed.wrapped_safe_input},
            )
            self.graph_store.upsert_node(adr_node)
            recorded_decisions.append(adr_node)

            if self.task_ledger and task_id:
                self.task_ledger.append_step_output(
                    task_id=task_id,
                    step_name="03-human-decisions-adr",
                    markdown_content=(
                        f"### `{adr_node.id}` ({card.feature_id})\n"
                        f"- **Decided By**: `{parsed.decided_by}`\n"
                        f"- **Decision**: {parsed.decision_text}\n"
                        f"- **Rationale**: {parsed.rationale}\n"
                    ),
                    actor=parsed.decided_by,
                )

            # Transition card to Ready for Dev (Spec Locked)
            self.transition_card(
                card.feature_id,
                target_column=self.columns.ready_for_dev,
                actor="agy",
            )

        return recorded_decisions

    def create_issue_card(self, issue: IssueNode) -> KanbanCard:
        """Creates a dual-tracked Issue card in the 'Issues & Security Findings' column."""
        issue_card = KanbanCard(
            card_id=f"CARD-{issue.id}",
            feature_id=issue.id,
            title=f"[{issue.severity.value}] [{issue.category.value}] {issue.title}",
            description=(
                f"# Issue `{issue.id}`: {issue.title}\n"
                f"- **Severity**: `{issue.severity.value}`\n"
                f"- **Category**: `{issue.category.value}`\n"
                f"- **Rule**: `{issue.rule_id}`\n"
                f"- **Affected Feature**: `{issue.affected_feature_id or 'N/A'}`\n\n"
                f"## Description\n{issue.description}\n\n"
                f"## Remediation\n{issue.remediation}\n"
            ),
            column=self.columns.issues,
            labels=[issue.category.value, issue.severity.value],
            last_modified_by="agy",
        )
        return self.adapter.upsert_card(issue_card)
