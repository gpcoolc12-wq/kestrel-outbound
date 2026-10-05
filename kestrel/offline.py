"""Offline agent: rule-based research and drafting, no API key and no model.

Same inputs/outputs as the model-backed functions in agent.py, and every result goes through
the same guardrails. Quotes are always cut verbatim from the fetched page text, so the
verbatim-source check holds by construction.
"""
from __future__ import annotations

import hashlib
import re
from urllib.parse import urlparse

from . import guardrails as G

RES = r"\b(residential|residences?|homes?|houses?|cottages?|camps?|single[- ]family|multi[- ]?family|duplex|dwellings?|apartments?|kitchens?)\b"
COM = (r"\b(commercial|office|offices|retail|restaurants?|schools?|institutional|civic|healthcare|hospitality|"
       r"laborator(?:y|ies)|manufacturing|municipal|library|university|campus|workplace|hotels?|nightclub|"
       r"amphitheat(?:er|re)|brewery|church|museum|clinic|fit-ups?|mixed-use)\b")
AFFIL = re.compile(r"(?:affiliate(?: company)?|subsidiary|division|sister company|parent company)\s+of\s+"
                   r"((?:[Tt]he\s+)?[A-Z][\w&'+-]*(?:\s+(?:[A-Z][\w&'+-]*|&|\+|of|and))*)")
AWARD_KW = re.compile(r"Award|of the Year|Prize")
HEADLINE = re.compile(r"\b(?:Announced|Announces|Announcing|Winners|Finalists?|Shortlist(?:ed)?|Nominees?|Call for|"
                      r"Entries|Deadline|Ceremony|Gala|Submissions?)\b", re.I)
FOR_TAIL = r"\s+for(?:\s+[A-Z][\w'’-]*(?![\w'’-])(?!\s\()){1,3}"  # "for Maine Savings Amphitheater", not "for KANU MEREDA (..."
GENERIC = {"about", "about-us", "contact", "home", "work", "projects", "project", "portfolio", "residential",
           "commercial", "institutional", "studio", "team", "people", "news", "press", "blog", "careers", "services",
           "process", "design-process", "info", "learn", "our-work", "ourwork", "current-projects", "all-projects",
           "press-awards", "meet-the-team", "zoning-feasibility", "zoning-feasabilty", "landscape", "fabrication"}
YEAR = re.compile(r"\b(?:19|20)\d\d\b")
AWARD = re.compile(r"((?:[A-Z(][\w&().'/-]*\s+){1,9}(?:Award|Awards|Prize|Project of the Year)(?:\s+(?:for|of|in)"
                   r"(?:\s+[A-Z][\w&'-]*){1,4})?(?:\s*[-–—:,]?\s*(?:for\s+)?(?:[A-Z][\w&'-]*\s+){0,4})?(?:19|20)\d\d"
                   r"(?:\s+for(?:\s+[A-Z][\w&'-]*){1,5})?)")
FOUNDED = re.compile(r"([^.]{0,90}\b(?:founded|established|formed|started|co-founding|since)\b[^.]{0,60}\b(19|20)\d\d\b[^.]{0,40})")
PROJECT_PATH = re.compile(r"/(project|projects|work|ourwork|portfolio)/[^/]+/?$|/work/[^/]+/[^/]+/?$", re.I)

SECOND = {
    "award": ["Award-winning work like that usually means long weeks in the model shop and a lot of client reviews.",
              "Work at that level must keep the plotters and the presentation room busy in the run-up to submission.",
              "Recognition like that tends to bring more client meetings into an already busy conference room."],
    "project": ["Projects like that tend to keep the conference room, plotters and model shop busy at the same time.",
                "I imagine the pin-ups and client reviews for it kept your presentation space in steady use.",
                "Deadline weeks on a project like that must put real pressure on the large-format plotters.",
                "A project like that usually means plenty of model-shop time and client walk-throughs."],
    "founding": ["A studio that has grown since then probably shares its meeting rooms, plotters and model shop across more people.",
                 "After that many years of projects, I imagine the model shop and plotters are rarely idle.",
                 "That is a long run of client meetings, plotter queues and model-shop deadlines.",
                 "By now the conference room must double as a pin-up wall during deadline weeks.",
                 "Over that time the studio has likely outgrown a shared spreadsheet for who gets the big plotter.",
                 "Years like that usually mean a model shop everyone wants on the same afternoon."],
}


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\s{2,}|\s\|\s", text) if 30 <= len(s.strip()) <= 400]


def _prose(s: str) -> bool:
    """A real sentence, not a run of navigation links: mostly lowercase words."""
    w = s.split()
    return len(w) >= 8 and sum(x[:1].islower() for x in w) / len(w) >= 0.55


def _count(pattern, text):
    return len(re.findall(pattern, text, re.I))


# ---------------------------------------------------------------- Step 2 / 3 inputs
def segment_and_affiliates(firm, pages):
    from .agent import Profile
    allt = " ".join(p.text for p in pages)
    r, c = _count(RES, allt), _count(COM, allt)
    both_named = _count(r"\bresidential\b", allt) >= 2 and _count(r"\bcommercial\b", allt) >= 2
    if r and c and (min(r, c) / max(r, c) >= 0.2 or both_named):
        seg = "Mixed"
    else:
        seg = "Residential" if r >= c else "Commercial"
    want = {"Mixed": (RES, COM), "Residential": (RES,), "Commercial": (COM,)}[seg]
    best = None
    for p in pages:
        for s in _sentences(p.text):
            if _prose(s) and all(re.search(w, s, re.I) for w in want):
                best = (s[:300], p.url)
                break
        if best:
            break
    if not best:  # fall back to any sentence with the dominant term
        dom = RES if seg == "Residential" else COM
        for p in pages:
            m = next((s for s in _sentences(p.text) if _prose(s) and re.search(dom, s, re.I)), None)
            if m:
                best = (m[:300], p.url)
                break
    quote, url = best or (pages[0].text[:200], pages[0].url)
    reason = f"site mentions residential work {r}x and commercial/institutional work {c}x"
    affs = []
    for p in pages:
        for m in AFFIL.finditer(p.text):
            name = m.group(1).strip(" .,")
            start = max(0, p.text.rfind(".", 0, m.start()) + 1)
            end = p.text.find(".", m.end())
            q = p.text[start:end if end > 0 else m.end()].strip()
            if len(name.split()) <= 6 and not any(a["name"] == name for a in affs):
                affs.append({"name": name, "relationship": "named on the site as related company", "quote": q, "url": p.url})
    return Profile(seg, reason, quote, url, affs)


# ---------------------------------------------------------------- Step 4
def _project_name(page, firm):
    title = re.split(r"\s[|–—-]\s", page.title or "")[0].strip()
    if not title or G.norm(firm) in G.norm(title) or len(title) > 60:
        slug = urlparse(page.url).path.rstrip("/").split("/")[-1]
        title = slug.replace("-", " ").title()
        title = re.sub(r"\s\d+(\s\d+)*$", "", title)  # "colchester-lake-house-1-2" -> "Colchester Lake House"
    title = title.split(",")[0].strip()  # "Treetops, Kennebunkport, Maine" -> "Treetops"
    return title if title and G.quote_in_page(title, page.text) or (title and G.norm(title) in G.norm(page.text)) else None


def research_fact(firm, pages, log=None):
    from .agent import Fact
    cands = []
    for p in pages:
        t = p.text
        years = list(YEAR.finditer(t))
        for i, y in enumerate(years):
            begin = years[i - 1].end() if i else max(0, y.start() - 160)
            if y.start() - begin > 160:
                begin = y.start() - 160
            m = re.match(r"(?:" + FOR_TAIL + r")?", t[begin:])  # skip the previous item's "for X" tail
            item = t[begin + (m.end() if m else 0):y.end()]
            tail = re.match(FOR_TAIL, t[y.end():])
            if tail:
                item += tail.group(0)
            item = re.sub(r"\s+", " ", item).strip(" ,-–—:")
            item = re.sub(r"^(?:Awards?|Press|Recognition|Honors)\s+", "", item)
            kws = AWARD_KW.findall(item)
            if HEADLINE.search(item):  # "Design Awards Winners Announced 2024" is news, not an award the firm won
                continue
            if (len(kws) == 1 and ":" not in item and item[:1].isupper() and 5 <= len(item.split()) <= 20
                    and not re.search(r"\b(?:January|February|March|April|May|June|July|August|September|October|"
                                      r"November|December)\b", item)):
                cands.append(("award", f"{firm} received the {item}.", item, p.url, int(y.group(0))))
    for p in pages:
        path = urlparse(p.url).path.strip("/")
        slug = path.split("/")[-1] if path else ""
        is_project = PROJECT_PATH.search(urlparse(p.url).path) or (
            "/" not in path and slug and slug.lower() not in GENERIC and not slug.startswith("category"))
        if is_project and slug.lower() not in GENERIC:
            name = _project_name(p, firm)
            if name and len(name) >= 4:
                first = re.escape(name.split()[0])
                occ = [m.start() for m in re.finditer(first, p.text, re.I)]
                q = name
                if len(occ) > 1:  # the second occurrence is usually the content heading, not the <title>
                    after = re.sub(r"\s+", " ", p.text[occ[1]:occ[1] + 200])
                    after = re.split(r"\s(?:[A-Z]{3,}:|Let’s|Let's|Contact|Read|\d{3,}\s[A-Z])", after)[0]
                    q = " ".join(after.split()[:12])
                    words = q.split()
                    if not G.quote_in_page(q, p.text) or sum(w[:1].islower() for w in words) / max(len(words), 1) < 0.3:
                        q = name  # the heading is followed by a list of links, not a description
                if not G.opens_with_fact(f"I was looking at your {name} project.", q):
                    q = name  # cite the project name itself so the opener provably carries the fact
                cands.append(("project", f"{firm}{chr(39) if firm.endswith('s') else chr(39) + 's'} portfolio includes the {name} project.", q, p.url, 0))
    for p in pages:
        for m in FOUNDED.finditer(p.text):
            q = re.sub(r"\s+", " ", m.group(1)).strip()
            year = re.search(r"\b(?:19|20)\d\d\b", q).group(0)
            kw = re.search(r"\b(?:founded|established|formed|started|co-founding|since)\b", q)
            anchor = [m2.start() for m2 in re.finditer(
                re.escape(firm.split()[0]) + r"|\b(?:[Hh]e|[Ss]he|[Ww]e|In|Since)\b|\b[A-Z][a-z]+(?=\s+(?:founded|established|started|formed)\b)", q)
                if m2.start() <= kw.start()]
            q = q[anchor[-1] if anchor else kw.start():].strip()
            q = q[: q.find(year) + 4] if q.find(year) >= 0 else q
            if G.norm(firm).split()[0] in G.norm(q) or re.match(r"(?:[Ww]e|[Hh]e|[Ss]he|In|Since|[A-Z][a-z]+ (?:founded|started))\b", q):
                cands.append(("founding", f"{firm} dates back to {year}.", q, p.url, int(year)))
    order = {"award": 0, "project": 1, "founding": 2}
    best = None
    seen = set()
    for kind, fact, quote, url, year in cands:
        if quote in seen:
            continue
        seen.add(quote)
        page = next(pp for pp in pages if pp.url == url)
        ok = G.quote_in_page(quote, page.text) or (len(quote) >= 4 and G.norm(quote) in G.norm(page.text))
        if log is not None:
            log.append({"kind": kind, "fact": fact, "url": url, "verified": ok, "engine": "offline"})
        # best kind first; among awards, the most recent
        if ok and (best is None or (order[kind], -year) < (order[best[0]], -best[4])):
            best = (kind, fact, quote, url, year)
    if not best:
        return None
    if log is not None:
        log.append({"chosen": best[1]})
    return Fact(best[1], best[2], best[3], best[0])


# ---------------------------------------------------------------- Step 5
def _kind(fact):
    k = getattr(fact, "kind", None)
    if k:
        return k
    t = G.norm(fact.fact)
    return "award" if "award" in t or "of the year" in t else "founding" if "dates back" in t or "founded" in t else "project"


def opener_options(firm, fact):
    kind = _kind(fact)
    q = fact.quote
    if kind == "award":
        award = re.sub(r"^(?:the\s+)", "", q, flags=re.I)
        award = re.sub(r"\s*\([^)]*\)", "", award)  # "MEREDA (Maine Real Estate ...) Project" -> "MEREDA Project"
        first = f"Congratulations on the {award}."
        subj = "Your " + " ".join(re.split(r"\s(?:for|-|–|—)\s", award)[0].split()[:6])
    elif kind == "project":
        name = fact.fact.split("includes the ", 1)[-1].rsplit(" project", 1)[0]
        first = f"I was looking at your {name} project."
        subj = f"Your {name} project"
    else:
        year = re.search(r"(19|20)\d\d", q).group(0)
        first = f"I read that {firm} dates back to {year}."
        subj = f"{firm}, since {year}"
    seed = int(hashlib.sha1(firm.encode()).hexdigest(), 16)
    seconds = SECOND[kind][seed % len(SECOND[kind]):] + SECOND[kind][:seed % len(SECOND[kind])]
    return subj, [f"{first} {s}" for s in seconds] + [first]


def draft_email(firm, fact, page_text, cfg, blocklist, log=None, avoid=None):
    from .agent import assemble, style_issues
    subj, options = opener_options(firm, fact)
    for i, opener in enumerate(options, 1):
        body = assemble(opener, cfg)
        errs = G.validate_email(subject=subj, opener=opener, body=body, quote=fact.quote, page_text=page_text,
                                firm=firm, cfg=cfg, blocklist=blocklist)
        style = style_issues(opener, avoid or [])
        if log is not None:
            log.append({"attempt": i, "subject": subj, "opener": opener, "violations": errs, "style": style,
                        "engine": "offline"})
        if not errs and not style:
            return {"subject": subj, "body": body, "words": G.word_count(body), "attempts": i, "engine": "offline"}
    return None
