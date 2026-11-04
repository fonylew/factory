# Enterprise Multi-Agent Spec-Driven Software Factory (`factory`)

> **Core Axiom**: *"Code can change; the Specification and Traceability Graph are what remain."*

An enterprise-grade, spec-driven multi-agent software factory designed for **Technical Leads** and **System Analysts**. It pairs **`agy` (with Gemini 4 Argon)** for interactive `/grill-me` problem discovery, system analysis, Gherkin specification authoring, and security/production PR review with **`pi`** for sandboxed coding inside isolated Git worktrees.

---

## 1. Key Capabilities

- **Grill-Me Problem Anchor & Spec Lock**: Every feature (`FEAT-XXX`) and code artifact (`CODE-XXX`) must trace back to a verified root `ProblemNode` (`PROB-XXX`) and `SystemSpecNode` (`SPEC-XXX`). `specs/` and `.feature` files are locked read-only and verified via SHA-256 checksums during coding.
- **Embedded Traceability Graph (`SQLite + NetworkX + Git JSON-LD/Mermaid`)**: Tracks Problems, ADRs (`DecisionNode`), System Specs, Gherkin Features, Code Artifacts, Task Ledgers (`TaskJournalNode`), and Security/Production Issues (`IssueNode`). Automatically exports deterministic snapshots to `specs/graph/traceability.json` and `specs/graph/traceability.mmd`.
- **7-Column Trello Kanban State Machine & Human-in-the-Loop**:
  1. `1. Problem & Spec Backlog`
  2. `2. Need Decision`
  3. `3. Human Decision`
  4. `4. Ready for Dev (Spec Locked)`
  5. `5. In Progress (pi Coding)`
  6. `6. PR & Security Review (agy)`
  7. `7. Done / Verified`
  *(Plus `Issues & Security Findings` for dual-tracked security/production issues).*
- **Step-by-Step Task Conversation & Design Ledger (`specs/tasks/`)**: Every task maintains a Git-versioned folder `specs/tasks/<YYYY-MM-DD>_<TASK-ID>_<slug>/` containing `README.md` and step outputs (`01-grill-me-conversation.md` through `05-agy-security-pr-review.md`) with automatic secret redaction.
- **Role & Privilege Separation (`agy` vs `pi`)**:
  - **`agy` (Gemini 4 Argon)**: Runs `/grill-me`, writes specs & `.feature` files, manages Trello decisions, and audits PRs for STRIDE security flaws and production failure modes.
  - **`pi`**: Runs in isolated Git worktrees (`worktrees/feat-XXX`) with all tokens/secrets scrubbed from its environment.

---

## 2. Quickstart & User Interaction

```bash
# 1. Initialize the Traceability Graph, Kanban Board, and deterministic exports
uv run factory init

# 2. View system status, graph traceability, orphan checks, and open issues
uv run factory status

# 3. Start a new Task Ledger folder (records Task ID, date, description)
uv run factory task new TASK-002 "Design payment webhook idempotency service"

# 4. Append a step output (e.g., from Grill-Me or System Analysis)
uv run factory task log-step TASK-002 01-grill-me-conversation "Problem statement & invariants..."

# 5. Poll Trello '3. Human Decision' column, record ADRs, and unlock Ready for Dev
uv run factory sync

# 6. Audit a file for STRIDE security & production readiness issues using agy driver
uv run factory audit FEAT-005 src/factory/kanban/trello_client.py --task-id TASK-001

# 7. Run the self-hosted Gherkin BDD regression suite
uv run --extra dev pytest -v
```

---

## 3. Configuring Trello & Git Authentication

Copy `.env.example` to `.env` and populate your credentials when ready (never exposed to `pi`):
```bash
cp .env.example .env
```
To expose the Factory tools directly to `agy` via Model Context Protocol (MCP), register `uv run python -m factory.mcp_server` in your Antigravity MCP settings.
