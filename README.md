# Kestrel Outbound agent

This repo runs the Kestrel Rooms outbound SOP (Invictus AI take-home) end to end. For each firm, an AI agent:

1. reads the firm's public website,
2. picks its segment,
3. checks it against the do-not-contact list, including any parent or affiliate the site names,
4. finds one fact it can check, with the source URL and a verbatim quote,
5. drafts a guardrail-checked email of 90 words or fewer.

Every step is recorded in Linear the way the SOP requires: status, labels, title, description template, and a comment with links for every action.

It runs in two modes, and the code path is the same:

| Mode | Linear | Email | Use |
|---|---|---|---|
| `--local` (simulation) | file-based stand-in in `local_linear/` | `.eml` files in `outbox/`, never sent | default; anyone can run it |
| Linear | real workspace via the GraphQL API (`LINEAR_API_KEY`) | `.eml` files in `outbox/` | real run |

## See a finished run without running anything

`examples/sample-run/` holds the run from 4 October 2026, covering all 10 prospects:

* `viewer.html`: download it and open it in a browser. It's a Linear-style board with every issue, comment, activity entry, project document, project update and outbox email.
* `local_linear/BOARD.md` and `local_linear/issues/KES-*.md`: the same content as Markdown, readable on GitHub.
* `outbox/*.eml`: the clarifying-questions email, the daily update and the submission email.
* `run.log`: every action in order.

## Quick start (full simulation, about 15–30 min on free models)

Requirements: Python 3.10+, `git`, and an OpenRouter API key (https://openrouter.ai/keys; a free key works).

```bash
git clone https://github.com/gpcoolc12-wq/kestrel-outbound.git
cd kestrel-outbound
cp .env.example .env              # put your key in OPENROUTER_API_KEY
./simulate.sh --fresh             # creates .venv, installs deps, runs every SOP step locally
open simulation/index.html        # Linear-style board: issues, comments, activity, docs, updates, outbox
```

Windows: run the commands in `simulate.sh` one by one, using `.venv\Scripts\python`.

`simulate.sh` runs, in order:

* the clarifying-questions email
* Step 1: setup and invite
* Steps 2–7 for all 10 prospects
* Step 8: daily update
* Nirbhay accepting the invite (simulated: this is the only step that stands in for another person)
* assignment
* the guardrail note and Part B documents
* Step 9: project update and submission email

Re-running is safe, because finished steps are skipped (`state/local.json`).

## Run the agent on a new firm (no Linear)

```bash
.venv/bin/python agent.py --firm "Whitten Architects" --url https://www.whittenarchitects.com --city Portland
```

It prints the pages it read, the segment and its evidence, the do-not-contact result, every candidate fact (kept or discarded), and any draft the guardrails rejected. At the end it prints the issue description, filled in using the SOP template. Add `--json` for machine output.

To add a firm to the pipeline, append a row to `config/prospects.csv` and run `run_sop.py run --local`.

## Running against a real Linear workspace

1. Sign up at https://linear.app (free plan) and create a workspace. The setup wizard creates one team, which is all the SOP needs.
2. Go to Settings → Security & access → Personal API keys → *New key*. Save the key as `LINEAR_API_KEY` in `.env`.
3. Run the same commands without `--local`:

```bash
.venv/bin/python run_sop.py setup --invite   # project "Kestrel Outbound", 5 labels, missing statuses, invites nbakshi@invictus.ai
.venv/bin/python run_sop.py run              # Steps 2-7
.venv/bin/python run_sop.py assign           # after Nirbhay accepts the invite
.venv/bin/python run_sop.py docs             # Guardrail note + Part B as project documents
.venv/bin/python run_sop.py daily-update     # Step 8 -> outbox/
.venv/bin/python run_sop.py submit --agent-link <repo> --loom <loom>   # Step 9
```

Note that `setup --invite` against real Linear sends a real invitation email from Linear.

## How the SOP maps to the code

| SOP step | Where |
|---|---|
| 1. Linear setup: project, labels, statuses, invite | `kestrel/backends.py` `setup()`, `invite()` |
| 2. One issue per prospect, title format, template, segment + Source: Brief | `run_sop.py` `step2`, `kestrel/template.py`, `agent.segment_and_affiliates` |
| 3. Do-not-contact first: firm + parent/affiliates; on a match, Canceled + `\| DROPPED` + reason | `run_sop.py` `step3`, `agent.dnc_check` |
| 4. In Progress; one fact with its source URL, quote verified on the page; dead site → drop, no replacement | `run_sop.py` `step4`, `agent.research_fact`, `fetch.read_site` |
| 5. 90 words or fewer, opens with the fact, approved claims only, sign-off, draft in description | `agent.draft_email`, `kestrel/guardrails.py` |
| 6. In Review + Ready for Approval + assign Nirbhay; never Done | `run_sop.py` `step6`, `assign` (no code path ever sets Done) |
| 7. Every action = a comment with links **and** a description/status update | `Run.act()`: the only way the pipeline changes an issue |
| 8. Daily update, exactly three lines | `run_sop.py daily-update` |
| 9. Project update with health, submission email | `run_sop.py submit` |

## Guardrails

See `docs/guardrails.md`. They are enforced in code at generation time, and `tests/test_guardrails.py` covers them:

```bash
.venv/bin/python tests/test_guardrails.py
```

## Model

The agent uses OpenRouter. `OPENROUTER_MODEL` takes a comma-separated fallback chain. The default is Claude Sonnet 5.5, then free Nemotron or Laguna models. A model that is out of credits (402) or rate-limited (429) is skipped. The guardrails don't depend on the model: they are deterministic code checks.

## Layout

```
agent.py              run the agent on one firm
run_sop.py            the SOP pipeline (all steps)
simulate.sh           full local simulation
view.py               builds simulation/index.html
kestrel/fetch.py      website reader (direct + reader fallback)
kestrel/agent.py      segment, do-not-contact, fact research, drafting
kestrel/guardrails.py generation-time checks
kestrel/backends.py   LinearBackend (GraphQL) + LocalBackend (simulation)
config/               client brief (claims, CTA, do-not-contact list) + prospects
docs/                 guardrail note, Part B, clarifying questions, Loom script
```
