**Scope:** what the Kestrel outbound agent must never say, and how each rule is enforced while the email is being generated, before any human reviews it. The code is in `kestrel/guardrails.py`, and `tests/test_guardrails.py` proves each rule blocks its violation.

**How every email is built.** The model never writes about Kestrel. It writes two things only: a subject line, and an opener of one or two sentences about the prospect. Code then appends the approved product sentence, the approved call to action and the sign-off, copied verbatim from `config/kestrel.json`. Every draft goes through `validate_email()`. If any check fails, the draft is rejected and the exact violations go back to the model to regenerate. After 3 failed attempts the agent returns **no email** and the issue is marked Blocked. A bad draft never reaches review.

## 1. Never say anything about Kestrel beyond the four approved claims

That means no extra features, numbers, customer names, comparisons, pricing or promises.

* **Structural:** product copy is a fixed block inserted by code, and the model has no field in which to write a claim. A check confirms the fixed blocks are present and unaltered.
* **Scan:** the model-written subject and opener are rejected if they contain product vocabulary ("Kestrel", software, booking, calendar, setup, trial, save, hours…), comparison or superlative words (better, faster, best, than, unlike, leading…), or `$ % € £`. A word is allowed only when it appears in the prospect's own source quote. For example, a firm that "designs a calendar" isn't penalised.
* The only numbers about Kestrel that can appear are "15-minute", "30-day" and "less than a day", all inside the fixed blocks.

## 2. Never say anything about the prospect that isn't backed by a verbatim quote from its own website

* **Research:** each candidate fact must come with a quote and the URL it came from. Code checks that the quote appears word for word (after whitespace and punctuation are normalised) in the text actually fetched from that URL. If it doesn't, the fact is discarded and the next candidate is tried. A fact without a verified source is never used.
* **Drafting:** every number in the opener and subject must appear in the source quote. Every capitalised name (a project, a place, a person, an award) must appear on the source page. That blocks invented details such as a wrong year, a made-up award or a misattributed project.
* The first sentence must share key words with the quote, so the email opens with the sourced fact, as Step 5 requires.

## 3. Never name another company

That covers Kestrel's customers (such as The Providence Group), do-not-contact firms, other prospects on the list, and competitors.

* **Blocklist:** before any draft is accepted, the whole email (subject and body) is checked against a list built at run time from the do-not-contact list, the other nine prospects and known room-booking competitors. Matching uses word boundaries and normalises "+" and "&".
* **Same root as rule 2:** any capitalised name has to come from the prospect's own page, so the model can't add a company from its own memory either.
* **Do-not-contact gate:** before any research, the firm and every parent or affiliate named on its site (each backed by a verified quote) are matched against the list. A mention anywhere on the site of a do-not-contact group whose affiliates are also excluded counts as a match. The issue is then dropped, and nothing about that firm is ever researched or drafted.

**What review still does:** Nirbhay approves tone and whether the fact is a good hook. Review is not where these three rules are enforced.
