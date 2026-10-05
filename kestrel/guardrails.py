"""Generation-time guardrails. Every email is checked here before it can leave the agent.

The agent must never say:
  G1. Anything about Kestrel beyond the four approved claims (no extra features,
      numbers, customer names or comparisons).
  G2. Anything about the prospect that is not backed by a verbatim quote from a page
      on the prospect's own website.
  G3. The name of any other company: Kestrel customers, do-not-contact firms,
      other prospects on the list, or competitors.

How it is enforced (structurally, not by asking the model nicely):
  * The model never writes product copy. It writes only a subject line and a one or
    two sentence opener about the prospect. Kestrel's claims and the call to action are
    inserted by code from config/kestrel.json, verbatim.
  * The model-written parts are scanned: product vocabulary, comparison words, money,
    percentages, "Kestrel" itself -> rejected (G1). Every number and every proper noun
    must appear in the source page or quote (G2). The source quote itself must appear
    word-for-word in the fetched page (G2). A blocklist of company names is checked
    across the whole email (G3).
  * A rejected draft is sent back to the model with the exact violations; after
    MAX_ATTEMPTS the agent stops and returns no email rather than a bad one.
"""
from __future__ import annotations

import re
import unicodedata

COMPETITORS = ["Robin", "Skedda", "Envoy", "Teem", "Condeco", "OfficeSpace", "Joan", "Calendly", "Eptura", "YArooms"]

# Words that would amount to a product claim if the model wrote them (G1).
PRODUCT_TERMS = [
    "kestrel", "software", "platform", "app", "tool", "booking", "book", "schedul", "calendar",
    "integrat", "sync", "setup", "set up", "onboard", "trial", "free", "demo", "feature",
    "automat", "dashboard", "save", "saves", "saving", "efficien", "productiv", "roi",
    "minutes", "hours", "per month", "price", "pricing", "cost", "discount", "guarantee",
    "customers", "trusted", "used by", "teams like", "studios like",
]
COMPARISON_TERMS = [
    "better", "best", "faster", "fastest", "easier", "easiest", "cheaper", "leading", "number one",
    "#1", "unlike", "than", "only solution", "world-class", "top-rated", "outperform",
]
SENTENCE_START_OK = {"congrats", "congratulations", "your", "the", "i", "we", "it", "this", "saw", "read", "noticed"}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("–", "-").replace("—", "-").replace("&amp;", "&")
    return re.sub(r"\s+", " ", s).strip().lower()


def quote_in_page(quote: str, page_text: str) -> bool:
    q = norm(quote)
    return len(q) >= 8 and q in norm(page_text)


def word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'’\-]*", text))


def _has_term(text_norm: str, term: str) -> bool:
    if term.startswith("#") or " " in term:
        return term in text_norm
    return re.search(r"\b" + re.escape(term), text_norm) is not None


def check_model_text(text: str, *, quote: str, page_text: str, firm: str) -> list[str]:
    """Checks for text the model wrote (subject or opener)."""
    errs = []
    t = norm(text)
    q = norm(quote)
    for term in PRODUCT_TERMS:
        if _has_term(t, term) and not _has_term(q, term):
            errs.append(f"G1: says '{term}' - product talk is inserted by code, never written by the model")
    for term in COMPARISON_TERMS:
        if _has_term(t, term) and not _has_term(q, term):
            errs.append(f"G1: comparison/superlative '{term}' is not allowed")
    if re.search(r"[$%€£]", text):
        errs.append("G1: money or percentage symbols are not allowed")
    page_n = norm(page_text) + " " + norm(firm)
    own = norm(firm)
    for num in re.findall(r"\d[\d,\.]*", text.replace(firm, "")):  # digits in the firm's own name (G4) are fine
        if num.strip(".,") not in q:
            errs.append(f"G2: number '{num}' does not appear in the source quote")
    # Proper nouns (capitalised words not at a sentence start) must come from the source page.
    for m in re.finditer(r"(?<![.!?]\s)(?<!^)\b([A-Z][a-zA-Z'\-]+)", text.strip()):
        w = m.group(1)
        if w.lower() in SENTENCE_START_OK:
            continue
        if not re.search(r"\b" + re.escape(w.lower()) + r"\b", page_n):
            errs.append(f"G2: name '{w}' does not appear on the firm's website")
    return errs


COMPANY_SUFFIX = re.compile(
    r"\b((?:[A-Z][\w&'\-]*\s+){0,4}(?:Construction|Builders?|Contracting|Contractors?|Inc|LLC|LLP|Corp|"
    r"Corporation|Company|Co\.|Group|Associates|Partners|Engineering|Engineers|Development|Developers|"
    r"Holdings|Realty|Properties|Bank|Photography))\b")


def check_third_party_companies(text: str, firm: str) -> list[str]:
    """G3: company-style names (e.g. 'Sutherland Construction') in model-written text, unless it is the
    prospect's own name. Catches companies the blocklist cannot know about, such as builders or clients
    that appear on the prospect's own project pages."""
    errs = []
    for m in COMPANY_SUFFIX.finditer(text):
        name = m.group(1).strip()
        if norm(name) not in norm(firm):
            errs.append(f"G3: names another company '{name}'")
    return errs


def check_company_names(email: str, blocklist: list[str]) -> list[str]:
    errs = []
    e = norm(email)
    for name in blocklist:
        n = norm(name)
        if n and re.search(r"(?<![a-z0-9])" + re.escape(n) + r"(?![a-z0-9])", e):
            errs.append(f"G3: names another company '{name}'")
    return errs


def opens_with_fact(opener: str, quote: str) -> bool:
    """First sentence must share at least two content words with the source quote."""
    first = re.split(r"(?<=[.!?])\s", opener.strip(), maxsplit=1)[0]
    stop = {"the", "and", "for", "with", "your", "you", "that", "this", "from", "was", "are", "its", "our", "has", "have"}
    fw = {w for w in re.findall(r"[a-z0-9']{3,}", norm(first)) if w not in stop}
    qw = {w for w in re.findall(r"[a-z0-9']{3,}", norm(quote)) if w not in stop}
    return len(fw & qw) >= 2 or (0 < len(qw) <= 3 and qw <= fw)


def validate_email(*, subject: str, opener: str, body: str, quote: str, page_text: str, firm: str,
                   cfg: dict, blocklist: list[str]) -> list[str]:
    errs = []
    errs += [f"subject {e}" for e in check_model_text(subject, quote=quote, page_text=page_text, firm=firm)]
    errs += [f"opener {e}" for e in check_model_text(opener, quote=quote, page_text=page_text, firm=firm)]
    errs += check_company_names(subject + "\n" + body, blocklist)
    errs += check_third_party_companies(subject + "\n" + opener, firm)
    if not opens_with_fact(opener, quote):
        errs.append("SOP: email must open with the sourced fact")
    if not body.startswith(opener.strip()):
        errs.append("SOP: the opener must be the first thing in the email")
    for key in ("product", "cta"):
        if cfg["email_blocks"][key] not in body:
            errs.append(f"G1: approved block '{key}' was altered")
    if not body.rstrip().endswith(cfg["sign_off"].strip()):
        errs.append("SOP: email must end with Kestrel's standard sign-off")
    wc = word_count(body)
    if wc > cfg["max_words"]:
        errs.append(f"SOP: {wc} words, limit is {cfg['max_words']}")
    return errs
