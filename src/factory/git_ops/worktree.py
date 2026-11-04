"""Isolated Git Worktree Manager, Read-Only Spec Lock, and SHA-256 Tamper Guard."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import subprocess
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from factory.graph.models import IssueCategory, IssueNode, IssueSeverity
from factory.graph.store import TraceabilityGraphStore


class SpecTamperError(Exception):
    """Raised when an untrusted coding agent (`pi`) modifies a locked spec or `.feature` file."""

    def __init__(self, code: str, tampered_files: List[str], message: str) -> None:
        super().__init__(f"[{code}] {message}: {', '.join(tampered_files)}")
        self.code = code
        self.tampered_files = tampered_files
        self.message = message


class WorktreeContext(BaseModel):
    feature_id: str
    branch_name: str
    worktree_path: str
    spec_checksums: Dict[str, str] = Field(default_factory=dict)
    sanitized_env: Dict[str, str] = Field(default_factory=dict)


class WorktreeManager:
    """Manages isolated Git worktrees (`worktrees/feat-XXX`) and read-only spec locks for `pi`."""

    DEFAULT_SCRUBBED_VARS = [
        "TRELLO_API_KEY",
        "TRELLO_TOKEN",
        "GITHUB_TOKEN",
        "GH_TOKEN",
        "GITLAB_TOKEN",
        "AWS_SECRET_ACCESS_KEY",
        "GOOGLE_APPLICATION_CREDENTIALS",
    ]

    def __init__(
        self,
        repo_root: Path,
        worktree_base_dir: Optional[Path] = None,
        read_only_rel_paths: Optional[List[str]] = None,
        scrubbed_env_vars: Optional[List[str]] = None,
        graph_store: Optional[TraceabilityGraphStore] = None,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.worktree_base_dir = (
            Path(worktree_base_dir).resolve()
            if worktree_base_dir
            else (self.repo_root / "worktrees")
        )
        self.read_only_rel_paths = read_only_rel_paths or ["specs"]
        self.scrubbed_env_vars = scrubbed_env_vars or self.DEFAULT_SCRUBBED_VARS
        self.graph_store = graph_store

    def build_sanitized_env(self, base_env: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Strips all sensitive tokens and ensures `/home/aimet/.local/bin` is in PATH for `pi` & `node`."""
        source_env = dict(base_env if base_env is not None else os.environ)
        scrubbed_upper = {k.upper() for k in self.scrubbed_env_vars}
        clean_env: Dict[str, str] = {}
        for k, v in source_env.items():
            if k.upper() in scrubbed_upper:
                continue
            if any(tok in k.upper() for tok in ("SECRET", "TOKEN", "API_KEY", "PASSWORD")):
                continue
            clean_env[k] = v

        local_bin = "/home/aimet/.local/bin"
        current_path = clean_env.get("PATH", "/usr/bin:/bin")
        if local_bin not in current_path:
            clean_env["PATH"] = f"{local_bin}:{current_path}"
        return clean_env

    @staticmethod
    def compute_directory_checksums(root_dir: Path, rel_paths: List[str]) -> Dict[str, str]:
        checksums: Dict[str, str] = {}
        for rel in rel_paths:
            target = root_dir / rel
            if not target.exists():
                continue
            if target.is_file():
                rel_key = str(target.relative_to(root_dir))
                checksums[rel_key] = WorktreeManager._sha256_file(target)
            elif target.is_dir():
                for file_path in sorted(target.rglob("*")):
                    if file_path.is_file():
                        rel_key = str(file_path.relative_to(root_dir))
                        checksums[rel_key] = WorktreeManager._sha256_file(file_path)
        return checksums

    @staticmethod
    def _sha256_file(path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def set_read_only_permissions(root_dir: Path, rel_paths: List[str], read_only: bool = True) -> None:
        for rel in rel_paths:
            target = root_dir / rel
            if not target.exists():
                continue
            paths_to_update: List[Path] = []
            if target.is_file():
                paths_to_update.append(target)
            else:
                for p in target.rglob("*"):
                    if p.is_file():
                        paths_to_update.append(p)
            for p in paths_to_update:
                mode = p.stat().st_mode
                if read_only:
                    p.chmod(mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
                else:
                    p.chmod(mode | stat.S_IWUSR)

    def create_isolated_worktree(
        self,
        feature_id: str,
        base_env: Optional[Dict[str, str]] = None,
    ) -> WorktreeContext:
        self.worktree_base_dir.mkdir(parents=True, exist_ok=True)
        branch_name = f"feat/{feature_id}"
        wt_path = self.worktree_base_dir / f"feat-{feature_id}"

        if wt_path.exists():
            self.cleanup_worktree(feature_id)

        subprocess.run(
            ["git", "worktree", "add", "-B", branch_name, str(wt_path), "HEAD"],
            cwd=str(self.repo_root),
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        )

        checksums = self.compute_directory_checksums(wt_path, self.read_only_rel_paths)
        self.set_read_only_permissions(wt_path, self.read_only_rel_paths, read_only=True)
        clean_env = self.build_sanitized_env(base_env=base_env)

        return WorktreeContext(
            feature_id=feature_id,
            branch_name=branch_name,
            worktree_path=str(wt_path),
            spec_checksums=checksums,
            sanitized_env=clean_env,
        )

    def verify_no_spec_tampering(self, context: WorktreeContext) -> None:
        wt_path = Path(context.worktree_path)
        current_checksums = self.compute_directory_checksums(
            wt_path, self.read_only_rel_paths
        )
        tampered: List[str] = []
        for rel_file, original_hash in context.spec_checksums.items():
            new_hash = current_checksums.get(rel_file)
            if new_hash != original_hash:
                tampered.append(rel_file)
        for rel_file in current_checksums:
            if rel_file not in context.spec_checksums:
                tampered.append(rel_file)

        if tampered:
            if self.graph_store is not None:
                issue = IssueNode(
                    id=f"ISS-TAMPER-{context.feature_id}",
                    title=f"SPEC_TAMPERING_DETECTED in {context.feature_id}",
                    severity=IssueSeverity.CRITICAL,
                    category=IssueCategory.SECURITY,
                    rule_id="INV-02-SPEC-TAMPER-GUARD",
                    description=(
                        f"SPEC_TAMPERING_DETECTED: Untrusted agent modified locked specification files: "
                        f"{', '.join(sorted(tampered))}"
                    ),
                    remediation="Reset worktree, reject Pull Request, and inspect agent prompt/logs.",
                    affected_feature_id=context.feature_id,
                )
                self.graph_store.upsert_node(issue)
            raise SpecTamperError(
                "SPEC_TAMPERING_DETECTED",
                sorted(tampered),
                "Specification or Gherkin feature files were modified inside isolated worktree",
            )

    def cleanup_worktree(self, feature_id: str) -> None:
        wt_path = self.worktree_base_dir / f"feat-{feature_id}"
        if wt_path.exists():
            self.set_read_only_permissions(wt_path, self.read_only_rel_paths, read_only=False)
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(wt_path)],
                cwd=str(self.repo_root),
                check=False,
                capture_output=True,
                text=True,
                timeout=15,
            )
