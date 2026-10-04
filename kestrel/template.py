"""Renders the SOP issue template exactly, from a prospect record."""


def render(rec: dict) -> str:
    fact = rec.get("fact") or {}
    draft = rec.get("draft") or {}
    body = draft.get("body", "")
    body_md = "\n".join(f"> {line}" if line else ">" for line in body.split("\n")) if body else ""
    lines = [
        f"Firm: {rec['firm']}",
        f"Website: {rec['website']}",
        f"Segment: {rec.get('segment_line', '')}",
        f"Do-not-contact check: {rec.get('dnc_line', '')}",
        "",
        "**Fact**",
        "",
        f"Fact: {fact.get('fact', '')}",
        f"Source URL: {fact.get('url', '')}",
        "",
        "**Draft email**",
        "",
        f"Subject: {draft.get('subject', '')}",
        "Body:",
    ]
    if body_md:
        lines += ["", body_md]
    lines += ["", "**Status notes**", "", rec.get("status_note", "")]
    return "\n".join(lines)
