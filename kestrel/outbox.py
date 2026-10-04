"""Writes emails as .eml files to outbox/ instead of sending them (demo mode: nothing is sent)."""
from __future__ import annotations

import os
import re
from datetime import datetime
from email.message import EmailMessage
from email.utils import format_datetime
from pathlib import Path


def write_email(root: Path, to: str, subject: str, body: str) -> Path:
    msg = EmailMessage()
    msg["From"] = os.environ.get("SENDER", "Gaurav Pawar")
    msg["To"] = to
    msg["Subject"] = subject
    msg["Date"] = format_datetime(datetime.now().astimezone())
    msg["X-Demo"] = "Not sent - written to outbox only"
    msg.set_content(body)
    out = root / "outbox"
    out.mkdir(exist_ok=True)
    path = out / f"{datetime.now():%Y-%m-%d_%H%M}_{re.sub(r'[^A-Za-z0-9]+', '_', subject).strip('_')}.eml"
    path.write_bytes(bytes(msg))
    return path
