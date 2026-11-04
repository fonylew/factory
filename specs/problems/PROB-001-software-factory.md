---
id: "PROB-001"
title: "Enterprise Multi-Agent Spec-Driven Software Delivery Without Drift or Security Erosion"
status: "ACTIVE"
created_at: "2026-11-01"
owner: "Technical Lead / System Analyst"
invariants:
  - "INV-01: Every FeatureNode and CodeArtifactNode MUST have a valid directed path in the Traceability Graph to an active ProblemNode."
  - "INV-02: Coding agents (pi) MUST NEVER modify files under specs/ or alter Gherkin .feature acceptance tests."
  - "INV-03: Coding agents (pi) MUST execute inside isolated Git worktrees with all Trello, GitHub, and cloud credentials scrubbed from their environment."
  - "INV-04: Every Trello feature card MUST contain System Analysis, Enterprise Design, and Gherkin Acceptance Criteria before transitioning to Ready for Dev."
  - "INV-05: Every Pull Request MUST be audited by agy (Gemini 4 Argon) for spec compliance, security flaws (STRIDE/OWASP), and production failure modes before merge."
  - "INV-06: Every task MUST maintain a timestamped step-by-step markdown journal under specs/tasks/<YYYY-MM-DD>_<TASK-ID>_<slug>/."
---

# Problem Statement (`PROB-001`)

## 1. Core Problem
Enterprise Technical Leads and System Analysts adopting agentic coding tools suffer from four critical failure modes:
1. **Goal & Architectural Drift**: Coding agents lose sight of the original business problem and non-functional invariants as tasks span multiple files and sessions.
2. **Specification Erosion & Test Tampering**: Unconstrained coding agents weaken tests or modify specs to pass builds rather than fixing root causes.
3. **Unchecked Security & Production Risks**: Agent-written code frequently introduces security vulnerabilities and production reliability hazards without formal System Analysis or threat modeling.
4. **Lost Context & Governance**: Architectural decisions and task histories vanish inside ephemeral chat sessions rather than living in auditable Git and Kanban workflows.

## 2. Solution Anchor
Build a **Spec-Driven Multi-Agent Software Factory** where:
- **Code is ephemeral; the Specification and Traceability Graph are permanent.**
- **`agy` (with Gemini 4 Argon)** acts as the System Analyst, Planner, and Principal Security Reviewer (`/grill-me`, Spec authoring, Kanban governance, and PR auditing).
- **`pi`** acts as the sandboxed coding agent inside isolated Git worktrees, implementing code until Gherkin `.feature` tests pass.
- **Trello Kanban (`Need Decision` -> `Human Decision`)** and **Git Task Ledgers (`specs/tasks/`)** preserve human-in-the-loop governance and complete step-by-step audit trails.
