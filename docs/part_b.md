I followed every step as written. Below are the changes I would make, starting with the ones that cost the most.

## 1. Run the do-not-contact check before the segment is chosen (Steps 2 and 3)

Step 2 has me read each firm's website to pick a segment label. Step 3 then says the do-not-contact check must happen "before any research". So a firm that should never be touched, such as a Providence Group affiliate, gets read, classified and written up before anyone checks the list. **Change:** at intake, create the issue with Source: Brief only, run the do-not-contact check, and add the segment label only if the firm is clear.

## 2. Say what happens when a website doesn't load at intake

Step 2 says every issue carries a segment label chosen from the firm's website. Step 4 says to drop a firm whose website doesn't load. Casco Bay Design Workshop's domain isn't registered, so I couldn't meet both rules. I left the segment blank rather than guess, and dropped the issue at Step 4. **Change:** add "Segment: Unknown", or let intake drop dead sites straight away.

## 3. Put the missing inputs in the brief

* **Kestrel's standard sign-off** isn't given anywhere, but Step 5 requires it. Every draft uses a placeholder that is flagged as unconfirmed.
* **"No numbers"** clashes with the approved claims themselves ("30-day", "15-minute", "less than a day"). It should say "no numbers beyond the approved claims".
* **Matching rule for the do-not-contact list.** "Affiliate" isn't defined, and fuzzy name matching would wrongly flag Providence Architecture & Building Co. against The Providence Group. **Change:** match exact names, plus any parent or affiliate the firm's own site names. Send near-misses to a human.

## 4. Make "invite accepted" a precondition for Step 6

You can only assign an issue to someone who is a member of the workspace. Until Nirbhay accepts the invite, Step 6 can't be completed, so issues sit in In Review unassigned. **Change:** make "approver has joined" part of Step 1's definition of done, or assign approvals to a placeholder or triage queue.

## 5. Lighten Step 7

Writing both a comment and a description update for every action is the right audit trail, but it doubles the manual work and the chance of the two disagreeing. **Change:** the description holds the current state, and comments are the change log, written automatically by the agent (which is what my agent does). People only comment on judgement calls.

## 6. Keep evidence of each fact, and capture it when the email is sent

Websites change. A fact that was true when researched can be gone by the time Nirbhay approves the draft. **Change:** store the verbatim quote and the date it was captured next to the URL (my agent stores the quote), and re-check the source just before sending.

## 7. Approve in batches, and record rejections

Ten one-by-one approvals don't scale. **Change:** Nirbhay approves a batch, and every rejection is recorded with a reason code ("weak hook", "tone"…). Those codes feed back into the agent's prompts and guardrails.
