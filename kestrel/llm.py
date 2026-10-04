"""Thin OpenRouter client that always returns parsed JSON.

OPENROUTER_MODEL may be a comma-separated fallback chain. A model that is out of
credits (402), rate-limited (429), down (5xx) or returns no JSON is skipped for the
next one, so the agent keeps working on a free-tier key.
"""
from __future__ import annotations

import json
import os
import re
import time

import requests

DEFAULT_CHAIN = ("anthropic/claude-sonnet-5.5,nvidia/nemotron-3-ultra-550b-a55b:free,"
                 "nvidia/nemotron-3-super-120b-a12b:free,poolside/laguna-s-2.1:free")
_dead: set[str] = set()  # models that returned 402/403 this run; don't retry them
last_model = ""


def _extract(content: str) -> dict | None:
    content = re.sub(r"<think>.*?</think>", "", content or "", flags=re.S)
    content = re.sub(r"^```(?:json)?|```$", "", content.strip(), flags=re.M)
    for m in sorted(re.finditer(r"\{.*\}", content, re.S), key=lambda m: -len(m.group(0))):
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            continue
    return None


def chat_json(system: str, user: str, temperature: float = 0.2) -> dict:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is not set (see .env.example)")
    chain = [m.strip() for m in (os.environ.get("OPENROUTER_MODEL") or DEFAULT_CHAIN).split(",") if m.strip()]
    errors = []
    for rnd in range(ROUNDS):
        if rnd:
            time.sleep(30 * rnd)  # every model was rate-limited; free tiers recover within a minute or two
        out = _try_chain(chain, key, system, user, temperature, errors)
        if out is not None:
            return out
    raise RuntimeError("all models failed: " + "; ".join(errors[-6:]))


ROUNDS = 4


def _try_chain(chain, key, system, user, temperature, errors):
    global last_model
    for model in chain:
        if model in _dead:
            continue
        for attempt in range(3):
            try:
                r = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {key}", "X-Title": "Kestrel Outbound Agent"},
                    json={"model": model, "temperature": temperature, "max_tokens": 4000,
                          "response_format": {"type": "json_object"},
                          "messages": [{"role": "system", "content": system + "\nRespond with one JSON object only."},
                                       {"role": "user", "content": user}]},
                    timeout=240,
                )
            except requests.RequestException as e:
                errors.append(f"{model}: {e}")
                continue
            if r.status_code in (402, 403):
                _dead.add(model)
                errors.append(f"{model}: {r.status_code}")
                break
            if r.status_code == 429 or r.status_code >= 500:
                errors.append(f"{model}: {r.status_code}")
                time.sleep(4 * (attempt + 1))
                continue
            if r.status_code != 200:
                errors.append(f"{model}: {r.status_code} {r.text[:120]}")
                break
            msg = (r.json().get("choices") or [{}])[0].get("message", {})
            out = _extract(msg.get("content") or "")
            if out is not None:
                last_model = model
                return out
            errors.append(f"{model}: no JSON in reply")
    return None
