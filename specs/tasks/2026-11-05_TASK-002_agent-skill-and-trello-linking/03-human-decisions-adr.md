# Step 03: Human Decisions & ADR (`TASK-002`)

- **Task ID**: `TASK-002`
- **Date**: `2026-11-05`
- **Decided By**: Technical Lead / System Analyst
- **Status**: APPROVED

---

## `ADR-010`: Agent Skill Installation & Atomic Task-to-Trello Linking
- **Context**: Agents need a zero-friction way to discover and operate the Software Factory across sessions, and users/agents need a single command/tool to initialize a task and link it bidirectionally with Trello.
- **Decision**:
  1. Package `software-factory`, `grill-me-analyst`, and `security-prod-auditor` skills with an installer (`factory setup-skills`) that registers them in `~/.gemini/config/skills/`, `~/.agents/skills/`, and `~/.gemini/config/mcp_config.json`.
  2. Provide `factory trello init-board`, `factory task create`, and `factory task link-trello` (plus matching FastMCP tools) to atomically link `specs/tasks/<YYYY-MM-DD>_<TASK-ID>_<slug>/`, the Traceability Graph, and Trello cards.
