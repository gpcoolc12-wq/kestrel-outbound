"""Two interchangeable backends for the SOP pipeline.

LinearBackend - the real thing, via Linear's GraphQL API (needs LINEAR_API_KEY).
LocalBackend  - a file-based stand-in with the same operations, so anyone can run the
                whole SOP without a Linear workspace. Writes local_linear/.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import requests

COLORS = {"Segment: Residential": "#4CB782", "Segment: Commercial": "#4EA7FC", "Segment: Mixed": "#F2C94C",
          "Source: Brief": "#95A2B3", "Ready for Approval": "#EB5757"}
STATE_COLORS = {"unstarted": "#E2E2E2", "started": "#F2C94C", "completed": "#5E6AD2", "canceled": "#95A2B3"}


class LinearBackend:
    name = "linear"

    def __init__(self, cfg: dict):
        self.key = os.environ.get("LINEAR_API_KEY")
        if not self.key:
            raise RuntimeError("LINEAR_API_KEY is not set")
        self.cfg = cfg["linear"]
        self.team_id = self.project_id = self.project_url = None
        self.labels: dict[str, str] = {}
        self.states: dict[str, str] = {}

    def gql(self, query: str, variables: dict | None = None) -> dict:
        r = requests.post("https://api.linear.app/graphql", json={"query": query, "variables": variables or {}},
                          headers={"Authorization": self.key, "Content-Type": "application/json"}, timeout=60)
        data = r.json()
        if r.status_code != 200 or data.get("errors"):
            raise RuntimeError(f"Linear API error: {data.get('errors') or r.text[:300]}")
        return data["data"]

    # ---------------------------------------------------------------- Step 1
    def setup(self, log) -> dict:
        teams = self.gql("{ teams { nodes { id key name } } }")["teams"]["nodes"]
        if not teams:
            raise RuntimeError("Workspace has no team. Create one in Linear first.")
        if len(teams) > 1:
            log(f"note: workspace has {len(teams)} teams; using the first: {teams[0]['name']}")
        team = teams[0]
        self.team_id = team["id"]

        proj = self.gql('query($n:String!){ projects(filter:{name:{eq:$n}}){ nodes { id url } } }',
                        {"n": self.cfg["project"]})["projects"]["nodes"]
        if proj:
            self.project_id, self.project_url = proj[0]["id"], proj[0]["url"]
            log(f"project exists: {self.project_url}")
        else:
            p = self.gql('mutation($i:ProjectCreateInput!){ projectCreate(input:$i){ project { id url } } }',
                         {"i": {"name": self.cfg["project"], "teamIds": [self.team_id]}})["projectCreate"]["project"]
            self.project_id, self.project_url = p["id"], p["url"]
            log(f"created project: {self.project_url}")

        existing = self.gql('query($t:String!){ team(id:$t){ labels(first:250){ nodes { id name } } } }',
                            {"t": self.team_id})["team"]["labels"]["nodes"]
        ws = self.gql('{ issueLabels(first:250){ nodes { id name team { id } } } }')["issueLabels"]["nodes"]
        have = {l["name"]: l["id"] for l in existing}
        have.update({l["name"]: l["id"] for l in ws if l["team"] is None})
        for name in self.cfg["labels"]:
            if name in have:
                self.labels[name] = have[name]
                continue
            l = self.gql('mutation($i:IssueLabelCreateInput!){ issueLabelCreate(input:$i){ issueLabel { id } } }',
                         {"i": {"name": name, "teamId": self.team_id, "color": COLORS.get(name, "#95A2B3")}})
            self.labels[name] = l["issueLabelCreate"]["issueLabel"]["id"]
            log(f"created label: {name}")

        states = self.gql('query($t:String!){ team(id:$t){ states { nodes { id name type } } } }',
                          {"t": self.team_id})["team"]["states"]["nodes"]
        have_s = {s["name"]: s["id"] for s in states}
        for name, typ in self.cfg["statuses"].items():
            if name in have_s:
                self.states[name] = have_s[name]
                continue
            s = self.gql('mutation($i:WorkflowStateCreateInput!){ workflowStateCreate(input:$i){ workflowState { id } } }',
                         {"i": {"name": name, "type": typ, "teamId": self.team_id, "color": STATE_COLORS[typ]}})
            self.states[name] = s["workflowStateCreate"]["workflowState"]["id"]
            log(f"created status: {name}")
        return {"team": team["name"], "project_url": self.project_url}

    def invite(self, email: str, log) -> None:
        pending = self.gql("{ organizationInvites { nodes { email acceptedAt } } }")["organizationInvites"]["nodes"]
        if self.find_user(email) or any(i["email"].lower() == email.lower() for i in pending):
            log(f"{email} already a member or invited")
            return
        self.gql('mutation($i:OrganizationInviteCreateInput!){ organizationInviteCreate(input:$i){ success } }',
                 {"i": {"email": email, "role": "user", "teamIds": [self.team_id]}})
        log(f"invited {email}")

    def find_user(self, email: str) -> str | None:
        u = self.gql('query($e:String!){ users(filter:{email:{eq:$e}}){ nodes { id active } } }', {"e": email})
        nodes = [n for n in u["users"]["nodes"] if n["active"]]
        return nodes[0]["id"] if nodes else None

    # ---------------------------------------------------------------- issues
    def create_issue(self, title, description, state, labels) -> dict:
        i = self.gql('mutation($i:IssueCreateInput!){ issueCreate(input:$i){ issue { id identifier url } } }',
                     {"i": {"teamId": self.team_id, "projectId": self.project_id, "title": title,
                            "description": description, "stateId": self.states[state],
                            "labelIds": [self.labels[l] for l in labels]}})
        return i["issueCreate"]["issue"]

    def update_issue(self, issue_id, *, title=None, description=None, state=None, labels=None, assignee_id=None):
        inp = {}
        if title is not None:
            inp["title"] = title
        if description is not None:
            inp["description"] = description
        if state is not None:
            inp["stateId"] = self.states[state]
        if labels is not None:
            inp["labelIds"] = [self.labels[l] for l in labels]
        if assignee_id is not None:
            inp["assigneeId"] = assignee_id
        self.gql('mutation($id:String!,$i:IssueUpdateInput!){ issueUpdate(id:$id,input:$i){ success } }',
                 {"id": issue_id, "i": inp})

    def comment(self, issue_id, body) -> None:
        self.gql('mutation($i:CommentCreateInput!){ commentCreate(input:$i){ success } }',
                 {"i": {"issueId": issue_id, "body": body}})

    # ---------------------------------------------------------------- project
    def create_document(self, title, content) -> str:
        docs = self.gql('query($p:String!){ project(id:$p){ documents { nodes { id title url } } } }',
                        {"p": self.project_id})["project"]["documents"]["nodes"]
        for d in docs:
            if d["title"] == title:
                self.gql('mutation($id:String!,$i:DocumentUpdateInput!){ documentUpdate(id:$id,input:$i){ success } }',
                         {"id": d["id"], "i": {"content": content}})
                return d["url"]
        d = self.gql('mutation($i:DocumentCreateInput!){ documentCreate(input:$i){ document { url } } }',
                     {"i": {"title": title, "content": content, "projectId": self.project_id}})
        return d["documentCreate"]["document"]["url"]

    def project_update(self, body, health) -> str:
        p = self.gql('mutation($i:ProjectUpdateCreateInput!){ projectUpdateCreate(input:$i){ projectUpdate { url } } }',
                     {"i": {"projectId": self.project_id, "body": body, "health": health}})
        return p["projectUpdateCreate"]["projectUpdate"]["url"]


class LocalBackend:
    """Same operations as LinearBackend, persisted to local_linear/workspace.json and
    rendered to Markdown so the result can be read like a Linear board."""
    name = "local"

    def __init__(self, cfg: dict, root: str = "local_linear"):
        self.cfg = cfg["linear"]
        self.root = Path(root)
        self.path = self.root / "workspace.json"
        self.ws = json.loads(self.path.read_text()) if self.path.exists() else {
            "team": "Kestrel", "members": ["you"], "invites": [], "project": None, "labels": [], "statuses":
            ["Backlog", "Todo", "In Progress", "Done", "Canceled"], "issues": {}, "documents": {}, "project_updates": []}
        self.project_url = "local_linear/BOARD.md"

    def _now(self):
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    def _save(self):
        self.root.mkdir(exist_ok=True)
        self.path.write_text(json.dumps(self.ws, indent=2))
        self._render()

    def setup(self, log) -> dict:
        if not self.ws["project"]:
            self.ws["project"] = self.cfg["project"]
            log(f"created project: {self.cfg['project']}")
        for l in self.cfg["labels"]:
            if l not in self.ws["labels"]:
                self.ws["labels"].append(l)
                log(f"created label: {l}")
        for s in self.cfg["statuses"]:
            if s not in self.ws["statuses"]:
                self.ws["statuses"].append(s)
                log(f"created status: {s}")
        self._save()
        return {"team": self.ws["team"], "project_url": self.project_url}

    def invite(self, email, log):
        if email not in self.ws["invites"]:
            self.ws["invites"].append(email)
            log(f"invited {email} (local stand-in: no email is sent)")
        self._save()

    def accept_invite(self, email, log):
        """SIMULATION of the invitee's own action (accepting the emailed invite)."""
        if email not in self.ws["invites"]:
            raise SystemExit(f"{email} was never invited; run setup --invite first")
        if email not in self.ws["members"]:
            self.ws["members"].append(email)
            log(f"[simulated] {email} accepted the invite and joined the workspace")
        self._save()

    def find_user(self, email):
        return email if email in self.ws["members"] else None

    def create_issue(self, title, description, state, labels):
        n = len(self.ws["issues"]) + 1
        ident = f"KES-{n}"
        self.ws["issues"][ident] = {"id": ident, "identifier": ident, "url": f"local_linear/issues/{ident}.md",
                                    "title": title, "description": description, "state": state,
                                    "labels": list(labels), "assignee": None, "comments": [], "history": []}
        self._save()
        return self.ws["issues"][ident]

    def update_issue(self, issue_id, *, title=None, description=None, state=None, labels=None, assignee_id=None):
        i = self.ws["issues"][issue_id]
        for k, v in (("title", title), ("description", description), ("state", state), ("labels", labels),
                     ("assignee", assignee_id)):
            if v is not None:
                if k in ("state", "title", "assignee", "labels") and i[k] != v:
                    i["history"].append(f"{self._now()} {k}: {i[k]} -> {v}")
                i[k] = v
        self._save()

    def comment(self, issue_id, body):
        self.ws["issues"][issue_id]["comments"].append({"at": self._now(), "body": body})
        self._save()

    def create_document(self, title, content):
        self.ws["documents"][title] = content
        self._save()
        return f"local_linear/docs/{re.sub(r'[^A-Za-z0-9]+', '_', title)}.md"

    def project_update(self, body, health):
        self.ws["project_updates"].append({"at": self._now(), "health": health, "body": body})
        self._save()
        return "local_linear/BOARD.md#project-updates"

    def _render(self):
        (self.root / "issues").mkdir(parents=True, exist_ok=True)
        (self.root / "docs").mkdir(exist_ok=True)
        lines = [f"# {self.ws['project'] or '(no project)'} — local Linear stand-in", "",
                 f"Team: {self.ws['team']} · Members: {', '.join(self.ws['members'])} · "
                 f"Invited: {', '.join(self.ws['invites']) or '—'}",
                 f"Labels: {', '.join(self.ws['labels'])}", f"Statuses: {', '.join(self.ws['statuses'])}", "",
                 "| Issue | Title | Status | Labels | Assignee |", "|---|---|---|---|---|"]
        for i in self.ws["issues"].values():
            lines.append(f"| [{i['identifier']}](issues/{i['identifier']}.md) | {i['title']} | {i['state']} | "
                         f"{', '.join(i['labels'])} | {i['assignee'] or '—'} |")
            md = [f"# {i['identifier']} · {i['title']}", "",
                  f"**Status:** {i['state']} · **Labels:** {', '.join(i['labels'])} · **Assignee:** {i['assignee'] or '—'}",
                  "", "---", "", i["description"], "", "---", "", "## Activity", ""]
            md += [f"- {h}" for h in i["history"]]
            md += ["", "## Comments", ""]
            for c in i["comments"]:
                md += [f"**{c['at']}**", "", c["body"], ""]
            (self.root / "issues" / f"{i['identifier']}.md").write_text("\n".join(md))
        if self.ws["documents"]:
            lines += ["", "## Documents", ""]
            for t, c in self.ws["documents"].items():
                f = re.sub(r"[^A-Za-z0-9]+", "_", t) + ".md"
                (self.root / "docs" / f).write_text(f"# {t}\n\n{c}")
                lines.append(f"- [{t}](docs/{f})")
        if self.ws["project_updates"]:
            lines += ["", "## Project updates", ""]
            for u in self.ws["project_updates"]:
                lines += [f"**{u['at']} · health: {u['health']}**", "", u["body"], ""]
        (self.root / "BOARD.md").write_text("\n".join(lines))
