"""CLI Entrypoint (`factory`) for Technical Leads, System Analysts, and Agent Orchestration."""

from __future__ import annotations

import json
from pathlib import Path
import click
from rich.console import Console
from rich.table import Table

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

console = Console()


def _get_services(repo_root: Path):
    cfg = FactoryConfig.load(repo_root / "factory.yaml")
    store = TraceabilityGraphStore(repo_root / cfg.project.graph_db_path)
    kanban = TrelloKanbanAdapter(state_file=repo_root / cfg.kanban.local_state_file)
    ledger = TaskLedgerManager(repo_root / cfg.project.tasks_dir, graph_store=store)
    sm = KanbanStateMachine(
        adapter=kanban,
        graph_store=store,
        columns=cfg.kanban.columns,
        task_ledger=ledger,
    )
    return cfg, store, kanban, ledger, sm


@click.group()
def main() -> None:
    """Enterprise Multi-Agent Spec-Driven Software Factory CLI."""


@main.command("init")
@click.option("--repo-root", default=".", help="Path to repository root.")
def init_cmd(repo_root: str) -> None:
    """Initializes and self-hosts the Traceability Graph, Kanban Board, and Exports."""
    root = Path(repo_root).resolve()
    cfg, store, kanban, _, _ = _get_services(root)
    bootstrap_factory_graph(root, cfg, store, kanban)
    console.print("[bold green]Factory initialized and graph exported successfully![/bold green]")


@main.command("status")
@click.option("--repo-root", default=".", help="Path to repository root.")
def status_cmd(repo_root: str) -> None:
    """Displays Traceability Graph summary, Kanban columns, and open security/prod issues."""
    root = Path(repo_root).resolve()
    cfg, store, kanban, _, _ = _get_services(root)
    nodes = store.list_nodes()
    if not nodes:
        bootstrap_factory_graph(root, cfg, store, kanban)
        nodes = store.list_nodes()

    validator = GraphValidator(store)
    orphans = validator.find_all_orphans()
    open_issues = store.get_open_issues()

    table = Table(title="Traceability Graph Nodes")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Type", style="magenta")
    table.add_column("Status", style="green")
    table.add_column("Anchored to PROB-001", style="yellow")
    table.add_column("Title")

    for n in nodes:
        anchored = "YES" if validator.is_anchored_to_problem(n.id) else "NO"
        table.add_row(n.id, n.node_type.value, n.status, anchored, n.title)

    console.print(table)
    console.print(
        f"\n[bold]Orphan Nodes:[/bold] {len(orphans)} | "
        f"[bold]Open Issues:[/bold] {len(open_issues)} | "
        f"[bold]Kanban Cards:[/bold] {len(kanban.list_cards())}"
    )


@main.group("task")
def task_group() -> None:
    """Manage step-by-step Task Conversation & Design Ledgers (`specs/tasks/`)."""


@task_group.command("new")
@click.argument("task_id")
@click.argument("description")
@click.option("--date", "date_str", default=None, help="Date YYYY-MM-DD")
@click.option("--problem-id", default="PROB-001", help="Root Problem ID")
@click.option("--repo-root", default=".", help="Path to repository root.")
def task_new_cmd(
    task_id: str,
    description: str,
    date_str: str | None,
    problem_id: str,
    repo_root: str,
) -> None:
    """Creates a new Task Ledger folder with README metadata."""
    root = Path(repo_root).resolve()
    _, _, _, ledger, _ = _get_services(root)
    task_dir = ledger.init_task_ledger(
        task_id=task_id,
        description=description,
        date_str=date_str,
        problem_id=problem_id,
    )
    console.print(f"[green]Created Task Ledger:[/green] {task_dir}")


@task_group.command("log-step")
@click.argument("task_id")
@click.argument("step_name")
@click.argument("content")
@click.option("--actor", default="agy (Gemini 4 Argon)")
@click.option("--repo-root", default=".", help="Path to repository root.")
def task_log_step_cmd(
    task_id: str,
    step_name: str,
    content: str,
    actor: str,
    repo_root: str,
) -> None:
    """Appends sanitized step output to the Task Ledger folder."""
    root = Path(repo_root).resolve()
    _, _, _, ledger, _ = _get_services(root)
    step_path = ledger.append_step_output(
        task_id=task_id,
        step_name=step_name,
        markdown_content=content,
        actor=actor,
    )
    console.print(f"[green]Recorded step output:[/green] {step_path}")


@main.command("sync")
@click.option("--repo-root", default=".", help="Path to repository root.")
def sync_cmd(repo_root: str) -> None:
    """Polls Trello '3. Human Decision' column, records ADRs, and exports Graph snapshots."""
    root = Path(repo_root).resolve()
    cfg, store, _, _, sm = _get_services(root)
    decisions = sm.process_human_decisions(problem_id=cfg.project.root_problem_id)
    store.export_json_ld(root / cfg.project.graph_json_export)
    store.export_mermaid(root / cfg.project.graph_mermaid_export)
    console.print(
        f"[green]Processed {len(decisions)} human decision(s) and updated graph exports.[/green]"
    )


@main.command("audit")
@click.argument("feature_id")
@click.argument("file_path")
@click.option("--task-id", default=None)
@click.option("--repo-root", default=".", help="Path to repository root.")
def audit_cmd(feature_id: str, file_path: str, task_id: str | None, repo_root: str) -> None:
    """Runs `agy` (Gemini 4 Argon) security & production readiness review on a file."""
    root = Path(repo_root).resolve()
    _, store, _, ledger, sm = _get_services(root)
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
    code_text = Path(file_path).read_text(encoding="utf-8")
    report = agy.review_feature_code(
        feature_id=feature_id,
        code_text=code_text,
        file_path=file_path,
        task_id=task_id,
    )
    console.print_json(json.dumps(report.model_dump(mode="json")))


if __name__ == "__main__":
    main()
