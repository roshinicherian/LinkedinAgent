#!/usr/bin/env python3
"""Send one test email. Sending only — no mailbox is read, no IMAP needed."""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import config, mailer  # noqa: E402


def main() -> int:
    missing = [k for k in ("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD",
                           "APPROVAL_EMAIL", "APPROVAL_FROM") if not config.get(k)]
    if missing:
        print("BLOCKED — not set: " + ", ".join(missing))
        return 1

    to = config.require("APPROVAL_EMAIL")
    subject = f"[LI-TEST] Your LinkedIn agent can reach you — {datetime.now():%H:%M}"
    text = ("If you're reading this, the agent can email you.\n\n"
            "You don't need to reply. Approvals happen on a web page, not by email.\n")
    html = ("<div style=\"font-family:-apple-system,Segoe UI,sans-serif;font-size:15px;"
            "line-height:1.6;color:#14212C\">"
            "<p>If you're reading this, the agent can email you.</p>"
            "<p style=\"color:#4A5C6B\">You don't need to reply — approvals happen on a "
            "web page, not by email.</p></div>")
    mailer.send(subject, html, text)
    print(f"Sent to {to} from {config.require('APPROVAL_FROM')}")
    print(f"Subject: {subject}\n\nCheck the inbox. Nothing to reply to.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
