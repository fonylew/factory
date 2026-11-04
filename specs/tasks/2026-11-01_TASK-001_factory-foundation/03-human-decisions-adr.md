# Step 03: Human Decisions & Architecture Decision Records (`TASK-001`)

- **Task ID**: `TASK-001`
- **Date**: `2026-11-01`
- **Decided By**: Technical Lead / System Analyst
- **Status**: APPROVED

---

## Recorded Decisions (`ADR-001` through `ADR-009`)

### `ADR-001`: Primary Scope — Reusable Software Factory Platform
- **Question**: Are we building the reusable Multi-Agent Software Factory platform itself inside `/home/aimet/projects/factory`, or a target app?
- **Decision**: Build the reusable Multi-Agent Software Factory System itself inside `/home/aimet/projects/factory`, self-hosted using its own Gherkin specs and task ledger.

### `ADR-002`: Embedded Traceability Graph Engine
- **Question**: How should the Requirement-Feature-Code-Issue traceability graph be stored and queried?
- **Decision**: Local embedded SQLite + NetworkX graph with automatic deterministic export to `specs/graph/traceability.json` (JSON-LD) and `specs/graph/traceability.mmd` (Mermaid) tracked in Git.

### `ADR-003`: MCP & CLI Integration for Trello and Git
- **Question**: How should the factory connect to Trello and Git?
- **Decision**: Expose both a CLI (`factory`) and an MCP Server (`factory-mcp`) with pluggable Trello REST/Local adapters so authentication tokens can be supplied via `.env` when ready.

### `ADR-004`: Language-Agnostic Gherkin BDD Runner
- **Question**: What stack should run Gherkin `.feature` tests?
- **Decision**: Language-agnostic BDD runner configured via `factory.yaml` adapters (`pytest-bdd`, `cucumber-js`, `godog`, or container runner), using `pytest-bdd` for self-hosting the factory itself.

### `ADR-005`: Dual Problem-Anchor & Read-Only Spec Lock
- **Question**: How do we prevent specification drift and test tampering?
- **Decision**: Enforce both: (1) Graph Validator rejects any `FeatureNode` or `CodeArtifactNode` without a valid path to an active `ProblemNode`, and (2) `specs/` and `.feature` files are locked read-only and verified via SHA-256 checksums during `pi` coding runs.

### `ADR-006`: Isolated Git Worktrees & Zero-Secret Sandbox for `pi`
- **Question**: How should `pi` coding executions be isolated from `agy`?
- **Decision**: Each `pi` task runs in an isolated git worktree (`worktrees/feat-XXX`) with all sensitive environment variables (`TRELLO_TOKEN`, `GITHUB_TOKEN`, etc.) stripped.

### `ADR-007`: Dual-Track Security & Production Issue Tracking
- **Question**: How are security flaws and production risks tracked?
- **Decision**: Dual-track every finding as an `IssueNode` (`ISS-XXX`) in the Traceability Graph AND sync it to Trello (`Issues & Security Findings` / card labels) and Git PR review comments.

### `ADR-008`: 7-Column Trello Kanban State Machine & HITL Decision Flow
- **Question**: How does the human-in-the-loop decision flow operate on Trello?
- **Decision**: Use the 7-column board (`1. Problem & Spec Backlog`, `2. Need Decision`, `3. Human Decision`, `4. Ready for Dev (Spec Locked)`, `5. In Progress (pi Coding)`, `6. PR & Security Review (agy)`, `7. Done / Verified`). Cards require System Analysis, Design, and Acceptance Criteria; human decisions are read from `## 5. Human Decision` when moved to `3. Human Decision`.

### `ADR-009`: Git-Tracked Task Conversation & Step Ledger (`specs/tasks/`)
- **Question**: Where and how should we store per-task conversations, design docs, and step outputs?
- **Decision**: Create `specs/tasks/<YYYY-MM-DD>_<TASK-ID>_<slug>/` containing `README.md` (with Task ID, date, and description) and numbered step files (`01-grill-me-conversation.md` through `05-agy-security-pr-review.md`), registered as a `TaskJournalNode` in the Traceability Graph.
