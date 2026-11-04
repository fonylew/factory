---
id: "ADR-001"
title: "Foundational Architecture Decisions for the Spec-Driven Software Factory"
problem_id: "PROB-001"
task_id: "TASK-001"
status: "APPROVED"
date: "2026-11-01"
decided_by: "Technical Lead / System Analyst"
---

# ADR-001: Foundational Architecture Decisions (`TASK-001`)

See detailed per-decision breakdown in [03-human-decisions-adr.md](../tasks/2026-11-01_TASK-001_factory-foundation/03-human-decisions-adr.md).

## Summary of Approved Decisions
1. **Self-Hosted Factory Platform (`ADR-001`)**: Build the reusable Multi-Agent Software Factory in `/home/aimet/projects/factory`.
2. **Embedded SQLite + NetworkX + Git Export Graph (`ADR-002`)**: Store the Traceability Graph in SQLite with NetworkX traversal and export deterministic JSON-LD (`specs/graph/traceability.json`) and Mermaid (`specs/graph/traceability.mmd`).
3. **MCP & CLI Adapter Architecture (`ADR-003`)**: Expose factory capabilities via both `factory` CLI and FastMCP server for seamless integration with `agy`, Trello, and Git.
4. **Language-Agnostic Gherkin Runner (`ADR-004`)**: Execute `.feature` specifications via configurable adapters (`pytest-bdd`, `cucumber-js`, `godog`, etc.).
5. **Dual Problem Anchor & Read-Only Spec Lock (`ADR-005`)**: Enforce graph path validation to `PROB-001` and cryptographic SHA-256 + POSIX read-only locks on `specs/` during `pi` execution.
6. **Isolated Git Worktree Sandbox (`ADR-006`)**: Spawn `pi` in `worktrees/feat-<ID>` with all tokens/secrets scrubbed.
7. **Dual-Track Security & Production Issue Tracking (`ADR-007`)**: Record findings as `IssueNode`s in the Graph AND sync to Trello cards and PR review comments.
8. **7-Column Trello State Machine (`ADR-008`)**: Enforce mandatory card sections and pause/resume via `2. Need Decision` $\rightarrow$ `3. Human Decision`.
9. **Step-by-Step Task Ledger (`ADR-009`)**: Store all task conversations, designs, decisions, execution summaries, and security reviews in `specs/tasks/<YYYY-MM-DD>_<TASK-ID>_<slug>/`.
