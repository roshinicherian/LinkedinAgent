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
    ap.add_argument("--title", help="override the variant's title")
    ap.add_argument("--no-title", action="store_true", help="publish without a bold title line")
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
        title = args.title or v.get("title")
    else:
        text = Path(args.text_file).read_text(encoding="utf-8").strip()
        formula, uses_stats = "EDIT (Roshini's own copy)", True
        title = args.title

    include_title = bool(title) and not args.no_title
    # Gate the PLAIN composition so banned phrases and spellings still match;
    # bold is applied only on the way out.
    text = safety.sanitise(text)
    plain = safety.compose(title, text, include_title)
    src_urls, cite_nums = safety.source_licences(run.get("sources", []))
    rep = safety.run_gate(plain, verified if uses_stats else [], personal,
                          src_urls, cite_nums)
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

    final = safety.to_bold(title.strip()) + "\n\n" + text.lstrip() if include_title else text
    if include_title:
        print(f"Title line: {title!r} (bold)")
    res = pub.publish(final, scheduled_time=None if args.now else run["scheduled_iso"],
                      media_urls=run.get("media_urls") or None)
    url = res.get("url") or res.get("postUrl") or ""
    when = res.get("scheduledTime") or ""
    pid = res.get("postGroupId") or ""
    print(f"Sent to Publora as {pid or '<no id returned>'}, due {when or '<no time returned>'}.")
    for w in res.get("warnings") or []:
        print(f"  warning: {w.get('code', '')} {w.get('message', '')}")

    # Publora files a post without a scheduledTime as a draft that never goes
    # out, so confirm what it actually holds rather than trusting the 200.
    if pid:
        try:
            state = pub.get_post(pid).get("post") or {}
            status = state.get("status", "unknown")
            print(f"Publora status: {status}")
            if status == "draft":
                print("STILL A DRAFT — nothing will go out. Release it with "
                      f"pub.release_draft({pid!r}).")
                return 1
        except pub.PubloraError as exc:
            print(f"Could not read the post back: {exc}")

    stats = run.get("sources", []) if uses_stats else []
    postlog.append_run(
        date=run["date"], run_id=run["run_id"], pillar=run["pillar"],
        hook_formula=formula, opening_line=(title or text.splitlines()[0]), topic=run["topic"],
        stats=stats, image_cost=run.get("image_cost", "$0.00"),
        rounds=run.get("round", 1), live_url=url,
        notes=f"approved via approval page ({args.variant or 'EDIT'})",
    )
    postlog.append_stats(stats)
    print(f"Logged. Live URL: {url or '(check Publora)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
