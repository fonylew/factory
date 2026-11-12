# Step 01: Grill-Me Discovery Conversation (`TASK-002`)

- **Task ID**: `TASK-002`
- **Date**: `2026-11-05`
- **Facilitator**: `agy` (Gemini 4 Argon)
- **Stakeholder**: Technical Lead / System Analyst

---

## 1. User Problem & Request
> *"how can an Agent interact and use this factory? create a factory skill to be install and a way to initialize and link the task with Trello"*

## 2. Key Problems Addressed (`PROB-001` Extension)
1. **Agent Discoverability Gap**: Without an installable global skill (`~/.gemini/config/skills/software-factory`) and MCP server registration (`~/.gemini/config/mcp_config.json`), an agent starting in a new session or target repository does not automatically know the Factory commands, MCP tools, or 6-step Spec-Driven workflow.
2. **Task-to-Trello Initialization Friction**: Creating a task ledger folder (`specs/tasks/...`), registering `FeatureNode` / `TaskJournalNode` in the Traceability Graph, and creating/linking the 5-section Trello card across the 7 Kanban columns needed to be a single atomic operation (`factory task create` and `factory task link-trello`) with board list provisioning (`factory trello init-board`).
