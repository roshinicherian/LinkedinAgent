#!/usr/bin/env python3
"""Gate a week's run manifest and email the approval request.

    python3 scripts/send_approval.py runs/2026-09-10-run01.json [--round N] [--dry]

Refuses to send if the safety gate fails or the publish target can't be proven.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import config, mailer, publora_client as pub, safety  # noqa: E402
from lib.approval_email import ApprovalEmail, Source, Variant  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    ap.add_argument("--round", type=int, default=1)
    ap.add_argument("--dry", action="store_true",
                    help="gate + render, print instead of sending")
    args = ap.parse_args()

    run = json.loads(Path(args.manifest).read_text(encoding="utf-8"))

    verified = [n for s in run.get("sources", []) for n in s.get("numbers", [])]
    personal = run.get("allowed_personal_numbers", [])
    src_urls, cite_nums = safety.source_licences(run.get("sources", []))

    # Older manifests carried the sources as a separate first comment. Publora
    # cannot post comments, so fold that text onto the end of every variant —
    # it is part of the body now, and editable on the approval page.
    legacy_comment = (run.get("first_comment") or "").strip()
    if legacy_comment:
        print("NOTE: this manifest still has 'first_comment'. Appending it to "
              "each variant body — edit it on the approval page.\n")

    variants, gate_reports = [], []
    for v in run["variants"]:
        text = safety.sanitise(v["text"])
        if legacy_comment:
            text = f"{text}\n\n{legacy_comment}"
        rep = safety.run_gate(text, verified if v.get("uses_stats") else [],
                              personal, src_urls, cite_nums)
        gate_reports.append((v["label"], rep))
        variants.append(Variant(v["label"], v["formula"], v["goal"], text))

    print("=" * 66)
    print("SAFETY GATE")
    print("=" * 66)
    failed = False
    for label, rep in gate_reports:
        print(f"\nVariant {label}:")
        print("  " + rep.render().replace("\n", "\n  "))
        if not rep.passed:
            failed = True
    if failed:
        print("\nBLOCKED — a check failed. Nothing is emailed. Fix and re-run.")
        return 1
    print("\nAll variants pass.\n")

    # Target guard — resolved fresh, printed at the top of the email.
    if args.dry and not config.get("PUBLORA_API_KEY"):
        name, cid, kind = "<unresolved — no PUBLORA_API_KEY>", "<unresolved>", "unknown"
        print("DRY: skipping channel resolution (no API key).")
    else:
        try:
            ch = pub.resolve_target()
        except pub.PubloraError as exc:
            print(f"BLOCKED — target guard: {exc}")
            return 1
        name, cid, kind = ch.name, ch.platform_id, ch.kind

    worst = min(gate_reports, key=lambda x: x[1].passed)[1]
    msg = ApprovalEmail(
        run_id=run["run_id"], date=run["date"], pillar=run["pillar"],
        channel_name=name, channel_id=cid, channel_kind=kind,
        scheduled=run["scheduled_human"],
        variants=variants,
        sources=[Source(s["claim"], s["org"], s["year"], s["url"], s.get("geography", ""))
                 for s in run.get("sources", [])],
        gate=worst, image_line=run.get("image_line", "none"),
        round_no=args.round, notes=run.get("notes", []),
    )

    if args.dry:
        print("=" * 66)
        print("SUBJECT:", msg.subject())
        print("=" * 66)
        print(msg.text_body())
        return 0

    msg_id = mailer.send(msg.subject(), msg.html_body(), msg.text_body())
    print(f"Approval email sent to {config.require('APPROVAL_EMAIL')} "
          f"via {config.email_transport()}" + (f" (id {msg_id})" if msg_id else ""))
    print(f"Subject: {msg.subject()}")
    print("\nNow run:  python3 scripts/await_approval.py", args.manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
