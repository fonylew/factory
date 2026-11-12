---
name: software-factory
description: >-
  Master orchestration skill for the Enterprise Multi-Agent Spec-Driven Software Factory.
  Activate whenever the user or agent wants to initialize or use the software factory, start a new
  spec-driven task or feature, link or sync tasks with Trello Kanban, escalate decisions to
  "Need Decision", read answers from "Human Decision", dispatch the `pi` coding agent in an
  isolated Git worktree, run Gherkin BDD tests, or trigger an `agy` (Gemini 4 Argon) security/PR review.
---

# Enterprise Multi-Agent Spec-Driven Software Factory Skill

This skill teaches an agent (`agy` with Gemini 4 Argon or any orchestrating agent) how to operate the **Spec-Driven Software Factory** (`/home/aimet/projects/factory`).

> **Core Invariant**: *Code is ephemeral; the Specification and Traceability Graph are permanent.* Never write application code before anchoring the task to a `ProblemNode`, `SystemSpecNode`, `FeatureNode` (`.feature` file), `TaskJournalNode` (`specs/tasks/`), and a linked **Trello Kanban Card**.

---

## 1. Quick Reference: MCP Tools vs CLI Commands

If the `agentic-software-factory` MCP server is active, prefer calling the **MCP Tools** directly. Otherwise, run the equivalent **`uv run factory` CLI commands** from `/home/aimet/projects/factory` (or pass `--repo-root <path>`).

| Lifecycle Action | MCP Tool Name | CLI Command |
| :--- | :--- | :--- |
| **Install Skills & MCP Globally** | `factory_setup_agent_skills` | `uv run factory setup-skills` |
| **Onboard a Target Repo** | `factory_project_init` | `uv run factory project-init <target_dir>` |
| **Initialize Trello Board Lists** | `factory_trello_init_board` | `uv run factory trello init-board` |
| **Create & Link Task + Feature + Trello Card** | `factory_task_create_and_link` | `uv run factory task create --task-id TASK-XXX --feature-id FEAT-XXX --title "..." --problem-context "..." --system-design "..."` |
| **Link Existing Task to Trello Card** | `factory_task_link_trello` | `uv run factory task link-trello TASK-XXX FEAT-XXX [--card-id ID]` |
| **Append Step Output (`01`..`05`)** | `factory_task_append_step` | `uv run factory task log-step TASK-XXX <step_name> "<markdown>"` |
| **Ask Human a Design Question (`Need Decision`)** | `factory_kanban_escalate_decision` | `uv run factory trello ask-decision FEAT-XXX ADR-XXX "<question>" -o "Option 1" -o "Option 2"` |
| **Pull Trello & Process `Human Decision`s** | `factory_kanban_process_human_decisions` | `uv run factory sync` |
| **Dispatch `pi` in Isolated Worktree** | `factory_dispatch_pi` | `uv run factory run-pi FEAT-XXX --task-id TASK-XXX --prompt "..."` |
| **Draft Formal Lean Spec (Stage 1)** | `factory_formal_init_spec` | `uv run factory formal init-spec --spec-id FSPEC-XXX --feature-id FEAT-XXX ...` |
| **Human Approve & Lock Lean Spec** | `factory_formal_approve_spec` | `uv run factory formal approve-spec FSPEC-XXX --approved-by <member>` |
| **Lift Code to Lean Processor Model (Stage 2)** | `factory_formal_lift_code` | `uv run factory formal lift-code --model-id CMOD-XXX --feature-id FEAT-XXX --source-path <file>` |
| **Run Prover Team + Gatekeeper (Stage 3)** | `factory_formal_run_prover_team` | `uv run factory formal prove --proof-id THM-XXX --spec-id FSPEC-XXX --model-id CMOD-XXX` |
| **Standalone Formal Gatekeeper Check** | `factory_formal_gatekeep` | `uv run factory formal gatekeep FSPEC-XXX CMOD-XXX <proof_file>` |
| **Run `agy` Security & Prod PR Review** | `factory_audit_code` | `uv run factory audit FEAT-XXX <file_path> --task-id TASK-XXX` |
| **Check Graph, Orphans & Open Issues** | `factory_graph_status` | `uv run factory status` |
| **Compute Change Blast Radius** | `factory_impact_analysis` | `uv run factory impact <NODE-ID>` |

---

## 2. Standard 6-Step Agent Execution Playbook

### Step 1: Ensure Board & Factory Are Initialized
Before starting work in a repository:
1. Run `factory_trello_init_board` (or `uv run factory trello init-board`) to ensure the 8 mandatory Trello lists exist (`1. Problem & Spec Backlog`, `2. Need Decision`, `3. Human Decision`, `4. Ready for Dev (Spec Locked)`, `5. In Progress (pi Coding)`, `6. PR & Security Review (agy)`, `7. Done / Verified`, and `Issues & Security Findings`).

### Step 2: Grill-Me Discovery & Atomic Task + Trello Card Creation
1. Activate the **`grill-me-analyst`** skill to interview the Tech Lead / System Analyst on the Problem Statement, Enterprise Architecture, Security (STRIDE), and Production Failure Modes.
2. Call `factory_task_create_and_link` (or `uv run factory task create ...`). This single call atomically:
   - Creates `specs/tasks/<YYYY-MM-DD>_<TASK-ID>_<slug>/README.md`
   - Writes `specs/features/<FEAT-ID>-<slug>.feature` and locks its SHA-256 checksum
   - Links `PROB-XXX -> SPEC-XXX -> FEAT-XXX -> TASK-XXX` in the Traceability Graph
   - Creates the 5-section card on Trello and records `trello_card_id` in both `README.md` and the Graph.
3. Log the interview and design outputs using `factory_task_append_step`:
   - `01-grill-me-conversation`
   - `02-system-analysis-design`

### Step 3: Human-in-the-Loop Decisions via Trello (`Need Decision` -> `Human Decision`)
- Whenever you encounter an architectural trade-off that requires Tech Lead approval:
  1. Call `factory_kanban_escalate_decision` (or `uv run factory trello ask-decision FEAT-XXX ADR-XXX "Question?" -o "Opt A" -o "Opt B"`).
  2. Inform the user that the card has been moved to **`2. Need Decision`** on Trello.
  3. Once the human writes their choice under `## 5. Human Decision` and moves the card to **`3. Human Decision`**, run `factory_kanban_process_human_decisions` (`uv run factory sync`). This validates the member ID, logs `ADR-XXX` in the Graph and `03-human-decisions-adr.md`, and transitions the card to **`4. Ready for Dev (Spec Locked)`**.

### Step 4: Dispatch `pi` Coding Agent in an Isolated Worktree
- Never let `pi` run in the main checkout or touch `specs/`.
- Call `factory_dispatch_pi` (or `uv run factory run-pi FEAT-XXX --task-id TASK-XXX --prompt "Implement step defs and code for FEAT-XXX"`).
- The factory automatically creates `worktrees/feat-FEAT-XXX`, locks `specs/` read-only, strips all credentials (`TRELLO_TOKEN`, `GITHUB_TOKEN`), runs `pi`, verifies zero spec tampering via SHA-256, runs the Gherkin BDD runner, opens a PR, and logs `04-pi-execution-summary.md`.

### Step 5: Execute `agy` (Gemini 4 Argon) Security & Production PR Audit
- Activate the **`security-prod-auditor`** skill and call `factory_audit_code` (or `uv run factory audit FEAT-XXX <changed_file> --task-id TASK-XXX`).
- If any `CRITICAL` or `HIGH` security/production issues (`HARDCODED_SECRET`, `MISSING_HTTP_TIMEOUT`, `SQL_INJECTION_RISK`, `UNSAFE_CODE_EXECUTION`) are found, `IssueNode`s (`ISS-XXX`) are automatically added to the Graph and the Trello `Issues & Security Findings` column, and the PR is marked `CHANGES_REQUESTED`.
- If clean, `05-agy-security-pr-review.md` is logged and the Trello card moves to **`7. Done / Verified`**.

### Step 6 (High-Assurance): Agentic Formal Software Verification (`formal-software-verification`)
- For cryptographic, safety-critical, or systems code (e.g. Rust), activate the **`formal-software-verification`** skill:
  1. **1 Specification**: Draft `Spec.lean` via `factory_formal_init_spec` (with Reviewer critiques) and get Human Approval on Trello (`factory_formal_approve_spec`) to lock `Spec.lean` as **Trusted**.
  2. **2 Code**: Lift compiled machine code onto the Lean processor model (`CodeModel.lean`) via `factory_formal_lift_code`.
  3. **3 Proof**: Run the multi-agent **Prover team** against the deterministic **Gatekeeper** (`factory_formal_run_prover_team`) until all theorems pass without `sorry`/`axiom`/`unsafe`, emitting `TheoremProofNode` (`THM-XXX`) and `06-formal-verification-proofs.md`.

---

## 3. Additional References & Helper Scripts
- Detailed CLI & MCP Reference: [references/agent_workflow.md](./references/agent_workflow.md)
- One-liner installation script: [scripts/install_factory.sh](./scripts/install_factory.sh)
