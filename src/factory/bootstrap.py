"""Self-Hosting Bootstrapper populating the Traceability Graph & Kanban Board from `specs/`."""

from __future__ import annotations

from pathlib import Path

from factory.bdd.gherkin_parser import GherkinParser
from factory.config import FactoryConfig
from factory.graph.models import (
    CodeArtifactNode,
    DecisionNode,
    EdgeType,
    FeatureNode,
    ProblemNode,
    SystemSpecNode,
    TaskJournalNode,
)
from factory.graph.store import TraceabilityGraphStore
from factory.graph.validator import GraphValidator
from factory.kanban.card_parser import CardParser
from factory.kanban.trello_client import KanbanCard, LocalKanbanAdapter


def bootstrap_factory_graph(
    repo_root: Path,
    config: FactoryConfig,
    store: TraceabilityGraphStore,
    kanban: LocalKanbanAdapter,
) -> None:
    """Seeds PROB-001, ADR-001, SPEC-001, TASK-001, TASK-002, FEAT-001..007, and CODE-001..007."""
    validator = GraphValidator(store)
    kanban.init_board_lists(config.kanban.columns)

    # 1. Root ProblemNode
    prob = ProblemNode(
        id="PROB-001",
        title="Enterprise Multi-Agent Spec-Driven Software Delivery Without Drift or Security Erosion",
        statement=(
            "Prevent coding agent drift, test tampering, and security/production flaws by enforcing "
            "a Traceability Graph, immutable Gherkin specifications, Trello HITL decisions, and role separation."
        ),
        business_impact="Eliminates unreviewed security flaws and specification drift in agentic delivery.",
        invariants=[
            "INV-01: Every FeatureNode and CodeArtifactNode must link to an active ProblemNode.",
            "INV-02: Coding agents (pi) cannot modify specs/ or .feature files.",
            "INV-03: Coding agents (pi) run in isolated Git worktrees without secrets.",
            "INV-04: Trello cards require System Analysis, Design, and Gherkin AC.",
            "INV-05: Every PR is audited by agy (Gemini 4 Argon) for STRIDE & production risks.",
            "INV-06: Every task maintains a step-by-step markdown journal in specs/tasks/.",
        ],
    )
    store.upsert_node(prob)

    # 2. Foundational DecisionNodes
    adr1 = DecisionNode(
        id="ADR-001",
        title="Foundational Architecture Decisions for Spec-Driven Software Factory",
        problem_id="PROB-001",
        question="Core architecture for Graph, Trello Kanban, Worktree isolation, BDD, and Task Ledgers",
        chosen_option="SQLite+NetworkX Graph, 7-Column Trello State Machine, Git Worktrees for pi, Gemini 4 Argon for agy",
        rationale="Zero-ops ACID traceability with strict privilege separation between planning/review and coding.",
        decided_by="Technical Lead / System Analyst",
        trello_card_id="CARD-TASK-001",
    )
    store.upsert_node(adr1)

    adr10 = DecisionNode(
        id="ADR-010",
        title="Agent Skill Installation & Atomic Task-to-Trello Linking",
        problem_id="PROB-001",
        question="How should agents discover factory skills and initialize/link tasks with Trello?",
        chosen_option="Installable software-factory skill + MCP config via `factory setup-skills` and atomic `factory task create` / `link-trello`",
        rationale="Enables zero-friction agent discovery across sessions and atomic Task <-> Graph <-> Trello synchronization.",
        decided_by="Technical Lead / System Analyst",
        trello_card_id="CARD-FEAT-007",
    )
    store.upsert_node(adr10)

    # 3. Core SystemSpecNode
    spec_path = repo_root / "specs/architecture/SPEC-001-core-factory.md"
    spec_hash = validator.compute_file_sha256(spec_path) if spec_path.exists() else ""
    spec = SystemSpecNode(
        id="SPEC-001",
        title="Core Enterprise Multi-Agent Software Factory Specification",
        problem_id="PROB-001",
        component="factory-core",
        architecture_md="specs/architecture/SPEC-001-core-factory.md",
        nfrs=[
            "Explicit timeouts on all external HTTP calls",
            "SQLite WAL concurrency and deterministic JSON-LD/Mermaid exports",
            "Max 3 coding iterations circuit breaker",
        ],
        security_constraints=[
            "STRIDE threat mitigation",
            "Secret redaction on Trello & Task Ledgers",
            "POSIX read-only + SHA-256 tamper guard on specs/",
        ],
        version_hash=spec_hash,
    )
    store.upsert_node(spec)
    store.add_edge("ADR-001", "SPEC-001", EdgeType.MODIFIES_SPEC)
    store.add_edge("ADR-010", "SPEC-001", EdgeType.MODIFIES_SPEC)

    # 4. TaskJournalNodes for TASK-001 and TASK-002
    task1 = TaskJournalNode(
        id="TASK-001",
        task_id="TASK-001",
        title="TASK-001: Multi-Agent Spec-Driven Software Factory Foundation",
        date="2026-11-01",
        description="Grill-Me Problem Discovery, Enterprise Architecture Design, and Self-Hosting Foundation",
        journal_dir="specs/tasks/2026-11-01_TASK-001_factory-foundation",
        problem_id="PROB-001",
        steps_completed=[
            "01-grill-me-conversation.md",
            "02-system-analysis-design.md",
            "03-human-decisions-adr.md",
            "04-pi-execution-summary.md",
            "05-agy-security-pr-review.md",
        ],
        trello_card_id="CARD-TASK-001",
    )
    store.upsert_node(task1)

    task2 = TaskJournalNode(
        id="TASK-002",
        task_id="TASK-002",
        title="TASK-002: Agent Interaction Protocol, Installable Factory Skill & Trello Task Linking",
        date="2026-11-05",
        description="Agent Interaction Protocol, Installable Factory Skills, and Bidirectional Trello Task Initialization & Linking",
        journal_dir="specs/tasks/2026-11-05_TASK-002_agent-skill-and-trello-linking",
        problem_id="PROB-001",
        steps_completed=[
            "01-grill-me-conversation.md",
            "02-system-analysis-design.md",
            "03-human-decisions-adr.md",
            "04-pi-execution-summary.md",
            "05-agy-security-pr-review.md",
        ],
        trello_card_id="CARD-FEAT-007",
    )
    store.upsert_node(task2)

    task3 = TaskJournalNode(
        id="TASK-003",
        task_id="TASK-003",
        title="TASK-003: Agentic Formal Verification Framework & Skills",
        date="2026-11-12",
        description="Agentic Formal Verification Framework (Lean Spec, Machine Code Processor Model, Multi-Agent Prover Team & Trusted Gatekeeper) and Skills",
        journal_dir="specs/tasks/2026-11-12_TASK-003_formal-verification-framework",
        problem_id="PROB-001",
        steps_completed=[
            "01-grill-me-conversation.md",
            "02-system-analysis-design.md",
            "03-human-decisions-adr.md",
            "04-pi-execution-summary.md",
            "05-agy-security-pr-review.md",
            "06-formal-verification-proofs.md",
        ],
        trello_card_id="CARD-FEAT-008",
    )
    store.upsert_node(task3)

    # 5. FeatureNodes & CodeArtifactNodes from specs/features/*.feature
    feature_code_map = {
        "FEAT-001": ("src/factory/graph/validator.py", "GraphValidator", "TASK-001"),
        "FEAT-002": ("src/factory/graph/store.py", "TraceabilityGraphStore", "TASK-001"),
        "FEAT-003": ("src/factory/kanban/state_machine.py", "KanbanStateMachine", "TASK-001"),
        "FEAT-004": ("src/factory/git_ops/worktree.py", "WorktreeManager", "TASK-001"),
        "FEAT-005": ("src/factory/analyzer/security_scanner.py", "EnterpriseSecurityAndProdAnalyzer", "TASK-001"),
        "FEAT-006": ("src/factory/journal/task_ledger.py", "TaskLedgerManager", "TASK-001"),
        "FEAT-007": ("src/factory/installer.py", "FactorySkillInstaller", "TASK-002"),
        "FEAT-008": ("src/factory/formal/gatekeeper.py", "FormalGatekeeper", "TASK-003"),
    }

    features_dir = repo_root / config.project.features_dir
    for feat_file in sorted(features_dir.glob("FEAT-*.feature")):
        parsed = GherkinParser.parse_file(feat_file)
        feat_id = next((t for t in parsed.tags if t.startswith("FEAT-")), feat_file.stem[:8])
        rel_path = str(feat_file.relative_to(repo_root))
        checksum = validator.compute_file_sha256(feat_file)
        linked_task_id = feature_code_map.get(feat_id, ("", "", "TASK-001"))[2]

        feat_node = FeatureNode(
            id=feat_id,
            title=parsed.feature_title,
            spec_id="SPEC-001",
            feature_file_path=rel_path,
            scenarios=parsed.scenarios,
            spec_checksum=checksum,
            trello_card_id=f"CARD-{feat_id}",
            status="DONE_VERIFIED",
        )
        store.upsert_node(feat_node)
        store.add_edge(feat_id, linked_task_id, EdgeType.LOGGED_IN)

        # Register corresponding CodeArtifactNode
        if feat_id in feature_code_map:
            code_path, sym, _ = feature_code_map[feat_id]
            code_node = CodeArtifactNode(
                id=f"CODE-{feat_id[-3:]}",
                title=f"{sym} ({code_path})",
                feature_id=feat_id,
                file_path=code_path,
                symbol_name=sym,
                git_branch=f"feat/{feat_id}",
                pr_number=int(feat_id[-1]),
            )
            store.upsert_node(code_node)

        # Seed Kanban Card
        card_desc = CardParser.render_card_template(
            feature_id=feat_id,
            title=parsed.feature_title,
            problem_id="PROB-001",
            spec_id="SPEC-001",
            problem_context="Addresses PROB-001 enterprise spec-driven governance & drift prevention.",
            system_design=f"Implemented in `{feature_code_map.get(feat_id, ('src/factory', '', ''))[0]}` with full STRIDE & production checks.",
            feature_file_path=rel_path,
            scenarios=parsed.scenarios,
            spec_sha256=checksum,
        )
        kanban.upsert_card(
            KanbanCard(
                card_id=f"CARD-{feat_id}",
                feature_id=feat_id,
                title=f"[{feat_id}] {parsed.feature_title}",
                description=card_desc,
                column=config.kanban.columns.done,
                labels=["enterprise-spec", "verified", linked_task_id],
                last_modified_by="agy",
                task_id=linked_task_id,
            )
        )

    # Export deterministic Graph snapshots
    store.export_json_ld(repo_root / config.project.graph_json_export)
    store.export_mermaid(repo_root / config.project.graph_mermaid_export)
