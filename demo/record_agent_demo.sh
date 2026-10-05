#!/usr/bin/env bash
# Record the agent running on a firm that is NOT on the prospect list (deliverable 2: "run it on a
# new firm's website"). Needs internet to read the live site; no API key.
set -euo pipefail
cd "$(dirname "$0")/.."
FIRM="${1:-Whitten Architects}"; URL="${2:-https://www.whittenarchitects.com}"; CITY="${3:-Portland}"
.venv/bin/python agent.py --firm "$FIRM" --url "$URL" --city "$CITY" --json > demo/agent_demo.json
echo "recorded demo/agent_demo.json ($FIRM)"
