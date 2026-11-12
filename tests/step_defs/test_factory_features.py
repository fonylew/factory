"""Step definitions and BDD regression tests for all 6 foundational Gherkin features (FEAT-001..FEAT-006)."""

from __future__ import annotations

from pathlib import Path
import stat
import subprocess
from typing import Any, Dict
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from factory.agents.agy_driver import AgyReviewDriver
from factory.analyzer.issue_tracker import DualTrackIssueTracker
from factory.analyzer.security_scanner import EnterpriseSecurityAndProdAnalyzer
from factory.formal.code_model import ExecutableLeanCodeModeler
from factory.formal.gatekeeper import FormalGatekeeper
from factory.formal.prover_team import ProverTeamCoordinator
from factory.formal.spec_pipeline import FormalSpecPipeline
from factory.git_ops.pr_manager import PullRequestManager
from factory.git_ops.worktree import SpecTamperError, WorktreeManager
from factory.graph.models import (
    CodeArtifactNode,
    CodeModelNode,
    DecisionNode,
    FeatureNode,
    FormalSpecNode,
    IssueCategory,
    IssueNode,
    IssueSeverity,
    ProblemNode,
    SystemSpecNode,
    TaskJournalNode,
    TheoremProofNode,
)
from factory.graph.store import TraceabilityGraphStore
from factory.graph.validator import GraphValidationError, GraphValidator
from factory.installer import FactorySkillInstaller
from factory.journal.task_ledger import TaskLedgerManager
from factory.kanban.card_parser import CardParser
from factory.kanban.state_machine import KanbanStateMachine, KanbanTransitionError
from factory.kanban.trello_client import KanbanCard, LocalKanbanAdapter

REPO_ROOT = Path(__file__).resolve().parents[2]
FEATURES_DIR = REPO_ROOT / "specs" / "features"

scenarios(str(FEATURES_DIR / "FEAT-001-grill-me-spec-anchor.feature"))
scenarios(str(FEATURES_DIR / "FEAT-002-traceability-graph.feature"))
scenarios(str(FEATURES_DIR / "FEAT-003-trello-kanban-hitl.feature"))
scenarios(str(FEATURES_DIR / "FEAT-004-git-worktree-pi-sandbox.feature"))
scenarios(str(FEATURES_DIR / "FEAT-005-agy-security-pr-review.feature"))
scenarios(str(FEATURES_DIR / "FEAT-006-task-ledger-journal.feature"))
scenarios(str(FEATURES_DIR / "FEAT-007-agent-skill-and-trello-linking.feature"))
scenarios(str(FEATURES_DIR / "FEAT-008-formal-verification-framework.feature"))


@pytest.fixture
def ctx(tmp_path: Path) -> Dict[str, Any]:
    return {"tmp_path": tmp_path}


# ============================================================================
# Shared & FEAT-001 / FEAT-002 Steps (Traceability Graph & Spec Anchor)
# ============================================================================


@given("an initialized Traceability Graph store")
def init_graph_store(ctx: Dict[str, Any]) -> None:
    store = TraceabilityGraphStore(":memory:")
    ctx["store"] = store
    ctx["validator"] = GraphValidator(store)


@given(parsers.parse('ProblemNode "{prob_id}" exists in the Traceability Graph'))
def given_problem_exists(ctx: Dict[str, Any], prob_id: str) -> None:
    store: TraceabilityGraphStore = ctx["store"]
    store.upsert_node(
        ProblemNode(
            id=prob_id,
            title=f"Problem {prob_id}",
            statement="Enterprise problem anchor",
            status="ACTIVE",
        )
    )


@given(
    parsers.parse(
        'SystemSpecNode "{spec_id}" is registered without a valid ProblemNode link'
    )
)
def given_orphan_spec(ctx: Dict[str, Any], spec_id: str) -> None:
    store: TraceabilityGraphStore = ctx["store"]
    store.upsert_node(
        SystemSpecNode(
            id=spec_id,
            title=f"Orphan Spec {spec_id}",
            problem_id=None,
        )
    )


@when(
    parsers.parse(
        'an agent attempts to validate FeatureNode "{feat_id}" linked to "{spec_id}"'
    )
)
def when_validate_orphan_feature(
    ctx: Dict[str, Any], feat_id: str, spec_id: str
) -> None:
    validator: GraphValidator = ctx["validator"]
    feat = FeatureNode(id=feat_id, title=f"Feature {feat_id}", spec_id=spec_id)
    try:
        validator.validate_feature_registration(feat)
        ctx["error_code"] = None
    except GraphValidationError as exc:
        ctx["error_code"] = exc.code


@then(parsers.parse('the Graph Validator rejects the feature with error "{err_code}"'))
def then_validator_rejects(ctx: Dict[str, Any], err_code: str) -> None:
    assert ctx.get("error_code") == err_code


@given(
    parsers.parse(
        'ProblemNode "{prob_id}" and SystemSpecNode "{spec_id}" are linked in the Traceability Graph'
    )
)
def given_prob_and_spec_linked(
    ctx: Dict[str, Any], prob_id: str, spec_id: str
) -> None:
    store: TraceabilityGraphStore = ctx["store"]
    store.upsert_node(ProblemNode(id=prob_id, title=f"Problem {prob_id}"))
    store.upsert_node(
        SystemSpecNode(id=spec_id, title=f"Spec {spec_id}", problem_id=prob_id)
    )


@given(parsers.parse('a Gherkin feature file exists for "{feat_id}"'))
def given_gherkin_file_exists(ctx: Dict[str, Any], feat_id: str) -> None:
    store: TraceabilityGraphStore = ctx["store"]
    feat_path = ctx["tmp_path"] / f"{feat_id}.feature"
    feat_path.write_text(
        f"@{feat_id}\nFeature: Sample {feat_id}\n  Scenario: Check\n    Given ok\n",
        encoding="utf-8",
    )
    ctx["feat_path"] = feat_path
    store.upsert_node(
        FeatureNode(
            id=feat_id,
            title=f"Feature {feat_id}",
            spec_id="SPEC-001",
            feature_file_path=str(feat_path),
        )
    )


@when(parsers.parse('the System Analyst locks "{feat_id}" for development'))
def when_lock_feature(ctx: Dict[str, Any], feat_id: str) -> None:
    validator: GraphValidator = ctx["validator"]
    locked = validator.lock_feature_spec(feat_id, ctx["feat_path"])
    ctx["locked_feature"] = locked


@then(
    parsers.parse(
        'FeatureNode "{feat_id}" stores a valid 64-character SHA-256 spec checksum'
    )
)
def then_valid_sha256(ctx: Dict[str, Any], feat_id: str) -> None:
    store: TraceabilityGraphStore = ctx["store"]
    node = store.get_node(feat_id)
    assert isinstance(node, FeatureNode)
    assert len(node.spec_checksum) == 64


@then(
    parsers.parse(
        'the Graph Validator confirms "{feat_id}" is anchored to "{prob_id}"'
    )
)
def then_confirmed_anchored(ctx: Dict[str, Any], feat_id: str, prob_id: str) -> None:
    validator: GraphValidator = ctx["validator"]
    assert validator.is_anchored_to_problem(feat_id) is True


@given(
    parsers.parse(
        'ProblemNode "{prob_id}", SystemSpecNode "{spec_id}", and FeatureNode "{feat_id}" are linked in the graph'
    )
)
@given(
    parsers.parse(
        'ProblemNode "{prob_id}", SystemSpecNode "{spec_id}", and FeatureNode "{feat_id}" exist in the graph'
    )
)
def given_prob_spec_feat_linked(
    ctx: Dict[str, Any], prob_id: str, spec_id: str, feat_id: str
) -> None:
    store: TraceabilityGraphStore = ctx["store"]
    store.upsert_node(ProblemNode(id=prob_id, title=f"Problem {prob_id}"))
    store.upsert_node(
        SystemSpecNode(id=spec_id, title=f"Spec {spec_id}", problem_id=prob_id)
    )
    store.upsert_node(
        FeatureNode(id=feat_id, title=f"Feature {feat_id}", spec_id=spec_id)
    )


@given(
    parsers.parse(
        'IssueNode "{iss_id}" of severity "{sev}" and category "{cat}" affects "{feat_id}"'
    )
)
def given_issue_affects_feature(
    ctx: Dict[str, Any], iss_id: str, sev: str, cat: str, feat_id: str
) -> None:
    store: TraceabilityGraphStore = ctx["store"]
    store.upsert_node(
        IssueNode(
            id=iss_id,
            title=f"Issue {iss_id}",
            severity=IssueSeverity(sev),
            category=IssueCategory(cat),
            affected_feature_id=feat_id,
        )
    )


@when("the graph is exported to JSON-LD and Mermaid files")
def when_export_graph(ctx: Dict[str, Any]) -> None:
    store: TraceabilityGraphStore = ctx["store"]
    json_path = ctx["tmp_path"] / "traceability.json"
    mmd_path = ctx["tmp_path"] / "traceability.mmd"
    ctx["json_ld"] = store.export_json_ld(json_path)
    ctx["mermaid"] = store.export_mermaid(mmd_path)


@then(
    parsers.parse(
        'the JSON-LD export contains nodes "{id1}", "{id2}", "{id3}", and "{id4}"'
    )
)
def then_json_ld_contains_nodes(
    ctx: Dict[str, Any], id1: str, id2: str, id3: str, id4: str
) -> None:
    exported_ids = {n["id"] for n in ctx["json_ld"]["nodes"]}
    for expected in (id1, id2, id3, id4):
        assert expected in exported_ids


@then(
    parsers.parse(
        'the Mermaid export contains a directed diagram linking "{prob_id}" to "{spec_id}" and "{feat_id}"'
    )
)
def then_mermaid_contains_links(
    ctx: Dict[str, Any], prob_id: str, spec_id: str, feat_id: str
) -> None:
    mmd: str = ctx["mermaid"]
    assert "flowchart TD" in mmd
    assert f'{prob_id} -->|"SOLVED_BY"| {spec_id}' in mmd
    assert f'{spec_id} -->|"SPECIFIED_BY"| {feat_id}' in mmd


@then(
    parsers.parse(
        'querying open issues returns "{iss_id}" blocking "{feat_id}"'
    )
)
def then_open_issues_returns(
    ctx: Dict[str, Any], iss_id: str, feat_id: str
) -> None:
    store: TraceabilityGraphStore = ctx["store"]
    open_issues = store.get_open_issues(feature_id=feat_id)
    assert any(i.id == iss_id for i in open_issues)


@given(parsers.parse('CodeArtifactNode "{code_id}" implements "{feat_id}"'))
def given_code_implements_feat(
    ctx: Dict[str, Any], code_id: str, feat_id: str
) -> None:
    store: TraceabilityGraphStore = ctx["store"]
    store.upsert_node(
        CodeArtifactNode(
            id=code_id,
            title=f"Code {code_id}",
            feature_id=feat_id,
            file_path="src/module.py",
        )
    )


@when(parsers.parse('impact analysis is executed for "{node_id}"'))
def when_impact_analysis(ctx: Dict[str, Any], node_id: str) -> None:
    store: TraceabilityGraphStore = ctx["store"]
    ctx["blast_radius"] = store.compute_impact_blast_radius(node_id)


@then(
    parsers.parse(
        'the downstream affected nodes include "{id1}" and "{id2}"'
    )
)
def then_blast_radius_includes(ctx: Dict[str, Any], id1: str, id2: str) -> None:
    assert id1 in ctx["blast_radius"]
    assert id2 in ctx["blast_radius"]


# ============================================================================
# FEAT-003 Steps (Trello Kanban State Machine & Human-in-the-Loop)
# ============================================================================


@given("an initialized Kanban State Machine and Traceability Graph")
def init_kanban_and_graph(ctx: Dict[str, Any]) -> None:
    store = TraceabilityGraphStore(":memory:")
    store.upsert_node(ProblemNode(id="PROB-001", title="Root Problem"))
    adapter = LocalKanbanAdapter(ctx["tmp_path"] / "kanban.json")
    sm = KanbanStateMachine(adapter=adapter, graph_store=store)
    ctx["store"] = store
    ctx["kanban_adapter"] = adapter
    ctx["kanban_sm"] = sm


@given(
    parsers.parse(
        'a Kanban card for "{feat_id}" is in column "{col_name}"'
    )
)
def given_incomplete_card(ctx: Dict[str, Any], feat_id: str, col_name: str) -> None:
    adapter: LocalKanbanAdapter = ctx["kanban_adapter"]
    adapter.upsert_card(
        KanbanCard(
            card_id=f"CARD-{feat_id}",
            feature_id=feat_id,
            title=f"[{feat_id}] Incomplete Card",
            description="## 1. Problem Context & Goal\nValid problem context here.\n",
            column=col_name,
        )
    )


@given(
    parsers.parse(
        'the card description is missing "{section_heading}"'
    )
)
def given_card_missing_section(ctx: Dict[str, Any], section_heading: str) -> None:
    # Verified by given_incomplete_card above
    assert section_heading not in ctx["kanban_adapter"].get_card("FEAT-003").description


@when(
    parsers.parse(
        'the orchestrator attempts to move card "{feat_id}" to "{target_col}"'
    )
)
def when_attempt_card_move(
    ctx: Dict[str, Any], feat_id: str, target_col: str
) -> None:
    sm: KanbanStateMachine = ctx["kanban_sm"]
    try:
        sm.transition_card(feat_id, target_column=target_col)
        ctx["kanban_error"] = None
    except KanbanTransitionError as exc:
        ctx["kanban_error"] = exc.code


@then(parsers.parse('the transition is rejected with error "{err_code}"'))
def then_transition_rejected(ctx: Dict[str, Any], err_code: str) -> None:
    assert ctx.get("kanban_error") == err_code


@then(parsers.parse('card "{feat_id}" remains in column "{expected_col}"'))
@then(parsers.parse('card "{feat_id}" transitions to column "{expected_col}"'))
def then_card_in_column(
    ctx: Dict[str, Any], feat_id: str, expected_col: str
) -> None:
    card = ctx["kanban_adapter"].get_card(feat_id)
    assert card is not None
    assert card.column == expected_col


@given(
    parsers.parse(
        'a valid Kanban card for "{feat_id}" is in column "{col_name}"'
    )
)
def given_valid_card(ctx: Dict[str, Any], feat_id: str, col_name: str) -> None:
    adapter: LocalKanbanAdapter = ctx["kanban_adapter"]
    desc = CardParser.render_card_template(
        feature_id=feat_id,
        title="Kanban HITL Feature",
        problem_id="PROB-001",
        spec_id="SPEC-001",
        problem_context="Ensure human decisions are tracked.",
        system_design="7-column Trello state machine with ADR logging.",
        feature_file_path="specs/features/FEAT-003.feature",
        scenarios=["Pausing and resuming after Human Decision"],
    )
    adapter.upsert_card(
        KanbanCard(
            card_id=f"CARD-{feat_id}",
            feature_id=feat_id,
            title=f"[{feat_id}] Kanban HITL Feature",
            description=desc,
            column=col_name,
        )
    )


@when(
    parsers.parse(
        'the analyst agent escalates question "{adr_id}" regarding "{topic}"'
    )
)
def when_escalate_question(
    ctx: Dict[str, Any], adr_id: str, topic: str
) -> None:
    sm: KanbanStateMachine = ctx["kanban_sm"]
    sm.escalate_to_need_decision(
        feature_id="FEAT-003",
        question_id=adr_id,
        question_text=topic,
        options=["Option A: Redis TTL", "Option B: In-memory LRU"],
    )


@when(
    parsers.parse(
        'authorized member "{member}" writes decision "{decision}" in "## 5. Human Decision"'
    )
)
def when_human_writes_decision(
    ctx: Dict[str, Any], member: str, decision: str
) -> None:
    ctx["pending_member"] = member
    ctx["pending_decision"] = decision


@when(parsers.parse('moves card "{feat_id}" to column "{col_name}"'))
def when_human_moves_card(
    ctx: Dict[str, Any], feat_id: str, col_name: str
) -> None:
    sm: KanbanStateMachine = ctx["kanban_sm"]
    sm.record_human_decision_on_card(
        feature_id=feat_id,
        decision_text=ctx["pending_decision"],
        member_id=ctx["pending_member"],
        rationale="Enterprise resilience requirement.",
    )
    assert ctx["kanban_adapter"].get_card(feat_id).column == col_name


@when("the orchestrator processes human decisions")
def when_process_human_decisions(ctx: Dict[str, Any]) -> None:
    sm: KanbanStateMachine = ctx["kanban_sm"]
    sm.process_human_decisions(problem_id="PROB-001")


@then(
    parsers.parse(
        'DecisionNode "{adr_id}" is recorded in the Traceability Graph with decision "{expected_decision}"'
    )
)
def then_decision_node_recorded(
    ctx: Dict[str, Any], adr_id: str, expected_decision: str
) -> None:
    store: TraceabilityGraphStore = ctx["store"]
    node = store.get_node(adr_id)
    assert isinstance(node, DecisionNode)
    assert node.chosen_option == expected_decision


# ============================================================================
# FEAT-004 Steps (Isolated Git Worktree & Spec Tamper Prevention)
# ============================================================================


@given('a temporary Git repository with a locked "specs/" directory')
def given_temp_git_repo(ctx: Dict[str, Any]) -> None:
    repo_dir = ctx["tmp_path"] / "sample_repo"
    repo_dir.mkdir(parents=True, exist_ok=True)
    specs_dir = repo_dir / "specs" / "features"
    specs_dir.mkdir(parents=True, exist_ok=True)
    feat_file = specs_dir / "FEAT-004.feature"
    feat_file.write_text(
        "@FEAT-004\nFeature: Worktree Lock\n  Scenario: Test\n    Given locked\n",
        encoding="utf-8",
    )

    subprocess.run(["git", "init", "-b", "main"], cwd=str(repo_dir), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "factory@example.com"], cwd=str(repo_dir), check=True)
    subprocess.run(["git", "config", "user.name", "Factory Bot"], cwd=str(repo_dir), check=True)
    subprocess.run(["git", "add", "."], cwd=str(repo_dir), check=True)
    subprocess.run(["git", "commit", "-m", "Initial spec commit"], cwd=str(repo_dir), check=True, capture_output=True)

    store = TraceabilityGraphStore(":memory:")
    store.upsert_node(ProblemNode(id="PROB-001", title="Root"))
    store.upsert_node(SystemSpecNode(id="SPEC-001", title="Spec", problem_id="PROB-001"))
    store.upsert_node(FeatureNode(id="FEAT-004", title="Worktree", spec_id="SPEC-001"))

    wt_mgr = WorktreeManager(
        repo_root=repo_dir,
        worktree_base_dir=repo_dir / "worktrees",
        read_only_rel_paths=["specs"],
        graph_store=store,
    )
    ctx["store"] = store
    ctx["wt_mgr"] = wt_mgr


@given(
    parsers.parse(
        'environment variables include sensitive tokens "{tok1}" and "{tok2}"'
    )
)
def given_sensitive_env(ctx: Dict[str, Any], tok1: str, tok2: str) -> None:
    ctx["mock_env"] = {
        tok1: "secret_trello_val_123456",
        tok2: "ghp_secret_github_val_123456",
        "PATH": "/usr/bin:/bin",
    }


@when(
    parsers.parse(
        'the Worktree Manager prepares an isolated worktree for "{feat_id}"'
    )
)
@given(
    parsers.parse(
        'an isolated worktree for "{feat_id}" with recorded spec SHA-256 checksums'
    )
)
def when_prepare_worktree(ctx: Dict[str, Any], feat_id: str) -> None:
    wt_mgr: WorktreeManager = ctx["wt_mgr"]
    wt_ctx = wt_mgr.create_isolated_worktree(
        feature_id=feat_id,
        base_env=ctx.get("mock_env", {"PATH": "/usr/bin:/bin"}),
    )
    ctx["wt_ctx"] = wt_ctx


@then(parsers.parse('a git worktree is created on branch "{branch_name}"'))
def then_worktree_branch_created(ctx: Dict[str, Any], branch_name: str) -> None:
    wt_ctx = ctx["wt_ctx"]
    assert wt_ctx.branch_name == branch_name
    assert Path(wt_ctx.worktree_path).exists()


@then('files inside the worktree "specs/" directory are marked read-only')
def then_specs_read_only(ctx: Dict[str, Any]) -> None:
    wt_path = Path(ctx["wt_ctx"].worktree_path)
    feat_file = wt_path / "specs" / "features" / "FEAT-004.feature"
    mode = feat_file.stat().st_mode
    assert (mode & stat.S_IWUSR) == 0


@then(
    parsers.parse(
        'the sanitized environment for "pi" does not contain "{tok1}" or "{tok2}"'
    )
)
def then_env_scrubbed(ctx: Dict[str, Any], tok1: str, tok2: str) -> None:
    env = ctx["wt_ctx"].sanitized_env
    assert tok1 not in env
    assert tok2 not in env


@when("an untrusted process forces a modification to a feature file in the worktree")
def when_force_tamper(ctx: Dict[str, Any]) -> None:
    wt_path = Path(ctx["wt_ctx"].worktree_path)
    feat_file = wt_path / "specs" / "features" / "FEAT-004.feature"
    feat_file.chmod(feat_file.stat().st_mode | stat.S_IWUSR)
    feat_file.write_text("# TAMPERED BY ROGUE AGENT\n", encoding="utf-8")


@then(
    parsers.parse(
        'the Worktree Manager tamper check fails with error "{err_code}"'
    )
)
def then_tamper_check_fails(ctx: Dict[str, Any], err_code: str) -> None:
    wt_mgr: WorktreeManager = ctx["wt_mgr"]
    with pytest.raises(SpecTamperError) as exc_info:
        wt_mgr.verify_no_spec_tampering(ctx["wt_ctx"])
    assert exc_info.value.code == err_code
    wt_mgr.cleanup_worktree(ctx["wt_ctx"].feature_id)


@then(
    parsers.parse(
        'a CRITICAL IssueNode of category "{cat}" is recorded in the Traceability Graph'
    )
)
def then_critical_issue_recorded(ctx: Dict[str, Any], cat: str) -> None:
    store: TraceabilityGraphStore = ctx["store"]
    issues = store.get_open_issues()
    assert any(
        i.severity == IssueSeverity.CRITICAL and i.category.value == cat
        for i in issues
    )


# ============================================================================
# FEAT-005 Steps (Automated PR Review, Security Analysis & Dual-Track Issues)
# ============================================================================


@given("an initialized Security Analyzer, Kanban Board, and Traceability Graph")
def init_security_analyzer_stack(ctx: Dict[str, Any]) -> None:
    store = TraceabilityGraphStore(":memory:")
    adapter = LocalKanbanAdapter(ctx["tmp_path"] / "kanban_sec.json")
    sm = KanbanStateMachine(adapter=adapter, graph_store=store)
    pr_mgr = PullRequestManager(ctx["tmp_path"] / "prs.json")
    analyzer = EnterpriseSecurityAndProdAnalyzer()
    tracker = DualTrackIssueTracker(store, kanban_sm=sm, pr_manager=pr_mgr)
    validator = GraphValidator(store)
    agy = AgyReviewDriver(validator=validator, analyzer=analyzer, issue_tracker=tracker)

    ctx["store"] = store
    ctx["kanban_adapter"] = adapter
    ctx["pr_mgr"] = pr_mgr
    ctx["agy"] = agy


@when(
    parsers.parse(
        '"agy" audits code for "{feat_id}" containing an unauthenticated secret and an HTTP call without a timeout'
    )
)
def when_agy_audits_flawed_code(ctx: Dict[str, Any], feat_id: str) -> None:
    bad_code = '''
import httpx

API_KEY = "ghp_1234567890abcdefghijklmnopqrstuv"

def fetch_data():
    return httpx.get("https://internal.enterprise.local/api/v1/data")
'''
    report = ctx["agy"].review_feature_code(
        feature_id=feat_id,
        code_text=bad_code,
        file_path="src/flawed_service.py",
    )
    ctx["review_report"] = report


@then(
    parsers.parse(
        'the Security Analyzer emits IssueNodes for "{rule1}" and "{rule2}"'
    )
)
def then_analyzer_emits_rules(ctx: Dict[str, Any], rule1: str, rule2: str) -> None:
    store: TraceabilityGraphStore = ctx["store"]
    issues = store.get_open_issues()
    rules = {i.rule_id for i in issues}
    assert rule1 in rules
    assert rule2 in rules


@then(
    parsers.parse(
        'the IssueNodes are linked to "{feat_id}" in the Traceability Graph'
    )
)
def then_issues_linked_to_feature(ctx: Dict[str, Any], feat_id: str) -> None:
    store: TraceabilityGraphStore = ctx["store"]
    issues = store.get_open_issues(feature_id=feat_id)
    assert len(issues) >= 2


@then(
    'corresponding issue cards are created in the Kanban "Issues & Security Findings" column'
)
def then_issue_cards_in_kanban(ctx: Dict[str, Any]) -> None:
    adapter: LocalKanbanAdapter = ctx["kanban_adapter"]
    issue_cards = adapter.list_cards(column="Issues & Security Findings")
    assert len(issue_cards) >= 2


@then(
    parsers.parse(
        'the Pull Request review status for "{feat_id}" is marked as "{expected_status}"'
    )
)
def then_pr_status_marked(
    ctx: Dict[str, Any], feat_id: str, expected_status: str
) -> None:
    assert ctx["review_report"].review_status == expected_status
    pr = ctx["pr_mgr"].get_pull_request(feat_id)
    assert pr is not None
    assert pr.status == expected_status


# ============================================================================
# FEAT-006 Steps (Task Conversation & Design Ledger Tracking)
# ============================================================================


@given("an initialized Task Ledger Manager and Traceability Graph")
def init_task_ledger_stack(ctx: Dict[str, Any]) -> None:
    store = TraceabilityGraphStore(":memory:")
    tasks_dir = ctx["tmp_path"] / "specs" / "tasks"
    ledger = TaskLedgerManager(tasks_base_dir=tasks_dir, graph_store=store)
    ctx["store"] = store
    ctx["tasks_dir"] = tasks_dir
    ctx["ledger"] = ledger


@when(
    parsers.parse(
        'I initialize a Task Ledger for task "{task_id}" on date "{date_str}" with description "{desc}"'
    )
)
def when_init_task_ledger(
    ctx: Dict[str, Any], task_id: str, date_str: str, desc: str
) -> None:
    ledger: TaskLedgerManager = ctx["ledger"]
    ctx["current_task_id"] = task_id
    ctx["task_folder"] = ledger.init_task_ledger(
        task_id=task_id,
        description=desc,
        date_str=date_str,
        problem_id="PROB-001",
    )


@when(
    parsers.parse(
        'I append step "{step_name}" containing a simulated token "{token}"'
    )
)
def when_append_step_with_token(
    ctx: Dict[str, Any], step_name: str, token: str
) -> None:
    ledger: TaskLedgerManager = ctx["ledger"]
    ctx["raw_token"] = token
    ledger.append_step_output(
        task_id=ctx["current_task_id"],
        step_name=step_name,
        markdown_content=f"User provided token {token} during session.",
    )


@when(
    parsers.parse(
        'I append step "{step_name}" containing "{content}"'
    )
)
def when_append_step_content(
    ctx: Dict[str, Any], step_name: str, content: str
) -> None:
    ledger: TaskLedgerManager = ctx["ledger"]
    ledger.append_step_output(
        task_id=ctx["current_task_id"],
        step_name=step_name,
        markdown_content=content,
    )


@then(
    parsers.parse(
        'the task folder "{folder_name}" exists with a "README.md" containing "{task_id}" and "{date_str}"'
    )
)
def then_task_folder_and_readme_exist(
    ctx: Dict[str, Any], folder_name: str, task_id: str, date_str: str
) -> None:
    folder = ctx["tasks_dir"] / folder_name
    assert folder.exists()
    readme_txt = (folder / "README.md").read_text(encoding="utf-8")
    assert task_id in readme_txt
    assert date_str in readme_txt


@then(
    parsers.parse(
        'step file "{step_file}" has redacted the simulated token'
    )
)
def then_step_file_redacted(ctx: Dict[str, Any], step_file: str) -> None:
    file_path = ctx["task_folder"] / step_file
    text = file_path.read_text(encoding="utf-8")
    assert ctx["raw_token"] not in text
    assert "[REDACTED_GITHUB_TOKEN]" in text


@then(
    parsers.parse(
        'TaskJournalNode "{task_id}" is registered in the Traceability Graph with completed steps'
    )
)
def then_task_journal_node_registered(ctx: Dict[str, Any], task_id: str) -> None:
    store: TraceabilityGraphStore = ctx["store"]
    node = store.get_node(task_id)
    assert isinstance(node, TaskJournalNode)
    assert "01-grill-me-conversation.md" in node.steps_completed
    assert "02-system-analysis-design.md" in node.steps_completed


# ============================================================================
# FEAT-007 Steps (Installable Factory Skill & Atomic Task-to-Trello Linking)
# ============================================================================


@given("a temporary agent configuration directory")
def given_temp_agent_config_dir(ctx: Dict[str, Any]) -> None:
    ctx["gemini_config_dir"] = ctx["tmp_path"] / "gemini_config"
    ctx["agents_skills_dir"] = ctx["tmp_path"] / "agents_skills"


@when("the factory skill installer executes setup for the agent configuration directory")
def when_run_skill_installer(ctx: Dict[str, Any]) -> None:
    installer = FactorySkillInstaller(REPO_ROOT)
    ctx["install_report"] = installer.setup_agent_environment(
        gemini_config_dir=ctx["gemini_config_dir"],
        agents_skills_dir=ctx["agents_skills_dir"],
        use_symlinks=False,
    )


@then(
    parsers.parse(
        'the skills "{s1}", "{s2}", and "{s3}" are installed in the skills directory'
    )
)
def then_skills_installed(ctx: Dict[str, Any], s1: str, s2: str, s3: str) -> None:
    skills_dir = ctx["gemini_config_dir"] / "skills"
    for name in (s1, s2, s3):
        skill_md = skills_dir / name / "SKILL.md"
        assert skill_md.exists(), f"Missing {skill_md}"


@then(
    parsers.parse(
        'the MCP configuration file registers the "{server_name}" server'
    )
)
def then_mcp_config_registered(ctx: Dict[str, Any], server_name: str) -> None:
    import json

    mcp_file = ctx["gemini_config_dir"] / "mcp_config.json"
    assert mcp_file.exists()
    data = json.loads(mcp_file.read_text(encoding="utf-8"))
    assert server_name in data.get("mcpServers", {})


@given("an initialized Trello Kanban board with all 8 mandatory factory lists")
def given_initialized_trello_board_8_lists(ctx: Dict[str, Any]) -> None:
    adapter = LocalKanbanAdapter(ctx["tmp_path"] / "trello_board.json")
    lists_map = adapter.init_board_lists()
    assert len(lists_map) == 8
    ctx["kanban_adapter"] = adapter
    ctx["tasks_dir"] = ctx["tmp_path"] / "specs" / "tasks"
    ctx["features_dir"] = ctx["tmp_path"] / "specs" / "features"
    ctx["ledger"] = TaskLedgerManager(
        tasks_base_dir=ctx["tasks_dir"],
        graph_store=ctx["store"],
    )


@when(
    parsers.parse(
        'an agent initializes and links task "{task_id}" and feature "{feat_id}" titled "{title}" on date "{date_str}"'
    )
)
def when_agent_initializes_and_links_task(
    ctx: Dict[str, Any],
    task_id: str,
    feat_id: str,
    title: str,
    date_str: str,
) -> None:
    ledger: TaskLedgerManager = ctx["ledger"]
    res = ledger.create_and_link_task_with_trello(
        task_id=task_id,
        feature_id=feat_id,
        title=title,
        problem_context="Ensure zero-trust validation on all incoming requests.",
        system_design="Validate JWT signature, issuer, audience, and expiry with 5s timeout.",
        scenarios=["Rejecting expired tokens", "Accepting valid tokens"],
        features_dir=ctx["features_dir"],
        kanban_adapter=ctx["kanban_adapter"],
        date_str=date_str,
        problem_id="PROB-001",
        spec_id="SPEC-001",
    )
    ctx["create_link_result"] = res


@then(
    parsers.parse(
        'the task folder "{folder_name}" contains a "README.md" linked to Trello card "{card_id}"'
    )
)
def then_task_folder_linked_to_card(
    ctx: Dict[str, Any], folder_name: str, card_id: str
) -> None:
    readme = ctx["tasks_dir"] / folder_name / "README.md"
    assert readme.exists()
    content = readme.read_text(encoding="utf-8")
    assert f'trello_card_id: "{card_id}"' in content


@then(
    parsers.parse(
        'FeatureNode "{feat_id}" and TaskJournalNode "{task_id}" are linked to "{card_id}" in the Traceability Graph'
    )
)
def then_graph_nodes_linked_to_card(
    ctx: Dict[str, Any], feat_id: str, task_id: str, card_id: str
) -> None:
    store: TraceabilityGraphStore = ctx["store"]
    fnode = store.get_node(feat_id)
    tnode = store.get_node(task_id)
    assert isinstance(fnode, FeatureNode)
    assert isinstance(tnode, TaskJournalNode)
    assert fnode.trello_card_id == card_id
    assert tnode.trello_card_id == card_id


@then(
    parsers.parse(
        'the Trello Kanban board has card "{feat_id}" in column "{col_name}" with complete System Analysis and Acceptance Criteria'
    )
)
def then_kanban_card_has_analysis_and_ac(
    ctx: Dict[str, Any], feat_id: str, col_name: str
) -> None:
    adapter: LocalKanbanAdapter = ctx["kanban_adapter"]
    card = adapter.get_card(feat_id)
    assert card is not None
    assert card.column == col_name
    parser = CardParser()
    assert parser.validate_card_description(card.description) == []


# ============================================================================
# FEAT-008 Steps (Agentic Formal Verification Framework & Gatekeeper)
# ============================================================================


@given("an initialized Formal Verification Pipeline, Kanban State Machine, and Traceability Graph")
def init_formal_verification_stack(ctx: Dict[str, Any]) -> None:
    store = TraceabilityGraphStore(":memory:")
    store.upsert_node(ProblemNode(id="PROB-001", title="Root Problem"))
    store.upsert_node(SystemSpecNode(id="SPEC-001", title="Core Spec", problem_id="PROB-001"))
    store.upsert_node(FeatureNode(id="FEAT-008", title="Formal Verification Feature", spec_id="SPEC-001"))

    adapter = LocalKanbanAdapter(ctx["tmp_path"] / "formal_kanban.json")
    adapter.init_board_lists()
    desc = CardParser.render_card_template(
        feature_id="FEAT-008",
        title="Formal Verification Feature",
        problem_id="PROB-001",
        spec_id="SPEC-001",
        problem_context="Mathematically verify constant-time ratchet step.",
        system_design="3-stage Lean 4 formal verification with trusted processor model and Gatekeeper.",
        feature_file_path="specs/features/FEAT-008-formal-verification-framework.feature",
        scenarios=["Drafting Lean spec", "Lifting Rust code", "Gatekeeper proof check"],
    )
    adapter.upsert_card(
        KanbanCard(
            card_id="CARD-FEAT-008",
            feature_id="FEAT-008",
            title="[FEAT-008] Formal Verification Feature",
            description=desc,
            column="1. Problem & Spec Backlog",
        )
    )
    sm = KanbanStateMachine(adapter=adapter, graph_store=store)
    formal_dir = ctx["tmp_path"] / "specs" / "formal"

    ctx["store"] = store
    ctx["kanban_adapter"] = adapter
    ctx["kanban_sm"] = sm
    ctx["formal_dir"] = formal_dir
    ctx["spec_pipeline"] = FormalSpecPipeline(
        formal_specs_dir=formal_dir,
        graph_store=store,
        kanban_sm=sm,
    )
    ctx["code_modeler"] = ExecutableLeanCodeModeler(
        formal_specs_dir=formal_dir,
        graph_store=store,
    )
    ctx["gatekeeper"] = FormalGatekeeper(lean_binary=None)


@given(
    parsers.parse(
        'research paper reference "{paper_ref}" for feature "{feat_id}"'
    )
)
def given_paper_reference(ctx: Dict[str, Any], paper_ref: str, feat_id: str) -> None:
    ctx["paper_ref"] = paper_ref
    ctx["formal_feat_id"] = feat_id


@when(
    parsers.parse(
        'the untrusted Spec-writer and Reviewer agents draft Lean spec "{fspec_id}" with obligation "{obligation}"'
    )
)
def when_draft_lean_spec(
    ctx: Dict[str, Any], fspec_id: str, obligation: str
) -> None:
    pipeline: FormalSpecPipeline = ctx["spec_pipeline"]
    node = pipeline.draft_lean_spec(
        formal_spec_id=fspec_id,
        feature_id=ctx["formal_feat_id"],
        title=f"Lean Spec {fspec_id}",
        paper_references=[ctx["paper_ref"]],
        theorem_obligations=[obligation],
    )
    ctx["fspec_node"] = node


@then(
    parsers.parse(
        'FormalSpecNode "{fspec_id}" is marked untrusted and card "{feat_id}" waits in "{expected_col}"'
    )
)
def then_fspec_untrusted_and_card_waiting(
    ctx: Dict[str, Any], fspec_id: str, feat_id: str, expected_col: str
) -> None:
    store: TraceabilityGraphStore = ctx["store"]
    node = store.get_node(fspec_id)
    assert isinstance(node, FormalSpecNode)
    assert node.trusted is False
    card = ctx["kanban_adapter"].get_card(feat_id)
    assert card is not None
    assert card.column == expected_col


@when(
    parsers.parse(
        'authorized user "{member}" approves Lean spec "{fspec_id}" via Human Decision'
    )
)
def when_human_approves_lean_spec(
    ctx: Dict[str, Any], member: str, fspec_id: str
) -> None:
    pipeline: FormalSpecPipeline = ctx["spec_pipeline"]
    pipeline.approve_and_lock_spec(formal_spec_id=fspec_id, approved_by=member)


@then(
    parsers.parse(
        'FormalSpecNode "{fspec_id}" becomes trusted with a locked 64-character SHA-256 checksum'
    )
)
def then_fspec_trusted_and_locked(ctx: Dict[str, Any], fspec_id: str) -> None:
    store: TraceabilityGraphStore = ctx["store"]
    node = store.get_node(fspec_id)
    assert isinstance(node, FormalSpecNode)
    assert node.trusted is True
    assert len(node.spec_sha256) == 64


@given(
    parsers.parse(
        'Rust source code for "{feat_id}" implementing a constant-time word comparison'
    )
)
def given_rust_source_code(ctx: Dict[str, Any], feat_id: str) -> None:
    rust_file = ctx["tmp_path"] / "ratchet_ct.rs"
    rust_file.write_text(
        "pub fn ct_eq_u64(a: u64, b: u64) -> u64 {\n"
        "    let diff = a ^ b;\n"
        "    ((diff | diff.wrapping_neg()) >> 63) ^ 1\n"
        "}\n",
        encoding="utf-8",
    )
    ctx["rust_source_file"] = rust_file
    ctx["formal_feat_id"] = feat_id


@when(
    parsers.parse(
        'the Executable Lean Code Modeler compiles and lifts the Rust code for "{feat_id}"'
    )
)
def when_lift_rust_code(ctx: Dict[str, Any], feat_id: str) -> None:
    modeler: ExecutableLeanCodeModeler = ctx["code_modeler"]
    cmod = modeler.lift_source_to_lean_model(
        code_model_id="CMOD-008",
        feature_id=feat_id,
        source_path=ctx["rust_source_file"],
        source_language="rust",
    )
    ctx["cmod_node"] = cmod


@then(
    parsers.parse(
        'a trusted CodeModelNode "{cmod_id}" is registered with compiled machine instructions and a Lean processor state model'
    )
)
def then_cmod_registered_with_processor_model(
    ctx: Dict[str, Any], cmod_id: str
) -> None:
    store: TraceabilityGraphStore = ctx["store"]
    node = store.get_node(cmod_id)
    assert isinstance(node, CodeModelNode)
    assert node.trusted is True
    assert len(node.model_sha256) == 64
    model_txt = Path(node.lean_model_path).read_text(encoding="utf-8")
    assert "structure ProcessorState" in model_txt
    assert "def compiledMachineCode" in model_txt
    assert "def runCompiledCode" in model_txt


@given(
    parsers.parse(
        'trusted FormalSpecNode "{fspec_id}" and trusted CodeModelNode "{cmod_id}" for "{feat_id}"'
    )
)
def given_trusted_fspec_and_cmod(
    ctx: Dict[str, Any], fspec_id: str, cmod_id: str, feat_id: str
) -> None:
    pipeline: FormalSpecPipeline = ctx["spec_pipeline"]
    pipeline.draft_lean_spec(
        formal_spec_id=fspec_id,
        feature_id=feat_id,
        title="Trusted Ratchet Spec",
        paper_references=["Signal PQXDH v1"],
        theorem_obligations=["constant_time_ratchet_step"],
    )
    fspec = pipeline.approve_and_lock_spec(fspec_id, approved_by="tech_lead_01")

    rust_file = ctx["tmp_path"] / "ratchet.rs"
    rust_file.write_text("pub fn ratchet(x: u64) -> u64 { x }\n", encoding="utf-8")
    cmod = ctx["code_modeler"].lift_source_to_lean_model(
        code_model_id=cmod_id,
        feature_id=feat_id,
        source_path=rust_file,
        source_language="rust",
    )
    ctx["fspec_node"] = fspec
    ctx["cmod_node"] = cmod


@when(
    parsers.parse(
        'the Prover Team submits an initial candidate proof containing "{bad_tok}" and a subsequent sound proof for "{obligation}"'
    )
)
def when_prover_team_runs_two_rounds(
    ctx: Dict[str, Any], bad_tok: str, obligation: str
) -> None:
    coord = ProverTeamCoordinator(
        proofs_base_dir=ctx["tmp_path"] / "proofs",
        gatekeeper=ctx["gatekeeper"],
        graph_store=ctx["store"],
        max_proof_rounds=3,
    )

    def mock_prover_team(round_idx: int, _diagnostics: list[str]) -> str:
        if round_idx == 1:
            return (
                f"namespace FactoryFormal.FEAT_008\n"
                f"theorem {obligation} (s : Nat) : {obligation}_prop s s := by\n"
                f"  {bad_tok}\n"
                f"end FactoryFormal.FEAT_008\n"
            )
        return (
            f"-- Round 2: Fixed after Gatekeeper rejected escape hatch\n"
            f"namespace FactoryFormal.FEAT_008\n"
            f"theorem {obligation} (s : Nat) : {obligation}_prop s s := by\n"
            f"  rfl\n"
            f"end FactoryFormal.FEAT_008\n"
        )

    res = coord.run_prover_loop(
        theorem_proof_id="THM-008",
        formal_spec=ctx["fspec_node"],
        code_model=ctx["cmod_node"],
        candidate_generator=mock_prover_team,
    )
    ctx["prover_result"] = res


@then(
    parsers.parse(
        'the Gatekeeper rejects round 1 due to forbidden escape hatch "{bad_tok}" and accepts round 2'
    )
)
def then_gatekeeper_rejects_round1_accepts_round2(
    ctx: Dict[str, Any], bad_tok: str
) -> None:
    res = ctx["prover_result"]
    assert res.rounds_used == 2
    assert res.verdict_history[0].passed is False
    assert bad_tok in res.verdict_history[0].forbidden_constructs_found
    assert res.verdict_history[1].passed is True
    assert res.final_verdict.status == "VERIFIED"


@then(
    parsers.parse(
        'a verified TheoremProofNode "{thm_id}" is linked to "{fspec_id}" and "{cmod_id}" in the Traceability Graph'
    )
)
def then_theorem_proof_node_linked(
    ctx: Dict[str, Any], thm_id: str, fspec_id: str, cmod_id: str
) -> None:
    store: TraceabilityGraphStore = ctx["store"]
    node = store.get_node(thm_id)
    assert isinstance(node, TheoremProofNode)
    assert node.gatekeeper_status == "VERIFIED"
    g = store.to_networkx()
    assert g.has_edge(fspec_id, thm_id)
    assert g.has_edge(cmod_id, thm_id)


