#!/usr/bin/env python3
"""Validate every Linear GraphQL call in kestrel/backends.py against Linear's published schema,
without needing an API key: query syntax, fields, argument types, and the input objects/enum
values the pipeline sends.

  .venv/bin/pip install graphql-core && .venv/bin/python tools/check_linear_api.py
"""
import re
import sys
from pathlib import Path

import requests
from graphql import build_schema, parse, validate
from graphql.type import GraphQLEnumType, GraphQLInputObjectType, GraphQLList, GraphQLNonNull

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_URL = "https://raw.githubusercontent.com/linear/linear/master/packages/sdk/src/schema.graphql"
schema = build_schema(requests.get(SCHEMA_URL, timeout=60).text)
src = (ROOT / "kestrel/backends.py").read_text()

ok = True
queries = re.findall(r"self\.gql\(\s*(['\"])(.+?)\1", src, re.S)
for _, q in queries:
    errs = validate(schema, parse(q))
    print(("FAIL " if errs else "ok   ") + re.sub(r"\s+", " ", q)[:90])
    for e in errs:
        ok = False
        print("     ", e.message)


def unwrap(t):
    while isinstance(t, (GraphQLNonNull, GraphQLList)):
        t = t.of_type
    return t


# Input objects the pipeline builds: (input type, fields sent, {field: enum value sent})
INPUTS = [
    ("ProjectCreateInput", ["name", "teamIds"], {}),
    ("IssueLabelCreateInput", ["name", "teamId", "color"], {}),
    ("WorkflowStateCreateInput", ["name", "type", "teamId", "color"], {}),
    ("OrganizationInviteCreateInput", ["email", "role", "teamIds"], {"role": "user"}),
    ("IssueCreateInput", ["teamId", "projectId", "title", "description", "stateId", "labelIds"], {}),
    ("IssueUpdateInput", ["title", "description", "stateId", "labelIds", "assigneeId"], {}),
    ("CommentCreateInput", ["issueId", "body"], {}),
    ("DocumentCreateInput", ["title", "content", "projectId"], {}),
    ("DocumentUpdateInput", ["content"], {}),
    ("ProjectUpdateCreateInput", ["projectId", "body", "health"], {"health": "onTrack"}),
]
for name, fields, enums in INPUTS:
    t = schema.get_type(name)
    if not isinstance(t, GraphQLInputObjectType):
        print(f"FAIL input type {name} missing"); ok = False; continue
    missing = [f for f in fields if f not in t.fields]
    bad = []
    for f, v in enums.items():
        et = unwrap(t.fields[f].type) if f in t.fields else None
        if isinstance(et, GraphQLEnumType) and v not in et.values:
            bad.append(f"{f}={v} (allowed: {list(et.values)})")
    print(("FAIL " if missing or bad else "ok   ") + f"{name} {fields}" + (f" missing={missing}" if missing else "")
          + (f" bad={bad}" if bad else ""))
    ok = ok and not missing and not bad

# Workflow state types and project health values used in config / CLI
st = unwrap(schema.get_type("WorkflowStateCreateInput").fields["type"].type)
print("     WorkflowState.type is", st, "- config uses unstarted/started/completed/canceled")
hl = unwrap(schema.get_type("ProjectUpdateCreateInput").fields["health"].type)
print("     health values:", list(getattr(hl, "values", {}) or []))
sys.exit(0 if ok else 1)
