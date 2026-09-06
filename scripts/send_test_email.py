#!/usr/bin/env python3
"""Send one test email. Sending only — no mailbox is read, no IMAP needed."""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import config, mailer  # noqa: E402


def main() -> int:
    # Only ask for what the configured transport actually uses: an HTTPS
    # provider needs no SMTP credentials at all.
    needed = ["APPROVAL_EMAIL", "APPROVAL_FROM"]
    if config.email_transport() in config.HTTPS_PROVIDERS:
        needed.append("EMAIL_API_KEY")
    else:
        needed += config.SMTP_KEYS
    missing = [k for k in needed if not config.get(k)]
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
    msg_id = mailer.send(subject, html, text)
    print(f"Sent to {to} from {config.require('APPROVAL_FROM')} "
          f"via {config.email_transport()}" + (f" (id {msg_id})" if msg_id else ""))
    print(f"Subject: {subject}\n\nCheck the inbox. Nothing to reply to.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
