# Loom script: Kestrel Outbound (target 9 minutes, hard limit 10)

The assessment asks the Loom to cover four things. This script covers them in this order:

| Required by the brief | Section | Time |
|---|---|---|
| One prospect from start to finish, in Linear and in your agent | 2 and 3 | 1:00–5:00 |
| One decision the AI tool made that you overrode, and why | 4 | 5:00–6:30 |
| One SOP step you would change, and whether you followed it anyway | 5 | 6:30–8:00 |
| How long the assignment took you | 7 | 8:45–9:00 |

Section 6 (guardrails, 8:00–8:45) isn't required, but guardrail judgement is one of the five things they assess. Everything runs locally as a simulation: no API key, no real Linear, no email sent.

---

## Part 1: Setup before you press record (about 5 minutes)

**1. Rebuild the demo and open the front end.** No key or internet is needed for this step.

```bash
cd ~/Downloads/kestrel-outbound && ./demo/run_demo.sh && open simulation/index.html
```

**2. Browser tabs, left to right:**
1. `simulation/index.html` (the front end). Tabs: Overview · Board · Simulation replay · Agent & guardrails · Outbox · Documents.
2. https://ervinarchitecture.com/press-awards/ (the source page for the fact)
3. https://github.com/gpcoolc12-wq/kestrel-outbound (README)

**3. Terminal:** open it in `~/Downloads/kestrel-outbound`, font size around 16, then run `clear`.

**4. Rehearse the live agent run once.** It takes about 10 seconds, needs internet (it reads the live site), and needs no key.

```bash
.venv/bin/python agent.py --firm "Ervin Architecture" --url https://ervinarchitecture.com --city Bangor
```

**5. Loom settings:** "Screen + Camera", one screen, mic checked. Turn on Do Not Disturb.

---

## Part 2: The script

Normal type is what you say. **Bold lines** are what you do on screen.

### 1. Opening (0:00–1:00)

**Front end, Overview tab.**

> Hi Nirbhay, I'm Gaurav. This is my Kestrel Outbound take-home.
>
> I built an agent and a pipeline that run your SOP end to end: workspace setup, one issue per prospect, the do-not-contact check, research, drafting, approval and logging. Everything here is a local simulation. A file-based stand-in replaces Linear, emails go to an outbox, and nothing is sent to anyone.
>
> These are the nine SOP steps with what happened at each. All 10 prospects have issues. Eight are In Review, Ready for Approval, assigned to you. Two were dropped: Casco Bay Design Workshop, because its domain isn't registered so the site can't load; and Providence Architecture & Building Co., because their own homepage says they're an affiliate of The Providence Group, an existing Kestrel customer.

### 2. One prospect in the agent (1:00–3:00)

**Terminal: run the agent on Ervin Architecture.**

```bash
.venv/bin/python agent.py --firm "Ervin Architecture" --url https://ervinarchitecture.com --city Bangor
```

> I'll follow one prospect all the way through: Ervin Architecture in Bangor. This is the same agent the pipeline uses, run on its own, so you can point it at any firm's website.
>
> First, it reads the public site: the homepage and up to seven internal pages, with About, Projects and Awards first.
>
> Second, the segment. It picked Mixed, and it shows the sentence from their own homepage that proves it: music venues, restaurants, offices, and custom homes.
>
> Third, before any research, the do-not-contact check, on the firm name and on every parent or affiliate the site names. Matching is on exact names, not fuzzy, so "Providence Architecture" isn't confused with "The Providence Group". The real affiliation was caught because that site says so in plain words. Ervin is clear.
>
> Fourth, the fact. It found two candidates, an award and a named project, and checked that each quote appears word for word on its page. It picks the strongest kind, so an award beats a project, and a project beats a founding year. Here that's the MEREDA Project of the Year 2023 for the Maine Savings Amphitheater.

**Switch to the press-awards tab. Find (Cmd+F) "MEREDA".**

> And there it is on their site, word for word.

**Back to the terminal, at the draft.**

> Fifth, the draft: 80 words, under the 90-word limit, and it opens with the fact. The key design choice is that the agent never writes anything about Kestrel. It writes only the subject and the opening lines about the firm. The product sentence, the call to action and the sign-off are inserted from config, word for word, so there's no way for it to make up a claim.
>
> It also doesn't need an API key. The research and writing rules run offline, and an LLM is an optional switch. The guardrails are identical either way.

### 3. The same prospect in the workspace (3:00–5:00)

**Front end, Board tab. Click KES-5 Ervin Architecture.**

> Now the same prospect on the board. The title follows the format: Firm, em dash, City, pipe, Outbound. It has the two labels Step 2 requires, Segment: Mixed and Source: Brief, plus Ready for Approval from Step 6. It's In Review and assigned to you.

**Description sub-tab, then Email.**

> The description is your issue template, filled in. The Email view shows what's written by the agent, highlighted, and what's inserted from the approved claims, in grey.

**Activity sub-tab.**

> Step 7 says every action gets a comment with links and an update to the description or status, both every time. So the trail runs in order: created with the segment evidence, do-not-contact Clear, In Progress, the research comment with the quote and source link, the draft, then In Review with the label, then assigned to you once you joined. One function in the code changes issues, and it always does both. Nothing ever moves to Done; that's yours.

**Simulation replay tab. Press Play, or step with the arrow keys.**

> And this is the whole run replayed action by action, 65 of them. You can watch Providence go straight from Todo to Canceled at the do-not-contact check, with no research and no draft.

### 4. A decision the AI made that I overrode (5:00–6:30)

**Agent & guardrails tab, scroll to "Human overrides" (or open KES-9 → Research).**

> Here's a decision the AI made that I overrode. For G4 Design Studios, the agent wrote "G4 Design Studios dates back to 2001". The source says Steve started the firm as Steve Guild Design in 2001, and it was only renamed G4 in 2014. So the agent's line is a small factual slip, exactly the kind a founder notices, and a bad first impression in a cold email.
>
> I rewrote it in the site's own terms: "Steve started the studio as Steve Guild Design in 2001." It's logged like any other action: a comment with the before, the after and the reason, plus a description update.
>
> And my edit went through the same guardrails. My first attempt was actually rejected, because my subject line said "G4" on its own and the checker treated the "4" as an unsourced number. Human edits don't get to skip the rules.

### 5. The SOP step I'd change, and whether I followed it (6:30–8:00)

**Documents tab → Part B.**

> The step I'd change is the order of Steps 2 and 3. Step 2 has me choose each firm's segment from its website, so I'm reading the site when I create the issue. But Step 3 says the do-not-contact check must come before any research. So a firm that's off limits, like the Providence affiliate, gets read and classified before anyone checks the list.
>
> Did I follow it anyway? Yes, exactly as written. You can see it on the board: Providence got a segment label before it was dropped.
>
> The same step contradicts itself for Casco Bay. Step 2 wants a segment from a website that doesn't exist. I didn't invent one. I left the label off, flagged it to you, and dropped it at Step 4.
>
> My change: create the issue with Source: Brief only, run the do-not-contact check, then add the segment once the firm is clear. Part B has six more, including the missing standard sign-off, which I asked you about in my clarifying email.

### 6. Guardrails (8:00–8:45)

**Agent & guardrails tab: the three rules, and the tests (11 of 11 passing).**

> Three things the agent can never say: no claim about Kestrel beyond the four approved ones, no fact about the firm without a word-for-word source, and no other company's name. All three are checked in code on every draft, before anyone reviews it. A draft that fails is regenerated, and if it keeps failing there's no email at all. The run also rejects drafts that sound the same as another email in the batch, so all eight read differently.

### 7. Time and close (8:45–9:00)

> All in, this took me 5 hours. The repo is public, and one command rebuilds this whole demo without any key. The links are in my submission email. Thanks, Nirbhay.

**Stop recording.**

---

## Part 3: After recording

1. Trim any pauses in Loom's editor, and check the video is 10:00 or less.
2. Set the Loom title to **Kestrel Outbound — Gaurav Pawar**, and sharing to "Anyone with the link".
3. Put the Loom link into the submission email:

   ```bash
   .venv/bin/python run_sop.py submit --local --agent-link https://github.com/gpcoolc12-wq/kestrel-outbound --loom <loom-url>
   ```

4. Send the submission email from `outbox/` yourself, before **Monday 5 October 2026, 5:00 pm IST**.

## Backup material

- **No internet during recording:** skip the live `agent.py` run. The Board → KES-5 → Research tab shows the same candidates, the same quote and the same draft from the bundled snapshot.
- **Asked "why Mixed for almost everyone?":** these sites all show both houses and commercial or institutional work. The Research tab shows the sentence and the counts behind each label.
- **A second override candidate:** Jonathan Chambers' fact is the "Raffa Yoga" project. That's the client's business name, so a reviewer could prefer one of their residential projects.
