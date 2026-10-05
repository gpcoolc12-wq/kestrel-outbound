"""The research + drafting agent. Each function maps to one SOP step.

segment_and_affiliates  -> Step 2 (segment from the firm's own site) and the input to Step 3
dnc_check               -> Step 3 (firm + any parent/affiliate named on the site)
research_fact           -> Step 4 (one checkable fact, verified against its source page)
draft_email             -> Step 5 (<=90 words, opens with the fact, approved claims only)
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, asdict

from . import guardrails as G
from .fetch import Page
from .llm import chat_json

MAX_ATTEMPTS = 3


def engine() -> str:
    """'offline' (rule-based, no API key) by default. AGENT_ENGINE=model opts in to the LLM,
    which needs OPENROUTER_API_KEY and falls back to offline if the model is unavailable."""
    return "model" if os.environ.get("AGENT_ENGINE", "").lower() == "model" else "offline"


def _with_fallback(name):
    """Run the model-backed step; if no key is set, or every model fails (quota, outage),
    use the offline rule-based version so the pipeline never depends on an API key."""
    def deco(fn):
        def wrapper(*a, **k):
            from . import offline
            if engine() == "offline":
                return getattr(offline, name)(*a, **k)
            try:
                return fn(*a, **k)
            except RuntimeError as e:
                if "all models failed" not in str(e) and "OPENROUTER_API_KEY" not in str(e):
                    raise
                print(f"      model unavailable ({str(e)[:80]}...) - using offline engine for {name}")
                return getattr(offline, name)(*a, **k)
        wrapper.__name__ = fn.__name__
        return wrapper
    return deco


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


@_with_fallback("segment_and_affiliates")
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
    kind: str = ""


FACT_PRIORITY = {"award": 0, "project": 1, "publication": 2, "other": 3, "founding": 4}


@_with_fallback("research_fact")
def research_fact(firm: str, pages: list[Page], log: list | None = None) -> Fact | None:
    """Collects candidate facts, keeps only those whose quote is verbatim on the cited page, then picks
    the best kind: a named award beats a named project beats press beats a founding year. A founding
    year is checkable but makes a weak opener, so it is used only when nothing better is verifiable."""
    sys = (
        "You research an architecture firm from its own website. Find specific facts someone could check on "
        "that page: a named award (with the awarding body), a named project (with its place or client type), "
        "a publication or press feature, or the year the firm was founded. Not opinions, not generic statements "
        "('we listen to clients'), not facts about other companies. Each fact needs a quote copied "
        "character-for-character from the page text and the URL of that page. Give up to 6 candidates and "
        "label each kind as award|project|publication|founding|other. Prefer recent, named, distinctive facts; "
        "include at least one award or named project if the site has any."
    )
    user = (f"Firm: {firm}\n\n{_pages_blob(pages)}\n\n"
            'Return {"candidates": [{"kind": "award|project|publication|founding|other", "fact": "one sentence", '
            '"quote": "verbatim", "url": "..."}]}')
    rejected, verified = [], []
    for _ in range(MAX_ATTEMPTS):
        out = chat_json(sys, user + (f"\n\nAlready rejected (quote not on the cited page): {json.dumps(rejected)}"
                                     if rejected else ""))
        for c in out.get("candidates") or []:
            page = _page_for(c.get("url", ""), pages)
            ok = bool(page and G.quote_in_page(c.get("quote", ""), page.text))
            kind = str(c.get("kind", "other")).lower()
            kind = kind if kind in FACT_PRIORITY else "other"
            if log is not None:
                log.append({"kind": kind, "fact": c.get("fact"), "url": c.get("url"), "verified": ok})
            if ok:
                verified.append((FACT_PRIORITY[kind], len(verified), Fact(c["fact"].strip(), c["quote"].strip(), page.url)))
            else:
                rejected.append(c.get("fact"))
        if verified and min(v[0] for v in verified) < FACT_PRIORITY["founding"]:
            break  # have something better than a founding year
    if not verified:
        return None
    best = min(verified)[2]
    if log is not None:
        log.append({"chosen": best.fact})
    return best


# ---------------------------------------------------------------- Step 5
def assemble(opener: str, cfg: dict) -> str:
    b = cfg["email_blocks"]
    return f"{opener.strip()}\n\n{b['product']}\n\n{b['cta']}\n\n{cfg['sign_off'].strip()}"


# Writing-quality checks (not guardrails): stop every email sounding the same.
STOCK = re.compile(r"\bhow (?:does|do) (?:the |your )?(?:team|you|studio)\b.*\bshare\b|\bcaught my eye\b|"
                   r"\bi hope\b|\bhope you\b|\breaching out\b|\bimpressive\b|\bamazing\b", re.I)


def style_issues(opener: str, avoid: list[str]) -> list[str]:
    errs = []
    if STOCK.search(opener):
        errs.append("STYLE: stock phrasing (e.g. 'How does the team share...', 'caught my eye', 'reaching out'); "
                    "write a specific second sentence instead")
    second = re.split(r"(?<=[.!?])\s", opener.strip(), maxsplit=1)[1:] or [""]
    sw = set(re.findall(r"[a-z']{4,}", second[0].lower()))
    for other in avoid:
        ow = set(re.findall(r"[a-z']{4,}", other.lower()))
        if sw and ow and len(sw & ow) / len(sw | ow) > 0.5:
            errs.append(f"STYLE: second sentence is too similar to another email in this batch: '{other}'")
            break
    return errs


@_with_fallback("draft_email")
def draft_email(firm: str, fact: Fact, page_text: str, cfg: dict, blocklist: list[str],
                log: list | None = None, avoid: list[str] | None = None) -> dict | None:
    avoid = avoid or []
    fixed_words = G.word_count(assemble("", cfg))
    budget = cfg["max_words"] - fixed_words
    sys = (
        "You write the first lines of a cold email to an architecture studio, for a peer who knows design "
        f"studios. Write ONLY a subject line and an opener of two sentences, at most {budget} words in total.\n"
        "Sentence 1 states the fact below about the studio: accurate, specific, plain words, no flattery, no "
        "exclamation marks.\n"
        "Sentence 2 links that specific fact to the studio's shared spaces or equipment (conference rooms, the "
        "model shop, large-format plotters, client presentation space) with a concrete, natural observation or "
        "question that fits THIS fact. Examples of the register (do not copy): 'A project like that usually means "
        "weeks of model-shop time and a lot of client walk-throughs.' / 'Deadline weeks must put the plotters "
        "under real pressure.' Do not start sentence 2 with 'How does' or 'How do'.\n"
        "Never mention Kestrel, software, booking, calendars, features, numbers not in the quote, other "
        "companies or people outside the firm, or comparisons. Product lines are added later by code.\n"
        "Subject: 3-6 words, natural, about the fact (e.g. 'Your MEREDA project of the year'), no product talk."
    )
    user = (f"Studio: {firm}\nFact: {fact.fact}\nVerbatim source quote: \"{fact.quote}\"\nSource: {fact.url}\n"
            + (f"Other emails in this batch already use these second sentences - write something different:\n- "
               + "\n- ".join(avoid) + "\n" if avoid else "")
            + '\nReturn {"subject": "...", "opener": "..."}')
    for attempt in range(1, MAX_ATTEMPTS + 2):
        out = chat_json(sys, user, temperature=0.5)
        subject, opener = out.get("subject", "").strip(), out.get("opener", "").strip()
        body = assemble(opener, cfg)
        errs = G.validate_email(subject=subject, opener=opener, body=body, quote=fact.quote,
                                page_text=page_text, firm=firm, cfg=cfg, blocklist=blocklist)
        style = style_issues(opener, avoid)
        if log is not None:
            log.append({"attempt": attempt, "subject": subject, "opener": opener, "violations": errs, "style": style})
        if not errs and (not style or attempt == MAX_ATTEMPTS + 1):
            return {"subject": subject, "body": body, "words": G.word_count(body), "attempts": attempt}
        user += ("\n\nYour previous draft was rejected:\n- " + "\n- ".join(errs + style) + "\nFix every point.")
    return None


def second_sentence(body: str) -> str:
    opener = body.split("\n\n")[0]
    parts = re.split(r"(?<=[.!?])\s", opener.strip(), maxsplit=1)
    return parts[1] if len(parts) > 1 else ""


def to_dict(x):
    return asdict(x) if x is not None else None
