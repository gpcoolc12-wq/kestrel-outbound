# Loom script: Kestrel Outbound (target 9 minutes, hard limit 10)

The assessment asks the Loom to cover four things. This script covers them in this order:

| Required by the brief | Section | Time |
|---|---|---|
| One prospect from start to finish, in Linear and in your agent | 2 and 3 | 1:00–5:00 |
| One decision the AI tool made that you overrode, and why | 4 | 5:00–6:30 |
| One SOP step you would change, and whether you followed it anyway | 5 | 6:30–8:00 |
| How long the assignment took you | 7 | 8:45–9:00 |

Section 6 (guardrails, 8:00–8:45) isn't required, but guardrail judgement is one of the five things they assess, so 45 seconds on it is worth it.

---

## Part 1: Setup before you press record (about 10 minutes)

**1. Open the workspace.**
- **Real Linear** (if you ran it without `--local`): open the Kestrel Outbound project.
- **Local simulation:**

  ```bash
  cd ~/Downloads/kestrel-outbound && .venv/bin/python view.py && .venv/bin/python -m http.server 8765 --directory simulation
  ```

  Then open http://127.0.0.1:8765/index.html.

**2. Browser tabs, left to right:**
1. The board (Linear, or the viewer above)
2. https://ervinarchitecture.com/press-awards/ (the source page for the fact)
3. https://github.com/gpcoolc12-wq/kestrel-outbound (README)
4. `docs/part_b.md` (in the repo or in Linear)

**3. Terminal:** open it in `~/Downloads/kestrel-outbound`, font size around 16, then run `clear`.

**4. Rehearse the live agent run once.** It takes 1–2 minutes on the free models, so you need to know what it prints.

```bash
.venv/bin/python agent.py --firm "Ervin Architecture" --url https://ervinarchitecture.com --city Bangor
```

**5. Loom settings:** "Screen + Camera", one screen, mic checked. Close Slack and email notifications (Do Not Disturb).

**6. Fill in the two blanks below:** `[TIME TAKEN]` and `[MY OVERRIDE]` if you want to use a different example.

**7. Long waits:** if the agent takes longer than 30 seconds on camera, keep talking (the script is written for that), or pause Loom and resume. Loom lets you trim afterwards.

---

## Part 2: The script

Normal type is what you say. **Bold lines** are what you do on screen. Speak at about 140 words a minute; each section fits its time box.

### 1. Opening (0:00–1:00)

**Show the board, with all 10 issues visible.**

> Hi Nirbhay, I'm Gaurav. This is my Kestrel Outbound take-home.
>
> In short, I built an agent that runs your SOP end to end: Linear setup, one issue per prospect, the do-not-contact check, research, drafting and the approval hand-off. Every action is logged in Linear as a comment and a description or status update.
>
> Here's where it landed. All 10 prospects have issues. Eight are In Review with the Ready for Approval label, assigned to you. Two were dropped: Casco Bay Design Workshop, because its domain isn't registered, so the website can't load; and Providence Architecture & Building Co., because their own homepage says they're an affiliate of The Providence Group, which is an existing Kestrel customer.
>
> Nothing was emailed to anyone. Emails go to an outbox, as the brief asked.

### 2. One prospect in the agent (1:00–3:00)

**Switch to the terminal. Start the agent run on Ervin Architecture.**

```bash
.venv/bin/python agent.py --firm "Ervin Architecture" --url https://ervinarchitecture.com --city Bangor
```

> I'll follow one prospect all the way through: Ervin Architecture in Bangor. This is the same agent the pipeline uses, run on its own, so you can point it at any firm's website.
>
> First it reads the firm's public site, which is the homepage and up to seven internal pages. It prioritises pages like About, Projects and Awards. If a site blocks a normal request, it falls back to a reader service. It only gives up, and the firm gets dropped, if both fail.

**When the segment line prints:**

> Second, the segment. It picked "Mixed". It has to back that with a quote copied word for word from a page on the site, and the code checks that the quote really is on that page. Here it's the About page, where Ervin presents both commercial and residential work.
>
> Third, before any research, the do-not-contact check. It checks the firm name and every parent or affiliate the site names. Matching is on exact names, not fuzzy, so "Providence Architecture" isn't confused with "The Providence Group". The real affiliation was caught because the site says so in plain words. For Ervin it's clear.

**When the fact prints:**

> Fourth, the fact. The model proposes candidate facts, each with a quote and the page it came from. Code checks the quote is word for word on that page. Any candidate that fails is discarded and the next one is tried, so a fact never goes in without a source. For Ervin it found that the firm won the MEREDA Project of the Year 2023 for the Maine Savings Amphitheater, on their Press and Awards page.

**Switch to the press-awards tab. Find (Cmd+F) "MEREDA" and highlight it.**

> And here it is on their site, word for word.

**Back to the terminal, at the draft:**

> Fifth, the draft: 74 words, under the 90-word limit, and it opens with the fact. The important design choice is that the model never writes anything about Kestrel. It writes only the subject and that first line about the firm. The product sentence, the call to action and the sign-off are inserted from config, word for word, so it can't make up a claim.

### 3. The same prospect in Linear (3:00–5:00)

**Switch to the board. Open KES-5, Ervin Architecture.**

> Now the same prospect in Linear. The title follows the format: Firm, em dash, City, pipe, Outbound. It has the two labels Step 2 requires, Segment: Mixed and Source: Brief, plus Ready for Approval from Step 6. It's In Review and assigned to you.
>
> The description is your issue template, filled in: Firm, Website, Segment, Do-not-contact check, then Fact with its Source URL, the draft email, and a one-line status note.

**Scroll to Activity and Comments.**

> Step 7 says every action gets a comment with links and an update to the description or status, both every time. So here's the trail, in order:
> - The issue was created from the brief, with the segment evidence.
> - The do-not-contact check came back Clear.
> - It moved to In Progress.
> - The research comment has the fact, the quote, the source link and every page it read.
> - Then the draft.
> - Then it moved to In Review with the label.
> - Finally, the assignment to you, which only happened once you'd accepted the workspace invite.
>
> Each of those also changed the description or the status. That's enforced in code: the pipeline has exactly one function that changes an issue, and it always does both. The pipeline never moves anything to Done; that's yours.

**Optional, 10 seconds: open KES-6 to show a drop.**

> And for contrast, here's the Providence one: straight from Todo to Canceled, DROPPED added to the title, the reason in the description, and no research or draft, because Step 3 stops it first.

### 4. A decision the AI made that I overrode (5:00–6:30)

**Open KES-10, Gabriel Stadecker Architect. Scroll to the "Human override" comment.**

> Here's a decision the AI made that I overrode. For Gabriel Stadecker, the agent picked a good fact, the 1812 Tavern House renovation in Charlotte, Vermont. But its opening line also credited the builder, Sutherland Construction, and the project photographer.
>
> Technically, everything in that line was on their website, so the sourcing check passed. But it names another company in a cold email, which is one of my three "never say" rules. And it's a bad hook: Gabriel doesn't want to read about his builder.
>
> So I rewrote the opening to keep the project and the place and drop the third parties. I logged it like any other action: a comment with the before, the after and the reason, plus a description update. My edit went back through the same guardrails, because human edits don't get to skip them.
>
> And I didn't stop at the one email. I added a rule to the agent so it now rejects company-style names by itself, like Construction, Builders, LLC or Group, unless it's the prospect's own name. There's a test for it. The point of an override is to fix the system, not just the one email.

### 5. The SOP step I'd change, and whether I followed it (6:30–8:00)

**Open Part B.**

> The step I'd change is the order of Steps 2 and 3. Step 2 has me choose each firm's segment from its own website, so I'm reading the site when I create the issue. But Step 3 says the do-not-contact check must come before any research. That means a firm that's off limits, like the Providence Group affiliate, gets read and classified before anyone checks the list.
>
> Did I follow it anyway? Yes, exactly as written. Issues were created with segments first, then the do-not-contact check ran. It cost us a little: the Providence affiliate got a segment label before it was dropped.
>
> The same step also contradicts itself for Casco Bay. Step 2 says every issue carries a segment chosen from the website, and Casco Bay's website doesn't exist. I didn't invent a segment. I left the label off, flagged it to you, and dropped the issue at Step 4, as the SOP says.
>
> My change: create the issue with Source: Brief only, run the do-not-contact check, then add the segment once the firm is clear. Part B has six more, including the missing standard sign-off. That isn't in the brief, so drafts use a placeholder, and I asked you about it in my clarifying email.

### 6. Guardrails (8:00–8:45)

**Show `docs/guardrails.md` or the terminal running the test file.**

```bash
.venv/bin/python tests/test_guardrails.py
```

> On guardrails: there are three things the agent can never say. No claim about Kestrel beyond the four approved ones. No fact about the firm without a word-for-word source. And no other company's name. All three are enforced when the email is generated, not in review. If a draft fails, the violations go back to the model, and after three failures it returns no email rather than a bad one. One studioblue draft got rejected live, for saying "Vermont" when the site only says "VT".

### 7. Time and close (8:45–9:00)

> All in, this took me [TIME TAKEN]. The repo is public, with run instructions and a sample run, and the links are in my submission email. Thanks, Nirbhay.

**Stop recording.**

---

## Part 3: After recording

1. Trim any long waits in Loom's editor, and check the video is 10:00 or less.
2. Set the Loom title to **Kestrel Outbound — Gaurav Pawar**.
3. Set Loom sharing to "Anyone with the link".
4. Copy the share link and regenerate the submission email with it:

   ```bash
   .venv/bin/python run_sop.py submit --agent-link https://github.com/gpcoolc12-wq/kestrel-outbound --loom <loom-url>
   ```

   Add `--local` if you're staying on the simulation.
5. Send the submission email from `outbox/` yourself, before **Monday 5 October 2026, 5:00 pm IST**.

## Backup material (if something goes wrong on camera)

- **The agent is slow or a model errors out:** say "free-tier model is slow, here's the same run from earlier", then open `examples/sample-run/run.log` and KES-5 in the board.
- **Asked "why Mixed for everyone?":** every one of these sites shows both houses and commercial or institutional work, and each label has a word-for-word quote behind it in the creation comment.
- **A second override example:** for studioblue, the model listed Ecopixel, a carbon-offset vendor, as an "affiliate". That's not a parent or sister company. It was harmless here, since Ecopixel isn't on the do-not-contact list, but I wouldn't trust its affiliate list without that check.
