# Step 01: Grill-Me Discovery Conversation & Problem Anchor (`TASK-001`)

- **Task ID**: `TASK-001`
- **Date**: `2026-11-01`
- **Facilitator**: `agy` (Gemini 4 Argon — System Analyst Skill)
- **Stakeholder**: Technical Lead / System Analyst

---

## 1. Original User Request & Vision
The user requested a **Multi-Agent Agentic Software Factory System** with the following core pillars:
- Built specifically for **Technical Leads** and **System Analysts**, designed with **Enterprise Architecture** in mind, continuously analyzing for **security flaws** and **production issues**.
- **Everything is spec-based**: Start with `/grill-me` skills to elicit the **Problem Statement** and **Solution Anchor** so the system never loses track of the original problem.
- **Code can change; Spec is what remains**: Leverage Spec-Driven Development (SDD).
- **Gherkin format (`.feature`)**: Track specifications as executable feature files and regression tests to verify behavior.
- **System & Code Issue Analysis**: Analyze and report on system/code issues and keep track of them as open issues.
- **Git Branching & PR Workflow**: Branch each feature (`feat/...`) and submit Pull Requests, even when another agent reviews it.
- **Traceability Graph System**: Keep track of every feature, how it solves the root problem, how features and systems connect, what is to-do, and what is an open issue.
- **Trello Kanban Integration**: Every card must have System Analysis, Design, and Acceptance Criteria. When a design decision is needed from the user, move the card to **`Need Decision`** and read the human's answer from **`Human Decision`**.
- **Multi-Agent Role Separation**:
  - Use **`pi`** for agentic coding tasks.
  - Use **`agy` with Gemini 4 Argon** for planning, reviewing, and guidance tasks.
- **Task Ledger (`specs/tasks/`)**: Keep a dedicated folder per task recording the `Task ID`, `date`, and `description` along with the markdown outputs of each step of that task.

---

## 2. Structured Grill-Me Q&A Transcript

### Round 1: Scope, Graph Engine, Integration Model, and BDD Stack
1. **Q1 (Problem Statement & Primary Scope)**: *Are we building the reusable Multi-Agent Software Factory platform itself inside `/home/aimet/projects/factory`, or a specific target application?*
   - **Answer**: **Build the Multi-Agent Software Factory System itself inside `/home/aimet/projects/factory`** (which can then be used to build and manage software projects).
2. **Q2 (Graph System Architecture)**: *How should the Requirement-Feature-Code-Issue traceability graph be stored and queried in production?*
   - **Answer**: **Local embedded graph (SQLite / NetworkX + JSON-LD/Mermaid export in Git)** — zero-ops, versioned alongside specs and code, ACID compliant.
3. **Q3 (Orchestration & Trello/Git Execution Model)**: *How should the factory orchestrate transitions between Trello columns, `pi` coding agents, and `agy` review agents?*
   - **Answer**: **Use MCP or CLI to connect to Trello and Git**, with authentication credentials provided via configuration/env later.
4. **Q4 (Implementation Stack & Gherkin Runner)**: *What primary technology stack should power the factory orchestrator and the Gherkin BDD regression runner?*
   - **Answer**: **Language-agnostic orchestrator** that delegates Gherkin test execution via per-project container/adapter configuration (`factory.yaml`).

### Round 2: Spec Lock, Privilege Isolation, Issue Dual-Tracking, and Kanban State Machine
5. **Q5 (Problem Statement & Drift Prevention)**: *How strictly should we lock Specifications against agent drift?*
   - **Answer**: **Both**: Enforce a **Graph-enforced Problem Anchor** (every Spec/Feature must link to a root Problem Statement & Invariants) **AND** a **Read-Only Spec/Feature Lock** during coding execution.
6. **Q6 (Security Boundary & Execution Isolation for `pi` vs `agy`)**: *How should we isolate privileges and prevent `pi` from tampering with tests or leaking credentials?*
   - **Answer**: **Isolated Git Worktrees + Sandboxed Subprocess per task**: Each `pi` coding agent runs in an isolated git worktree (`worktrees/feat-xyz`) with restricted filesystem/env access (no Trello/Git admin tokens exposed to `pi`) and cannot modify `.feature` test files.
7. **Q7 (System & Code Issue Tracking)**: *When `agy` detects security flaws, production failure modes, or code issues, how should they be persisted and tracked?*
   - **Answer**: **Dual-track tracking**: Store structured issues as `IssueNode`s in the Traceability Graph (`mitigates`, `affects_feature`, `blocks_pr`) + auto-sync as Trello Cards (labeled `security`/`bug`/`tech-debt`) and Git Issues/PR Review Comments.
8. **Q8 (Trello Kanban State Machine & HITL)**: *How should the card lifecycle and decision handoff work on the Trello board?*
   - **Answer**: **Structured Card Template + 7-Column State Machine**: Columns = `['1. Problem & Spec Backlog', '2. Need Decision', '3. Human Decision', '4. Ready for Dev (Spec Locked)', '5. In Progress (pi Coding)', '6. PR & Security Review (agy)', '7. Done / Verified']`; moving a card to `Human Decision` requires a parsed `## 5. Human Decision` block from the Tech Lead before `agy` resumes.

### Round 3: Task Ledger & User Interaction Flow
9. **Q9 (Task Conversation & Design Ledger)**: *Add a folder to keep track of the conversation and design document by adding Task ID, date, and description in the markdown file to keep the output of each step of that task.*
   - **Decision**: Track structured step outputs in Git under `specs/tasks/<YYYY-MM-DD>_<TASK-ID>_<slug>/` (`01-grill-me` through `05-agy-security-pr-review`), linked into the Traceability Graph via `TaskJournalNode`, and protected as read-only during `pi` execution.
