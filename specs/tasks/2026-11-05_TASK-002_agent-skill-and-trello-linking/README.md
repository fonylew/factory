---
task_id: "TASK-002"
date: "2026-11-05"
description: "Agent Interaction Protocol, Installable Factory Skills, and Bidirectional Trello Task Initialization & Linking"
problem_id: "PROB-001"
spec_id: "SPEC-001"
features:
  - "FEAT-007"
trello_card_id: "CARD-FEAT-007"
status: "DONE_VERIFIED"
---

# [TASK-002] Agent Interaction Protocol, Installable Factory Skill & Trello Task Linking

## Task Overview
- **Task ID**: `TASK-002`
- **Date**: `2026-11-05`
- **Description**: Create an installable `software-factory` skill and MCP installer (`factory setup-skills`), project onboarding command (`factory project-init`), and atomic Task-to-Trello initialization and linking (`factory trello init-board`, `factory task create`, `factory task link-trello`).
- **Problem Anchor**: `PROB-001`
- **System Spec**: `SPEC-001`
- **Feature**: `FEAT-007`

## Step Execution Ledger
| Step | Document | Agent / Actor | Status | Timestamp | Summary |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **01** | [01-grill-me-conversation.md](./01-grill-me-conversation.md) | `agy` (Gemini 4 Argon) + User | COMPLETED | 2026-11-05T02:22:36+07:00 | Defined requirements for how an Agent interacts with the factory, installing the factory skill, and initializing/linking tasks with Trello. |
| **02** | [02-system-analysis-design.md](./02-system-analysis-design.md) | `agy` (Gemini 4 Argon) | COMPLETED | 2026-11-05T02:23:30+07:00 | Designed 3-layer agent integration (Skills, MCP/CLI, Workspace Rules), `factory setup-skills`, and atomic `Task <-> Graph <-> Trello` linking. |
| **03** | [03-human-decisions-adr.md](./03-human-decisions-adr.md) | Tech Lead / System Analyst | COMPLETED | 2026-11-05T02:25:03+07:00 | Approved `ADR-010` (Global + Workspace Skill/MCP installer and unified Task-to-Trello linking). |
| **04** | [04-pi-execution-summary.md](./04-pi-execution-summary.md) | Implementation Engine | COMPLETED | 2026-11-05T02:30:01+07:00 | Implemented `installer.py`, `software-factory` skill, Trello board initializer, and `FEAT-007` BDD tests (`12/12` passing). |
| **05** | [05-agy-security-pr-review.md](./05-agy-security-pr-review.md) | `agy` (Gemini 4 Argon) | COMPLETED | 2026-11-05T02:30:10+07:00 | Security & production audit of skill installer and Trello bidirectional sync (`APPROVED`). |
