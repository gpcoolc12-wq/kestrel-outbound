#!/usr/bin/env bash
# Full SOP simulation, end to end, all local: no real Linear and no real email.
# Output: local_linear/ (workspace), outbox/ (emails), simulation/index.html (viewer).
set -euo pipefail
cd "$(dirname "$0")"
[ -d .venv ] || { python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt; }
P=.venv/bin/python
[ "${1:-}" = "--fresh" ] && rm -rf state local_linear outbox logs simulation
$P run_sop.py ask --local             # clarifying questions to Nirbhay (outbox)
$P run_sop.py setup --invite --local  # Step 1
$P run_sop.py run --local             # Steps 2-7 for all 10 prospects
$P run_sop.py daily-update --local    # Step 8 (end of day)
$P run_sop.py accept-invite --local   # [simulated] Nirbhay joins the workspace
$P run_sop.py assign --local          # Step 6 completed: assign In Review issues
$P run_sop.py docs --local            # Guardrail note + Part B as project documents
$P run_sop.py submit --local --health onTrack \
   --agent-link "${AGENT_LINK:-<repo link>}" --loom "${LOOM_LINK:-<Loom link>}"   # Step 9
$P run_sop.py status --local
$P view.py
echo "Open simulation/index.html"
