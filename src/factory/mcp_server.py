"""FastMCP Server exposing the Software Factory Graph, Kanban, Task Ledger, and Security Auditor to `agy`."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
from mcp.server.fastmcp import FastMCP

from factory.analyzer.issue_tracker import DualTrackIssueTracker
from factory.analyzer.security_scanner import EnterpriseSecurityAndProdAnalyzer
from factory.agents.agy_driver import AgyReviewDriver
from factory.bootstrap import bootstrap_factory_graph
from factory.config import FactoryConfig
from factory.git_ops.pr_manager import PullRequestManager
from factory.graph.store import TraceabilityGraphStore
from factory.graph.validator import GraphValidator
from factory.journal.task_ledger import TaskLedgerManager
from factory.kanban.state_machine import KanbanStateMachine
from factory.kanban.trello_client import TrelloKanbanAdapter

mcp = FastMCP("agentic-software-factory")


def _load_runtime(repo_root: Optional[str] = None):
    root = Path(repo_root or ".").resolve()
    cfg = FactoryConfig.load(root / "factory.yaml")
    store = TraceabilityGraphStore(root / cfg.project.graph_db_path)
    kanban = TrelloKanbanAdapter(state_file=root / cfg.kanban.local_state_file)
    if not store.list_nodes():
        bootstrap_factory_graph(root, cfg, store, kanban)
    ledger = TaskLedgerManager(root / cfg.project.tasks_dir, graph_store=store)
    sm = KanbanStateMachine(
        adapter=kanban,
        graph_store=store,
        columns=cfg.kanban.columns,
        task_ledger=ledger,
    )
    return root, cfg, store, kanban, ledger, sm


@mcp.tool()
def factory_graph_status(repo_root: str = ".") -> Dict[str, Any]:
    """Returns Traceability Graph nodes, edges, orphans, and open security/production issues."""
    _, _, store, _, _, _ = _load_runtime(repo_root)
    validator = GraphValidator(store)
    return {
        "node_count": len(store.list_nodes()),
        "edge_count": len(store.list_edges()),
        "orphans": validator.find_all_orphans(),
        "open_issues": [i.model_dump(mode="json") for i in store.get_open_issues()],
    }


@mcp.tool()
def factory_impact_analysis(node_id: str, repo_root: str = ".") -> List[str]:
    """Computes the downstream blast radius if a ProblemNode or SystemSpecNode changes."""
    _, _, store, _, _, _ = _load_runtime(repo_root)
    return store.compute_impact_blast_radius(node_id)


@mcp.tool()
def factory_task_init(
    task_id: str,
    description: str,
    date_str: Optional[str] = None,
    problem_id: str = "PROB-001",
    repo_root: str = ".",
) -> str:
    """Initializes a new Task Ledger folder in `specs/tasks/<YYYY-MM-DD>_<TASK-ID>_<slug>/`."""
    _, _, _, _, ledger, _ = _load_runtime(repo_root)
    path = ledger.init_task_ledger(
        task_id=task_id,
        description=description,
        date_str=date_str,
        problem_id=problem_id,
    )
    return str(path)


@mcp.tool()
def factory_task_append_step(
    task_id: str,
    step_name: str,
    markdown_content: str,
    actor: str = "agy (Gemini 4 Argon)",
    repo_root: str = ".",
) -> str:
    """Appends a sanitized step markdown output (01-grill-me .. 05-review) to a Task Ledger."""
    _, _, _, _, ledger, _ = _load_runtime(repo_root)
    path = ledger.append_step_output(
        task_id=task_id,
        step_name=step_name,
        markdown_content=markdown_content,
        actor=actor,
    )
    return str(path)


@mcp.tool()
def factory_kanban_escalate_decision(
    feature_id: str,
    question_id: str,
    question_text: str,
    options: List[str],
    repo_root: str = ".",
) -> Dict[str, Any]:
    """Moves a feature card to '2. Need Decision' with formatted architectural options."""
    _, _, _, _, _, sm = _load_runtime(repo_root)
    card = sm.escalate_to_need_decision(
        feature_id=feature_id,
        question_id=question_id,
        question_text=question_text,
        options=options,
    )
    return card.model_dump(mode="json")


@mcp.tool()
def factory_kanban_process_human_decisions(
    problem_id: str = "PROB-001",
    task_id: Optional[str] = None,
    repo_root: str = ".",
) -> List[Dict[str, Any]]:
    """Reads '3. Human Decision' column, verifies member auth, logs ADRs, and moves cards to Ready for Dev."""
    _, _, _, _, _, sm = _load_runtime(repo_root)
    decisions = sm.process_human_decisions(problem_id=problem_id, task_id=task_id)
    return [d.model_dump(mode="json") for d in decisions]


@mcp.tool()
def factory_audit_code(
    feature_id: str,
    code_text: str,
    file_path: str = "src/feature_impl.py",
    task_id: Optional[str] = None,
    repo_root: str = ".",
) -> Dict[str, Any]:
    """Executes `agy` (Gemini 4 Argon) security & production readiness review and emits Dual-Track IssueNodes."""
    root, _, store, _, ledger, sm = _load_runtime(repo_root)
    validator = GraphValidator(store)
    analyzer = EnterpriseSecurityAndProdAnalyzer()
    pr_mgr = PullRequestManager(root / ".factory/pull_requests.json")
    tracker = DualTrackIssueTracker(store, kanban_sm=sm, pr_manager=pr_mgr)
    agy = AgyReviewDriver(
        validator=validator,
        analyzer=analyzer,
        issue_tracker=tracker,
        task_ledger=ledger,
    )
    report = agy.review_feature_code(
        feature_id=feature_id,
        code_text=code_text,
        file_path=file_path,
        task_id=task_id,
    )
    return report.model_dump(mode="json")


if __name__ == "__main__":
    mcp.run()
