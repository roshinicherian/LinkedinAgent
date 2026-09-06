#!/usr/bin/env python3
"""Poll IMAP for Roshini's reply, then act on it. Fail-closed by design.

    python3 scripts/await_approval.py runs/<manifest>.json [--publish-now]

Never publishes on silence, on an ambiguous reply, or on mail from any other
address.
"""
import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import config, mailer, postlog, publora_client as pub, safety  # noqa: E402


def _publish(text: str, run: dict, now: bool) -> dict:
    text = safety.sanitise(text)
    scheduled = None if now else run["scheduled_iso"]
    media = run.get("media_urls") or None
    result = pub.publish(text, scheduled_time=scheduled, media_urls=media)
    print("Published." if now else f"Scheduled for {scheduled}.")
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    ap.add_argument("--publish-now", action="store_true",
                    help="publish immediately instead of scheduling (test runs)")
    ap.add_argument("--poll-minutes", type=int, default=10)
    ap.add_argument("--max-hours", type=float, default=11.0)
    args = ap.parse_args()

    run = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    token = f"#{run['run_id']}"
    by_label = {v["label"]: v for v in run["variants"]}

    deadline = time.time() + args.max_hours * 3600
    print(f"Polling for a reply containing {token!r} every {args.poll_minutes} min.")
    print(f"Cutoff: {run['cutoff_human']}. Silence = no post.\n")

    while time.time() < deadline:
        for r in mailer.fetch_replies(token):
            if not r.trusted:
                print(f"[IGNORED] {r.sender}: {'; '.join(r.notes)}")
                continue

            print(f"[{datetime.now():%H:%M}] reply from {r.sender}: cmd={r.command!r}")

            if r.command in ("A", "B"):
                variant = by_label.get(r.command)
                if not variant:
                    print(f"Variant {r.command} isn't in this run. Not publishing.")
                    return 1
                res = _publish(variant["text"], run, args.publish_now)
                url = res.get("url") or res.get("postUrl") or ""
                if run.get("first_comment") and (pid := res.get("id") or res.get("postId")):
                    try:
                        pub.comment(pid, run["first_comment"])
                        print("First comment posted.")
                    except pub.PubloraError as exc:
                        print(f"Post is live but the first comment failed: {exc}")
                postlog.append_run(
                    date=run["date"], run_id=run["run_id"], pillar=run["pillar"],
                    hook_formula=variant["formula"],
                    opening_line=variant["text"].splitlines()[0],
                    topic=run["topic"],
                    stats=run.get("sources", []) if variant.get("uses_stats") else [],
                    image_cost=run.get("image_cost", "$0.00"),
                    rounds=run.get("round", 1), live_url=url,
                    notes=f"variant {r.command} approved",
                )
                postlog.append_stats(run.get("sources", []) if variant.get("uses_stats") else [])
                print(f"Logged. Live URL: {url or '(check Publora)'}")
                return 0

            if r.command == "SKIP":
                postlog.append_run(
                    date=run["date"], run_id=run["run_id"], pillar=run["pillar"],
                    hook_formula="-", opening_line="-", topic=run["topic"],
                    stats=[], image_cost="$0.00", rounds=run.get("round", 1),
                    live_url="-", notes="SKIP — no post this week",
                )
                print("SKIP logged. Not asking again this week.")
                return 0

            if r.command == "EDIT":
                text = safety.sanitise(r.payload)
                rep = safety.run_gate(text, [n for s in run.get("sources", [])
                                             for n in s.get("numbers", [])],
                                      run.get("allowed_personal_numbers", []))
                if rep.passed:
                    res = _publish(text, run, args.publish_now)
                    print("Your copy published verbatim.")
                    print(f"Live URL: {res.get('url') or '(check Publora)'}")
                    return 0
                print("Your copy did not pass the gate. NOT published, NOT rewritten:")
                print(rep.render())
                print("Emailing you the exact findings to decide on.")
                return 2

            if r.command in ("REWRITE", "HOOK", "SHORTER", "IMAGE"):
                print(f"Revision requested: {r.command} {r.argument}")
                print("Hand this to the agent for a new round (max 3), then resend.")
                return 3

            print("Reply had no recognisable command. Ambiguity is never approval.")
            print(f"  received: {r.body[:200]!r}")

        print(f"  no trusted reply yet ({datetime.now():%H:%M:%S})")
        time.sleep(args.poll_minutes * 60)

    print("\nCUTOFF REACHED WITH NO APPROVAL — nothing published. Correct behaviour.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
