#!/usr/bin/env python3
"""Runs the Kestrel Outbound SOP end to end, step by step, logging every action.

  python run_sop.py setup [--invite]     Step 1: project, labels, statuses (+ invite Nirbhay)
  python run_sop.py run                  Steps 2-7 for every prospect in config/prospects.csv
  python run_sop.py assign               Step 6 retry: assign In Review issues once Nirbhay has joined
  python run_sop.py docs                 Post the guardrail note and Part B as project documents
  python run_sop.py daily-update         Step 8: write today's update email to outbox/
  python run_sop.py submit               Step 9: project update + submission email to outbox/
  python run_sop.py status               Print where every prospect stands
  python run_sop.py ask                  Write the clarifying-questions email to outbox/
  python run_sop.py accept-invite        --local only: simulate Nirbhay accepting the invite

Add --local to any command to use the file-based Linear stand-in (local_linear/) instead of Linear.
Re-running is safe: finished steps are skipped, using state/<backend>.json.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from kestrel import agent as A  # noqa: E402
from kestrel.backends import LinearBackend, LocalBackend  # noqa: E402
from kestrel.fetch import Page, SiteUnreachable, read_site  # noqa: E402
from kestrel.outbox import write_email  # noqa: E402
from kestrel.template import render  # noqa: E402

CFG = json.loads((ROOT / "config/kestrel.json").read_text())
LIN = CFG["linear"]
APPROVER = LIN["approver_name"]


def log(msg: str) -> None:
    line = f"[{datetime.now():%H:%M:%S}] {msg}"
    print(line, flush=True)
    (ROOT / "logs").mkdir(exist_ok=True)
    with open(ROOT / "logs" / f"{datetime.now():%Y-%m-%d}.log", "a") as f:
        f.write(line + "\n")


class Run:
    def __init__(self, local: bool):
        self.be = LocalBackend(CFG, root=str(ROOT / "local_linear")) if local else LinearBackend(CFG)
        self.state_path = ROOT / "state" / f"{self.be.name}.json"
        self.state = json.loads(self.state_path.read_text()) if self.state_path.exists() else {"prospects": {}}
        self.cache = ROOT / "state" / "site_cache"

    def save(self):
        self.state_path.parent.mkdir(exist_ok=True)
        self.state_path.write_text(json.dumps(self.state, indent=2))

    # Step 7: every action = one comment with links + one description/status update. Always both.
    def act(self, rec: dict, comment: str, *, status: str | None = None, title: str | None = None,
            labels: list | None = None, assignee: str | None = None):
        rec["history"].append({"at": datetime.now().isoformat(timespec="seconds"), "action": comment.split("\n")[0]})
        if status:
            rec["status"] = status
        if title:
            rec["title"] = title
        if labels is not None:
            rec["labels"] = labels
        self.be.update_issue(rec["issue_id"], title=title, description=render(rec), state=status,
                             labels=labels, assignee_id=assignee)
        self.be.comment(rec["issue_id"], comment)
        self.save()
        log(f"  {rec['identifier']}: {comment.splitlines()[0]}")

    # ---------------------------------------------------------------- site cache
    def pages(self, rec) -> list[Page]:
        f = self.cache / f"{rec['n']}.json"
        if f.exists():
            return [Page(**p) for p in json.loads(f.read_text())]
        pages = read_site(rec["website"])
        self.cache.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps([p.__dict__ for p in pages]))
        return pages

    def blocklist(self, rec) -> list[str]:
        others = [p["firm"] for p in self.state["prospects"].values() if p["firm"] != rec["firm"]]
        return [d["company"] for d in CFG["do_not_contact"]] + others + A.G.COMPETITORS

    # ---------------------------------------------------------------- Step 1
    def setup(self, invite: bool):
        log("Step 1: set up Linear")
        info = self.be.setup(log)
        self.state["project_url"] = info["project_url"]
        if invite:
            self.be.invite(LIN["approver_email"], log)
            self.state["invited"] = True
        self.save()

    def _ready(self):
        if hasattr(self.be, "team_id") and self.be.team_id is None:
            self.be.setup(lambda m: None)

    # ---------------------------------------------------------------- Steps 2-7
    def run(self):
        self._ready()
        rows = list(csv.DictReader(open(ROOT / "config/prospects.csv")))
        log("Step 2: one issue per prospect")
        for row in rows:
            self.step2(row)
        for row in rows:
            rec = self.state["prospects"][row["n"]]
            log(f"{rec['identifier']} {rec['firm']}")
            if rec["status"] == "Canceled":
                continue
            if not rec.get("dnc_done"):
                self.step3(rec)
            if rec["status"] == "Canceled":
                continue
            if not rec.get("fact"):
                self.step4(rec)
            if rec["status"] == "Canceled" or not rec.get("fact"):
                continue
            if not rec.get("draft"):
                self.step5(rec)
            if rec.get("draft") and rec["status"] != "In Review":
                self.step6(rec)

    def step2(self, row):
        if row["n"] in self.state["prospects"]:
            return
        rec = {"n": row["n"], "firm": row["firm"], "city": row["city"], "website": row["website"],
               "title": f"{row['firm']} — {row['city']} | Outbound", "status": "Todo", "history": [],
               "status_note": "Issue created; next: do-not-contact check."}
        labels = ["Source: Brief"]
        try:
            pages = self.pages(rec)
            prof = A.segment_and_affiliates(rec["firm"], pages)
            rec["profile"] = A.to_dict(prof)
            rec["segment_line"] = f"{prof.segment} — {prof.segment_reason} (source: {prof.segment_url})"
            labels.insert(0, f"Segment: {prof.segment}")
            comment = (f"Created this issue from the Kestrel brief (label Source: Brief) and filled the issue template.\n\n"
                       f"Segment **{prof.segment}**, chosen from the firm's own website: "
                       f"\"{prof.segment_quote}\" — [{prof.segment_url}]({prof.segment_url})")
        except SiteUnreachable as e:
            rec["site_error"] = str(e)
            rec["segment_line"] = ("Not set — the website did not load, so no segment can be chosen from the firm's "
                                   "own website (raised with Nirbhay).")
            comment = (f"Created this issue from the Kestrel brief (label Source: Brief) and filled the issue template.\n\n"
                       f"Could not choose a segment: {rec['website']} did not load ({e}). "
                       f"No segment label applied rather than guessing; raised with {APPROVER}.")
        rec["labels"] = labels
        issue = self.be.create_issue(rec["title"], render(rec), "Todo", labels)
        rec.update(issue_id=issue["id"], identifier=issue["identifier"], url=issue["url"])
        self.state["prospects"][row["n"]] = rec
        self.be.comment(rec["issue_id"], comment)
        rec["history"].append({"at": datetime.now().isoformat(timespec="seconds"), "action": "created"})
        self.save()
        log(f"  {rec['identifier']}: created '{rec['title']}' [{', '.join(labels)}]")

    def drop(self, rec, reason: str, links: str):
        rec["status_note"] = f"Dropped: {reason}"
        self.act(rec, f"Moved to Canceled and marked DROPPED. Reason: {reason}\n\n{links}",
                 status="Canceled", title=rec["title"] + " | DROPPED")

    def step3(self, rec):
        affs = (rec.get("profile") or {}).get("affiliates", [])
        site_text = ""
        if not rec.get("site_error"):
            site_text = " ".join(p.text for p in self.pages(rec))
        res = A.dnc_check(rec["firm"], affs, site_text, CFG["do_not_contact"])
        rec["dnc"] = res
        rec["dnc_done"] = True
        if res["result"] == "Match":
            rec["dnc_line"] = f"Match — {res['company']}: {res['reason']} ({res['detail']})"
            self.act(rec, f"Do-not-contact check: **Match** with {res['company']} ({res['reason']}). {res['detail']}. "
                          f"No research or drafting done.\n\nChecked: {rec['website']} {res.get('url', '')}")
            self.drop(rec, f"do-not-contact match — {res['company']} ({res['reason']})", f"Website: {rec['website']}")
            return
        if rec.get("site_error"):
            rec["dnc_line"] = ("Clear — firm name checked against the list; parent/affiliate check not possible "
                               "because the website did not load")
        else:
            names = ", ".join(a["name"] for a in affs) or "none named on the website"
            rec["dnc_line"] = f"Clear (firm and parent/affiliates checked: {names})"
        rec["status_note"] = "Do-not-contact check clear; next: research."
        self.act(rec, f"Do-not-contact check: **Clear**. {res['detail']}.\n\nSite checked: {rec['website']}")

    def step4(self, rec):
        if rec["status"] != "In Progress":
            rec["status_note"] = "Research in progress."
            self.act(rec, "Moved to In Progress to start research.", status="In Progress")
        if rec.get("site_error"):
            self.drop(rec, f"website does not load ({rec['site_error']}); not replaced with another firm per SOP",
                      f"Tried: {rec['website']}")
            return
        pages = self.pages(rec)
        trail = []
        fact = A.research_fact(rec["firm"], pages, log=trail)
        rec["fact_trail"] = trail
        discarded = [t for t in trail if not t["verified"]]
        if not fact:
            rec["status_note"] = "Blocked: agent could not find a fact it could source verbatim."
            self.act(rec, f"Research: no candidate fact could be verified against its source page "
                          f"({len(discarded)} discarded). Needs a human look.\n\nPages read: "
                          + ", ".join(p.url for p in pages))
            return
        rec["fact"] = A.to_dict(fact)
        rec["status_note"] = "Fact sourced; next: draft email."
        extra = f" Discarded {len(discarded)} candidate(s) whose quote was not on the cited page." if discarded else ""
        self.act(rec, f"Research: sourced fact — {fact.fact}\n\nQuote: \"{fact.quote}\"\n\nSource: [{fact.url}]({fact.url})"
                      f"{extra}\n\nPages read: " + ", ".join(p.url for p in pages))

    def step5(self, rec):
        page = next((p for p in self.pages(rec) if p.url == rec["fact"]["url"]), None)
        fact = A.Fact(**rec["fact"])
        trail = []
        draft = A.draft_email(rec["firm"], fact, page.text if page else "", CFG, self.blocklist(rec), log=trail)
        rec["draft_trail"] = trail
        if not draft:
            rec["status_note"] = "Blocked: every draft failed the guardrail checks."
            self.act(rec, "Draft: all attempts failed the guardrail checks; no email written. Violations:\n- "
                     + "\n- ".join(v for t in trail for v in t["violations"]))
            return
        rec["draft"] = draft
        rec["status_note"] = "Draft written; next: send for approval."
        rej = sum(1 for t in trail if t["violations"])
        note = f" {rej} earlier draft(s) were rejected by the guardrails and regenerated." if rej else ""
        self.act(rec, f"Draft: wrote email ({draft['words']} words), opening with the sourced fact "
                      f"([source]({fact.url})). Approved claims only, standard sign-off.{note}")

    def step6(self, rec):
        uid = self.be.find_user(LIN["approver_email"])
        labels = rec["labels"] + (["Ready for Approval"] if "Ready for Approval" not in rec["labels"] else [])
        if uid:
            rec["assigned"] = True
            rec["status_note"] = f"In Review with {APPROVER}; waiting for approval."
            self.act(rec, f"Sent for approval: moved to In Review, added Ready for Approval, assigned to {APPROVER}.",
                     status="In Review", labels=labels, assignee=uid)
        else:
            rec["status_note"] = (f"In Review; assignment to {APPROVER} pending — {LIN['approver_email']} "
                                  "has not joined the workspace yet.")
            self.act(rec, f"Sent for approval: moved to In Review and added Ready for Approval. Could not assign to "
                          f"{APPROVER} yet: {LIN['approver_email']} has been invited but has not joined the workspace.",
                     status="In Review", labels=labels)

    def assign(self):
        self._ready()
        uid = self.be.find_user(LIN["approver_email"])
        if not uid:
            log(f"{LIN['approver_email']} has not joined yet; nothing to assign")
            return
        for rec in self.state["prospects"].values():
            if rec["status"] == "In Review" and not rec.get("assigned"):
                rec["assigned"] = True
                rec["status_note"] = f"In Review with {APPROVER}; waiting for approval."
                self.act(rec, f"Assigned to {APPROVER} for approval now that they have joined the workspace.",
                         assignee=uid)

    # ---------------------------------------------------------------- docs / Step 8 / Step 9
    def docs(self):
        self._ready()
        urls = {}
        for title, f in (("Guardrail note", "docs/guardrails.md"), ("Part B — What I would change about this SOP",
                                                                     "docs/part_b.md")):
            urls[title] = self.be.create_document(title, (ROOT / f).read_text())
            log(f"document '{title}': {urls[title]}")
        self.state["docs"] = urls
        self.save()

    def summary(self):
        P = list(self.state["prospects"].values())
        review = [p for p in P if p["status"] == "In Review"]
        dropped = [p for p in P if p["status"] == "Canceled"]
        stuck = [p for p in P if p["status"] not in ("In Review", "Canceled", "Done")]
        return P, review, dropped, stuck

    def daily_update(self):
        P, review, dropped, stuck = self.summary()
        today = datetime.now().strftime("%-d %B %Y")
        done = (f"Set up the Kestrel Outbound project in Linear; created all {len(P)} issues; "
                f"{len(review)} researched and drafted, now In Review; "
                f"{len(dropped)} dropped ({'; '.join(p['firm'] + ': ' + p['status_note'].removeprefix('Dropped: ') for p in dropped)}).")
        blocked = []
        if any(p["status"] == "In Review" and not p.get("assigned") for p in P):
            blocked.append(f"cannot assign In Review issues to you until you accept the Linear invite")
        blocked += [f"{p['firm']}: {p['status_note']}" for p in stuck]
        calls = []
        if not CFG.get("sign_off_is_confirmed"):
            calls.append("what is Kestrel's standard sign-off? Drafts use \"Best, The Kestrel Rooms team\" until you confirm")
        if any(p.get("site_error") for p in P):
            calls.append("for firms whose website does not load, which segment label should the issue carry?")
        body = (f"Done: {done}\nBlocked: {'; '.join(blocked) or 'Nothing'}\n"
                f"Needs your call: {'; '.join(c[0].upper() + c[1:] for c in calls) or 'Nothing'}")
        path = write_email(ROOT, LIN["approver_email"], f"Kestrel Outbound Update {today}", body)
        log(f"daily update written: {path}")

    def submit(self, name: str, health: str, agent_link: str, loom: str):
        self._ready()
        P, review, dropped, stuck = self.summary()
        summary = (f"All {len(P)} prospects processed through the SOP. {len(review)} are In Review with "
                   f"{APPROVER} (Ready for Approval), each with a sourced fact and a guardrail-checked draft. "
                   f"{len(dropped)} dropped: " + "; ".join(f"{p['firm']} ({p['status_note'].removeprefix('Dropped: ')})" for p in dropped)
                   + ". Open items: Kestrel's standard sign-off is unconfirmed (placeholder in drafts); "
                   + ("assignment waits on the Linear invite being accepted." if any(not p.get('assigned') for p in review) else "none."))
        url = self.be.project_update(summary, health)
        log(f"project update posted ({health}): {url}")
        docs = self.state.get("docs", {})
        body = "\n".join([
            "Hi Nirbhay,", "", "Here is my submission for the Kestrel Outbound take-home.", "",
            f"1. Linear workspace and the 10 issues: {self.state.get('project_url', '')}",
            f"2. Agent (repo + run instructions): {agent_link}",
            f"3. Guardrail note: {docs.get('Guardrail note', '')}",
            f"4. Part B: {docs.get('Part B — What I would change about this SOP', '')}",
            f"5. Loom: {loom}", "", f"Project update: {url}", "", "Thanks,", name])
        path = write_email(ROOT, LIN["approver_email"], f"Kestrel Outbound Submission {name}", body)
        log(f"submission email written: {path}")

    def ask(self):
        path = write_email(ROOT, LIN["approver_email"], "Kestrel Outbound: clarifying questions",
                           (ROOT / "docs/clarifying_questions.md").read_text())
        log(f"clarifying questions written: {path}")

    def accept_invite(self):
        if self.be.name != "local":
            raise SystemExit("accept-invite is a simulation step; only Nirbhay can accept a real invite")
        self.be.accept_invite(LIN["approver_email"], log)

    def status(self):
        for p in self.state["prospects"].values():
            print(f"{p['identifier']:7} {p['status']:12} {p['title']}\n        {p['status_note']}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["setup", "run", "assign", "docs", "daily-update", "submit", "status", "ask", "accept-invite"])
    ap.add_argument("--local", action="store_true", help="use the local Linear stand-in")
    ap.add_argument("--invite", action="store_true", help="setup: invite the approver to the workspace")
    ap.add_argument("--name", default="Gaurav Pawar")
    ap.add_argument("--health", default="onTrack", choices=["onTrack", "atRisk", "offTrack"])
    ap.add_argument("--agent-link", default="<repo link>")
    ap.add_argument("--loom", default="<Loom link>")
    a = ap.parse_args()
    r = Run(a.local)
    {"setup": lambda: r.setup(a.invite), "run": r.run, "assign": r.assign, "docs": r.docs,
     "daily-update": r.daily_update, "submit": lambda: r.submit(a.name, a.health, a.agent_link, a.loom),
     "status": r.status, "ask": r.ask, "accept-invite": r.accept_invite}[a.command]()


if __name__ == "__main__":
    main()
