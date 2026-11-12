#!/usr/bin/env bash
set -euo pipefail

export PATH="/home/aimet/.local/bin:$PATH"
FACTORY_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"

echo "Installing Enterprise Software Factory skills and MCP server from ${FACTORY_ROOT}..."
cd "${FACTORY_ROOT}"
uv run factory setup-skills
echo "Done! Skills installed in ~/.gemini/config/skills/ and MCP server registered in ~/.gemini/config/mcp_config.json."
