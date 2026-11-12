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
  - **`agy` (Gemini 4 Argon / Carbon)**: Runs `/grill-me`, writes specs & `.feature` files, manages Trello decisions, and audits PRs for STRIDE security flaws and production failure modes.
  - **`pi`**: Runs in isolated Git worktrees (`worktrees/feat-XXX`) with all tokens/secrets scrubbed from its environment.
- **3-Stage Agentic Formal Verification Framework (`src/factory/formal/`)**:
  1. **`1 Specification`**: Untrusted Spec-writer & Reviewer agents draft `Spec.lean` from research papers; elevated to **Trusted** (SHA-256 locked) only after Human Approval via Trello `Need Decision` $\rightarrow$ `Human Decision`.
  2. **`2 Code`**: Compiles/lifts Rust or systems code (`rustc --emit=asm`) into compiled machine instructions running on a **Trusted Lean Processor Model** (`CodeModel.lean`).
  3. **`3 Proof`**: Multi-agent **Prover team** synthesizes proofs against a deterministic **Gatekeeper** (`FormalGatekeeper`) that bans `sorry`, `admit`, `axiom`, `unsafe`, and `native_decide`, certifying **`TheoremProofNode`** (`THM-XXX`).

---

## 2. Quickstart & User / Agent Interaction

```bash
# 1. Install the Software Factory Skills & MCP Server globally for agy (~/.gemini/config/)
uv run factory setup-skills

# 2. Initialize the Traceability Graph, Kanban Board, and deterministic exports
uv run factory init

# 3. Provision all 8 mandatory lists on your Trello Board (and optionally push existing cards)
uv run factory trello init-board --sync-cards

# 4. Atomically create a Task Ledger, Gherkin .feature, Graph nodes, AND linked Trello Card
uv run factory task create \
  --task-id TASK-003 \
  --feature-id FEAT-008 \
  --title "Design payment webhook idempotency service" \
  --problem-context "Prevent duplicate webhook charges on network retries." \
  --system-design "HMAC-SHA256 verification + SQLite WAL idempotency key with 10s timeout." \
  --scenario "Rejecting duplicate webhook delivery"

# 5. Link an existing Task Ledger & Feature to a Trello Card ID
uv run factory task link-trello TASK-002 FEAT-007

# 6. Escalate an architectural question to Trello '2. Need Decision'
uv run factory trello ask-decision FEAT-008 ADR-011 "Fail-open or fail-closed on lock timeout?" \
  -o "Option A: Fail-closed (HTTP 503)" \
  -o "Option B: Queue to dead-letter table"

# 7. Poll Trello '3. Human Decision' column, record ADRs, and unlock Ready for Dev
uv run factory sync --task-id TASK-003

# 8. Dispatch `pi` coding agent inside an isolated Git worktree (`worktrees/feat-FEAT-008`)
uv run factory run-pi FEAT-008 --task-id TASK-003 --prompt "Implement step defs and service for FEAT-008"

# 9. Audit a file for STRIDE security & production readiness issues using agy driver
uv run factory audit FEAT-007 src/factory/installer.py --task-id TASK-002

# 10. Run the self-hosted Gherkin BDD regression suite (12 scenarios across FEAT-001..FEAT-007)
uv run --extra dev pytest -v
```

---

## 3. Configuring Trello & Git Authentication

Copy `.env.example` to `.env` and populate your credentials when ready (never exposed to `pi`):
```bash
cp .env.example .env
```
To expose the Factory tools directly to `agy` via Model Context Protocol (MCP), register `uv run python -m factory.mcp_server` in your Antigravity MCP settings.
