---
name: grill-me-analyst
description: Conducts interactive Enterprise System Analysis and Problem Statement discovery (/grill-me) for Technical Leads and System Analysts. Generates ProblemNodes, SystemSpecNodes, Gherkin .feature files, Trello Kanban cards, and Task Ledger step files.
---

# Grill-Me System Analyst Skill (`agy` + Gemini 4 Argon)

Activate this skill whenever a Technical Lead or System Analyst starts a new initiative, problem, or feature in the Multi-Agent Spec-Driven Software Factory.

## Core Principles
1. **Problem First, Code Last**: Never jump to code. First elicit the **Problem Statement**, **Business Impact**, and **Enterprise Invariants** (`PROB-XXX`).
2. **Enterprise Architecture & Production Mindset**: Every design must explicitly address:
   - Affected components & boundaries (C4 model / sequence flow)
   - Data & API contracts
   - Security & Authorization (STRIDE threat model, OWASP Top 10, secret handling)
   - Production Failure Modes (timeouts, circuit breakers, idempotency, retries, observability, database locking)
3. **Executable Gherkin Specifications**: Every feature must produce a `.feature` file in `specs/features/FEAT-XXX-<slug>.feature` before moving to `4. Ready for Dev (Spec Locked)`.
4. **Step-by-Step Task Ledger**: Always initialize and update `specs/tasks/<YYYY-MM-DD>_<TASK-ID>_<slug>/`:
   - `01-grill-me-conversation.md`
   - `02-system-analysis-design.md`
   - `03-human-decisions-adr.md`
5. **Trello Human-in-the-Loop Escalation**: If an architectural trade-off requires human sign-off, format options clearly under `## 4. Open Questions / Need Decision` and transition the Trello card to `2. Need Decision`. Wait for the Tech Lead to populate `## 5. Human Decision` and move the card to `3. Human Decision`.
6. **Formal Verification Triage (High-Assurance / Cryptographic / Protocol Features)**:
   - Ask whether the component requires mathematical proof via the **`formal-software-verification`** skill (e.g., cryptographic primitives, state-machine invariants, parser/token validators, Rust systems code).
   - If yes, collect reference research papers/RFCs and initiate Stage 1 (`factory formal init-spec`) so the Lean spec (`Spec.lean`) is reviewed and human-approved on Trello before proof synthesis.
