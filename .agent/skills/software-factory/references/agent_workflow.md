# Agent Workflow & Trello Integration Reference

## 1. Configuring Live Trello Credentials
Set the following in `/home/aimet/projects/factory/.env` (or environment):
```bash
TRELLO_API_KEY="your_trello_api_key"
TRELLO_TOKEN="your_trello_token"
TRELLO_BOARD_ID="your_board_id"
TRELLO_AUTHORIZED_MEMBERS="tech_lead_01,system_analyst_01,aimet"
```
When these variables are present, `TrelloKanbanAdapter` automatically synchronizes all 8 lists and cards with `https://api.trello.com/1` while maintaining a local transactional mirror in `.factory/local_kanban.json`. When not yet set, the Factory operates seamlessly in `local_mirror` mode and can be pushed to Trello at any time via `uv run factory trello init-board --sync-cards`.

## 2. Example End-to-End CLI Session for an Agent
```bash
# 1. Install skills and MCP server into ~/.gemini/config/
uv run factory setup-skills

# 2. Initialize Trello board lists
uv run factory trello init-board

# 3. Create a Task, Feature spec, Graph nodes, and linked Trello card in one step
uv run factory task create \
  --task-id TASK-105 \
  --feature-id FEAT-105 \
  --title "Idempotent Webhook Signature Verifier" \
  --problem-context "Prevent replay attacks and duplicate webhook processing." \
  --system-design "HMAC-SHA256 verification + Redis idempotency key with 24h TTL and 5s timeout." \
  --scenario "Rejecting a webhook with an invalid HMAC signature" \
  --scenario "Rejecting a replayed webhook event ID"

# 4. Escalate a design question to Trello '2. Need Decision'
uv run factory trello ask-decision FEAT-105 ADR-105 "Should replay cache fail-open or fail-closed if Redis is unreachable?" \
  -o "Option A: Fail-closed (HTTP 503 so sender retries with backoff)" \
  -o "Option B: Fail-open with SQLite fallback"

# 5. Sync decisions from Trello '3. Human Decision'
uv run factory sync

# 6. Dispatch pi in isolated worktree
uv run factory run-pi FEAT-105 --task-id TASK-105 --prompt "Implement HMAC verifier for FEAT-105"

# 7. Audit implementation with agy security scanner
uv run factory audit FEAT-105 src/factory/kanban/trello_client.py --task-id TASK-105
```
