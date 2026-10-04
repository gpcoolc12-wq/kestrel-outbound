#!/usr/bin/env python3
"""Build simulation/index.html: a Linear-style view of the local workspace + the outbox.

  python view.py && open simulation/index.html
"""
from __future__ import annotations

import email
import html
import json
import re
from email import policy
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "simulation" / "index.html"

STATUS_COLOR = {"Todo": "#9aa0a6", "In Progress": "#f2c94c", "In Review": "#4ea7fc", "Done": "#5e6ad2",
                "Canceled": "#95a2b3"}
LABEL_COLOR = {"Segment: Residential": "#4cb782", "Segment: Commercial": "#4ea7fc", "Segment: Mixed": "#e2b93b",
               "Source: Brief": "#95a2b3", "Ready for Approval": "#eb5757"}


def md(text: str) -> str:
    """Tiny Markdown: bold, links, blockquote, headings, bullets, paragraphs."""
    out, para = [], []

    def inline(s):
        s = html.escape(s)
        s = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2" target="_blank">\1</a>', s)
        s = re.sub(r"(?<![\"'>=])(https?://[^\s<)]+)", r'<a href="\1" target="_blank">\1</a>', s)
        s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
        return s

    def flush():
        if para:
            out.append("<p>" + "<br>".join(inline(x) for x in para) + "</p>")
            para.clear()

    quote, items = [], []
    for line in text.split("\n") + [""]:
        if line.startswith(">"):
            flush(); quote.append(line[1:].lstrip()); continue
        if quote:
            out.append('<blockquote class="email">' + "<br>".join(inline(q) for q in quote) + "</blockquote>"); quote = []
        if re.match(r"^\s*[\*\-] ", line):
            flush(); items.append(re.sub(r"^\s*[\*\-] ", "", line)); continue
        if items:
            out.append("<ul>" + "".join(f"<li>{inline(i)}</li>" for i in items) + "</ul>"); items = []
        if line.startswith("#"):
            flush(); lvl = min(len(line) - len(line.lstrip("#")) + 2, 5)
            out.append(f"<h{lvl}>{inline(line.lstrip('#').strip())}</h{lvl}>"); continue
        if not line.strip():
            flush()
        else:
            para.append(line)
    return "\n".join(out)


def chip(name: str, color: str) -> str:
    return f'<span class="chip"><i style="background:{color}"></i>{html.escape(name)}</span>'


def build():
    ws = json.loads((ROOT / "local_linear/workspace.json").read_text())
    issues = list(ws["issues"].values())
    counts = {s: sum(1 for i in issues if i["state"] == s) for s in STATUS_COLOR}
    rows, details = [], []
    for i in issues:
        rows.append(
            f'<tr onclick="show(\'{i["identifier"]}\')"><td class="id">{i["identifier"]}</td>'
            f'<td>{chip(i["state"], STATUS_COLOR.get(i["state"], "#999"))}</td><td class="t">{html.escape(i["title"])}</td>'
            f'<td>{"".join(chip(l, LABEL_COLOR.get(l, "#999")) for l in i["labels"])}</td>'
            f'<td class="muted">{html.escape(i["assignee"] or "—")}</td></tr>')
        comments = "".join(f'<div class="comment"><div class="muted">{c["at"]}</div>{md(c["body"])}</div>'
                           for c in i["comments"])
        hist = "".join(f"<li>{html.escape(h)}</li>" for h in i["history"]) or "<li>—</li>"
        details.append(
            f'<section class="issue" id="{i["identifier"]}" hidden><div class="muted">{i["identifier"]} · '
            f'Kestrel Outbound</div><h2>{html.escape(i["title"])}</h2><div class="props">'
            f'{chip(i["state"], STATUS_COLOR.get(i["state"], "#999"))}'
            f'{"".join(chip(l, LABEL_COLOR.get(l, "#999")) for l in i["labels"])}'
            f'<span class="muted">Assignee: {html.escape(i["assignee"] or "—")}</span></div>'
            f'<div class="desc">{md(i["description"])}</div><h3>Activity</h3><ul class="hist">{hist}</ul>'
            f'<h3>Comments ({len(i["comments"])})</h3>{comments}</section>')
    docs = "".join(f'<details class="doc"><summary>{html.escape(t)}</summary>{md(c)}</details>'
                   for t, c in ws["documents"].items()) or '<p class="muted">No documents yet.</p>'
    ups = "".join(f'<div class="comment"><div class="muted">{u["at"]} · health: <b>{u["health"]}</b></div>{md(u["body"])}</div>'
                  for u in ws["project_updates"]) or '<p class="muted">No project updates yet.</p>'
    mails = []
    for f in sorted((ROOT / "outbox").glob("*.eml")):
        m = email.message_from_bytes(f.read_bytes(), policy=policy.default)
        mails.append(f'<details class="doc"><summary>{html.escape(m["Subject"])} <span class="muted">· to {html.escape(m["To"])} · '
                     f'{html.escape(m["Date"])}</span></summary><pre>{html.escape(m.get_content())}</pre></details>')
    page = f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Kestrel Outbound Simulation</title><style>
:root{{--bg:#fff;--fg:#1f2023;--muted:#6b6f76;--line:#e6e6e9;--panel:#f7f7f8;--accent:#5e6ad2}}
@media (prefers-color-scheme:dark){{:root{{--bg:#151618;--fg:#e6e6e9;--muted:#8a8f98;--line:#2a2c30;--panel:#1d1e21}}}}
body{{margin:0;background:var(--bg);color:var(--fg);font:14px/1.5 -apple-system,BlinkMacSystemFont,Inter,Segoe UI,sans-serif}}
header{{padding:16px 24px;border-bottom:1px solid var(--line)}} h1{{font-size:18px;margin:0}}
.muted{{color:var(--muted);font-size:12px}} main{{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(0,1fr);gap:0}}
@media (max-width:900px){{main{{grid-template-columns:1fr}}}}
.col{{padding:16px 24px;border-right:1px solid var(--line);min-width:0;height:calc(100vh - 92px);overflow:auto}}
@media (max-width:900px){{.col{{height:auto}}}}
table{{width:100%;border-collapse:collapse}} td{{padding:7px 6px;border-bottom:1px solid var(--line);vertical-align:top}}
tr{{cursor:pointer}} tr:hover{{background:var(--panel)}} .id{{color:var(--muted);white-space:nowrap}} .t{{font-weight:500}}
.chip{{display:inline-flex;align-items:center;gap:5px;border:1px solid var(--line);border-radius:12px;padding:1px 8px;margin:1px 3px 1px 0;font-size:12px;white-space:nowrap}}
.chip i{{width:8px;height:8px;border-radius:50%;display:inline-block}}
.stats span{{margin-right:14px}} .props{{margin:8px 0 14px}} .desc{{background:var(--panel);border-radius:8px;padding:4px 14px}}
blockquote.email{{border-left:3px solid var(--accent);margin:6px 0;padding:6px 12px;background:var(--bg)}}
.comment{{border:1px solid var(--line);border-radius:8px;padding:6px 12px;margin:8px 0}} .comment p{{margin:6px 0}}
.doc{{border:1px solid var(--line);border-radius:8px;padding:8px 12px;margin:8px 0}} summary{{cursor:pointer;font-weight:600}}
pre{{white-space:pre-wrap;font:13px/1.5 ui-monospace,Menlo,monospace}} a{{color:var(--accent);overflow-wrap:anywhere}}
.hist{{font-size:12px;color:var(--muted)}} h2{{margin:4px 0}} h3{{margin-top:20px;font-size:14px}}
</style></head><body><header><h1>Kestrel Outbound <span class="muted">· local Linear simulation · team {html.escape(ws['team'])}</span></h1>
<div class="muted">Members: {html.escape(', '.join(ws['members']))} · Invited: {html.escape(', '.join(ws['invites']) or '—')}
· Labels: {html.escape(', '.join(ws['labels']))} · Statuses: {html.escape(', '.join(ws['statuses']))}</div>
<div class="stats muted">{''.join(f'<span>{s}: <b>{n}</b></span>' for s, n in counts.items())}</div></header>
<main><div class="col"><h3>Issues</h3><table>{''.join(rows)}</table>
<h3>Project documents</h3>{docs}<h3>Project updates</h3>{ups}<h3>Outbox (simulated — nothing sent)</h3>{''.join(mails) or '<p class="muted">Empty.</p>'}</div>
<div class="col">{''.join(details)}<p class="muted" id="hint">Click an issue to open it.</p></div></main>
<script>function show(id){{document.querySelectorAll('.issue').forEach(e=>e.hidden=e.id!==id);document.getElementById('hint').hidden=true;
history.replaceState(null,'','#'+id);document.querySelectorAll('.col')[1].scrollTop=0}} if(location.hash) show(location.hash.slice(1)); else {{const f=document.querySelector('.issue'); if(f) show(f.id)}}</script>
</body></html>"""
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(page)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    build()
