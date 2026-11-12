"""FastMCP Server exposing the Software Factory Graph, Kanban, Task Ledger, Skill Installer, and Security Auditor to `agy`."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
from mcp.server.fastmcp import FastMCP

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
def factory_setup_agent_skills(
    gemini_config_dir: Optional[str] = None,
    use_symlinks: bool = False,
    repo_root: str = ".",
) -> Dict[str, Any]:
    """Installs `software-factory`, `grill-me-analyst`, and `security-prod-auditor` skills + MCP config."""
    root = Path(repo_root).resolve()
    installer = FactorySkillInstaller(root)
    report = installer.setup_agent_environment(
        gemini_config_dir=Path(gemini_config_dir) if gemini_config_dir else None,
        use_symlinks=use_symlinks,
    )
    return report.model_dump(mode="json")


@mcp.tool()
def factory_project_init(target_dir: str, repo_root: str = ".") -> Dict[str, Any]:
    """Scaffolds `factory.yaml`, `specs/`, `AGENTS.md`, and `.agent/skills/` into a target repository."""
    root = Path(repo_root).resolve()
    installer = FactorySkillInstaller(root)
    return installer.init_target_project(Path(target_dir))


@mcp.tool()
def factory_trello_init_board(
    sync_cards: bool = False,
    repo_root: str = ".",
) -> Dict[str, Any]:
    """Provisions all 8 mandatory Kanban columns on Trello (or local mirror) and optionally syncs cards."""
    _, cfg, _, kanban, _, _ = _load_runtime(repo_root)
    lists = kanban.init_board_lists(cfg.kanban.columns)
    synced = []
    if sync_cards:
        for card in kanban.list_cards():
            synced.append(kanban.sync_card_to_trello_remote(card))
    return {
        "live_trello_configured": kanban.is_live_configured,
        "lists": lists,
        "synced_cards": synced,
    }


@mcp.tool()
def factory_task_create_and_link(
    task_id: str,
    feature_id: str,
    title: str,
    problem_context: str,
    system_design: str,
    scenarios: Optional[List[str]] = None,
    date_str: Optional[str] = None,
    problem_id: str = "PROB-001",
    spec_id: str = "SPEC-001",
    repo_root: str = ".",
) -> Dict[str, Any]:
    """Atomically creates a Task Ledger folder, Gherkin `.feature`, Graph nodes, and linked Trello Card."""
    root, cfg, store, kanban, ledger, _ = _load_runtime(repo_root)
    kanban.init_board_lists(cfg.kanban.columns)
    res = ledger.create_and_link_task_with_trello(
        task_id=task_id,
        feature_id=feature_id,
        title=title,
        problem_context=problem_context,
        system_design=system_design,
        scenarios=scenarios or [f"Verify {title}"],
        features_dir=root / cfg.project.features_dir,
        kanban_adapter=kanban,
        target_column=cfg.kanban.columns.ready_for_dev,
        date_str=date_str,
        problem_id=problem_id,
        spec_id=spec_id,
    )
    store.export_json_ld(root / cfg.project.graph_json_export)
    store.export_mermaid(root / cfg.project.graph_mermaid_export)
    return res


@mcp.tool()
def factory_task_link_trello(
    task_id: str,
    feature_id: str,
    trello_card_id: Optional[str] = None,
    repo_root: str = ".",
) -> Dict[str, Any]:
    """Links an existing Task Ledger and FeatureNode to a Trello card ID."""
    root, cfg, store, kanban, ledger, _ = _load_runtime(repo_root)
    existing_card = kanban.get_card(feature_id)
    final_id = trello_card_id or (existing_card.card_id if existing_card else f"CARD-{feature_id}")
    if existing_card and kanban.is_live_configured:
        sync_res = kanban.sync_card_to_trello_remote(existing_card)
        final_id = sync_res["card_id"]
    readme_path = ledger.link_existing_task_to_trello(
        task_id=task_id,
        feature_id=feature_id,
        trello_card_id=final_id,
    )
    store.export_json_ld(root / cfg.project.graph_json_export)
    store.export_mermaid(root / cfg.project.graph_mermaid_export)
    return {
        "task_id": task_id,
        "feature_id": feature_id,
        "trello_card_id": final_id,
        "readme_path": str(readme_path),
    }


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
def factory_dispatch_pi(
    feature_id: str,
    prompt: str,
    task_id: Optional[str] = None,
    repo_root: str = ".",
) -> Dict[str, Any]:
    """Spawns `pi` in an isolated Git worktree with read-only specs and zero secrets."""
    root, cfg, store, _, ledger, sm = _load_runtime(repo_root)
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
    return report.model_dump(mode="json")


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


@mcp.tool()
def factory_formal_init_spec(
    spec_id: str,
    feature_id: str,
    title: str,
    paper_references: List[str],
    theorem_obligations: List[str],
    repo_root: str = ".",
) -> Dict[str, Any]:
    """Stage 1a: Drafts untrusted `Spec.lean` with Reviewer critiques and escalates to Trello Need Decision."""
    root, cfg, store, _, _, sm = _load_runtime(repo_root)
    pipeline = FormalSpecPipeline(
        formal_specs_dir=root / cfg.project.specs_dir / "formal",
        graph_store=store,
        kanban_sm=sm,
    )
    node = pipeline.draft_lean_spec(
        formal_spec_id=spec_id,
        feature_id=feature_id,
        title=title,
        paper_references=paper_references,
        theorem_obligations=theorem_obligations,
    )
    store.export_json_ld(root / cfg.project.graph_json_export)
    store.export_mermaid(root / cfg.project.graph_mermaid_export)
    return node.model_dump(mode="json")


@mcp.tool()
def factory_formal_approve_spec(
    spec_id: str,
    approved_by: str,
    repo_root: str = ".",
) -> Dict[str, Any]:
    """Stage 1b: Marks `Spec.lean` as Trusted after Human Approval and locks its SHA-256 checksum."""
    root, cfg, store, _, _, sm = _load_runtime(repo_root)
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
    return node.model_dump(mode="json")


@mcp.tool()
def factory_formal_lift_code(
    model_id: str,
    feature_id: str,
    source_path: str,
    source_language: str = "rust",
    repo_root: str = ".",
) -> Dict[str, Any]:
    """Stage 2: Lifts source/Rust code into a Trusted Executable Lean Processor Model (`CodeModel.lean`)."""
    root, cfg, store, _, _, _ = _load_runtime(repo_root)
    modeler = ExecutableLeanCodeModeler(
        formal_specs_dir=root / cfg.project.specs_dir / "formal",
        graph_store=store,
    )
    node = modeler.lift_source_to_lean_model(
        code_model_id=model_id,
        feature_id=feature_id,
        source_path=Path(source_path),
        source_language=source_language,
    )
    store.export_json_ld(root / cfg.project.graph_json_export)
    store.export_mermaid(root / cfg.project.graph_mermaid_export)
    return node.model_dump(mode="json")


@mcp.tool()
def factory_formal_gatekeep(
    spec_id: str,
    model_id: str,
    proof_file_path: str,
    repo_root: str = ".",
) -> Dict[str, Any]:
    """Stage 3b: Runs the deterministic Gatekeeper checking SHA-256 locks, zero sorry/axioms, and theorem coverage."""
    _, _, store, _, _, _ = _load_runtime(repo_root)
    fspec = store.get_node(spec_id)
    cmod = store.get_node(model_id)
    if not isinstance(fspec, FormalSpecNode) or not isinstance(cmod, CodeModelNode):
        raise ValueError("Both FormalSpecNode and CodeModelNode must exist in the Graph.")
    gk = FormalGatekeeper()
    return gk.verify_proof(fspec, cmod, Path(proof_file_path)).model_dump(mode="json")


@mcp.tool()
def factory_formal_run_prover_team(
    proof_id: str,
    spec_id: str,
    model_id: str,
    task_id: Optional[str] = None,
    repo_root: str = ".",
) -> Dict[str, Any]:
    """Stage 3a+3b: Runs the multi-agent Prover Team loop against the Gatekeeper to emit verified TheoremProofNodes."""
    root, cfg, store, _, ledger, _ = _load_runtime(repo_root)
    fspec = store.get_node(spec_id)
    cmod = store.get_node(model_id)
    if not isinstance(fspec, FormalSpecNode) or not isinstance(cmod, CodeModelNode):
        raise ValueError("Both FormalSpecNode and CodeModelNode must exist in the Graph.")
    gk = FormalGatekeeper()
    coord = ProverTeamCoordinator(
        proofs_base_dir=root / "src" / "formal_proofs",
        gatekeeper=gk,
        graph_store=store,
        task_ledger=ledger,
    )
    res = coord.run_prover_loop(
        theorem_proof_id=proof_id,
        formal_spec=fspec,
        code_model=cmod,
        task_id=task_id,
    )
    store.export_json_ld(root / cfg.project.graph_json_export)
    store.export_mermaid(root / cfg.project.graph_mermaid_export)
    return res.model_dump(mode="json")


if __name__ == "__main__":
    mcp.run()
