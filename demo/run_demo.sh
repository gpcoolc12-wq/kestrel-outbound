#!/usr/bin/env bash
# Rebuild the bundled demo exactly as submitted: fresh offline simulation + the one human override.
# No API key and no internet needed.
set -euo pipefail
cd "$(dirname "$0")/.."
export AGENT_ENGINE=offline
P=.venv/bin/python
[ -d .venv ] || { python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt; }
AGENT_LINK=${AGENT_LINK:-https://github.com/gpcoolc12-wq/kestrel-outbound} ./simulate.sh --fresh
$P run_sop.py override --local --issue KES-9 --subject "Steve Guild Design, since 2001" \
  --opener "I read that Steve started the studio as Steve Guild Design in 2001. By now the conference room must double as a pin-up wall during deadline weeks." \
  --reason "The agent wrote that G4 Design Studios dates back to 2001, but the source says the firm was Steve Guild Design until it was renamed in 2014. Saying G4 existed in 2001 is a small factual slip a founder would notice, so I used the site's own wording."
# end of day: daily update + submission reflect the reviewed state
$P -c "import json;p='local_linear/workspace.json';w=json.load(open(p));w['project_updates']=[];json.dump(w,open(p,'w'),indent=2)"
rm -f outbox/*Update*.eml outbox/*Submission*.eml
$P run_sop.py daily-update --local
$P run_sop.py submit --local --agent-link "${AGENT_LINK:-https://github.com/gpcoolc12-wq/kestrel-outbound}"
$P view.py
cp simulation/index.html index.html   # published copy: GitHub Pages serves the repo root
echo "Open simulation/index.html"
