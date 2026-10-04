"""Read a firm's public website: fetch pages, extract visible text and internal links.

Direct HTTP first (with normal browser headers). If the site blocks that (403, bot
wall) we fall back to the r.jina.ai reader, which renders the same public page.
A site "does not load" only when both paths fail.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse, urldefrag

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/129.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}
TIMEOUT = 25
MIN_TEXT = 200  # fewer visible characters than this is treated as an empty/blocked page

# Pages most likely to hold checkable facts (projects, awards, founding year).
PRIORITY = re.compile(
    r"about|firm|studio|history|story|who-we-are|people|team|award|news|press|"
    r"project|portfolio|work|recognition|publication",
    re.I,
)
SKIP = re.compile(r"\.(jpg|jpeg|png|gif|pdf|zip|mp4|svg|webp)$|mailto:|tel:|#|/wp-json|/feed|login|cart", re.I)


@dataclass
class Page:
    url: str
    title: str
    text: str
    links: list[str] = field(default_factory=list)
    via: str = "direct"  # "direct" or "reader"


class SiteUnreachable(Exception):
    pass


def _norm_host(u: str) -> str:
    h = urlparse(u).netloc.lower()
    return h[4:] if h.startswith("www.") else h


def _direct(url: str) -> Page | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
    except requests.RequestException:
        return None
    if r.status_code != 200 or "html" not in r.headers.get("content-type", "html"):
        return None
    soup = BeautifulSoup(r.text, "html.parser")
    for t in soup(["script", "style", "noscript", "svg", "iframe"]):
        t.decompose()
    title = (soup.title.string or "").strip() if soup.title else ""
    text = re.sub(r"\s+", " ", soup.get_text(" ")).strip()
    links = [urldefrag(urljoin(r.url, a["href"]))[0] for a in soup.find_all("a", href=True)]
    if len(text) < MIN_TEXT:
        return None
    return Page(url=r.url, title=title, text=text, links=links, via="direct")


def _reader(url: str) -> Page | None:
    try:
        r = requests.get(f"https://r.jina.ai/{url}", timeout=60, headers={"X-Return-Format": "markdown"})
    except requests.RequestException:
        return None
    if r.status_code != 200:
        return None
    body = r.text
    m = re.search(r"^Title:\s*(.*)$", body, re.M)
    title = m.group(1).strip() if m else ""
    md = body.split("Markdown Content:", 1)[-1]
    links = [urldefrag(u)[0] for u in re.findall(r"\]\((https?://[^)\s]+)", md)]
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", md)          # drop images
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)       # keep link text
    text = re.sub(r"[#*_>`]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) < MIN_TEXT:
        return None
    return Page(url=url, title=title, text=text, links=links, via="reader")


def fetch(url: str) -> Page | None:
    return _direct(url) or _reader(url)


def read_site(home: str, max_pages: int = 8) -> list[Page]:
    """Homepage plus up to max_pages-1 same-site pages, fact-rich pages first."""
    first = fetch(home)
    if not first:
        raise SiteUnreachable(f"{home} did not load (direct request and reader both failed)")
    host = _norm_host(first.url)
    seen = {first.url.rstrip("/"), home.rstrip("/")}
    candidates = []
    for link in first.links:
        if _norm_host(link) != host or SKIP.search(link):
            continue
        key = link.rstrip("/")
        if key in seen:
            continue
        seen.add(key)
        candidates.append(link)
    candidates.sort(key=lambda u: (0 if PRIORITY.search(urlparse(u).path) else 1, len(u)))
    pages = [first]
    got = {first.url.rstrip("/")}
    for link in candidates:
        if len(pages) >= max_pages:
            break
        p = fetch(link)
        if p and p.url.rstrip("/") not in got:  # two links can redirect to the same page
            got.add(p.url.rstrip("/"))
            pages.append(p)
    return pages
