"""Graph Validator for Problem-Anchor Integrity, Spec Locks, and Orphan Detection."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import List
import networkx as nx

from factory.graph.models import (
    CodeArtifactNode,
    FeatureNode,
    NodeType,
    ProblemNode,
)
from factory.graph.store import TraceabilityGraphStore


class GraphValidationError(Exception):
    """Raised when a Traceability Graph invariant is violated."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message


class GraphValidator:
    """Enforces that no Spec, Feature, or Code Artifact loses track of the root Problem."""

    def __init__(self, store: TraceabilityGraphStore) -> None:
        self.store = store

    def is_anchored_to_problem(self, node_id: str) -> bool:
        """Checks whether there is a directed path from any ACTIVE ProblemNode to node_id."""
        g = self.store.to_networkx()
        if node_id not in g:
            return False
        problems = [
            n
            for n in self.store.list_nodes(NodeType.PROBLEM)
            if isinstance(n, ProblemNode) and n.status == "ACTIVE"
        ]
        for prob in problems:
            if prob.id == node_id:
                return True
            if prob.id in g and nx.has_path(g, prob.id, node_id):
                return True
        return False

    def validate_feature_registration(self, feature: FeatureNode) -> None:
        """Ensures a FeatureNode is anchored to an active ProblemNode before locking/dev."""
        self.store.upsert_node(feature)
        if not self.is_anchored_to_problem(feature.id):
            raise GraphValidationError(
                "ORPHAN_FEATURE_ERROR",
                f"Feature '{feature.id}' has no valid traceability path to an ACTIVE ProblemNode.",
            )

    def validate_code_artifact(self, artifact: CodeArtifactNode) -> None:
        """Ensures a CodeArtifactNode links to a FeatureNode anchored to a ProblemNode."""
        self.store.upsert_node(artifact)
        if not self.is_anchored_to_problem(artifact.id):
            raise GraphValidationError(
                "ORPHAN_CODE_ERROR",
                f"Code artifact '{artifact.id}' is not anchored to any ACTIVE ProblemNode.",
            )

    def find_all_orphans(self) -> List[str]:
        """Returns IDs of all SystemSpecNodes, FeatureNodes, or CodeArtifactNodes lacking a Problem anchor."""
        orphans: List[str] = []
        for node in self.store.list_nodes():
            if node.node_type in (
                NodeType.SYSTEM_SPEC,
                NodeType.FEATURE,
                NodeType.CODE_ARTIFACT,
            ):
                if not self.is_anchored_to_problem(node.id):
                    orphans.append(node.id)
        return sorted(orphans)

    @staticmethod
    def compute_file_sha256(file_path: Path) -> str:
        hasher = hashlib.sha256()
        with open(file_path, "rb") as fh:
            for chunk in iter(lambda: fh.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def lock_feature_spec(self, feature_id: str, feature_file_path: Path) -> FeatureNode:
        """Computes SHA-256 of the Gherkin .feature file, verifies Problem anchor, and locks it."""
        node = self.store.get_node(feature_id)
        if not isinstance(node, FeatureNode):
            raise GraphValidationError(
                "FEATURE_NOT_FOUND",
                f"FeatureNode '{feature_id}' does not exist in the graph.",
            )
        if not feature_file_path.exists():
            raise GraphValidationError(
                "MISSING_FEATURE_FILE",
                f"Gherkin file '{feature_file_path}' does not exist.",
            )
        self.validate_feature_registration(node)
        checksum = self.compute_file_sha256(feature_file_path)
        node.feature_file_path = str(feature_file_path)
        node.spec_checksum = checksum
        node.status = "READY_FOR_DEV"
        self.store.upsert_node(node)
        return node
