"""Domain models for the Enterprise Traceability & Knowledge Graph."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class NodeType(str, Enum):
    PROBLEM = "ProblemNode"
    DECISION = "DecisionNode"
    SYSTEM_SPEC = "SystemSpecNode"
    FEATURE = "FeatureNode"
    CODE_ARTIFACT = "CodeArtifactNode"
    ISSUE = "IssueNode"
    TASK_JOURNAL = "TaskJournalNode"


class EdgeType(str, Enum):
    SOLVED_BY = "SOLVED_BY"                # ProblemNode -> SystemSpecNode
    GOVERNED_BY = "GOVERNED_BY"            # ProblemNode -> DecisionNode
    MODIFIES_SPEC = "MODIFIES_SPEC"        # DecisionNode -> SystemSpecNode
    SPECIFIED_BY = "SPECIFIED_BY"          # SystemSpecNode -> FeatureNode
    IMPLEMENTED_BY = "IMPLEMENTED_BY"      # FeatureNode -> CodeArtifactNode
    DEPENDS_ON = "DEPENDS_ON"              # FeatureNode -> FeatureNode
    LOGGED_IN = "LOGGED_IN"                # FeatureNode / ProblemNode -> TaskJournalNode
    AFFECTS_FEATURE = "AFFECTS_FEATURE"    # IssueNode -> FeatureNode
    DETECTED_IN = "DETECTED_IN"            # IssueNode -> CodeArtifactNode
    VIOLATES_INVARIANT = "VIOLATES_INVARIANT"  # IssueNode -> SystemSpecNode / ProblemNode


class IssueSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class IssueCategory(str, Enum):
    SECURITY = "SECURITY"
    PROD_RISK = "PROD_RISK"
    BUG = "BUG"
    DRIFT = "DRIFT"


class IssueStatus(str, Enum):
    OPEN = "OPEN"
    MITIGATED = "MITIGATED"
    ACCEPTED_RISK = "ACCEPTED_RISK"


class BaseGraphNode(BaseModel):
    id: str
    node_type: NodeType
    title: str
    status: str = "ACTIVE"
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ProblemNode(BaseGraphNode):
    node_type: NodeType = NodeType.PROBLEM
    statement: str = ""
    business_impact: str = ""
    invariants: List[str] = Field(default_factory=list)


class DecisionNode(BaseGraphNode):
    node_type: NodeType = NodeType.DECISION
    problem_id: str
    question: str
    options: List[str] = Field(default_factory=list)
    chosen_option: str = ""
    rationale: str = ""
    decided_by: str = ""
    trello_card_id: Optional[str] = None


class SystemSpecNode(BaseGraphNode):
    node_type: NodeType = NodeType.SYSTEM_SPEC
    problem_id: Optional[str] = None
    component: str = "core"
    architecture_md: str = ""
    nfrs: List[str] = Field(default_factory=list)
    security_constraints: List[str] = Field(default_factory=list)
    version_hash: str = ""


class FeatureNode(BaseGraphNode):
    node_type: NodeType = NodeType.FEATURE
    spec_id: Optional[str] = None
    feature_file_path: str = ""
    scenarios: List[str] = Field(default_factory=list)
    spec_checksum: str = ""
    trello_card_id: Optional[str] = None
    status: str = "BACKLOG"


class CodeArtifactNode(BaseGraphNode):
    node_type: NodeType = NodeType.CODE_ARTIFACT
    feature_id: str
    file_path: str
    symbol_name: str = ""
    git_branch: str = ""
    commit_sha: str = ""
    pr_number: Optional[int] = None


class IssueNode(BaseGraphNode):
    node_type: NodeType = NodeType.ISSUE
    severity: IssueSeverity = IssueSeverity.HIGH
    category: IssueCategory = IssueCategory.SECURITY
    rule_id: str = ""
    description: str = ""
    remediation: str = ""
    affected_feature_id: Optional[str] = None
    detected_in_code_id: Optional[str] = None
    trello_card_id: Optional[str] = None
    status: str = IssueStatus.OPEN.value


class TaskJournalNode(BaseGraphNode):
    node_type: NodeType = NodeType.TASK_JOURNAL
    task_id: str
    date: str
    description: str
    journal_dir: str
    problem_id: Optional[str] = None
    steps_completed: List[str] = Field(default_factory=list)
    trello_card_id: Optional[str] = None


class GraphEdge(BaseModel):
    source_id: str
    target_id: str
    edge_type: EdgeType
    metadata: Dict[str, Any] = Field(default_factory=dict)
