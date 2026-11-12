"""CLI Entrypoint (`factory`) for Technical Leads, System Analysts, and Agent Orchestration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Tuple
import click
from rich.console import Console
from rich.table import Table

from factory.agents.agy_driver import AgyReviewDriver
from factory.agents.pi_driver import PiAgentDriver
from factory.analyzer.issue_tracker import DualTrackIssueTracker
from factory.analyzer.security_scanner import EnterpriseSecurityAndProdAnalyzer
from factory.bdd.runner import LanguageAgnosticBDDRunner
from factory.bootstrap import bootstrap_factory_graph
from factory.config import FactoryConfig
from factory.formal.code_model import ExecutableLeanCodeModeler
from factory.formal.gatekeeper import FormalGatekeeper
from factory.formal.prover_team import ProverTeamCoordinator
from factory.formal.spec_pipeline import FormalSpecPipeline
from factory.git_ops.pr_manager import PullRequestManager
from factory.git_ops.worktree import WorktreeManager
from factory.graph.models import CodeModelNode, FormalSpecNode
from factory.graph.store import TraceabilityGraphStore
from factory.graph.validator import GraphValidator
from factory.installer import FactorySkillInstaller
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


@main.command("setup-skills")
@click.option("--gemini-config-dir", default=None, help="Override ~/.gemini/config directory.")
@click.option("--symlink/--copy", default=False, help="Symlink skills instead of copying.")
@click.option("--repo-root", default=".", help="Path to factory repository root.")
def setup_skills_cmd(
    gemini_config_dir: str | None,
    symlink: bool,
    repo_root: str,
) -> None:
    """Installs `software-factory`, `grill-me-analyst`, and `security-prod-auditor` skills + MCP config."""
    root = Path(repo_root).resolve()
    installer = FactorySkillInstaller(root)
    report = installer.setup_agent_environment(
        gemini_config_dir=Path(gemini_config_dir) if gemini_config_dir else None,
        use_symlinks=symlink,
    )
    console.print_json(json.dumps(report.model_dump(mode="json")))


@main.command("project-init")
@click.argument("target_dir", default=".")
@click.option("--repo-root", default=".", help="Path to factory repository root.")
def project_init_cmd(target_dir: str, repo_root: str) -> None:
    """Initializes a target repository with `factory.yaml`, `specs/`, `AGENTS.md`, and `.agent/skills/`."""
    root = Path(repo_root).resolve()
    installer = FactorySkillInstaller(root)
    result = installer.init_target_project(Path(target_dir))
    console.print_json(json.dumps(result))


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


@main.command("impact")
@click.argument("node_id")
@click.option("--repo-root", default=".", help="Path to repository root.")
def impact_cmd(node_id: str, repo_root: str) -> None:
    """Computes downstream blast-radius impact if a Problem or Spec node changes."""
    root = Path(repo_root).resolve()
    _, store, _, _, _ = _get_services(root)
    affected = store.compute_impact_blast_radius(node_id)
    console.print_json(json.dumps({"node_id": node_id, "downstream_affected": affected}))


@main.group("trello")
def trello_group() -> None:
    """Initialize Trello Kanban board lists, escalate design decisions, and sync cards."""


@trello_group.command("init-board")
@click.option("--sync-cards/--no-sync-cards", default=False, help="Push all local cards to remote Trello.")
@click.option("--repo-root", default=".", help="Path to repository root.")
def trello_init_board_cmd(sync_cards: bool, repo_root: str) -> None:
    """Provisions all 8 mandatory Kanban columns on Trello (or local mirror)."""
    root = Path(repo_root).resolve()
    cfg, _, kanban, _, _ = _get_services(root)
    board_lists = kanban.init_board_lists(cfg.kanban.columns)
    synced = []
    if sync_cards:
        for card in kanban.list_cards():
            synced.append(kanban.sync_card_to_trello_remote(card))
    console.print_json(
        json.dumps(
            {
                "live_trello_configured": kanban.is_live_configured,
                "lists": board_lists,
                "synced_cards": synced,
            }
        )
    )


@trello_group.command("ask-decision")
@click.argument("feature_id")
@click.argument("question_id")
@click.argument("question_text")
@click.option("--option", "-o", "options", multiple=True, required=True, help="Decision option.")
@click.option("--repo-root", default=".", help="Path to repository root.")
def trello_ask_decision_cmd(
    feature_id: str,
    question_id: str,
    question_text: str,
    options: Tuple[str, ...],
    repo_root: str,
) -> None:
    """Moves a feature card to '2. Need Decision' with formatted options for the Tech Lead."""
    root = Path(repo_root).resolve()
    _, _, kanban, _, sm = _get_services(root)
    card = sm.escalate_to_need_decision(
        feature_id=feature_id,
        question_id=question_id,
        question_text=question_text,
        options=list(options),
    )
    if kanban.is_live_configured:
        kanban.sync_card_to_trello_remote(card)
    console.print_json(json.dumps(card.model_dump(mode="json")))


@main.group("task")
def task_group() -> None:
    """Manage step-by-step Task Conversation & Design Ledgers (`specs/tasks/`) and Trello links."""


@task_group.command("new")
@click.argument("task_id")
@click.argument("description")
@click.option("--date", "date_str", default=None, help="Date YYYY-MM-DD")
@click.option("--problem-id", default="PROB-001", help="Root Problem ID")
@click.option("--trello-card-id", default=None, help="Optional Trello Card ID to link")
@click.option("--repo-root", default=".", help="Path to repository root.")
def task_new_cmd(
    task_id: str,
    description: str,
    date_str: str | None,
    problem_id: str,
    trello_card_id: str | None,
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
        trello_card_id=trello_card_id,
    )
    console.print(f"[green]Created Task Ledger:[/green] {task_dir}")


@task_group.command("create")
@click.option("--task-id", required=True, help="Task ID (e.g. TASK-003)")
@click.option("--feature-id", required=True, help="Feature ID (e.g. FEAT-008)")
@click.option("--title", required=True, help="Feature & Task Title")
@click.option("--problem-context", required=True, help="Section 1: Problem Context & Goal")
@click.option("--system-design", required=True, help="Section 2: System Analysis & Enterprise Design")
@click.option("--scenario", "scenarios", multiple=True, help="Gherkin Scenario titles")
@click.option("--date", "date_str", default=None, help="Date YYYY-MM-DD")
@click.option("--problem-id", default="PROB-001", help="Root Problem ID")
@click.option("--spec-id", default="SPEC-001", help="System Spec ID")
@click.option("--repo-root", default=".", help="Path to repository root.")
def task_create_cmd(
    task_id: str,
    feature_id: str,
    title: str,
    problem_context: str,
    system_design: str,
    scenarios: Tuple[str, ...],
    date_str: str | None,
    problem_id: str,
    spec_id: str,
    repo_root: str,
) -> None:
    """Atomically initializes a Task Ledger, Gherkin `.feature`, Graph nodes, and linked Trello Card."""
    root = Path(repo_root).resolve()
    cfg, store, kanban, ledger, _ = _get_services(root)
    kanban.init_board_lists(cfg.kanban.columns)
    result = ledger.create_and_link_task_with_trello(
        task_id=task_id,
        feature_id=feature_id,
        title=title,
        problem_context=problem_context,
        system_design=system_design,
        scenarios=list(scenarios) if scenarios else [f"Verify {title}"],
        features_dir=root / cfg.project.features_dir,
        kanban_adapter=kanban,
        target_column=cfg.kanban.columns.ready_for_dev,
        date_str=date_str,
        problem_id=problem_id,
        spec_id=spec_id,
    )
    store.export_json_ld(root / cfg.project.graph_json_export)
    store.export_mermaid(root / cfg.project.graph_mermaid_export)
    console.print_json(json.dumps(result))


@task_group.command("link-trello")
@click.argument("task_id")
@click.argument("feature_id")
@click.option("--card-id", default=None, help="Trello Card ID (defaults to CARD-<feature_id>)")
@click.option("--repo-root", default=".", help="Path to repository root.")
def task_link_trello_cmd(
    task_id: str,
    feature_id: str,
    card_id: str | None,
    repo_root: str,
) -> None:
    """Links an existing Task Ledger and FeatureNode to a Trello card."""
    root = Path(repo_root).resolve()
    cfg, store, kanban, ledger, _ = _get_services(root)
    existing_card = kanban.get_card(feature_id)
    final_card_id = card_id or (existing_card.card_id if existing_card else f"CARD-{feature_id}")
    if existing_card and kanban.is_live_configured:
        sync_res = kanban.sync_card_to_trello_remote(existing_card)
        final_card_id = sync_res["card_id"]
    readme_path = ledger.link_existing_task_to_trello(
        task_id=task_id,
        feature_id=feature_id,
        trello_card_id=final_card_id,
    )
    store.export_json_ld(root / cfg.project.graph_json_export)
    store.export_mermaid(root / cfg.project.graph_mermaid_export)
    console.print_json(
        json.dumps(
            {
                "task_id": task_id,
                "feature_id": feature_id,
                "trello_card_id": final_card_id,
                "readme_path": str(readme_path),
            }
        )
    )


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
@click.option("--task-id", default=None, help="Optional Task ID to log ADR step output.")
@click.option("--repo-root", default=".", help="Path to repository root.")
def sync_cmd(task_id: str | None, repo_root: str) -> None:
    """Polls Trello '3. Human Decision' column, records ADRs, and exports Graph snapshots."""
    root = Path(repo_root).resolve()
    cfg, store, _, _, sm = _get_services(root)
    decisions = sm.process_human_decisions(
        problem_id=cfg.project.root_problem_id, task_id=task_id
    )
    store.export_json_ld(root / cfg.project.graph_json_export)
    store.export_mermaid(root / cfg.project.graph_mermaid_export)
    console.print(
        f"[green]Processed {len(decisions)} human decision(s) and updated graph exports.[/green]"
    )


@main.command("run-pi")
@click.argument("feature_id")
@click.option("--prompt", required=True, help="Coding instruction for pi agent.")
@click.option("--task-id", default=None, help="Task ID for logging 04-pi-execution-summary.md")
@click.option("--repo-root", default=".", help="Path to repository root.")
def run_pi_cmd(
    feature_id: str,
    prompt: str,
    task_id: str | None,
    repo_root: str,
) -> None:
    """Dispatches `pi` in an isolated Git worktree with read-only specs and zero secrets."""
    root = Path(repo_root).resolve()
    cfg, store, _, ledger, sm = _get_services(root)
    wt_mgr = WorktreeManager(
        repo_root=root,
        worktree_base_dir=root / cfg.agents.coder.worktree_base_dir,
        read_only_rel_paths=cfg.agents.coder.read_only_paths,
        scrubbed_env_vars=cfg.agents.coder.scrubbed_env_vars,
        graph_store=store,
    )
    bdd = LanguageAgnosticBDDRunner(cfg.bdd)
    pr_mgr = PullRequestManager(root / ".factory/pull_requests.json")
    pi_driver = PiAgentDriver(
        worktree_manager=wt_mgr,
        bdd_runner=bdd,
        pr_manager=pr_mgr,
        pi_binary=cfg.agents.coder.binary,
        max_iterations=cfg.agents.coder.max_iterations_per_task,
        task_ledger=ledger,
    )
    report = pi_driver.execute_feature_task(
        feature_id=feature_id,
        prompt=prompt,
        task_id=task_id,
    )
    if report.bdd_passed and sm.adapter.get_card(feature_id):
        sm.transition_card(feature_id, target_column=cfg.kanban.columns.pr_review, actor="pi")
    console.print_json(json.dumps(report.model_dump(mode="json")))


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


@main.group("formal")
def formal_group() -> None:
    """3-Stage Agentic Formal Verification (Lean Spec, Machine Processor Model, Prover Team & Gatekeeper)."""


@formal_group.command("init-spec")
@click.option("--spec-id", required=True, help="Formal Spec ID (e.g. FSPEC-008)")
@click.option("--feature-id", required=True, help="Linked Feature ID (e.g. FEAT-008)")
@click.option("--title", required=True, help="Formal Specification Title")
@click.option("--paper", "papers", multiple=True, required=True, help="Research paper / RFC references")
@click.option("--obligation", "obligations", multiple=True, required=True, help="Theorem obligation names")
@click.option("--repo-root", default=".", help="Path to repository root.")
def formal_init_spec_cmd(
    spec_id: str,
    feature_id: str,
    title: str,
    papers: Tuple[str, ...],
    obligations: Tuple[str, ...],
    repo_root: str,
) -> None:
    """Stage 1a: Spec-writer & Reviewers draft candidate `Spec.lean` and escalate to Trello Need Decision."""
    root = Path(repo_root).resolve()
    cfg, store, _, _, sm = _get_services(root)
    pipeline = FormalSpecPipeline(
        formal_specs_dir=root / cfg.project.specs_dir / "formal",
        graph_store=store,
        kanban_sm=sm,
    )
    node = pipeline.draft_lean_spec(
        formal_spec_id=spec_id,
        feature_id=feature_id,
        title=title,
        paper_references=list(papers),
        theorem_obligations=list(obligations),
    )
    store.export_json_ld(root / cfg.project.graph_json_export)
    store.export_mermaid(root / cfg.project.graph_mermaid_export)
    console.print_json(json.dumps(node.model_dump(mode="json")))


@formal_group.command("approve-spec")
@click.argument("spec_id")
@click.option("--approved-by", required=True, help="Authorized Tech Lead / User ID")
@click.option("--repo-root", default=".", help="Path to repository root.")
def formal_approve_spec_cmd(spec_id: str, approved_by: str, repo_root: str) -> None:
    """Stage 1b: Human approves `Spec.lean`, marking it Trusted and locking its SHA-256 checksum."""
    root = Path(repo_root).resolve()
    cfg, store, _, _, sm = _get_services(root)
    pipeline = FormalSpecPipeline(
        formal_specs_dir=root / cfg.project.specs_dir / "formal",
        graph_store=store,
        kanban_sm=sm,
    )
    node = pipeline.approve_and_lock_spec(
        formal_spec_id=spec_id,
        approved_by=approved_by,
        problem_id=cfg.project.root_problem_id,
    )
    store.export_json_ld(root / cfg.project.graph_json_export)
    store.export_mermaid(root / cfg.project.graph_mermaid_export)
    console.print_json(json.dumps(node.model_dump(mode="json")))


@formal_group.command("lift-code")
@click.option("--model-id", required=True, help="CodeModelNode ID (e.g. CMOD-008)")
@click.option("--feature-id", required=True, help="Linked Feature ID (e.g. FEAT-008)")
@click.option("--source-path", required=True, help="Path to target Rust/C/Source file")
@click.option("--language", default="rust", help="Source language (default: rust)")
@click.option("--repo-root", default=".", help="Path to repository root.")
def formal_lift_code_cmd(
    model_id: str,
    feature_id: str,
    source_path: str,
    language: str,
    repo_root: str,
) -> None:
    """Stage 2: Compiles/lifts source code into a Trusted Lean machine-code processor model (`CodeModel.lean`)."""
    root = Path(repo_root).resolve()
    cfg, store, _, _, _ = _get_services(root)
    modeler = ExecutableLeanCodeModeler(
        formal_specs_dir=root / cfg.project.specs_dir / "formal",
        graph_store=store,
    )
    node = modeler.lift_source_to_lean_model(
        code_model_id=model_id,
        feature_id=feature_id,
        source_path=Path(source_path),
        source_language=language,
    )
    store.export_json_ld(root / cfg.project.graph_json_export)
    store.export_mermaid(root / cfg.project.graph_mermaid_export)
    console.print_json(json.dumps(node.model_dump(mode="json")))


@formal_group.command("gatekeep")
@click.argument("spec_id")
@click.argument("model_id")
@click.argument("proof_file")
@click.option("--repo-root", default=".", help="Path to repository root.")
def formal_gatekeep_cmd(
    spec_id: str,
    model_id: str,
    proof_file: str,
    repo_root: str,
) -> None:
    """Stage 3b: Runs the deterministic Gatekeeper against a candidate Lean proof file."""
    root = Path(repo_root).resolve()
    _, store, _, _, _ = _get_services(root)
    fspec = store.get_node(spec_id)
    cmod = store.get_node(model_id)
    if not isinstance(fspec, FormalSpecNode) or not isinstance(cmod, CodeModelNode):
        raise click.ClickException("Both FormalSpecNode and CodeModelNode must exist in the Graph.")
    gk = FormalGatekeeper()
    verdict = gk.verify_proof(fspec, cmod, Path(proof_file))
    console.print_json(json.dumps(verdict.model_dump(mode="json")))


@formal_group.command("prove")
@click.option("--proof-id", required=True, help="TheoremProofNode ID (e.g. THM-008)")
@click.option("--spec-id", required=True, help="Trusted FormalSpecNode ID")
@click.option("--model-id", required=True, help="Trusted CodeModelNode ID")
@click.option("--task-id", default=None, help="Optional Task ID for logging 06-formal-verification-proofs.md")
@click.option("--repo-root", default=".", help="Path to repository root.")
def formal_prove_cmd(
    proof_id: str,
    spec_id: str,
    model_id: str,
    task_id: str | None,
    repo_root: str,
) -> None:
    """Stage 3a+3b: Runs the Prover Team synthesis loop gated by the deterministic Gatekeeper."""
    root = Path(repo_root).resolve()
    cfg, store, _, ledger, _ = _get_services(root)
    fspec = store.get_node(spec_id)
    cmod = store.get_node(model_id)
    if not isinstance(fspec, FormalSpecNode) or not isinstance(cmod, CodeModelNode):
        raise click.ClickException("Both FormalSpecNode and CodeModelNode must exist in the Graph.")
    gk = FormalGatekeeper()
    coord = ProverTeamCoordinator(
        proofs_base_dir=root / "src" / "formal_proofs",
        gatekeeper=gk,
        graph_store=store,
        task_ledger=ledger,
    )
    result = coord.run_prover_loop(
        theorem_proof_id=proof_id,
        formal_spec=fspec,
        code_model=cmod,
        task_id=task_id,
    )
    store.export_json_ld(root / cfg.project.graph_json_export)
    store.export_mermaid(root / cfg.project.graph_mermaid_export)
    console.print_json(json.dumps(result.model_dump(mode="json")))


if __name__ == "__main__":
    main()
