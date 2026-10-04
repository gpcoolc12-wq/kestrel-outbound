"""Proves a real-Linear `run` reuses the reviewed local simulation exactly, with no model calls.

The Linear backend is swapped for a throwaway file backend and the OpenRouter key is removed,
so any attempt to research or draft again would fail loudly.
Needs a finished local simulation (state/local.json). Run: .venv/bin/python tests/test_reuse_offline.py
"""
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    local_state = ROOT / "state" / "local.json"
    if not local_state.exists():
        print("SKIP: run ./simulate.sh first")
        return 0
    import run_sop
    from kestrel import llm
    from kestrel.backends import LocalBackend

    tmp = Path(tempfile.mkdtemp())
    real_state = ROOT / "state" / "linear.json"
    backup = real_state.read_bytes() if real_state.exists() else None
    try:
        run_sop.LinearBackend = lambda cfg: LocalBackend(cfg, root=str(tmp / "linear"))
        os.environ["OPENROUTER_API_KEY"] = ""
        boom = lambda *a, **k: (_ for _ in ()).throw(AssertionError("model was called"))  # noqa: E731
        llm.chat_json = run_sop.A.chat_json = boom
        r = run_sop.Run(local=False)
        r.state_path = tmp / "linear.json"
        r.state = {"prospects": {}}
        r.setup(invite=True)
        r.run()
        seed = json.loads(local_state.read_text())["prospects"]
        fails = 0
        for n, rec in r.state["prospects"].items():
            s = seed[n]
            same = (rec["status"] == s["status"] or (s["status"] == "In Review" and rec["status"] == "In Review")) \
                and rec.get("fact") == s.get("fact") and (rec.get("draft") or {}).get("body") == (s.get("draft") or {}).get("body") \
                and rec["labels"][:2] == s["labels"][:2]
            n_comments = len(r.be.ws["issues"][rec["identifier"]]["comments"])
            print(("PASS" if same else "FAIL"), rec["identifier"], rec["status"], f"{n_comments} comments")
            fails += not same
        return fails
    finally:
        if backup is not None:
            real_state.write_bytes(backup)
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
