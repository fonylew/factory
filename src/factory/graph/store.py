"""SQLite WAL + NetworkX Traceability Graph Store with JSON-LD & Mermaid Export."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Type
import networkx as nx

from factory.graph.models import (
    BaseGraphNode,
    CodeArtifactNode,
    DecisionNode,
    EdgeType,
    FeatureNode,
    GraphEdge,
    IssueNode,
    IssueStatus,
    NodeType,
    ProblemNode,
    SystemSpecNode,
    TaskJournalNode,
)

NODE_MODEL_MAP: Dict[NodeType, Type[BaseGraphNode]] = {
    NodeType.PROBLEM: ProblemNode,
    NodeType.DECISION: DecisionNode,
    NodeType.SYSTEM_SPEC: SystemSpecNode,
    NodeType.FEATURE: FeatureNode,
    NodeType.CODE_ARTIFACT: CodeArtifactNode,
    NodeType.ISSUE: IssueNode,
    NodeType.TASK_JOURNAL: TaskJournalNode,
}


class TraceabilityGraphStore:
    """ACID-compliant local SQLite + NetworkX graph repository."""

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self.db_path = str(db_path)
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self._conn:
            self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.execute("PRAGMA foreign_keys=ON;")
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS graph_nodes (
                    id TEXT PRIMARY KEY,
                    node_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS graph_edges (
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    edge_type TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    PRIMARY KEY (source_id, target_id, edge_type)
                );
                """
            )

    def upsert_node(self, node: BaseGraphNode, auto_link: bool = True) -> BaseGraphNode:
        payload = node.model_dump(mode="json")
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO graph_nodes (id, node_type, title, status, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    node_type = excluded.node_type,
                    title = excluded.title,
                    status = excluded.status,
                    payload_json = excluded.payload_json;
                """,
                (
                    node.id,
                    node.node_type.value,
                    node.title,
                    node.status,
                    json.dumps(payload, sort_keys=True),
                    node.created_at,
                ),
            )
        if auto_link:
            self._auto_create_edges(node)
        return node

    def _auto_create_edges(self, node: BaseGraphNode) -> None:
        if isinstance(node, SystemSpecNode) and node.problem_id:
            if self.get_node(node.problem_id):
                self.add_edge(node.problem_id, node.id, EdgeType.SOLVED_BY)
        elif isinstance(node, DecisionNode) and node.problem_id:
            if self.get_node(node.problem_id):
                self.add_edge(node.problem_id, node.id, EdgeType.GOVERNED_BY)
        elif isinstance(node, FeatureNode) and node.spec_id:
            if self.get_node(node.spec_id):
                self.add_edge(node.spec_id, node.id, EdgeType.SPECIFIED_BY)
        elif isinstance(node, CodeArtifactNode) and node.feature_id:
            if self.get_node(node.feature_id):
                self.add_edge(node.feature_id, node.id, EdgeType.IMPLEMENTED_BY)
        elif isinstance(node, IssueNode):
            if node.affected_feature_id and self.get_node(node.affected_feature_id):
                self.add_edge(node.id, node.affected_feature_id, EdgeType.AFFECTS_FEATURE)
            if node.detected_in_code_id and self.get_node(node.detected_in_code_id):
                self.add_edge(node.id, node.detected_in_code_id, EdgeType.DETECTED_IN)
        elif isinstance(node, TaskJournalNode) and node.problem_id:
            if self.get_node(node.problem_id):
                self.add_edge(node.problem_id, node.id, EdgeType.LOGGED_IN)

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: EdgeType,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> GraphEdge:
        edge = GraphEdge(
            source_id=source_id,
            target_id=target_id,
            edge_type=edge_type,
            metadata=metadata or {},
        )
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO graph_edges (source_id, target_id, edge_type, metadata_json)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(source_id, target_id, edge_type) DO UPDATE SET
                    metadata_json = excluded.metadata_json;
                """,
                (
                    edge.source_id,
                    edge.target_id,
                    edge.edge_type.value,
                    json.dumps(edge.metadata, sort_keys=True),
                ),
            )
        return edge

    def get_node(self, node_id: str) -> Optional[BaseGraphNode]:
        cur = self._conn.execute(
            "SELECT node_type, payload_json FROM graph_nodes WHERE id = ?;",
            (node_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        node_type = NodeType(row["node_type"])
        model_cls = NODE_MODEL_MAP.get(node_type, BaseGraphNode)
        return model_cls.model_validate_json(row["payload_json"])

    def list_nodes(self, node_type: Optional[NodeType] = None) -> List[BaseGraphNode]:
        if node_type:
            cur = self._conn.execute(
                "SELECT node_type, payload_json FROM graph_nodes WHERE node_type = ? ORDER BY id ASC;",
                (node_type.value,),
            )
        else:
            cur = self._conn.execute(
                "SELECT node_type, payload_json FROM graph_nodes ORDER BY id ASC;"
            )
        nodes: List[BaseGraphNode] = []
        for row in cur.fetchall():
            nt = NodeType(row["node_type"])
            model_cls = NODE_MODEL_MAP.get(nt, BaseGraphNode)
            nodes.append(model_cls.model_validate_json(row["payload_json"]))
        return nodes

    def list_edges(self) -> List[GraphEdge]:
        cur = self._conn.execute(
            "SELECT source_id, target_id, edge_type, metadata_json FROM graph_edges ORDER BY source_id, target_id, edge_type;"
        )
        return [
            GraphEdge(
                source_id=row["source_id"],
                target_id=row["target_id"],
                edge_type=EdgeType(row["edge_type"]),
                metadata=json.loads(row["metadata_json"]),
            )
            for row in cur.fetchall()
        ]

    def to_networkx(self) -> nx.DiGraph:
        g = nx.DiGraph()
        for node in self.list_nodes():
            g.add_node(node.id, **node.model_dump(mode="json"))
        for edge in self.list_edges():
            g.add_edge(
                edge.source_id,
                edge.target_id,
                edge_type=edge.edge_type.value,
                **edge.metadata,
            )
        return g

    def get_open_issues(self, feature_id: Optional[str] = None) -> List[IssueNode]:
        issues = [
            n
            for n in self.list_nodes(NodeType.ISSUE)
            if isinstance(n, IssueNode) and n.status == IssueStatus.OPEN.value
        ]
        if feature_id is None:
            return issues
        g = self.to_networkx()
        result: List[IssueNode] = []
        for iss in issues:
            if iss.affected_feature_id == feature_id or g.has_edge(iss.id, feature_id):
                result.append(iss)
        return result

    def compute_impact_blast_radius(self, start_node_id: str) -> List[str]:
        """Returns sorted list of all downstream nodes reachable from start_node_id."""
        g = self.to_networkx()
        if start_node_id not in g:
            return []
        descendants: Set[str] = nx.descendants(g, start_node_id)
        return sorted(descendants)

    def export_json_ld(self, output_path: Optional[Path] = None) -> Dict[str, Any]:
        nodes = [n.model_dump(mode="json") for n in self.list_nodes()]
        edges = [e.model_dump(mode="json") for e in self.list_edges()]
        doc: Dict[str, Any] = {
            "@context": {
                "@vocab": "https://antigravity.google/schemas/software-factory/v1#",
                "nodes": "@graph",
            },
            "nodes": nodes,
            "edges": edges,
        }
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
        return doc

    def export_mermaid(self, output_path: Optional[Path] = None) -> str:
        lines = ["flowchart TD"]
        for node in self.list_nodes():
            safe_title = node.title.replace('"', "'")
            label = f'{node.id}["{node.id}: {safe_title} ({node.node_type.value})"]'
            lines.append(f"    {label}")
        for edge in self.list_edges():
            lines.append(
                f'    {edge.source_id} -->|"{edge.edge_type.value}"| {edge.target_id}'
            )
        content = "\n".join(lines) + "\n"
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(content, encoding="utf-8")
        return content

    def close(self) -> None:
        self._conn.close()
