"""The research + drafting agent. Each function maps to one SOP step.

segment_and_affiliates  -> Step 2 (segment from the firm's own site) and the input to Step 3
dnc_check               -> Step 3 (firm + any parent/affiliate named on the site)
research_fact           -> Step 4 (one checkable fact, verified against its source page)
draft_email             -> Step 5 (<=90 words, opens with the fact, approved claims only)
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict

from . import guardrails as G
from .fetch import Page
from .llm import chat_json

MAX_ATTEMPTS = 3


def _pages_blob(pages: list[Page], per_page: int = 6000) -> str:
    return "\n\n".join(f"=== PAGE {p.url}\nTITLE: {p.title}\n{p.text[:per_page]}" for p in pages)


def _page_for(url: str, pages: list[Page]) -> Page | None:
    u = url.rstrip("/")
    for p in pages:
        if p.url.rstrip("/") == u:
            return p
    return None


# ---------------------------------------------------------------- Step 2 / 3 inputs
@dataclass
class Profile:
    segment: str               # Residential | Commercial | Mixed
    segment_reason: str
    segment_quote: str
    segment_url: str
    affiliates: list           # [{"name", "relationship", "quote", "url"}] - quotes verified


def segment_and_affiliates(firm: str, pages: list[Page]) -> Profile:
    sys = (
        "You classify architecture/design firms for a B2B outbound list, using only the firm's own website. "
        "Segment rules: Residential = the site presents homes/houses/residential as its work and little or no "
        "commercial/institutional work. Commercial = commercial, institutional, civic, healthcare, education, "
        "hospitality, retail or office work with little or no residential. Mixed = both are presented as "
        "real lines of work. Also list every parent company, sister company, affiliate, partner firm or "
        "corporate group the site names as related to this firm (not clients, not award bodies). "
        "Every quote must be copied character-for-character from the page text."
    )
    user = (
        f"Firm: {firm}\n\n{_pages_blob(pages)}\n\n"
        'Return {"segment": "Residential|Commercial|Mixed", "reason": "...", "quote": "verbatim evidence", '
        '"url": "page url of the quote", "affiliates": [{"name": "...", "relationship": "...", '
        '"quote": "verbatim", "url": "..."}]}'
    )
    for _ in range(MAX_ATTEMPTS):
        out = chat_json(sys, user)
        seg = str(out.get("segment", "")).strip().title()
        page = _page_for(out.get("url", ""), pages)
        if seg in {"Residential", "Commercial", "Mixed"} and page and G.quote_in_page(out.get("quote", ""), page.text):
            affs = []
            for a in out.get("affiliates") or []:
                ap = _page_for(a.get("url", ""), pages)
                if ap and G.quote_in_page(a.get("quote", ""), ap.text):
                    affs.append({k: a.get(k, "") for k in ("name", "relationship", "quote", "url")})
            return Profile(seg, out.get("reason", ""), out["quote"], page.url, affs)
        user += "\n\nYour last answer's quote was not found verbatim on the page you cited. Try again."
    raise RuntimeError("could not ground a segment in the website text")


# ---------------------------------------------------------------- Step 3
def _n(s: str) -> str:
    s = G.norm(s).replace("+", " and ").replace("&", " and ")
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = re.sub(r"\b(the|inc|llc|llp|pc|pa|co|company|ltd)\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def dnc_check(firm: str, affiliates: list, site_text: str, dnc: list[dict]) -> dict:
    """Exact (normalised) name matching - no fuzzy matching, so 'Providence Architecture'
    is not confused with 'The Providence Group'. A literal mention of a do-not-contact
    company that names itself an affiliate group (include_affiliates) anywhere on the site
    is treated as a match for safety and flagged for human review."""
    names = [("firm", firm, "")] + [("affiliate", a["name"], a["url"]) for a in affiliates]
    for entry in dnc:
        target = _n(entry["company"])
        for kind, name, url in names:
            if _n(name) == target:
                return {"result": "Match", "company": entry["company"], "reason": entry["reason"],
                        "detail": f"{kind} '{name}' matches do-not-contact entry '{entry['company']}'", "url": url}
        if entry.get("include_affiliates") and target in _n(site_text):
            return {"result": "Match", "company": entry["company"], "reason": entry["reason"],
                    "detail": f"website mentions '{entry['company']}' (affiliates are also do-not-contact); "
                              "treated as a match pending human review", "url": ""}
    return {"result": "Clear", "detail": "firm and named affiliates checked: "
            + (", ".join(n for _, n, _ in names))}


# ---------------------------------------------------------------- Step 4
@dataclass
class Fact:
    fact: str
    quote: str
    url: str


def research_fact(firm: str, pages: list[Page], log: list | None = None) -> Fact | None:
    sys = (
        "You research an architecture firm from its own website. Find specific facts someone could check on "
        "that page: a named project, a named award (with the awarding body), or the year the firm was founded. "
        "Not opinions, not generic statements ('we listen to clients'). Each fact needs a quote copied "
        "character-for-character from the page text and the URL of that page. Give up to 5 candidates, "
        "best first: prefer recent, named, distinctive facts."
    )
    user = (f"Firm: {firm}\n\n{_pages_blob(pages)}\n\n"
            'Return {"candidates": [{"fact": "one sentence", "quote": "verbatim", "url": "..."}]}')
    rejected = []
    for _ in range(MAX_ATTEMPTS):
        out = chat_json(sys, user + (f"\n\nAlready rejected (not verifiable): {json.dumps(rejected)}" if rejected else ""))
        for c in out.get("candidates") or []:
            page = _page_for(c.get("url", ""), pages)
            ok = bool(page and G.quote_in_page(c.get("quote", ""), page.text))
            if log is not None:
                log.append({"fact": c.get("fact"), "url": c.get("url"), "verified": ok})
            if ok:
                return Fact(c["fact"].strip(), c["quote"].strip(), page.url)
            rejected.append(c.get("fact"))
    return None


# ---------------------------------------------------------------- Step 5
def assemble(opener: str, cfg: dict) -> str:
    b = cfg["email_blocks"]
    return f"{opener.strip()}\n\n{b['product']}\n\n{b['cta']}\n\n{cfg['sign_off'].strip()}"


def draft_email(firm: str, fact: Fact, page_text: str, cfg: dict, blocklist: list[str],
                log: list | None = None) -> dict | None:
    fixed_words = G.word_count(assemble("", cfg))
    budget = cfg["max_words"] - fixed_words
    sys = (
        "You write the first lines of a cold email to an architecture studio. You write ONLY: a subject line, "
        f"and an opener of one or two sentences, at most {budget} words, whose first sentence states the fact "
        "below about the studio, accurately and specifically, in plain words (no flattery, no exclamation marks). "
        "The second sentence, if any, may ask a light question about how the studio shares rooms, plotters or "
        "its model shop - without describing any product. Never mention Kestrel, software, features, numbers "
        "that are not in the quote, other companies, or comparisons. Product lines are added later by code. "
        "Subject: 3-7 words, about the studio, no product talk."
    )
    user = (f"Studio: {firm}\nFact: {fact.fact}\nVerbatim source quote: \"{fact.quote}\"\nSource: {fact.url}\n\n"
            'Return {"subject": "...", "opener": "..."}')
    for attempt in range(1, MAX_ATTEMPTS + 1):
        out = chat_json(sys, user, temperature=0.4)
        subject, opener = out.get("subject", "").strip(), out.get("opener", "").strip()
        body = assemble(opener, cfg)
        errs = G.validate_email(subject=subject, opener=opener, body=body, quote=fact.quote,
                                page_text=page_text, firm=firm, cfg=cfg, blocklist=blocklist)
        if log is not None:
            log.append({"attempt": attempt, "subject": subject, "opener": opener, "violations": errs})
        if not errs:
            return {"subject": subject, "body": body, "words": G.word_count(body), "attempts": attempt}
        user += "\n\nYour previous draft was rejected by the guardrail checker:\n- " + "\n- ".join(errs) + "\nFix every point."
    return None


def to_dict(x):
    return asdict(x) if x is not None else None
