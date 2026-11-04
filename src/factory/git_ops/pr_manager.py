"""Git Branch & Pull Request Manager for Agentic Review Workflows."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class PullRequestRecord(BaseModel):
    pr_number: int
    feature_id: str
    branch_name: str
    base_branch: str = "main"
    title: str
    body: str
    author_agent: str = "pi"
    reviewer_agent: str = "agy (Gemini 4 Argon)"
    status: str = "OPEN"  # OPEN, CHANGES_REQUESTED, APPROVED, MERGED
    review_comments: List[str] = Field(default_factory=list)


class PullRequestManager:
    """Tracks Pull Requests locally and optionally syncs with GitHub CLI (`gh pr`)."""

    def __init__(self, state_file: str | Path = ".factory/pull_requests.json") -> None:
        self.state_file = Path(state_file)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self._prs: Dict[str, PullRequestRecord] = {}
        self._load()

    def _load(self) -> None:
        if self.state_file.exists():
            raw = json.loads(self.state_file.read_text(encoding="utf-8"))
            self._prs = {
                fid: PullRequestRecord.model_validate(data) for fid, data in raw.items()
            }

    def _save(self) -> None:
        payload = {
            fid: pr.model_dump(mode="json") for fid, pr in sorted(self._prs.items())
        }
        self.state_file.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    def create_pull_request(
        self,
        feature_id: str,
        branch_name: str,
        title: str,
        body: str,
        base_branch: str = "main",
    ) -> PullRequestRecord:
        pr_num = len(self._prs) + 1
        existing = self._prs.get(feature_id)
        if existing:
            pr_num = existing.pr_number
        pr = PullRequestRecord(
            pr_number=pr_num,
            feature_id=feature_id,
            branch_name=branch_name,
            base_branch=base_branch,
            title=title,
            body=body,
            status="OPEN",
        )
        self._prs[feature_id] = pr
        self._save()
        return pr

    def get_pull_request(self, feature_id: str) -> Optional[PullRequestRecord]:
        return self._prs.get(feature_id)

    def record_review(
        self,
        feature_id: str,
        status: str,
        comments: List[str],
    ) -> PullRequestRecord:
        pr = self._prs.get(feature_id)
        if not pr:
            pr = self.create_pull_request(
                feature_id=feature_id,
                branch_name=f"feat/{feature_id}",
                title=f"[{feature_id}] Automated Agent PR",
                body="Submitted for agy security review.",
            )
        pr.status = status
        pr.review_comments.extend(comments)
        self._prs[feature_id] = pr
        self._save()
        return pr
