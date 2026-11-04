# Step 02: System Analysis & Enterprise Architecture Design (`TASK-001`)

- **Task ID**: `TASK-001`
- **Date**: `2026-11-01`
- **System Analyst**: `agy` (Gemini 4 Argon)
- **Linked Problem**: `PROB-001`
- **Linked Spec**: `SPEC-001`

---

## 1. System Context & Role Separation
The Software Factory enforces a strict separation of duties between **high-reasoning governance/review (`agy` with Gemini 4 Argon)** and **untrusted sandboxed code execution (`pi`)**:

1. **Control & Governance Plane (`agy` + Gemini 4 Argon)**:
   - Runs `/grill-me` discovery, writes System Analysis & Design specs, authors Gherkin `.feature` files, manages the Trello Kanban board, and conducts security/production PR reviews.
2. **Traceability & State Plane (`SQLite + NetworkX + Git JSON-LD/Mermaid`)**:
   - Maintains a directed graph connecting `ProblemNode` $\rightarrow$ `SystemSpecNode` $\rightarrow$ `FeatureNode` $\rightarrow$ `CodeArtifactNode`, governed by `DecisionNode` (`ADR-`) and audited by `IssueNode` (`ISS-`) and `TaskJournalNode` (`TASK-`).
3. **Sandboxed Execution Plane (`pi` in Git Worktrees)**:
   - Executes inside `worktrees/feat-<ID>` with all secrets scrubbed from its environment (`TRELLO_TOKEN`, `GITHUB_TOKEN`, etc. removed) and `specs/` marked read-only + verified via SHA-256 checksums.

---

## 2. User Interaction Surfaces
1. **Interactive CLI & MCP (`factory` / `agy`)**:
   - Tech Leads / System Analysts start tasks via `factory task new` or `/grill-me` inside `agy`.
2. **Trello Kanban Board (7 Columns)**:
   - `1. Problem & Spec Backlog` $\rightarrow$ `2. Need Decision` $\rightarrow$ `3. Human Decision` $\rightarrow$ `4. Ready for Dev (Spec Locked)` $\rightarrow$ `5. In Progress (pi Coding)` $\rightarrow$ `6. PR & Security Review (agy)` $\rightarrow$ `7. Done / Verified`.
3. **Git Pull Requests & `specs/tasks/` Ledger**:
   - Every feature produces an auditable PR and a 5-step markdown journal in `specs/tasks/<YYYY-MM-DD>_<TASK-ID>_<slug>/`.

---

## 3. Enterprise Security (STRIDE) & Production Readiness Analysis

| Threat / Production Hazard | STRIDE / Risk Category | Mitigation Implemented in `SPEC-001` |
| :--- | :--- | :--- |
| **Prompt Injection via Trello `Human Decision`** | Tampering / Elevation of Privilege | Validate Trello member ID against `TRELLO_AUTHORIZED_MEMBERS` allowlist; wrap external text in `<untrusted_trello_input>` tags; never pass raw Trello text as shell arguments. |
| **`pi` Agent Tampering with `.feature` Files** | Tampering / Integrity | Apply `chmod -R a-w specs/` inside worktree before spawning `pi` AND verify cryptographic SHA-256 checksums of all files in `specs/` after `pi` exits. Abort PR and raise `CRITICAL` `IssueNode` on mismatch. |
| **Credential / Secret Leakage to Trello or Git** | Information Disclosure | Redact API keys, Bearer tokens, PEM blocks, and high-entropy secrets in `SecretSanitizer` before writing to Trello cards or Task Ledger markdown files; scan diffs before PR creation. |
| **Infinite Agent Coding / Review Loops** | Denial of Service / Cost Exhaustion | Enforce `max_iterations_per_task: 3` for `pi` and `max_review_cycles: 3` for `agy`. Circuit breaker halts execution and transitions card to `2. Need Decision`. |
| **Split-Brain State Across Trello, Git, and SQLite** | Production Reliability | Use SQLite WAL mode with deterministic idempotency keys (`sha256(card_id + target_column + content_hash)`) so retries are safe and idempotent. |
