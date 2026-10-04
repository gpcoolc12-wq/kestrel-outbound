# Loom outline (10 minutes or less)

Have three things open: `simulation/index.html`, a terminal in the repo, and `local_linear/workspace.json`.

**0:00 Setup (1 min)**
* What the system is: an agent plus a pipeline that runs the SOP. Linear is simulated locally and emails go to `outbox/`. With a `LINEAR_API_KEY`, the same code drives real Linear.
* Show the top of the board: members, the pending invite, the 5 labels, the statuses, and the issue count for each status.

**1:00 One prospect, start to finish (4 min)**
* Run it live: `agent.py --firm … --url …`. Point out the pages it reads, the segment it picks with its evidence quote, the do-not-contact result, each candidate fact (kept or discarded), any draft the guardrails rejected, and the final email.
* In the board, open the same firm's issue. Show the title format and labels, the filled template, the activity history (Todo → In Progress → In Review) and the comments, one for every action, each with links.
* Show that the fact's quote really is on the source page: click the link.

**5:00 A decision the AI made that I overrode (1.5 min)**
* Pick one real example from this run (see "Overrides" in my notes). Candidates:
  - **Segment.** The model wanted to call a firm Mixed or Commercial from one sentence on the site. Check that against the firm's project list.
  - **The fact the model ranked first.** Generic, e.g. "founded in 19xx", when a named, recent award or project is a better hook.
  - **A fuzzy do-not-contact hit.** Providence Architecture & Building Co. versus The Providence Group. Exact-name matching is why it isn't dropped.

**6:30 One SOP step I would change (1.5 min)**
* Steps 2 and 3: the segment is chosen from the website before the do-not-contact check. Yes, I followed the step as written. That's why Casco Bay has no segment label and was dropped at Step 4. Show Part B.

**8:00 Guardrails (1 min)**
* The model never writes product copy. Show `tests/test_guardrails.py` passing, and one rejected draft from the logs.

**9:00 Time taken, and close (30 s)**
