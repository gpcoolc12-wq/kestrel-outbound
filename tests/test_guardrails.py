"""Offline tests: each guardrail must block its violation and pass a clean draft.
Run: .venv/bin/python -m pytest -q   (or: .venv/bin/python tests/test_guardrails.py)"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from kestrel import guardrails as G  # noqa: E402
from kestrel.agent import assemble, dnc_check  # noqa: E402

CFG = json.loads((ROOT / "config/kestrel.json").read_text())
PAGE = "Founded in 1998, Acme Studio designed the Harbor Library, which won a 2021 AIA Maine Honor Award."
QUOTE = "the Harbor Library, which won a 2021 AIA Maine Honor Award"
BLOCK = ["The Providence Group", "Hollis + Reed Architects", "Stonecut Studio", "BRIBURN"] + G.COMPETITORS


def check(opener, subject="Harbor Library award"):
    return G.validate_email(subject=subject, opener=opener, body=assemble(opener, CFG), quote=QUOTE,
                            page_text=PAGE, firm="Acme Studio", cfg=CFG, blocklist=BLOCK)


def test_clean_draft_passes():
    assert check("Your Harbor Library won a 2021 AIA Maine Honor Award. How does the team share the model shop?") == []


def test_g1_product_claims_blocked():
    errs = check("Your Harbor Library won a 2021 AIA Maine Honor Award. Kestrel saves studios hours every week.")
    assert any(e.startswith("opener G1") for e in errs)


def test_g1_comparison_blocked():
    assert any("G1" in e for e in check("Your Harbor Library won a 2021 AIA Maine Honor Award, better than most."))


def test_g2_unsourced_number_blocked():
    assert any("G2" in e for e in check("Your Harbor Library won a 2021 AIA Maine Honor Award with 40 staff."))


def test_g2_unsourced_name_blocked():
    assert any("G2" in e for e in check("Your Harbor Library won a 2021 AIA Maine Honor Award, beating Gensler."))


def test_g3_company_name_blocked():
    assert any("G3" in e for e in check("Your Harbor Library won a 2021 AIA Maine Honor Award, like BRIBURN."))


def test_must_open_with_fact():
    assert any("open with" in e for e in check("Hope your week is going well. Your Harbor Library won an award."))


def test_quote_must_be_verbatim():
    assert G.quote_in_page(QUOTE, PAGE)
    assert not G.quote_in_page("the Harbor Library, which won a 2022 AIA Maine Honor Award", PAGE)


def test_word_limit_and_signoff():
    long = "Your Harbor Library won a 2021 AIA Maine Honor Award. " + "Maine " * 60
    assert any("words" in e for e in check(long))
    assert assemble("x", CFG).endswith(CFG["sign_off"])


def test_dnc_exact_not_fuzzy():
    dnc = CFG["do_not_contact"]
    assert dnc_check("Providence Architecture & Building Co.", [], "We build in Providence.", dnc)["result"] == "Clear"
    assert dnc_check("Stonecut Studio", [], "", dnc)["result"] == "Match"
    assert dnc_check("Hollis and Reed Architects", [], "", dnc)["result"] == "Match"
    affs = [{"name": "Providence Group", "url": "u"}]
    assert dnc_check("Acme", affs, "", dnc)["result"] == "Match"
    assert dnc_check("Acme", [], "A member of The Providence Group of companies.", dnc)["result"] == "Match"


if __name__ == "__main__":
    fails = 0
    for k, f in list(globals().items()):
        if k.startswith("test_"):
            try:
                f(); print("PASS", k)
            except AssertionError:
                fails += 1; print("FAIL", k)
    sys.exit(fails)
