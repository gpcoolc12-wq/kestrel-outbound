#!/usr/bin/env python3
"""Build simulation/index.html: a self-contained front end for the simulated run.

Tabs: Overview (SOP steps + KPIs), Board (Linear-style, click an issue), Replay (step through
every logged action), Agent & guardrails (fact candidates, rejected drafts, overrides),
Outbox (emails, not sent) and Documents. All data is embedded; no server, key or internet needed.

  python view.py && open simulation/index.html
"""
from __future__ import annotations

import email
import json
import subprocess
import sys
from email import policy
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "simulation" / "index.html"


def load():
    ws = json.loads((ROOT / "local_linear/workspace.json").read_text())
    st = json.loads((ROOT / "state/local.json").read_text())
    cfg = json.loads((ROOT / "config/kestrel.json").read_text())
    mails = []
    for f in sorted((ROOT / "outbox").glob("*.eml")):
        m = email.message_from_bytes(f.read_bytes(), policy=policy.default)
        mails.append({"subject": m["Subject"], "to": m["To"], "from": m["From"], "date": m["Date"],
                      "body": m.get_content(), "file": f.name})
    tests = subprocess.run([sys.executable, str(ROOT / "tests/test_guardrails.py")], capture_output=True, text=True)
    test_lines = [l.split(" ", 1) for l in tests.stdout.splitlines() if l.startswith(("PASS", "FAIL"))]
    docs = {t: c for t, c in ws["documents"].items()}
    docs["Clarifying questions (email to Nirbhay)"] = (ROOT / "docs/clarifying_questions.md").read_text()
    prospects = []
    for n, p in st["prospects"].items():
        issue = ws["issues"].get(p["identifier"], {})
        prospects.append({
            "n": n, "id": p["identifier"], "firm": p["firm"], "city": p["city"], "website": p["website"],
            "title": p["title"], "status": p["status"], "labels": p["labels"], "assignee": issue.get("assignee"),
            "status_note": p.get("status_note", ""), "segment_line": p.get("segment_line", ""),
            "dnc_line": p.get("dnc_line", ""), "dnc": p.get("dnc"), "profile": p.get("profile"),
            "site_error": p.get("site_error"), "fact": p.get("fact"), "draft": p.get("draft"),
            "fact_trail": p.get("fact_trail", []), "draft_trail": p.get("draft_trail", []),
            "overrides": p.get("overrides", []), "history": p.get("history", []),
            "description": issue.get("description", ""), "comments": issue.get("comments", []),
        })
    import csv
    demo = ROOT / "demo/agent_demo.json"
    return {
        "agent_demo": json.loads(demo.read_text()) if demo.exists() else None,
        "brief_prospects": list(csv.DictReader(open(ROOT / "config/prospects.csv"))),
        "email_blocks": cfg["email_blocks"], "max_words": cfg["max_words"],
        "time_taken": cfg.get("time_taken", ""), "approver_email": cfg["linear"]["approver_email"],
        "required_labels": cfg["linear"]["labels"], "required_statuses": list(cfg["linear"]["statuses"]),
        "workspace": {"team": ws["team"], "members": ws["members"], "invites": ws["invites"],
                      "labels": ws["labels"], "statuses": ws["statuses"], "project": ws["project"]},
        "project_updates": ws["project_updates"], "prospects": prospects, "mails": mails, "docs": docs,
        "tests": test_lines, "claims": list(cfg["approved_claims"].values()), "dnc_list": cfg["do_not_contact"],
        "sign_off": cfg["sign_off"], "sign_off_confirmed": cfg.get("sign_off_is_confirmed", False),
        "engine": next((t.get("engine") for p in st["prospects"].values() for t in p.get("draft_trail", [])
                        if t.get("engine")), "model"),
    }


PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Kestrel Outbound Simulation</title>
<style>
:root{--bg:#f7f7f8;--panel:#fff;--panel2:#f2f3f5;--fg:#1b1c1f;--muted:#6b6f78;--line:#e4e5e9;--accent:#5e6ad2;
--accent-bg:#eef0fc;--good:#2f9e6b;--good-bg:#e6f5ee;--warn:#c47f00;--warn-bg:#fdf3dc;--bad:#d1453b;--bad-bg:#fbe9e7;
--blue:#3b82d6;--shadow:0 1px 2px rgba(0,0,0,.05),0 4px 16px rgba(0,0,0,.04)}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#0f1012;--panel:#17181b;--panel2:#1e1f23;--fg:#e7e8ea;
--muted:#8e939c;--line:#2a2c31;--accent:#8b93f0;--accent-bg:#23264a;--good:#4cc38a;--good-bg:#173226;--warn:#e0a83a;
--warn-bg:#3a2e14;--bad:#f0706a;--bad-bg:#3d1c1a;--blue:#6aa8f0;--shadow:none}}
:root[data-theme=dark]{--bg:#0f1012;--panel:#17181b;--panel2:#1e1f23;--fg:#e7e8ea;--muted:#8e939c;--line:#2a2c31;
--accent:#8b93f0;--accent-bg:#23264a;--good:#4cc38a;--good-bg:#173226;--warn:#e0a83a;--warn-bg:#3a2e14;--bad:#f0706a;
--bad-bg:#3d1c1a;--blue:#6aa8f0;--shadow:none}
*{box-sizing:border-box}html,body{margin:0}body{background:var(--bg);color:var(--fg);
font:14px/1.55 -apple-system,BlinkMacSystemFont,"Inter","Segoe UI",Roboto,sans-serif;-webkit-font-smoothing:antialiased}
a{color:var(--accent);text-decoration:none;overflow-wrap:anywhere}a:hover{text-decoration:underline}
@media(max-width:700px){header{position:static!important}.now{position:static!important}}
header{position:sticky;top:0;z-index:20;background:color-mix(in srgb,var(--bg) 88%,transparent);backdrop-filter:blur(8px);
border-bottom:1px solid var(--line)}
.wrap{max-width:1280px;margin:0 auto;padding:0 20px}
.top{display:flex;align-items:center;gap:14px;padding:14px 0 10px;flex-wrap:wrap}
.logo{width:30px;height:30px;border-radius:8px;background:linear-gradient(135deg,var(--accent),#9a6ad2);display:grid;
place-items:center;color:#fff;font-weight:700}
h1{font-size:17px;margin:0;letter-spacing:-.01em}.sub{color:var(--muted);font-size:12.5px}
.badges{margin-left:auto;display:flex;gap:6px;flex-wrap:wrap}
.badge{font-size:11.5px;padding:3px 9px;border-radius:999px;background:var(--panel2);color:var(--muted);border:1px solid var(--line)}
.badge.ok{background:var(--good-bg);color:var(--good);border-color:transparent}
nav{display:flex;gap:2px;overflow-x:auto;scrollbar-width:none}nav::-webkit-scrollbar{display:none}
nav button{all:unset;cursor:pointer;padding:9px 12px;color:var(--muted);font-weight:500;border-bottom:2px solid transparent;white-space:nowrap}
nav button[aria-selected=true]{color:var(--fg);border-color:var(--accent)}
main{padding:22px 0 60px}.tab{display:none}.tab.on{display:block}
.grid{display:grid;gap:14px}.k6{grid-template-columns:repeat(6,minmax(0,1fr))}
@media(max-width:1000px){.k6{grid-template-columns:repeat(3,minmax(0,1fr))}}@media(max-width:560px){.k6{grid-template-columns:repeat(2,minmax(0,1fr))}}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;box-shadow:var(--shadow)}
.pad{padding:16px 18px}.kpi .v{font-size:26px;font-weight:650;letter-spacing:-.02em}.kpi .l{color:var(--muted);font-size:12.5px}
h2{font-size:15px;margin:26px 0 10px;letter-spacing:-.01em}h3{font-size:13.5px;margin:16px 0 6px}
.muted{color:var(--muted)}.small{font-size:12.5px}
.steps{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}
@media(max-width:900px){.steps{grid-template-columns:1fr}}
.step{display:flex;gap:12px;align-items:flex-start}.num{flex:none;width:26px;height:26px;border-radius:50%;
display:grid;place-items:center;font-size:12px;font-weight:650;background:var(--good-bg);color:var(--good)}
.num.sim{background:var(--warn-bg);color:var(--warn)}
.step .st{display:block;font-weight:650;font-size:13.5px}.step p{margin:2px 0 0;color:var(--muted);font-size:12.5px}
table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:9px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-size:11.5px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);font-weight:600}
tbody tr{cursor:pointer}tbody tr:hover{background:var(--panel2)}.tablewrap{overflow-x:auto}
.chip{display:inline-flex;align-items:center;gap:5px;padding:1px 8px;margin:1px 4px 1px 0;border-radius:999px;
font-size:11.5px;border:1px solid var(--line);white-space:nowrap;background:var(--panel)}
.dot{width:7px;height:7px;border-radius:50%;display:inline-block;flex:none}
.board{display:grid;grid-template-columns:repeat(5,minmax(220px,1fr));gap:12px;overflow-x:auto;padding-bottom:6px}
.col{background:var(--panel2);border-radius:12px;padding:10px;min-height:120px}
.colh{display:flex;align-items:center;gap:7px;font-weight:600;font-size:12.5px;padding:2px 4px 10px}
.colh .n{color:var(--muted);font-weight:500}
.icard{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:10px 11px;margin-bottom:8px;cursor:pointer;
transition:transform .15s,box-shadow .15s,border-color .3s}.icard:hover{transform:translateY(-1px);box-shadow:var(--shadow)}
.icard .id{font-size:11.5px;color:var(--muted)}.icard .t{font-weight:550;margin:2px 0 6px;font-size:13px}
.board.compact{grid-template-columns:repeat(5,minmax(120px,1fr))}.icard.mini{padding:7px 9px;margin-bottom:6px}
.icard.mini .t{margin:1px 0 3px;font-size:12.5px}
.icard.flash{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-bg)}
.avatar{display:inline-grid;place-items:center;width:20px;height:20px;border-radius:50%;background:var(--accent);color:#fff;font-size:10px;font-weight:700}
.drawer{position:fixed;inset:0;z-index:50;display:none}.drawer.on{display:block}
.scrim{position:absolute;inset:0;background:rgba(0,0,0,.35)}
.sheet{position:absolute;top:0;right:0;bottom:0;width:min(760px,100%);background:var(--panel);border-left:1px solid var(--line);
overflow:auto;padding:22px 24px 40px}
.close{all:unset;cursor:pointer;float:right;font-size:22px;line-height:1;color:var(--muted);padding:2px 6px}
.subtabs{display:flex;gap:4px;margin:14px 0;border-bottom:1px solid var(--line);flex-wrap:wrap}
.subtabs button{all:unset;cursor:pointer;padding:7px 10px;color:var(--muted);border-bottom:2px solid transparent;font-weight:500}
.subtabs button[aria-selected=true]{color:var(--fg);border-color:var(--accent)}
.kv{display:grid;grid-template-columns:150px 1fr;gap:6px 14px;font-size:13px}@media(max-width:560px){.kv{grid-template-columns:1fr}}
.kv dt{color:var(--muted)}.kv dd{margin:0}
.mail{border:1px solid var(--line);border-radius:12px;overflow:hidden}
.mailh{background:var(--panel2);padding:10px 14px;font-size:12.5px;border-bottom:1px solid var(--line)}
.mailb{padding:16px 18px;white-space:pre-wrap;font-size:14px;line-height:1.6}
.hl-fact{background:var(--accent-bg);border-radius:4px;padding:0 2px}
.hl-fixed{color:var(--muted)}
.quote{border-left:3px solid var(--accent);background:var(--panel2);padding:8px 12px;border-radius:0 8px 8px 0;margin:6px 0;font-size:13px}
.tl{position:relative;margin-left:8px;border-left:2px solid var(--line);padding-left:16px}
.tl .ev{position:relative;margin:0 0 14px}.tl .ev:before{content:"";position:absolute;left:-23px;top:5px;width:10px;height:10px;
border-radius:50%;background:var(--panel);border:2px solid var(--accent)}
.tl .ev .when{font-size:11.5px;color:var(--muted)}
.md p{margin:8px 0}.md ul{margin:6px 0;padding-left:20px}.md h2,.md h3,.md h4{margin:14px 0 6px}.md code{background:var(--panel2);padding:1px 5px;border-radius:5px;font-size:12.5px}
.ok{color:var(--good)}.bad{color:var(--bad)}.warn{color:var(--warn)}
.pill{font-size:11px;font-weight:600;padding:1px 7px;border-radius:999px;white-space:nowrap}.pill.ok{background:var(--good-bg)}.pill.bad{background:var(--bad-bg)}.pill.warn{background:var(--warn-bg)}
.controls{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.btn{all:unset;cursor:pointer;padding:7px 12px;border-radius:8px;border:1px solid var(--line);background:var(--panel);font-weight:550;font-size:13px}
.btn.primary{background:var(--accent);border-color:var(--accent);color:#fff}.btn:disabled{opacity:.4;cursor:default}
input[type=range]{accent-color:var(--accent)}
.progress{height:6px;background:var(--panel2);border-radius:99px;overflow:hidden;flex:1;min-width:120px}
.progress i{display:block;height:100%;background:var(--accent);width:0;transition:width .2s}
.replay{display:grid;grid-template-columns:minmax(0,1fr) 380px;gap:14px;margin-top:14px}@media(max-width:1000px){.replay{grid-template-columns:1fr}}
.now{position:sticky;top:110px}
.diff{display:grid;grid-template-columns:1fr 1fr;gap:10px}@media(max-width:700px){.diff{grid-template-columns:1fr}}
.diff div{border:1px solid var(--line);border-radius:10px;padding:10px 12px;font-size:13px}
.diff .before{background:var(--bad-bg)}.diff .after{background:var(--good-bg)}
.split{display:grid;grid-template-columns:320px minmax(0,1fr);gap:14px}@media(max-width:800px){.split{grid-template-columns:1fr}}
.list button{all:unset;display:block;width:100%;box-sizing:border-box;cursor:pointer;padding:10px 12px;border-bottom:1px solid var(--line)}
.list button[aria-selected=true]{background:var(--accent-bg)}
.rule{border-top:3px solid var(--accent)}
.themebtn{all:unset;cursor:pointer;color:var(--muted);font-size:16px;padding:4px}
</style></head><body>
<header><div class="wrap">
 <div class="top"><div class="logo">K</div><div><h1>Kestrel Outbound</h1>
 <div class="sub">SOP simulation for Kestrel Rooms · Invictus AI Operations Associate take-home</div></div>
 <div class="badges" id="badges"></div><button class="themebtn" id="theme" title="Toggle theme">◐</button></div>
 <nav role="tablist" id="nav"></nav></div></header>
<main class="wrap">
 <section class="tab" id="t-overview"></section><section class="tab" id="t-board"></section>
 <section class="tab" id="t-replay"></section><section class="tab" id="t-agent"></section>
 <section class="tab" id="t-outbox"></section><section class="tab" id="t-docs"></section>
 <section class="tab" id="t-checklist"></section><section class="tab" id="t-demo"></section>
</main>
<div class="drawer" id="drawer"><div class="scrim" onclick="closeIssue()"></div><div class="sheet" id="sheet"></div></div>
<script>
const D = __DATA__;
const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const STATUS = ["Todo","In Progress","In Review","Done","Canceled"];
const SCOL = {"Todo":"#9aa0a6","In Progress":"#e0a83a","In Review":"#3b82d6","Done":"#5e6ad2","Canceled":"#95a2b3"};
const LCOL = {"Segment: Residential":"#2f9e6b","Segment: Commercial":"#3b82d6","Segment: Mixed":"#c9a227","Source: Brief":"#95a2b3","Ready for Approval":"#d1453b"};
const chip = (t,c) => `<span class="chip"><i class="dot" style="background:${c||'#999'}"></i>${esc(t)}</span>`;
const sChip = s => chip(s, SCOL[s]);
const labels = ls => (ls||[]).map(l => chip(l, LCOL[l])).join("");
const P = D.prospects;
const byId = id => P.find(p => p.id === id);

function md(t){
  const inl = s => esc(s).replace(/\[([^\]]+)\]\((https?:[^)\s]+)\)/g,'<a href="$2" target="_blank">$1</a>')
    .replace(/(^|[\s(])(https?:\/\/[^\s<)]+)/g,'$1<a href="$2" target="_blank">$2</a>')
    .replace(/\*\*([^*]+)\*\*/g,"<strong>$1</strong>").replace(/`([^`]+)`/g,"<code>$1</code>");
  let out=[], para=[], list=[], quote=[];
  const flush=()=>{ if(para.length){out.push("<p>"+para.map(inl).join("<br>")+"</p>");para=[]}
    if(list.length){out.push("<ul>"+list.map(i=>"<li>"+inl(i)+"</li>").join("")+"</ul>");list=[]}
    if(quote.length){out.push('<div class="quote">'+quote.map(inl).join("<br>")+"</div>");quote=[]} };
  for(const line of String(t||"").split("\n")){
    if(/^#{1,4}\s/.test(line)){flush();const l=line.match(/^#+/)[0].length;out.push(`<h${l+1}>${inl(line.replace(/^#+\s*/,""))}</h${l+1}>`);continue}
    if(/^\s*[*-]\s+/.test(line)){ if(para.length||quote.length){const l=list;list=[];flush();list=l} list.push(line.replace(/^\s*[*-]\s+/,""));continue}
    if(/^>/.test(line)){ if(para.length||list.length){flush()} quote.push(line.replace(/^>\s?/,""));continue}
    if(!line.trim()){flush();continue}
    if(list.length||quote.length) flush();
    para.push(line);
  }
  flush(); return '<div class="md">'+out.join("")+"</div>";
}

// ---------------------------------------------------------------- navigation
const TABS=[["overview","Overview"],["checklist","Brief & checklist"],["board","Board"],["replay","Simulation replay"],["demo","Agent demo"],["agent","Agent & guardrails"],["outbox","Outbox"],["docs","Documents"]];
$("#nav").innerHTML = TABS.map(([k,v])=>`<button role="tab" data-t="${k}">${v}</button>`).join("");
function show(k){ document.querySelectorAll("nav button").forEach(b=>b.setAttribute("aria-selected", b.dataset.t===k));
  document.querySelectorAll(".tab").forEach(s=>s.classList.toggle("on", s.id==="t-"+k));
  try{localStorage.setItem("kes-tab",k)}catch(e){} if(location.hash!=="#"+k) history.replaceState(null,"","#"+k) }
$("#nav").onclick = e => { const b=e.target.closest("button"); if(b) show(b.dataset.t) };
$("#theme").onclick = () => { const r=document.documentElement, dark=r.dataset.theme? r.dataset.theme==="dark" : matchMedia("(prefers-color-scheme: dark)").matches;
  r.dataset.theme = dark? "light":"dark"; try{localStorage.setItem("kes-theme",r.dataset.theme)}catch(e){} };
try{const t=localStorage.getItem("kes-theme"); if(t) document.documentElement.dataset.theme=t}catch(e){}

const inReview=P.filter(p=>p.status==="In Review"), dropped=P.filter(p=>p.status==="Canceled");
const rejections=P.flatMap(p=>(p.draft_trail||[]).filter(t=>(t.violations||[]).length).map(t=>({p,t})));
const styleRej=P.flatMap(p=>(p.draft_trail||[]).filter(t=>!(t.violations||[]).length&&(t.style||[]).length).map(t=>({p,t})));
const overrides=P.flatMap(p=>(p.overrides||[]).map(o=>({p,o})));
const discarded=P.flatMap(p=>(p.fact_trail||[]).filter(t=>"fact" in t && !t.verified));
const engineLabel = D.engine==="offline" ? "Offline engine · no API key" : "LLM engine";
$("#badges").innerHTML = [`<span class="badge ok">✓ ${engineLabel}</span>`,`<span class="badge">Linear: local stand-in</span>`,
  `<span class="badge">Emails: outbox only, nothing sent</span>`].join("");

// ---------------------------------------------------------------- overview
function overview(){
  const kpis=[[P.length,"Firms on the list"],[inReview.length,"Drafts waiting for Nirbhay"],[dropped.length,"Closed without contact"],
    [rejections.length+styleRej.length,"Drafts the checks sent back"],[overrides.length,"Drafts I corrected by hand"],[D.mails.length,"Emails in the outbox (unsent)"]];
  const facts=P.filter(p=>p.fact);
  const step=(n,title,detail,sim)=>`<div class="card pad step"><span class="num ${sim?'sim':''}">${sim?'~':'✓'}</span><div><span class="st">Step ${n}. ${title}</span><p>${detail}</p></div></div>`;
  const s1=`Project <b>${esc(D.workspace.project)}</b>, ${D.workspace.labels.length} labels, statuses ${D.workspace.statuses.filter(s=>STATUS.includes(s)).join(", ")}. Invited ${esc(D.workspace.invites.join(", "))}.`;
  const facts2=facts.length, words=facts.map(p=>p.draft?.words||0).filter(Boolean);
  $("#t-overview").innerHTML = `
  <div class="card pad" style="margin-bottom:14px"><b>What happened here</b><p class="muted" style="margin:6px 0 0">The agent worked through ten architecture firms for Kestrel Rooms the way the process asks. It set up a workspace, opened a ticket for each firm, checked who was off-limits, found one real fact about each firm, and wrote a short email that leads with it. Then it handed the drafts to Nirbhay for approval. Two firms were stopped on the way: one because it's linked to an existing customer, the other because its website doesn't exist. Nothing was actually sent.</p></div>
  <div class="grid k6">${kpis.map(([v,l])=>`<div class="card pad kpi"><div class="v">${v}</div><div class="l">${l}</div></div>`).join("")}</div>
  <h2>How it went, step by step</h2>
  <div class="steps">
   ${step(1,"Set up the workspace",`A project called “${esc(D.workspace.project)}”, the labels and stages it needs, and an invite for Nirbhay.`,true)}
   ${step(2,"Open a ticket per firm",`${P.length} tickets. Each one is tagged with the kind of work the firm does, judged from its own website.`)}
   ${step(3,"Check who's off-limits",`Done before any research. ${P.filter(p=>p.dnc&&p.dnc.result==="Match").map(p=>esc(p.firm)+" turned out to belong to "+esc(p.dnc.company)+", an existing customer, so it was closed").join(". ")||"No matches"}.`)}
   ${step(4,"Find one real fact",`${facts2} facts, each traced back to the exact words on the firm's site. A firm with a dead website was closed, not replaced.`)}
   ${step(5,"Write the email",`${Math.min(...words)}–${Math.max(...words)} words each. It opens with the fact, and the product lines are copied straight from the approved list.`)}
   ${step(6,"Hand over for approval",`${inReview.length} drafts are with Nirbhay. Nothing was marked Done, because that's Nirbhay's decision.`)}
   ${step(7,"Leave a trail",`Every one of the ${P.reduce((a,p)=>a+(p.history||[]).length,0)} actions left a note with a link on its ticket.`)}
   ${step(8,"Send an end-of-day note",`Three lines for Nirbhay: what's done, what's stuck, what needs a decision.`,true)}
   ${step(9,"Wrap up",`A status update on the project (on track) and a handover email with every link.`,true)}
  </div>
  <p class="small muted">✓ fully done · ~ done in the simulation (a local stand-in for Linear and email)</p>
  <h2>The workspace</h2>
  <div class="card pad small"><div class="kv"><dt>Team</dt><dd>${esc(D.workspace.team)}</dd><dt>Project</dt><dd>${esc(D.workspace.project)}</dd>
   <dt>Members</dt><dd>${esc(D.workspace.members.join(", "))}</dd><dt>Invited</dt><dd>${esc(D.workspace.invites.join(", "))} <span class="pill warn">acceptance simulated</span></dd>
   <dt>Labels</dt><dd>${labels(D.workspace.labels)}</dd><dt>Statuses</dt><dd>${D.workspace.statuses.map(s=>sChip(s)).join("")}</dd></div></div>
  <h2>The ten firms</h2>
  <div class="card tablewrap"><table><thead><tr><th>Issue</th><th>Firm</th><th>Status</th><th>Segment</th><th>Fact</th><th>Words</th></tr></thead><tbody>
  ${P.map(p=>`<tr onclick="openIssue('${p.id}')"><td class="muted">${p.id}</td><td><b>${esc(p.firm)}</b><div class="small muted">${esc(p.city)}</div></td>
   <td>${sChip(p.status)}</td><td>${labels(p.labels.filter(l=>l.startsWith("Segment")))||'<span class="muted small">—</span>'}</td>
   <td class="small">${p.fact?esc(p.fact.fact):`<span class="muted">${esc(p.status_note)}</span>`}</td><td>${p.draft?p.draft.words:"—"}</td></tr>`).join("")}
  </tbody></table></div>
  <h2>Latest project update</h2>${D.project_updates.map(u=>`<div class="card pad"><div class="small muted">${esc(u.at)} · health <b class="ok">${esc(u.health)}</b></div>${md(u.body)}</div>`).join("")}`;
}

// ---------------------------------------------------------------- board
function issueCard(p, st, compact){
  const s = st || p;
  if(compact) return `<div class="icard mini" id="card-${p.id}" onclick="openIssue('${p.id}')"><div class="id">${p.id}${s.assignee?' · NB':''}</div>
   <div class="t">${esc(p.firm)}</div><div>${(s.labels||[]).map(l=>`<i class="dot" title="${esc(l)}" style="background:${LCOL[l]||'#999'};margin-right:3px"></i>`).join("")}</div></div>`;
  return `<div class="icard" id="card-${p.id}" onclick="openIssue('${p.id}')"><div class="id">${p.id}</div>
   <div class="t">${esc(s.title)}</div><div>${labels(s.labels)}</div>
   <div class="small muted" style="margin-top:6px;display:flex;justify-content:space-between;align-items:center">
   <span>${esc(p.city)}</span>${s.assignee?`<span class="avatar" title="${esc(s.assignee)}">NB</span>`:""}</div></div>`;
}
function boardHTML(get, compact){
  return `<div class="board ${compact?'compact':''}">${STATUS.map(s=>{const items=P.map(p=>[p,get(p)]).filter(([p,st])=>st&&st.status===s);
    return `<div class="col"><div class="colh"><i class="dot" style="background:${SCOL[s]}"></i>${s}<span class="n">${items.length}</span></div>
    ${items.map(([p,st])=>issueCard(p,st,compact)).join("")}</div>`}).join("")}</div>`;
}
function board(){
  $("#t-board").innerHTML = `<div class="small muted" style="margin-bottom:12px">Team <b>${esc(D.workspace.team)}</b> · Project <b>${esc(D.workspace.project)}</b> ·
   Members ${esc(D.workspace.members.join(", "))} · Labels ${labels(D.workspace.labels)}</div>${boardHTML(p=>p)}`;
}

// ---------------------------------------------------------------- issue drawer
function emailHTML(p){
  if(!p.draft) return `<p class="muted">No draft: ${esc(p.status_note)}</p>`;
  const parts=p.draft.body.split("\n\n");
  return `<div class="mail"><div class="mailh"><b>To:</b> ${esc(p.firm)} · <b>Subject:</b> ${esc(p.draft.subject)}
   <span style="float:right" class="pill ok">${p.draft.words} words · guardrails pass</span></div>
   <div class="mailb"><span class="hl-fact" title="Written by the agent, grounded in the sourced fact">${esc(parts[0])}</span>\n\n<span class="hl-fixed" title="Inserted verbatim from the approved claims">${esc(parts.slice(1).join("\n\n"))}</span></div></div>
   <p class="small muted">Highlighted: written by the agent from the sourced fact. Grey: approved claims, call to action and sign-off, inserted by code word for word.</p>`;
}
function researchHTML(p){
  const pr=p.profile; let h="";
  if(pr) h+=`<h3>Segment: ${esc(pr.segment)}</h3><div class="small muted">${esc(pr.segment_reason)}</div><div class="quote">“${esc(pr.segment_quote)}”<br><a href="${esc(pr.segment_url)}" target="_blank">${esc(pr.segment_url)}</a></div>`;
  if(p.site_error) h+=`<h3>Website</h3><p class="bad">${esc(p.site_error)}</p>`;
  if(p.dnc) h+=`<h3>Do-not-contact check: <span class="${p.dnc.result==="Match"?"bad":"ok"}">${esc(p.dnc.result)}</span></h3><p class="small">${esc(p.dnc.detail)}</p>`;
  if(pr&&pr.affiliates&&pr.affiliates.length) h+=pr.affiliates.map(a=>`<div class="quote"><b>${esc(a.name)}</b> (${esc(a.relationship)}): “${esc(a.quote)}”<br><a href="${esc(a.url)}" target="_blank">${esc(a.url)}</a></div>`).join("");
  const ft=(p.fact_trail||[]).filter(t=>"fact" in t);
  if(ft.length) h+=`<h3>Fact candidates (${ft.length})</h3><table><tbody>${ft.map(t=>`<tr style="cursor:default"><td><span class="pill ${t.verified?'ok':'bad'}">${t.verified?'verified':'discarded'}</span></td>
    <td class="small"><span class="muted">${esc(t.kind||"")}</span> ${esc(t.fact)}</td></tr>`).join("")}</tbody></table>`;
  if(p.fact) h+=`<h3>Chosen fact</h3><p>${esc(p.fact.fact)}</p><div class="quote">“${esc(p.fact.quote)}”<br><a href="${esc(p.fact.url)}" target="_blank">${esc(p.fact.url)}</a></div>`;
  const dt=p.draft_trail||[];
  if(dt.length) h+=`<h3>Draft attempts (${dt.length})</h3>${dt.map(t=>{const errs=[...(t.violations||[]),...(t.style||[])];
    return `<div class="card pad" style="margin:8px 0"><div class="small"><span class="pill ${errs.length?'bad':'ok'}">attempt ${t.attempt}: ${errs.length?'rejected':'accepted'}</span></div>
    <div class="small" style="margin-top:6px">${esc(t.opener)}</div>${errs.length?`<ul class="small bad">${errs.map(e=>`<li>${esc(e)}</li>`).join("")}</ul>`:""}</div>`}).join("")}`;
  (p.overrides||[]).forEach(o=>{h+=`<h3>Human override</h3><p class="small">${esc(o.reason)}</p><div class="diff"><div class="before"><b class="small">Before (AI)</b><br>${esc(o.before.opener)}</div><div class="after"><b class="small">After (human)</b><br>${esc(o.after.opener)}</div></div>`});
  return h||'<p class="muted">No research: dropped before Step 4.</p>';
}
function activityHTML(p){
  return `<div class="tl">${(p.history||[]).map(h=>`<div class="ev"><div class="when">#${h.seq} · ${esc((h.at||"").replace("T"," "))} · ${sChip(h.status||"")}</div>${md(h.comment||h.action)}</div>`).join("")}</div>`;
}
let cur=null;
function openIssue(id, sub){
  const p=byId(id); cur=id;
  const subs=[["desc","Description"],["email","Email"],["research","Research"],["activity",`Activity (${(p.history||[]).length})`]];
  const which=sub||"desc";
  const body={desc:md(p.description),email:emailHTML(p),research:researchHTML(p),activity:activityHTML(p)}[which];
  $("#sheet").innerHTML=`<button class="close" onclick="closeIssue()" aria-label="Close">×</button>
   <div class="small muted">${p.id} · ${esc(D.workspace.project)}</div><h2 style="margin:4px 0 8px;font-size:19px">${esc(p.title)}</h2>
   <div>${sChip(p.status)}${labels(p.labels)}${p.assignee?chip("Assignee: Nirbhay","#5e6ad2"):""}</div>
   <div class="subtabs">${subs.map(([k,v])=>`<button aria-selected="${k===which}" onclick="openIssue('${id}','${k}')">${v}</button>`).join("")}</div>${body}`;
  $("#drawer").classList.add("on"); document.body.style.overflow="hidden";
}
function closeIssue(){ $("#drawer").classList.remove("on"); document.body.style.overflow=""; cur=null }
addEventListener("keydown",e=>{ if(e.key==="Escape") closeIssue() });

// ---------------------------------------------------------------- replay
const EVENTS=[{seq:0,id:null,action:"Step 1: workspace set up",comment:`Project **${D.workspace.project}** created with labels ${D.workspace.labels.join(", ")} and statuses ${D.workspace.statuses.join(", ")}. Invited ${D.workspace.invites.join(", ")}.`}]
  .concat(P.flatMap(p=>(p.history||[]).map(h=>({...h,id:p.id})))).sort((a,b)=>a.seq-b.seq);
let ri=0, timer=null;
function stateAt(i){ const st={}; for(let k=1;k<=i;k++){const e=EVENTS[k]; st[e.id]={status:e.status,title:e.title,labels:e.labels,assignee:e.assignee}} return st }
function renderReplay(){
  const e=EVENTS[ri], st=stateAt(ri), p=e.id?byId(e.id):null;
  $("#r-board").innerHTML=boardHTML(q=>st[q.id], true);
  if(e.id){const c=$("#card-"+e.id); if(c) c.classList.add("flash")}
  $("#r-now").innerHTML=`<div class="small muted">Action ${ri+1} of ${EVENTS.length}${p?` · ${p.id} ${esc(p.firm)}`:""}</div>
   <h3 style="margin:6px 0">${esc(e.action.replace(/\*\*/g,""))}</h3>${e.status?`<div>${sChip(e.status)}${labels(e.labels)}</div>`:""}${md(e.comment)}`;
  $("#r-bar").style.width=((ri+1)/EVENTS.length*100)+"%";
  $("#r-prev").disabled=ri===0; $("#r-next").disabled=ri===EVENTS.length-1;
}
function play(){ if(timer){clearInterval(timer);timer=null;$("#r-play").textContent="▶ Play";return}
  if(ri===EVENTS.length-1) ri=0; $("#r-play").textContent="❚❚ Pause";
  timer=setInterval(()=>{ if(ri>=EVENTS.length-1){play();return} ri++; renderReplay() }, +$("#r-speed").value) }
function replay(){
  $("#t-replay").innerHTML=`<div class="card pad"><div class="controls">
   <button class="btn" id="r-first" onclick="ri=0;renderReplay()">⏮</button><button class="btn" id="r-prev" onclick="ri--;renderReplay()">◀ Step</button>
   <button class="btn primary" id="r-play" onclick="play()">▶ Play</button><button class="btn" id="r-next" onclick="ri++;renderReplay()">Step ▶</button>
   <button class="btn" onclick="ri=EVENTS.length-1;renderReplay()">⏭</button>
   <label class="small muted">Speed <select id="r-speed" class="btn" style="padding:4px 8px"><option value="1400">Slow</option><option value="700" selected>Normal</option><option value="250">Fast</option></select></label>
   <div class="progress"><i id="r-bar"></i></div></div>
   <p class="small muted" style="margin:10px 0 0">Every action the pipeline took, in order. Each one is a comment plus a description or status update (SOP Step 7). Click a card to open its issue.</p></div>
   <div class="replay"><div id="r-board"></div><div class="card pad now" id="r-now"></div></div>`;
  renderReplay();
}
addEventListener("keydown",e=>{ if(!$("#t-replay").classList.contains("on")||$("#drawer").classList.contains("on")) return;
  if(e.key==="ArrowRight"&&ri<EVENTS.length-1){ri++;renderReplay()} if(e.key==="ArrowLeft"&&ri>0){ri--;renderReplay()} if(e.key===" "){e.preventDefault();play()} });

// ---------------------------------------------------------------- agent & guardrails
function agent(){
  const rules=[["Never claim anything about Kestrel beyond the four approved claims","The model or rules write only the subject and opener. Product sentence, call to action and sign-off are inserted from config, word for word. Product, comparison and pricing words in the written parts are rejected."],
   ["Never state a prospect fact without a word-for-word source","Every quote must appear on the page it cites. Every number and proper noun in the opener must come from the source. The first sentence must carry the fact."],
   ["Never name another company","Blocklist of Kestrel customers, do-not-contact firms, other prospects and competitors, plus a check that rejects company-style names (Construction, LLC, Group…) other than the prospect's own."]];
  const pass=D.tests.filter(t=>t[0]==="PASS").length;
  $("#t-agent").innerHTML=`<div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(260px,1fr))">${rules.map(([t,d],i)=>`<div class="card pad rule"><div class="small muted">Guardrail ${i+1}</div><b>${t}</b><p class="small muted">${d}</p></div>`).join("")}</div>
  <h2>How the agent works</h2>
  <div class="card pad small"><ol style="margin:0;padding-left:18px">
   <li><b>Read the site:</b> homepage plus up to 7 internal pages, with About, Projects and Awards first. If a site blocks requests, a reader service is tried; if both fail, the firm is dropped.</li>
   <li><b>Segment and affiliates</b> (Step 2/3 inputs), each backed by a quote from the site.</li>
   <li><b>Do-not-contact:</b> exact name matching for the firm and every named affiliate, not fuzzy matching.</li>
   <li><b>Fact:</b> candidates are verified against their page. The best kind wins: named award, then named project, then founding year.</li>
   <li><b>Draft:</b> the written opener plus the fixed approved blocks. Guardrails and style checks run on every attempt; a rejected draft is regenerated, and after repeated failures there's no email.</li></ol>
   <p class="muted">Engine: <b>${esc(engineLabel)}</b>. With an OpenRouter key the same steps can use an LLM, and if the model is unavailable it falls back to the offline rules. The guardrails are identical either way.</p></div>
  <h2>Guardrail tests <span class="pill ok">${pass}/${D.tests.length} pass</span></h2>
  <div class="card tablewrap"><table><tbody>${D.tests.map(([r,n])=>`<tr style="cursor:default"><td style="width:70px"><span class="pill ${r==="PASS"?"ok":"bad"}">${r}</span></td><td class="small">${esc(n.replace(/^test_/,"").replace(/_/g," "))}</td></tr>`).join("")}</tbody></table></div>
  <h2>Drafts blocked during this run (${rejections.length} guardrail · ${styleRej.length} style)</h2>
  ${rejections.concat(styleRej).length?`<div class="card tablewrap"><table><thead><tr><th>Issue</th><th>Rejected opener</th><th>Why</th></tr></thead><tbody>${rejections.concat(styleRej).map(({p,t})=>`<tr onclick="openIssue('${p.id}','research')"><td class="muted">${p.id}</td><td class="small">${esc(t.opener)}</td><td class="small bad">${[...(t.violations||[]),...(t.style||[])].map(esc).join("<br>")}</td></tr>`).join("")}</tbody></table></div>`:'<p class="muted">No drafts were rejected in this run.</p>'}
  <h2>Human overrides (${overrides.length})</h2>
  ${overrides.map(({p,o})=>`<div class="card pad" style="margin-bottom:10px"><b>${p.id} · ${esc(p.firm)}</b><p class="small">${esc(o.reason)}</p>
   <div class="diff"><div class="before"><b class="small">Before (AI)</b><br>${esc(o.before.opener)}<div class="small muted">Subject: ${esc(o.before.subject)}</div></div>
   <div class="after"><b class="small">After (human, re-checked by the guardrails)</b><br>${esc(o.after.opener)}<div class="small muted">Subject: ${esc(o.after.subject)}</div></div></div></div>`).join("")||'<p class="muted">None.</p>'}
  <h2>Approved claims and do-not-contact list</h2>
  <div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(300px,1fr))"><div class="card pad small"><b>Approved claims</b><ul>${D.claims.map(c=>`<li>${esc(c)}</li>`).join("")}</ul>
   <b>Sign-off</b> ${D.sign_off_confirmed?"":'<span class="pill warn">placeholder, asked Nirbhay</span>'}<div class="quote">${esc(D.sign_off).replace("\n","<br>")}</div></div>
   <div class="card pad small"><b>Do-not-contact</b><ul>${D.dnc_list.map(d=>`<li><b>${esc(d.company)}</b>${d.include_affiliates?" and affiliates":""}: ${esc(d.reason)}</li>`).join("")}</ul></div></div>`;
}

// ---------------------------------------------------------------- brief & checklist
function checklist(){
  const issues=P, real=P.filter(p=>p.draft), mails=D.mails;
  const ev=(p,re)=>(p.history||[]).findIndex(h=>re.test(h.action));
  const all=(arr,f)=>arr.length>0&&arr.every(f);
  const daily=mails.find(m=>/^Kestrel Outbound Update /.test(m.subject));
  const sub=mails.find(m=>/^Kestrel Outbound Submission /.test(m.subject));
  const dailyLines=daily?daily.body.trim().split("\n"):[];
  const tmpl=["Firm:","Website:","Segment:","Do-not-contact check:","Fact:","Source URL:","Subject:","Body:","Status notes"];
  const partb=D.docs["Part B — What I would change about this SOP"]||"";
  const casco=P.find(p=>p.site_error), dncMatch=P.filter(p=>p.dnc&&p.dnc.result==="Match");
  const comments=P.flatMap(p=>p.comments||[]);
  const R=(req,ok,evidence,kind,go)=>({req,st:ok===null?"pending":ok?(kind||"pass"):"fail",evidence,go});
  const range=real.length?`${Math.min(...real.map(p=>p.draft.words))}–${Math.max(...real.map(p=>p.draft.words))}`:"";
  const kinds=Object.entries(real.reduce((a,p)=>(a[p.fact.kind]=(a[p.fact.kind]||0)+1,a),{})).map(([k,v])=>`${v} ${k==="founding"?"founding year":k}${v>1?"s":""}`).join(", ");
  const groups=[
   ["House rules",[
    R("No real emails, and nobody on the list gets contacted", true, `All ${mails.length} emails are sitting unsent in the outbox. The ten firms' websites were read, nothing more.`, "pass","outbox"),
    R("An agent does the heavy lifting", true, "It read every website, chose the facts and wrote the drafts. I reviewed the results and corrected one.", "pass","demo"),
    R("Questions asked before getting stuck", !!mails.find(m=>/clarifying/i.test(m.subject)), "Five questions to Nirbhay: the missing sign-off, the dead website, how strictly to match names, which numbers are allowed, and when tickets can be assigned.", "sim","outbox"),
    R("The process is followed even where I'd do it differently", !!partb, "Every step was done in the given order. My objections are written up in Part B rather than acted on.", "pass","docs"),
    R("Time spent", !!D.time_taken, esc(D.time_taken||"not filled in"), "pass")]],
   ["Setting up the workspace",[
    R("A place to track the work", D.workspace.project==="Kestrel Outbound", `A team called “${esc(D.workspace.team)}” with a project called “${esc(D.workspace.project)}”. It lives in a local stand-in for Linear.`, "sim","board"),
    R("Nirbhay can see it", D.workspace.invites.includes(D.approver_email), `An invite went to ${esc(D.approver_email)}. Accepting it is simulated, so tickets can be handed over.`, "sim"),
    R("Labels for segment, source and approval", all(D.required_labels,l=>D.workspace.labels.includes(l)), labels(D.required_labels)),
    R("The right ticket stages", all(D.required_statuses,s=>D.workspace.statuses.includes(s)), `${D.required_statuses.map(sChip).join("")} “In Review” didn't exist yet, so it was added.`)]],
   ["One ticket for each firm",[
    R("Ten firms, ten tickets, all starting in Todo", issues.length===D.brief_prospects.length&&all(issues,p=>(p.history[0]||{}).status==="Todo"), `${issues.length} tickets, each one opened in Todo.`, "pass","board"),
    R("Every title reads the same way", all(issues,p=>/^.+ — .+ \| Outbound( \| DROPPED)?$/.test(p.title)), `For example, “${esc(issues[0].title)}”. Closed tickets end with “| DROPPED”.`),
    R("Every ticket uses the same layout", all(issues,p=>tmpl.every(f=>p.description.includes(f))), "Firm, website, segment, the do-not-contact result, the fact and its source, the draft, and a one-line status. Nothing is left out."),
    R("Each ticket says what kind of firm it is and where it came from", all(issues.filter(p=>!p.site_error),p=>p.labels.includes("Source: Brief")&&p.labels.some(l=>l.startsWith("Segment:"))), `Each segment is chosen from the firm's own site, and the sentence that proves it is kept.${casco?` ${esc(casco.firm)} has no segment, because there is no site to read.`:""}`)]],
   ["Checking who is off-limits",[
    R("The check happens before any research", all(issues,p=>{const d=ev(p,/^Do-not-contact/), r=ev(p,/^Research/); return d>=0&&(r<0||d<r)}), "On every ticket, the do-not-contact check is logged before any research starts."),
    R("Off-limits firms are stopped, with the reason written down", all(dncMatch,p=>p.status==="Canceled"&&p.title.endsWith("| DROPPED")&&!p.fact&&!p.draft), dncMatch.map(p=>`${esc(p.firm)}'s homepage says it belongs to ${esc(p.dnc.company)}, which is already a Kestrel customer. The ticket was closed, and nothing was researched or written.`).join(" "), "pass", dncMatch[0]&&("issue:"+dncMatch[0].id))]],
   ["Finding something real to say",[
    R("Research only starts once a ticket is marked as being worked on", all(issues,p=>{const i=ev(p,/^Moved to In Progress/), r=ev(p,/^Research/); return r<0||(i>=0&&i<r)}), "Every researched ticket moved to In Progress first."),
    R("One concrete fact per firm", all(real,p=>!!p.fact), `${kinds}. Awards win over projects, and projects win over founding years.`),
    R("Every fact can be traced back to its page", all(real,p=>p.fact.url&&p.fact.url.startsWith("http")), "Before a fact is used, its quote is matched word for word against the page it came from. Anything that doesn't match is thrown away."),
    R("A dead website closes the ticket instead of being swapped for another firm", casco? casco.status==="Canceled"&&casco.title.endsWith("| DROPPED"):true, casco?`${esc(casco.firm)}'s domain isn't registered. The ticket was closed, and no other firm was put in its place.`:"Every website loaded.", "pass", casco&&("issue:"+casco.id))]],
   ["Writing the email",[
    R("Short, and it leads with the fact", all(real,p=>p.draft.words<=D.max_words), `Between ${range} words, against a limit of ${D.max_words}. The first sentence is always the fact.`),
    R("Nothing about Kestrel that the client hasn't approved", all(real,p=>p.draft.body.includes(D.email_blocks.product)&&p.draft.body.includes(D.email_blocks.cta)), "The product lines are pasted in from the approved list and never reworded. Automatic checks catch anything else.", "pass","agent"),
    R("Signed the same way every time", all(real,p=>p.draft.body.trim().endsWith(D.sign_off.trim())), D.sign_off_confirmed?"Uses the confirmed sign-off.":"The brief never says what Kestrel's sign-off is. A placeholder is used everywhere, and I've asked Nirbhay for the real one.", D.sign_off_confirmed?"pass":"sim"),
    R("The draft sits on its ticket", all(real,p=>p.description.includes(p.draft.subject)), "Subject and body are in each ticket's description.")]],
   ["Handing over for approval",[
    R("Finished drafts go to Nirbhay", all(real,p=>p.status==="In Review"&&p.labels.includes("Ready for Approval")&&p.assignee), `All ${real.length} drafts are in review, labelled ready, and assigned to Nirbhay.`, "pass","board"),
    R("Only Nirbhay closes a ticket as done", !P.some(p=>p.status==="Done"||(p.history||[]).some(h=>h.status==="Done")), "Nothing was marked Done. That's Nirbhay's call.")]],
   ["Leaving a trail",[
    R("Every action leaves a note with a link and changes the ticket", comments.length>0&&comments.every(c=>/https?:\/\//.test(c.body)), `${comments.length} notes, each with a link and each paired with a change to the ticket. You can watch them happen in the replay.`, "pass","replay")]],
   ["End-of-day update",[
    R("A short note to Nirbhay at the end of the day", !!daily, daily?`Subject: “${esc(daily.subject)}”`:"missing", "sim","outbox"),
    R("Three lines: what's done, what's stuck, what needs a decision", dailyLines.length===3&&/^Done: /.test(dailyLines[0])&&/^Blocked: /.test(dailyLines[1])&&/^Needs your call: /.test(dailyLines[2]), "Exactly three lines, nothing else.")]],
   ["Wrapping up",[
    R("A status update on the project", !!(D.project_updates[0]&&D.project_updates[0].health), D.project_updates[0]?`Marked “on track”, with a short summary.`:"missing", "pass","overview"),
    R("A handover email with every link in it", !!sub, sub?`Subject: “${esc(sub.subject)}”`:"missing", "sim","outbox")]],
   ["What gets handed in",[
    R("The workspace with all ten tickets", issues.length===10, "This page: the Board tab, and the copy in the repo.", "sim","board"),
    R("The agent, and how to run it on any firm", !!D.agent_demo, D.agent_demo?`Code and instructions are in the repo. It was tried on ${esc(D.agent_demo.firm)}, a firm that isn't on the list.`:"agent.py", "pass","demo"),
    R("The guardrail note", !!D.docs["Guardrail note"], "Three things the agent may never say, and how the code stops each one before a human ever sees the draft.", "pass","docs"),
    R("Part B: what I'd change about the process", !!partb && partb.split(/\s+/).length<=650, partb?`About one page (${partb.split(/\s+/).length} words).`:"missing", "pass","docs"),
    R("The video walkthrough", null, "Recorded separately.")]],
  ];
  const ICON={pass:'<span class="pill ok">✓ Done</span>',sim:'<span class="pill warn">✓ Done (simulated)</span>',fail:'<span class="pill bad">✗ Missing</span>',pending:'<span class="pill">Separate</span>'};
  const rows=groups.flatMap(g=>g[1]); const n=k=>rows.filter(r=>r.st===k).length;
  $("#t-checklist").innerHTML=`
  <div class="grid k6"><div class="card pad kpi"><div class="v">${rows.length}</div><div class="l">Things asked for</div></div>
   <div class="card pad kpi"><div class="v ok">${n("pass")}</div><div class="l">Done</div></div><div class="card pad kpi"><div class="v warn">${n("sim")}</div><div class="l">Done, in the simulation</div></div>
   <div class="card pad kpi"><div class="v bad">${n("fail")}</div><div class="l">Missing</div></div><div class="card pad kpi"><div class="v">${n("pending")}</div><div class="l">Sent separately (the video)</div></div>
   <div class="card pad kpi"><div class="v">${esc(D.time_taken||"—")}</div><div class="l">Time taken</div></div></div>
  <p class="small muted">Nothing here is ticked by hand: each line is worked out from the run itself, so if something broke it would show up red. “Simulated” means it happened in the local stand-in for Linear and email, not the real services. Click a line to jump to the proof.</p>
  ${groups.map(([g,rs])=>`<h2>${g}</h2><div class="card tablewrap"><table><tbody>${rs.map(r=>`<tr ${r.go?`onclick="go('${r.go}')"`:'style="cursor:default"'}><td style="width:150px">${ICON[r.st]}</td><td style="width:42%"><b class="small">${esc(r.req)}</b></td><td class="small muted">${r.evidence}</td></tr>`).join("")}</tbody></table></div>`).join("")}
  <h2>The job, in short</h2>
  <div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(300px,1fr))">
   <div class="card pad small"><b>Who we're writing for: Kestrel Rooms</b><p class="muted">Small design studios constantly juggle the same shared things: the meeting room, the model shop, the big plotter and the space where clients come to see work. Kestrel puts all of them on one calendar.</p>
    <b>What the emails are allowed to say about Kestrel</b><p class="muted">These four lines are quoted exactly as the client approved them, so they are never reworded.</p><ul>${D.claims.map(c=>`<li>${esc(c)}</li>`).join("")}</ul><b>What we ask for:</b> a quick call, or a go at the free trial.</div>
   <div class="card pad small"><b>Firms we must leave alone</b><ul>${D.dnc_list.map(d=>`<li><b>${esc(d.company)}</b>${d.include_affiliates?" and all affiliates":""}: ${esc(d.reason)}</li>`).join("")}</ul></div></div>
  <h3>The ten firms</h3><div class="card tablewrap"><table><thead><tr><th>#</th><th>Firm</th><th>City</th><th>Website</th><th>Outcome</th></tr></thead><tbody>
   ${D.brief_prospects.map(b=>{const p=P.find(x=>x.n===b.n);return `<tr onclick="openIssue('${p.id}')"><td>${b.n}</td><td>${esc(b.firm)}</td><td>${esc(b.city)}</td><td><a href="${esc(b.website)}" target="_blank" onclick="event.stopPropagation()">${esc(b.website)}</a></td><td>${sChip(p.status)}</td></tr>`}).join("")}</tbody></table></div>`;
}
function go(t){ if(t.startsWith("issue:")) openIssue(t.slice(6)); else { show(t); scrollTo(0,0) } }

// ---------------------------------------------------------------- agent demo (new firm)
function demo(){
  const d=D.agent_demo;
  if(!d){ $("#t-demo").innerHTML='<p class="muted">No recorded demo. Run ./demo/record_agent_demo.sh</p>'; return }
  const ft=(d.fact_trail||[]).filter(t=>"fact" in t), dt=d.draft_trail||[];
  const box=(n,t,b)=>`<div class="card pad step" style="margin-bottom:10px"><span class="num">${n}</span><div style="min-width:0;flex:1"><span class="st">${t}</span>${b}</div></div>`;
  $("#t-demo").innerHTML=`<div class="card pad"><b>Does it work on a firm it has never seen?</b> To show the agent isn't tuned to the ten firms on the list, here it is on <b>${esc(d.firm)}</b>, a firm that isn't on the list. It runs in a few seconds, needs no API key, and you can repeat it with <code>./demo/record_agent_demo.sh</code>.
   <div style="margin-top:8px">Result: <span class="pill ${d.result==="READY"?"ok":"bad"}">${d.result==="READY"?"Draft ready for approval":esc(d.result)}</span></div></div>
  <h2>What it did, in order</h2>
  ${box(1,`Read the website (${(d.pages_read||[]).length} pages, most useful first)`,`<ul class="small">${(d.pages_read||[]).map(p=>`<li><a href="${esc(p.url)}" target="_blank">${esc(p.url)}</a> <span class="muted">(${esc(p.via)})</span></li>`).join("")}</ul>`)}
  ${box(2,`Decided what kind of work they do: ${esc(d.profile?.segment)}`,`<div class="small muted">${esc(d.profile?.segment_reason)}</div><div class="quote">“${esc(d.profile?.segment_quote)}”<br><a href="${esc(d.profile?.segment_url)}" target="_blank">${esc(d.profile?.segment_url)}</a></div>`)}
  ${box(3,`Checked they're not off-limits: <span class="${d.dnc?.result==="Match"?"bad":"ok"}">${esc(d.dnc?.result)}</span>`,`<p class="small muted">${esc(d.dnc?.detail)}</p>`)}
  ${box(4,"Looked for one real fact, and checked it against the page",`<table><tbody>${ft.map(t=>`<tr style="cursor:default"><td style="width:90px"><span class="pill ${t.verified?'ok':'bad'}">${t.verified?'verified':'discarded'}</span></td><td class="small"><span class="muted">${esc(t.kind)}</span> ${esc(t.fact)}</td></tr>`).join("")}</tbody></table>
     ${d.fact?`<p class="small"><b>Chosen:</b> ${esc(d.fact.fact)}</p><div class="quote">“${esc(d.fact.quote)}”<br><a href="${esc(d.fact.url)}" target="_blank">${esc(d.fact.url)}</a></div>`:""}`)}
  ${box(5,"Wrote the email, then ran the safety checks",`${dt.map(t=>{const e=[...(t.violations||[]),...(t.style||[])];return `<div class="small" style="margin:6px 0"><span class="pill ${e.length?'bad':'ok'}">attempt ${t.attempt}: ${e.length?'rejected':'accepted'}</span> ${esc(t.opener)}${e.length?`<div class="bad">${e.map(esc).join("<br>")}</div>`:""}</div>`}).join("")}
     ${d.draft?`<div style="margin-top:10px">${emailHTML({firm:d.firm,draft:d.draft,status_note:""})}</div>`:""}`)}
  <h2>Try it yourself</h2><div class="card pad small"><pre>git clone https://github.com/gpcoolc12-wq/kestrel-outbound.git && cd kestrel-outbound
./demo/run_demo.sh                       # whole SOP, all 10 prospects (no key, no internet)
.venv/bin/python agent.py --firm "Any Studio" --url https://any-studio.com --city "Any City"   # new firm (internet, no key)</pre></div>`;
}

// ---------------------------------------------------------------- outbox / docs
function listDetail(sel, items, title, sub, body){
  let i=0; const el=$(sel);
  const draw=()=>{ el.innerHTML=`<div class="split"><div class="card list">${items.map((x,k)=>`<button aria-selected="${k===i}" data-k="${k}"><b class="small">${esc(title(x))}</b><div class="small muted">${esc(sub(x))}</div></button>`).join("")}</div>
    <div class="card pad">${body(items[i])}</div></div>`;
    el.querySelectorAll(".list button").forEach(b=>b.onclick=()=>{i=+b.dataset.k;draw()}) };
  draw();
}
function outbox(){
  listDetail("#t-outbox", D.mails, m=>m.subject, m=>"to "+m.to,
    m=>`<p class="small muted"><span class="pill warn">Not sent: demo outbox</span> ${esc(m.file)}</p><div class="mail"><div class="mailh"><b>From:</b> ${esc(m.from)}<br><b>To:</b> ${esc(m.to)}<br><b>Subject:</b> ${esc(m.subject)}<br><b>Date:</b> ${esc(m.date)}</div><div class="mailb">${esc(m.body)}</div></div>`);
}
function docs(){
  const items=Object.entries(D.docs);
  listDetail("#t-docs", items, x=>x[0], x=>x[0].startsWith("Clarifying")?"email draft":"Linear project document", x=>`<h2 style="margin-top:0">${esc(x[0])}</h2>${md(x[1])}`);
}

overview(); board(); replay(); agent(); outbox(); docs(); checklist(); demo();
let start="overview"; try{start=localStorage.getItem("kes-tab")||start}catch(e){}
if(location.hash&&TABS.some(t=>"#"+t[0]===location.hash)) start=location.hash.slice(1);
show(start);
addEventListener("hashchange",()=>{ const k=location.hash.slice(1); if(TABS.some(t=>t[0]===k)) show(k) });
</script></body></html>"""


def build():
    data = json.dumps(load(), ensure_ascii=False).replace("</", "<\\/")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(PAGE.replace("__DATA__", data))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    build()
