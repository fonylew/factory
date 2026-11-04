"""Dual-Track Issue Tracker syncing IssueNodes to the Traceability Graph, Trello, and PRs."""

from __future__ import annotations

from typing import List, Optional

from factory.analyzer.security_scanner import ScanFinding
from factory.git_ops.pr_manager import PullRequestManager
from factory.graph.models import IssueNode, IssueSeverity
from factory.graph.store import TraceabilityGraphStore
from factory.kanban.state_machine import KanbanStateMachine


class DualTrackIssueTracker:
    """Persists security and production findings in both the Graph DB and Kanban/PR systems."""

    def __init__(
        self,
        graph_store: TraceabilityGraphStore,
        kanban_sm: Optional[KanbanStateMachine] = None,
        pr_manager: Optional[PullRequestManager] = None,
    ) -> None:
        self.graph_store = graph_store
        self.kanban_sm = kanban_sm
        self.pr_manager = pr_manager
        self._counter = 0

    def record_findings_for_feature(
        self,
        feature_id: str,
        findings: List[ScanFinding],
        code_artifact_id: Optional[str] = None,
    ) -> List[IssueNode]:
        emitted_nodes: List[IssueNode] = []
        pr_comments: List[str] = []
        blocking = False

        for finding in findings:
            self._counter += 1
            issue_id = f"ISS-{feature_id}-{finding.rule_id}-{self._counter}"
            issue_node = IssueNode(
                id=issue_id,
                title=finding.title,
                severity=finding.severity,
                category=finding.category,
                rule_id=finding.rule_id,
                description=finding.description,
                remediation=finding.remediation,
                affected_feature_id=feature_id,
                detected_in_code_id=code_artifact_id,
            )
            self.graph_store.upsert_node(issue_node)

            if self.kanban_sm is not None:
                card = self.kanban_sm.create_issue_card(issue_node)
                issue_node.trello_card_id = card.card_id
                self.graph_store.upsert_node(issue_node)

            emitted_nodes.append(issue_node)
            pr_comments.append(
                f"[{finding.severity.value}] [{finding.category.value}] {finding.rule_id}: "
                f"{finding.description} | Remediation: {finding.remediation}"
            )
            if finding.severity in (IssueSeverity.CRITICAL, IssueSeverity.HIGH):
                blocking = True

        if self.pr_manager is not None:
            status = "CHANGES_REQUESTED" if blocking else "APPROVED"
            if not pr_comments:
                pr_comments.append(
                    "All STRIDE security checks, production readiness gates, and Gherkin specs passed."
                )
            self.pr_manager.record_review(
                feature_id=feature_id,
                status=status,
                comments=pr_comments,
            )

        return emitted_nodes
