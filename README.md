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

## No API key needed

The default engine is **offline**. It does rule-based research and drafting, and every result passes the same guardrails as the LLM path. A snapshot of the 10 prospect websites is bundled in `demo/site_snapshot/`, so the full demo runs with **no API key and no internet**. To use an LLM instead, set `AGENT_ENGINE=model` and an `OPENROUTER_API_KEY`. If the model is unavailable, the agent falls back to the offline engine.

## Quick start: full simulation and front end (about 10 seconds)

Requirements: Python 3.10+ and `git`.

```bash
git clone https://github.com/gpcoolc12-wq/kestrel-outbound.git
cd kestrel-outbound
./demo/run_demo.sh              # creates .venv, runs every SOP step locally, applies the reviewed override
open simulation/index.html      # the front end
```

The front end is a single self-contained HTML file with six tabs:

* **Overview:** the nine SOP steps with what happened at each, KPIs and the prospect table.
* **Board:** a Linear-style board. Click an issue to see its description (the SOP template), the email, the research (segment evidence, do-not-contact check, fact candidates, draft attempts, override) and the full activity log.
* **Simulation replay:** steps through all ~65 logged actions in order, with the board updating as you go. Play, or use the arrow keys.
* **Agent & guardrails:** the three "never say" rules, how each is enforced, test results, drafts rejected during the run, and human overrides with before and after.
* **Outbox:** the clarifying questions, the daily update and the submission email (not sent).
* **Documents:** the guardrail note, Part B and the clarifying questions.

`./simulate.sh --fresh` runs the pipeline alone, with no override. To read the live websites instead of the snapshot, add `LIVE_FETCH=1`. That needs internet, but still no key.

A copy of the finished run is in `examples/sample-run/`. Open `viewer.html` there, or browse `local_linear/BOARD.md` on GitHub.

## Run the agent on a new firm (no Linear)

```bash
.venv/bin/python agent.py --firm "Whitten Architects" --url https://www.whittenarchitects.com --city Portland
```

About 10 seconds, no key; it needs internet to read the live site. It prints the pages it read, the segment and its evidence, the do-not-contact result, every candidate fact (kept or discarded), and any draft the guardrails rejected. At the end it prints the issue description, filled in using the SOP template. Add `--json` for machine output.

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

Note that `setup --invite` against real Linear sends a real invitation email from Linear. Use an admin API key: the workspace creator is an admin by default, and both inviting members and creating statuses need admin rights.

**`run` reuses the reviewed results.** If you ran the local simulation first, `run` against real Linear does not ask the model again. It reuses that run's segments, do-not-contact results, facts, drafts and human overrides from `state/local.json`, so what you reviewed is exactly what goes into Linear. Every SOP step is still carried out and logged in Linear, in order. Pass `--fresh-research` to research everything again.

**Checking the Linear calls without a key.** `tools/check_linear_api.py` validates every GraphQL query and mutation, plus the input fields and enum values they send, against Linear's published schema:

```bash
.venv/bin/pip install graphql-core && .venv/bin/python tools/check_linear_api.py
```

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

## Optional: LLM engine

With `AGENT_ENGINE=model`, the agent uses OpenRouter. `OPENROUTER_MODEL` takes a comma-separated fallback chain. The default is Claude Sonnet 5.5, then free Nemotron or Laguna models. A model that is out of credits (402) or rate-limited (429) is skipped. The guardrails don't depend on the model: they are deterministic code checks.

**Free-tier limits.** An OpenRouter key with no credits gets 50 free-model requests per day, and a full 10-firm run uses roughly 40–70. If the daily quota runs out, the agent retries for a few minutes and then stops with "all models failed". Re-run the same command after the quota resets (00:00 UTC). Finished steps are skipped, so it resumes where it stopped. Adding $10 of credit raises the limit to 1,000 requests a day and enables Claude Sonnet.

## Layout

```
agent.py              run the agent on one firm
run_sop.py            the SOP pipeline (all steps)
simulate.sh           full local simulation
view.py               builds simulation/index.html
kestrel/fetch.py      website reader (direct + reader fallback)
kestrel/agent.py      segment, do-not-contact, fact research, drafting (engine switch)
kestrel/offline.py    offline rule-based engine (default, no API key)
demo/                 run_demo.sh + site_snapshot/ (bundled websites for offline runs)
kestrel/guardrails.py generation-time checks
kestrel/backends.py   LinearBackend (GraphQL) + LocalBackend (simulation)
tools/                check_linear_api.py - validates the Linear calls against Linear's schema
config/               client brief (claims, CTA, do-not-contact list) + prospects
docs/                 guardrail note, Part B, clarifying questions, Loom script
```
