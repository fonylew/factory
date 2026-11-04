---
id: "SPEC-001"
title: "Core Enterprise Multi-Agent Software Factory Specification"
problem_id: "PROB-001"
adr_ids:
  - "ADR-001"
status: "LOCKED"
version: "1.0.0"
---

# System Architecture Specification (`SPEC-001`)

## 1. Subsystems Overview
1. **Traceability Graph (`src/factory/graph/`)**:
   - Models: `ProblemNode`, `DecisionNode`, `SystemSpecNode`, `FeatureNode`, `CodeArtifactNode`, `IssueNode`, `TaskJournalNode`.
   - Storage: SQLite WAL database + NetworkX directed graph + deterministic JSON-LD & Mermaid exporters.
   - Validation: Orphan detection (`ORPHAN_FEATURE_ERROR`, `ORPHAN_CODE_ERROR`), invariant checking, and downstream blast-radius impact analysis.
2. **Task Conversation & Design Ledger (`src/factory/journal/`)**:
   - Manages `specs/tasks/<YYYY-MM-DD>_<TASK-ID>_<slug>/` with `README.md` (frontmatter: `task_id`, `date`, `description`, `status`) and step files `01` through `05`.
   - Applies secret redaction before persisting any output.
3. **Trello Kanban & HITL Engine (`src/factory/kanban/`)**:
   - Validates mandatory card sections (`## 1. Problem Context & Goal`, `## 2. System Analysis & Enterprise Design`, `## 3. Acceptance Criteria (Gherkin Reference)`, `## 4. Open Questions / Need Decision`, `## 5. Human Decision`).
   - Enforces the 7-column state machine and member-ID authorization on `Human Decision` transitions.
4. **Git Worktree Sandbox & PR Manager (`src/factory/git_ops/`)**:
   - Creates isolated worktrees (`worktrees/feat-<ID>`), applies read-only permissions to `specs/`, verifies SHA-256 checksums before/after `pi` execution, and manages branches/PRs.
5. **Language-Agnostic Gherkin BDD Runner (`src/factory/bdd/`)**:
   - Parses `.feature` files to extract scenarios and executes configured test adapters (`pytest-bdd`, `cucumber-js`, `godog`).
6. **Multi-Agent Drivers & Security Analyzer (`src/factory/agents/`, `src/factory/analyzer/`)**:
   - `pi_driver.py`: Scrubs secrets from env, enforces `max_iterations_per_task` circuit breaker, and executes `pi` in the isolated worktree.
   - `agy_driver.py` & `security_scanner.py`: Executes static/secret/production-readiness analysis (missing timeouts, hardcoded secrets, SQL injection, unbounded retries, spec drift) and dual-tracks `IssueNode`s to the Graph, Trello, and PR reviews.
