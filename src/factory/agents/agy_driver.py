"""`agy` (Gemini 4 Argon) Driver for Planning, System Analysis, and Security/PR Reviews."""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field

from factory.analyzer.issue_tracker import DualTrackIssueTracker
from factory.analyzer.security_scanner import EnterpriseSecurityAndProdAnalyzer, ScanFinding
from factory.graph.models import IssueNode
from factory.graph.validator import GraphValidator
from factory.journal.task_ledger import TaskLedgerManager


class AgyReviewReport(BaseModel):
    feature_id: str
    model: str = "gemini-4-argon"
    anchored_to_problem: bool
    review_status: str  # APPROVED or CHANGES_REQUESTED
    findings: List[ScanFinding] = Field(default_factory=list)
    emitted_issue_ids: List[str] = Field(default_factory=list)


class AgyReviewDriver:
    """Orchestrates `agy` (Gemini 4 Argon) enterprise security, spec drift, and production reviews."""

    def __init__(
        self,
        validator: GraphValidator,
        analyzer: EnterpriseSecurityAndProdAnalyzer,
        issue_tracker: DualTrackIssueTracker,
        model: str = "gemini-4-argon",
        task_ledger: Optional[TaskLedgerManager] = None,
    ) -> None:
        self.validator = validator
        self.analyzer = analyzer
        self.issue_tracker = issue_tracker
        self.model = model
        self.task_ledger = task_ledger

    def review_feature_code(
        self,
        feature_id: str,
        code_text: str,
        file_path: str = "src/feature_impl.py",
        task_id: Optional[str] = None,
    ) -> AgyReviewReport:
        anchored = self.validator.is_anchored_to_problem(feature_id)
        findings = self.analyzer.analyze_code_text(code_text, file_path=file_path)

        emitted_nodes: List[IssueNode] = self.issue_tracker.record_findings_for_feature(
            feature_id=feature_id,
            findings=findings,
        )

        pr = (
            self.issue_tracker.pr_manager.get_pull_request(feature_id)
            if self.issue_tracker.pr_manager
            else None
        )
        review_status = pr.status if pr else ("CHANGES_REQUESTED" if findings else "APPROVED")
        if not anchored:
            review_status = "CHANGES_REQUESTED"

        if self.task_ledger and task_id:
            findings_md = (
                "\n".join(
                    f"  - `[{f.severity.value}] [{f.category.value}] {f.rule_id}`: {f.description}"
                    for f in findings
                )
                or "  - None (Zero security or production risks found)"
            )
            self.task_ledger.append_step_output(
                task_id=task_id,
                step_name="05-agy-security-pr-review",
                markdown_content=(
                    f"- **Reviewer**: `agy ({self.model})`\n"
                    f"- **Feature ID**: `{feature_id}`\n"
                    f"- **Anchored to Root Problem**: `{anchored}`\n"
                    f"- **Review Decision**: `{review_status}`\n"
                    f"- **Findings**:\n{findings_md}\n"
                ),
                actor=f"agy ({self.model})",
            )

        return AgyReviewReport(
            feature_id=feature_id,
            model=self.model,
            anchored_to_problem=anchored,
            review_status=review_status,
            findings=findings,
            emitted_issue_ids=[n.id for n in emitted_nodes],
        )
