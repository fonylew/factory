"""Configuration & Security Policy Settings for the Software Factory."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional
import yaml
from pydantic import BaseModel, Field


class ProjectConfig(BaseModel):
    name: str = "agentic-software-factory"
    root_problem_id: str = "PROB-001"
    specs_dir: str = "specs"
    features_dir: str = "specs/features"
    tasks_dir: str = "specs/tasks"
    graph_db_path: str = ".factory/factory_graph.db"
    graph_json_export: str = "specs/graph/traceability.json"
    graph_mermaid_export: str = "specs/graph/traceability.mmd"


class KanbanColumnsConfig(BaseModel):
    backlog: str = "1. Problem & Spec Backlog"
    need_decision: str = "2. Need Decision"
    human_decision: str = "3. Human Decision"
    ready_for_dev: str = "4. Ready for Dev (Spec Locked)"
    in_progress: str = "5. In Progress (pi Coding)"
    pr_review: str = "6. PR & Security Review (agy)"
    done: str = "7. Done / Verified"
    issues: str = "Issues & Security Findings"


class KanbanConfig(BaseModel):
    provider: str = "trello"
    local_state_file: str = ".factory/local_kanban.json"
    columns: KanbanColumnsConfig = Field(default_factory=KanbanColumnsConfig)
    mandatory_card_sections: List[str] = Field(
        default_factory=lambda: [
            "## 1. Problem Context & Goal",
            "## 2. System Analysis & Enterprise Design",
            "## 3. Acceptance Criteria (Gherkin Reference)",
            "## 4. Open Questions / Need Decision",
            "## 5. Human Decision",
        ]
    )


class PlannerAgentConfig(BaseModel):
    engine: str = "agy"
    model: str = "gemini-4-argon"
    max_review_cycles: int = 3


class CoderAgentConfig(BaseModel):
    engine: str = "pi"
    binary: str = "/home/aimet/.local/bin/pi"
    worktree_base_dir: str = "worktrees"
    max_iterations_per_task: int = 3
    read_only_paths: List[str] = Field(default_factory=lambda: ["specs", "factory.yaml"])
    scrubbed_env_vars: List[str] = Field(
        default_factory=lambda: [
            "TRELLO_API_KEY",
            "TRELLO_TOKEN",
            "GITHUB_TOKEN",
            "GH_TOKEN",
            "gitlab_token",
            "AWS_SECRET_ACCESS_KEY",
            "GOOGLE_APPLICATION_CREDENTIALS",
        ]
    )


class AgentsConfig(BaseModel):
    planner_reviewer: PlannerAgentConfig = Field(default_factory=PlannerAgentConfig)
    coder: CoderAgentConfig = Field(default_factory=CoderAgentConfig)


class BDDAdapterSpec(BaseModel):
    command: str
    report_json: str = "reports/cucumber.json"


class BDDConfig(BaseModel):
    default_adapter: str = "pytest-bdd"
    adapters: Dict[str, BDDAdapterSpec] = Field(
        default_factory=lambda: {
            "pytest-bdd": BDDAdapterSpec(
                command="uv run pytest -q",
                report_json="reports/cucumber.json",
            )
        }
    )


class FactoryConfig(BaseModel):
    project: ProjectConfig = Field(default_factory=ProjectConfig)
    kanban: KanbanConfig = Field(default_factory=KanbanConfig)
    agents: AgentsConfig = Field(default_factory=AgentsConfig)
    bdd: BDDConfig = Field(default_factory=BDDConfig)

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "FactoryConfig":
        path = config_path or Path(os.environ.get("FACTORY_CONFIG", "factory.yaml"))
        if path.exists():
            with open(path, "r", encoding="utf-8") as fh:
                raw = yaml.safe_load(fh) or {}
            return cls.model_validate(raw)
        return cls()
