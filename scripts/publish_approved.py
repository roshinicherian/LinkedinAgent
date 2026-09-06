#!/usr/bin/env python3
"""Publish an approved post. Used after a decision is recorded on the approval page.

    python3 scripts/publish_approved.py runs/<manifest>.json --variant A --now
    python3 scripts/publish_approved.py runs/<manifest>.json --text-file edit.txt --now

Re-runs the safety gate and the publish-target guard before sending. Refuses on
either failure — an approved decision does not bypass the checks.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import postlog, publora_client as pub, safety  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    ap.add_argument("--variant", choices=["A", "B"])
    ap.add_argument("--text-file", help="Roshini's own copy; published verbatim if it passes")
    ap.add_argument("--now", action="store_true", help="publish immediately instead of scheduling")
    args = ap.parse_args()

    if bool(args.variant) == bool(args.text_file):
        print("Give exactly one of --variant or --text-file.")
        return 1

    run = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    verified = [n for s in run.get("sources", []) for n in s.get("numbers", [])]
    personal = run.get("allowed_personal_numbers", [])

    if args.variant:
        v = next((x for x in run["variants"] if x["label"] == args.variant), None)
        if not v:
            print(f"Variant {args.variant} is not in this run.")
            return 1
        text, formula, uses_stats = v["text"], v["formula"], v.get("uses_stats", False)
    else:
        text = Path(args.text_file).read_text(encoding="utf-8").strip()
        formula, uses_stats = "EDIT (Roshini's own copy)", True

    text = safety.sanitise(text)
    rep = safety.run_gate(text, verified if uses_stats else [], personal)
    print("SAFETY GATE\n" + rep.render())
    if not rep.passed:
        print("\nBLOCKED — not publishing, and not rewriting. "
              "Report the failing lines and ask.")
        return 1

    try:
        target = pub.resolve_target()
    except pub.PubloraError as exc:
        print(f"\nBLOCKED — target guard: {exc}")
        return 1
    print(f"\nTarget: {target.summary()}")

    res = pub.publish(text, scheduled_time=None if args.now else run["scheduled_iso"],
                      media_urls=run.get("media_urls") or None)
    url = res.get("url") or res.get("postUrl") or ""
    print("Published." if args.now else f"Scheduled for {run['scheduled_iso']}.")

    pid = res.get("id") or res.get("postId")
    if run.get("first_comment") and pid:
        try:
            pub.comment(pid, run["first_comment"])
            print("First comment posted.")
        except pub.PubloraError as exc:
            print(f"Post is live but the first comment failed: {exc}")

    stats = run.get("sources", []) if uses_stats else []
    postlog.append_run(
        date=run["date"], run_id=run["run_id"], pillar=run["pillar"],
        hook_formula=formula, opening_line=text.splitlines()[0], topic=run["topic"],
        stats=stats, image_cost=run.get("image_cost", "$0.00"),
        rounds=run.get("round", 1), live_url=url,
        notes=f"approved via approval page ({args.variant or 'EDIT'})",
    )
    postlog.append_stats(stats)
    print(f"Logged. Live URL: {url or '(check Publora)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
