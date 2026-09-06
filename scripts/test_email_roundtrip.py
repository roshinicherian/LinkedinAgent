#!/usr/bin/env python3
"""STEP 2 — send a one-line test email, then poll IMAP for the reply.

    python3 scripts/test_email_roundtrip.py send
    python3 scripts/test_email_roundtrip.py poll [--minutes 30]

The round trip must work before anything else runs.
"""
import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import config, mailer  # noqa: E402

TOKEN = "[LI-TEST]"


def do_send() -> int:
    subject = f"{TOKEN} transport check {datetime.now():%Y-%m-%d %H:%M}"
    text = (
        "This is the transport check for your LinkedIn agent.\n\n"
        "Reply to this email with the single word:  OK\n"
        "Keep [LI-TEST] in the subject line so the agent can match your reply.\n\n"
        "Nothing is published as a result of this message.\n"
    )
    html = (
        "<p>This is the transport check for your LinkedIn agent.</p>"
        "<p>Reply with the single word <b>OK</b>. Keep <code>[LI-TEST]</code> "
        "in the subject line so the agent can match your reply.</p>"
        "<p>Nothing is published as a result of this message.</p>"
    )
    mailer.send(subject, html, text)
    print(f"Sent to {config.require('APPROVAL_EMAIL')} from {config.require('APPROVAL_FROM')}")
    print(f"Subject: {subject}")
    print("Now run:  python3 scripts/test_email_roundtrip.py poll")
    return 0


def do_poll(minutes: int) -> int:
    allowed = (config.get("APPROVAL_ALLOWED_SENDER") or config.require("APPROVAL_EMAIL")).lower()
    deadline = time.time() + minutes * 60
    print(f"Polling IMAP every 10 min for up to {minutes} min. Only {allowed} is honoured.")
    while time.time() < deadline:
        replies = mailer.fetch_replies(TOKEN)
        for r in replies:
            status = "TRUSTED" if r.trusted else "IGNORED"
            print(f"\n[{status}] from {r.sender}: {r.body[:120]!r}")
            for n in r.notes:
                print(f"    {n}")
            if r.trusted:
                print("\nROUND TRIP CONFIRMED — send and receive both work.")
                return 0
        print(f"  no trusted reply yet ({datetime.now():%H:%M:%S}); sleeping 10 min")
        time.sleep(600)
    print("\nTIMED OUT — no trusted reply. Do not proceed to publishing.")
    return 1


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["send", "poll"])
    p.add_argument("--minutes", type=int, default=30)
    a = p.parse_args()
    raise SystemExit(do_send() if a.mode == "send" else do_poll(a.minutes))
