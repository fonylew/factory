# Step 02: System Analysis & Enterprise Design (`TASK-002`)

- **Task ID**: `TASK-002`
- **Date**: `2026-11-05`
- **System Analyst**: `agy` (Gemini 4 Argon)
- **Linked Feature**: `FEAT-007`

---

## 1. Component Architecture
1. **Master Factory Skill (`.agent/skills/software-factory/SKILL.md`)**:
   - Teaches `agy` (and any compatible coding agent) the complete 6-stage lifecycle:
     1. Project & Trello Board Initialization (`factory project-init`, `factory trello init-board`)
     2. `/grill-me` Problem Discovery & Atomic Task-Trello Creation (`factory task create` / `factory_task_create_and_link`)
     3. Escalating Ambiguities to Trello `2. Need Decision` (`factory trello ask-decision` / `factory_kanban_escalate_decision`)
     4. Polling Trello `3. Human Decision` & Recording ADRs (`factory sync` / `factory_kanban_process_human_decisions`)
     5. Dispatching `pi` in Isolated Git Worktrees (`factory run-pi` / `factory_dispatch_pi`)
     6. Running `agy` Security & Production PR Audits (`factory audit` / `factory_audit_code`)
2. **Skill & MCP Installer (`src/factory/installer.py`)**:
   - `setup_global_skills_and_mcp()`: Copies/symlinks `software-factory`, `grill-me-analyst`, and `security-prod-auditor` into `~/.gemini/config/skills/` and `~/.agents/skills/`, and non-destructively merges the `agentic-software-factory` stdio server into `~/.gemini/config/mcp_config.json`.
   - `init_target_project()`: Initializes any target git repository with `factory.yaml`, `specs/`, `AGENTS.md`, and `.agent/skills/`.
3. **Trello Board Provisioner & Bidirectional Task Linker (`src/factory/kanban/trello_client.py` & `src/factory/journal/task_ledger.py`)**:
   - `init_board_lists()`: Ensures all 8 mandatory Kanban columns exist on Trello (or local mirror) and persists list metadata in `.factory/trello_board_map.json`.
   - `create_and_link_task()`: Atomically initializes `specs/tasks/<YYYY-MM-DD>_<TASK-ID>_<slug>/`, creates the `.feature` file, links `ProblemNode -> SystemSpecNode -> FeatureNode -> TaskJournalNode`, pushes the 5-section card to Trello, and writes `trello_card_id` + `trello_card_url` into both `README.md` and the Traceability Graph.
   - `pull_remote_board_state()`: Fetches cards from live Trello lists (with explicit `timeout=10.0` and secret redaction) so human decisions made in the Trello UI flow directly into the local state machine.

---

## 2. Security & Production Readiness Considerations
- **Non-Destructive Config Updates**: `setup_global_skills_and_mcp()` parses existing `mcp_config.json` safely (handling empty or 0-byte files like `~/.gemini/config/mcp_config.json`) without overwriting other configured MCP servers.
- **Path Traversal & Symlink Safety**: Validates all target installation paths before copying/linking skill directories.
- **Explicit HTTP Timeouts & Idempotency**: All Trello API calls (`init_board_lists`, `sync_card_to_trello_remote`, `pull_remote_board_state`) enforce `timeout=10.0` and avoid duplicating lists or cards when called repeatedly.
