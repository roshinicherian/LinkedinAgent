#!/usr/bin/env python3
"""Email Roshini a link to this week's page. Sending only — no mailbox is read.

    python3 scripts/send_link_email.py --kind input   --url <page> --pillar "..."
    python3 scripts/send_link_email.py --kind draft   --url <page> --pillar "..." --run 02
    python3 scripts/send_link_email.py --kind remind  --url <page> --run 02
    python3 scripts/send_link_email.py --kind live    --url <post-url> --run 02
"""
import argparse
import html
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import config, mailer  # noqa: E402

COPY = {
    "input": (
        "[LI-INPUT {d}]",
        "Anything worth writing about this week?",
        "One line is plenty — what you worked on, what annoyed you, what "
        "surprised you. There's a box at the top of the page.\n\n"
        "This week's pillar: {pillar}\n\n"
        "Nothing needed from you if it's been a quiet week. No answer by "
        "Wednesday night and the post gets written from the plan alone, "
        "which is fine.",
    ),
    "draft": (
        "[LI-DRAFT {d} #{run}] {pillar} — approval needed",
        "This week's post is ready for you",
        "Two variants, both through the safety gate. You can edit either one "
        "directly on the page before approving.\n\n"
        "Nothing publishes until you approve. If you decide nothing by "
        "6:30am Thursday, nothing goes out.",
    ),
    "remind": (
        "[REMINDER] [LI-DRAFT {d} #{run}] approval needed",
        "30 minutes to the cutoff",
        "Nothing decided yet on this week's post. The cutoff is 6:30am and "
        "nothing publishes without a decision.\n\nNo action needed if you'd "
        "rather skip this week.",
    ),
    "live": (
        "[LI-LIVE {d} #{run}] your post is up",
        "Published",
        "This week's post is live. The sources comment went up with it.",
    ),
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", choices=sorted(COPY), required=True)
    ap.add_argument("--url", required=True)
    ap.add_argument("--pillar", default="")
    ap.add_argument("--run", default="")
    a = ap.parse_args()

    subj_t, heading, body_t = COPY[a.kind]
    d = date.today().isoformat()
    subject = subj_t.format(d=d, run=a.run, pillar=a.pillar)
    body = body_t.format(pillar=a.pillar or "see the page")

    label = "Open this week's post" if a.kind == "live" else "Open the page"
    text = f"{heading}\n\n{body}\n\n{label}: {a.url}\n"
    html_body = (
        '<div style="font-family:-apple-system,Segoe UI,sans-serif;font-size:15px;'
        'line-height:1.6;color:#14212C;max-width:560px">'
        f'<h2 style="font-size:19px;margin:0 0 12px">{html.escape(heading)}</h2>'
        f'<p style="white-space:pre-wrap;color:#4A5C6B">{html.escape(body)}</p>'
        f'<p style="margin:22px 0"><a href="{html.escape(a.url)}" '
        'style="background:#0F4C81;color:#fff;text-decoration:none;padding:11px 20px;'
        f'border-radius:7px;display:inline-block;font-weight:600">{html.escape(label)}</a></p>'
        '</div>'
    )
    mailer.send(subject, html_body, text)
    print(f"Sent [{a.kind}] to {config.require('APPROVAL_EMAIL')}\nSubject: {subject}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
