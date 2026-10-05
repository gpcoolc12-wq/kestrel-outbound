# Kestrel Outbound: setup, usage and submission

**Candidate:** Gaurav Pawar · **Role:** Operations Associate, Invictus AI · **Brief:** Kestrel Outbound take-home (due Monday 5 October 2026, 5:00 pm IST)

**Repo:** https://github.com/gpcoolc12-wq/kestrel-outbound (public)

**Time taken:** 5 hours

This document covers:
1. What was delivered
2. Results
3. How to set up and run it
4. How to use the agent
5. Command reference
6. Guardrails
7. Decisions, assumptions and open questions
8. Troubleshooting

The Loom video is sent separately.

---

## 1. What was delivered

The whole SOP runs as a **local simulation**:

- **Linear** is replaced by a file-based stand-in with the same operations: project, labels, statuses, issues, comments, documents and project updates.
- **Emails** are written to an outbox as `.eml` files. Nothing is sent to anyone, and no firm on the list is contacted.
- **No API key** is needed. The agent's default engine is rule-based and offline, and a snapshot of the 10 prospect websites ships with the repo.

| # | Deliverable (from the brief) | Where it is |
|---|---|---|
| 1 | Workspace with Nirbhay invited, all 10 issues | Simulated workspace: `local_linear/` (raw state in `workspace.json`, Markdown in `BOARD.md` and `issues/KES-*.md`). Front end: `simulation/index.html`. Snapshot in the repo: [`examples/sample-run/`](examples/sample-run/) |
| 2 | The agent, with run instructions | This repo. Setup is in section 3 and usage in section 4. One-firm runner: `agent.py`. Full SOP pipeline: `run_sop.py` |
| 3 | Guardrail note: three things the agent must never say, and how each is enforced at generation | [`docs/guardrails.md`](docs/guardrails.md), also posted as a project document in the workspace |
| 4 | Part B: what I would change about the SOP, and why | [`docs/part_b.md`](docs/part_b.md), also posted as a project document in the workspace |
| 5 | Loom | Sent separately |
| Step 8 | Daily update email | `outbox/*Kestrel_Outbound_Update*.eml` (exactly three lines) |
| Step 9 | Project update with health, and the submission email | Project update in the workspace (health: onTrack). `outbox/*Kestrel_Outbound_Submission*.eml` |
| Comms | Clarifying questions to Nirbhay | [`docs/clarifying_questions.md`](docs/clarifying_questions.md), plus `outbox/*clarifying_questions.eml` |

---

## 2. Results

| Issue | Firm | Status | Segment | Sourced fact (verbatim on the source page) | Words |
|---|---|---|---|---|---|
| KES-1 | BRIBURN | In Review | Mixed | AIA Maine Citation Award for Excellence in Architecture, West End Garden House, 2025 | 80 |
| KES-2 | RDS Architects | In Review | Mixed | Founded by Carol Morrissette in 2010 | 72 |
| KES-3 | Ryan Senatore Architecture | In Review | Mixed | Hiawatha project | 69 |
| KES-4 | Casco Bay Design Workshop | **Canceled, DROPPED** | — | The website doesn't load (the domain is not registered, NXDOMAIN). Not replaced, per Step 4 | — |
| KES-5 | Ervin Architecture | In Review | Mixed | MEREDA Project of the Year 2023 for Maine Savings Amphitheater | 80 |
| KES-6 | Providence Architecture & Building Co. | **Canceled, DROPPED** | Residential | Do-not-contact match: their homepage says they are "an affiliate company of The Providence Group" (existing Kestrel customer). No research or draft | — |
| KES-7 | Jonathan Chambers Architects | In Review | Mixed | Raffa Yoga project | 73 |
| KES-8 | studioblue Architecture | In Review | Mixed | Established in 2008 in Burlington, VT | 77 |
| KES-9 | G4 Design Studios | In Review | Mixed | Started as Steve Guild Design in 2001 (human override, see section 7) | 76 |
| KES-10 | Gabriel Stadecker Architect | In Review | Mixed | 1812 Tavern House project | 73 |

All 8 drafts:
- are 90 words or fewer;
- open with the sourced fact;
- use only the approved claims, plus the call to action and sign-off;
- are In Review with the Ready for Approval label, assigned to Nirbhay.

No issue was moved to Done. 65 actions were logged, each as a comment with links plus a description or status update (Step 7).

---

## 3. Setup

**Requirements:** macOS or Linux, Python 3.10+ and `git`. You don't need an API key, a Linear account, or internet access after cloning.

```bash
git clone https://github.com/gpcoolc12-wq/kestrel-outbound.git
cd kestrel-outbound
./demo/run_demo.sh
open simulation/index.html        # Linux: xdg-open simulation/index.html
```

`demo/run_demo.sh` does the following:
1. Creates `.venv` and installs `requests`, `beautifulsoup4` and `python-dotenv`.
2. Runs every SOP step for the 10 prospects (`simulate.sh --fresh`).
3. Applies the one reviewed human override.
4. Writes the end-of-day emails.
5. Builds the front end.

It takes about 10 seconds.

**Windows:** run the commands from `demo/run_demo.sh` one by one, using `.venv\Scripts\python`.

### The front end (`simulation/index.html`)

It's a single self-contained file, and it works offline.

| Tab | What it shows |
|---|---|
| Overview | The 9 SOP steps with what happened at each, KPIs, the prospect table and the project update |
| Board | A Linear-style board. Click an issue for:<br>- **Description:** the SOP issue template<br>- **Email:** agent-written text highlighted, approved blocks in grey<br>- **Research:** segment evidence, do-not-contact check, fact candidates, draft attempts, override<br>- **Activity:** every logged action |
| Simulation replay | All 65 actions in order, with the board updating as you go. Use Play or the arrow keys |
| Agent & guardrails | The three rules, guardrail test results, drafts rejected during the run, human overrides (before and after), the approved claims and the do-not-contact list |
| Outbox | Clarifying questions, daily update and submission email. None of them are sent |
| Documents | The guardrail note, Part B and the clarifying questions |

---

## 4. Using the agent

### Run it on a new firm's website

```bash
.venv/bin/python agent.py --firm "Whitten Architects" --url https://www.whittenarchitects.com --city Portland
```

This reads the live site, so it needs internet, but it needs no key. It takes about 10 seconds and prints each stage:

1. **Pages read:** the homepage plus up to 7 internal pages, with About, Projects and Awards first. If a site blocks normal requests, a reader service is tried; if both fail, the firm is dropped.
2. **Segment** (Residential, Commercial or Mixed), with the sentence from the site that supports it.
3. **Do-not-contact check** on the firm and on every parent or affiliate the site names, using exact name matching.
4. **Fact candidates:** each one is either verified (its quote is word for word on the page) or discarded. Then the chosen fact: a named award beats a named project, and a named project beats a founding year.
5. **Draft attempts,** including any the guardrails rejected and why, and the final issue description in the SOP template.

Add `--json` for output a machine can read.

### Add prospects to the pipeline

Add a row to `config/prospects.csv` (`n,firm,city,website`), then run:

```bash
LIVE_FETCH=1 .venv/bin/python run_sop.py run --local
```

`LIVE_FETCH=1` reads the live website for firms that aren't in the bundled snapshot. Re-running is safe, because finished steps are skipped (`state/local.json`).

### Change the client brief

Edit `config/kestrel.json`. It holds:
- the approved claims;
- the product and call-to-action blocks inserted into every email;
- the sign-off;
- the 90-word limit;
- the do-not-contact list;
- the Linear labels, statuses and approver.

Re-run the pipeline after changing it.

### Review and override a draft (human in the loop)

```bash
.venv/bin/python run_sop.py override --local --issue KES-9 \
  --subject "New subject" --opener "New opening sentences." --reason "Why the AI version was wrong"
```

The edit goes through the same guardrails; a rejected edit is not saved. It is logged as a comment showing the before, the after and the reason, plus a description update.

To re-research issues after changing the agent:

```bash
.venv/bin/python run_sop.py rework --local --issue KES-2,KES-8 --reason "..."
```

That logs the reopen, moves the issue back to In Progress, and redoes Steps 4–6.

---

## 5. Command reference

Every `run_sop.py` command takes `--local` to use the simulated workspace.

| Command | SOP step | What it does |
|---|---|---|
| `run_sop.py ask` | Comms | Writes the clarifying-questions email to `outbox/` |
| `run_sop.py setup --invite` | 1 | Creates the project, 5 labels and any missing statuses, and invites `nbakshi@invictus.ai` |
| `run_sop.py run` | 2–7 | One issue per prospect, the do-not-contact check, research, the draft, and sending for approval. Every action is logged |
| `run_sop.py accept-invite` | (simulation) | Simulates Nirbhay accepting the invite. This is the only step that stands in for another person |
| `run_sop.py assign` | 6 | Assigns In Review issues to Nirbhay once Nirbhay has joined |
| `run_sop.py docs` | Deliverables 3 and 4 | Posts the guardrail note and Part B as project documents |
| `run_sop.py daily-update` | 8 | Three-line update email (Done / Blocked / Needs your call) to `outbox/` |
| `run_sop.py submit --agent-link URL --loom URL` | 9 | Project update with health, and the submission email to `outbox/` |
| `run_sop.py status` | — | Where every prospect stands |
| `run_sop.py override …` / `rework …` | 7 | Human edits and re-research, both logged |
| `view.py` | — | Rebuilds `simulation/index.html` |
| `tests/test_guardrails.py` | — | 11 guardrail tests |
| `tests/test_reuse_offline.py` | — | Proves a Linear run reuses the reviewed results, with zero model calls |
| `tools/check_linear_api.py` | — | Validates every Linear GraphQL call against Linear's published schema |

### Optional switches

- **LLM engine:** set `AGENT_ENGINE=model` and an `OPENROUTER_API_KEY` in `.env` (see `.env.example`). If the model is unavailable, the agent falls back to the offline engine, and the guardrails are identical either way.
- **Real Linear:** set `LINEAR_API_KEY` in `.env` (an admin key from Linear → Settings → Security & access → Personal API keys), then run the commands above without `--local`. A real-Linear run reuses the reviewed simulation results, including the override, instead of researching again. Note that `setup --invite` against real Linear sends a real invitation email.

---

## 6. Guardrails

The agent must never say these three things. Each is enforced in code on every draft, before anyone reviews it. The full details are in [`docs/guardrails.md`](docs/guardrails.md).

1. **Anything about Kestrel beyond the four approved claims.**
   - The agent writes only the subject line and the opening one or two sentences.
   - The product sentence, the call to action and the sign-off are inserted from config, word for word.
   - Product, comparison and pricing words in the agent-written parts are rejected.
2. **A fact about the prospect without a word-for-word source.**
   - Every quote must appear on the page it cites.
   - Every number and proper noun in the opener must come from the source.
   - The first sentence must carry the fact.
3. **The name of another company.** This covers Kestrel customers, do-not-contact firms, other prospects, competitors, and company-style names (Construction, LLC, Group…) other than the prospect's own.

A draft that fails is regenerated. If it still fails after repeated attempts, the agent writes no email at all. A style check also rejects stock phrasing, and openers too similar to another email in the same batch.

---

## 7. Decisions, assumptions and open questions

- **Simulation instead of real Linear and real email.** This was my choice for this submission. The Linear code path exists, and every query has been validated against Linear's schema. Pointing it at a real workspace needs only a `LINEAR_API_KEY`.
- **Standard sign-off (open question).** The brief doesn't define it. Drafts use "Best, The Kestrel Rooms team" as a placeholder, flagged in every daily update and in the clarifying questions.
- **Casco Bay segment.** Step 2 requires a segment chosen from the firm's website, and that website doesn't exist. I didn't guess. The issue carries only Source: Brief and was dropped at Step 4. This is raised in Part B.
- **Do-not-contact matching.** Names are matched exactly, plus any parent or affiliate named on the firm's own site. Providence Architecture & Building Co. was not matched on its name; it was matched because its homepage names The Providence Group as its parent.
- **"No numbers".** This was read as "no numbers beyond the approved claims". "15-minute", "30-day" and "less than a day" appear only inside the fixed blocks.
- **Steps 2 and 3 followed as written,** even though the order conflicts (the site is read for the segment before the do-not-contact check). That's why Providence has a segment label. It's the main change proposed in Part B.
- **Human override (KES-9, G4 Design Studios).** The agent wrote "G4 Design Studios dates back to 2001", but the source says the firm was Steve Guild Design until it was renamed in 2014. I rewrote it as "Steve started the studio as Steve Guild Design in 2001." My first edit was rejected by the guardrails (a lone "G4" in the subject was flagged as an unsourced number), so the guardrails apply to human edits too.

---

## 8. Troubleshooting

| Problem | Fix |
|---|---|
| `python3: command not found` or Python older than 3.10 | Install Python 3.10+ (on macOS, `brew install python`), then rerun `./demo/run_demo.sh` |
| `pip install` fails (no internet) | Install the three packages in `requirements.txt` from a local wheel cache, or run once while online |
| `agent.py` reports "did not load" for a live site | The site is blocking requests or is down. The SOP says to drop the firm rather than replace it |
| The front end looks stale | Run `.venv/bin/python view.py` again, then reload |
| You want a clean slate | Run `./demo/run_demo.sh`. It deletes `state/`, `local_linear/`, `outbox/` and `logs/` and rebuilds everything |
