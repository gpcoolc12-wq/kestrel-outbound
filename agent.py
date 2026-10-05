#!/usr/bin/env python3
"""Run the research + drafting agent on any firm's website, without touching Linear.

  python agent.py --firm "Acme Studio" --url https://acme.example --city Boston

Prints: segment (with evidence), do-not-contact result, the sourced fact, the draft
email, and every guardrail decision the agent made along the way. Add --json for
machine-readable output.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from kestrel import agent as A  # noqa: E402
from kestrel.fetch import SiteUnreachable, read_site  # noqa: E402
from kestrel.guardrails import COMPETITORS  # noqa: E402
from kestrel.template import render  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--firm", required=True)
    ap.add_argument("--url", required=True)
    ap.add_argument("--city", default="")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    cfg = json.loads((ROOT / "config/kestrel.json").read_text())
    rec = {"firm": a.firm, "website": a.url, "city": a.city}
    say = (lambda *x: None) if a.json else print

    say(f"[1/4] Reading {a.url} ...")
    try:
        pages = read_site(a.url)
    except SiteUnreachable as e:
        rec.update(result="DROP", reason=str(e))
        print(json.dumps(rec, indent=2) if a.json else f"DROP: {e}")
        return
    say("      read " + ", ".join(f"{p.url} ({p.via})" for p in pages))

    prof = A.segment_and_affiliates(a.firm, pages)
    rec["segment_line"] = f"{prof.segment} — {prof.segment_reason} (source: {prof.segment_url})"
    say(f"[2/4] Segment: {prof.segment} — \"{prof.segment_quote}\" ({prof.segment_url})")
    say(f"      Affiliates named on site: {[x['name'] for x in prof.affiliates] or 'none'}")

    dnc = A.dnc_check(a.firm, prof.affiliates, " ".join(p.text for p in pages), cfg["do_not_contact"])
    rec["dnc_line"] = dnc["result"] + ("" if dnc["result"] == "Clear" else f" — {dnc['company']}: {dnc['reason']}")
    say(f"[3/4] Do-not-contact: {dnc['result']} — {dnc['detail']}")
    if dnc["result"] == "Match":
        rec.update(result="DROP", reason=dnc["detail"])
        print(json.dumps(rec, indent=2) if a.json else "DROP: do-not-contact match; no research or drafting.")
        return

    trail = []
    fact = A.research_fact(a.firm, pages, log=trail)
    say(f"      engine: {A.engine()}")
    for t in trail:
        if "fact" in t:
            say(f"      candidate [{t.get('kind') or '?'}] {'verified' if t['verified'] else 'DISCARDED (quote not on cited page)'}: {t['fact']}")
        elif "chosen" in t:
            say(f"      chosen (award > named project > founding year): {t['chosen']}")
    if not fact:
        rec.update(result="BLOCKED", reason="no verifiable fact")
        print(json.dumps(rec, indent=2) if a.json else "BLOCKED: no fact could be sourced.")
        return
    rec["fact"] = A.to_dict(fact)
    say(f"[4/4] Fact: {fact.fact}\n      Quote: \"{fact.quote}\"\n      Source: {fact.url}")

    page = next(p for p in pages if p.url == fact.url)
    blocklist = [d["company"] for d in cfg["do_not_contact"]] + COMPETITORS
    dtrail = []
    draft = A.draft_email(a.firm, fact, page.text, cfg, blocklist, log=dtrail)
    for t in dtrail:
        if t.get("violations") or t.get("style"):
            say(f"      draft {t['attempt']} REJECTED: {(t.get('violations') or []) + (t.get('style') or [])}")
    if not draft:
        rec.update(result="BLOCKED", reason="all drafts failed guardrails", draft_trail=dtrail)
        print(json.dumps(rec, indent=2) if a.json else "BLOCKED: every draft failed the guardrails.")
        return
    rec["draft"] = draft
    rec["status_note"] = "Draft ready for approval."
    rec["result"] = "READY"
    if a.json:
        print(json.dumps(rec, indent=2))
    else:
        print("\n" + "=" * 70 + "\nIssue description (Linear template):\n" + "=" * 70)
        print(render(rec))


if __name__ == "__main__":
    main()
