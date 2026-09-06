#!/usr/bin/env python3
"""Build this week's approval page from the manifest and the template.

    python3 scripts/build_approval_page.py runs/<week>.json [-o page.html]

Runs the safety gate and resolves the publish target first, so the page shows
what is actually true rather than the template's placeholders. Refuses to build
a page for a draft that fails the gate — nothing should reach an approve button
that the gate would block on the way out.

The output is published with the Artifact tool, declaring the `db` capability
so the page can store your decision. Nothing here talks to LinkedIn.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import publora_client as pub, safety  # noqa: E402

TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "approval-console.html"


def build(manifest_path: Path) -> tuple[str, list[tuple[str, safety.GateReport]]]:
    run = json.loads(manifest_path.read_text(encoding="utf-8"))
    verified = [n for s in run.get("sources", []) for n in s.get("numbers", [])]
    personal = run.get("allowed_personal_numbers", [])
    src_urls, cite_nums = safety.source_licences(run.get("sources", []))

    reports, variants = [], []
    for v in run["variants"]:
        text = safety.sanitise(v["text"])
        rep = safety.run_gate(text, verified if v.get("uses_stats") else [],
                              personal, src_urls, cite_nums)
        reports.append((v["label"], rep))
        variants.append({
            "label": v["label"],
            "title": v.get("title", ""),
            "formula": v["formula"],
            "goal": v["goal"],
            "stats": "carries a verified statistic" if v.get("uses_stats") else "no statistic",
            "text": text,
        })

    if not all(rep.passed for _, rep in reports):
        return "", reports

    named = [("Client scrub", "client-scrub"), ("Negativity", "negativity"),
             ("Politics / religion", "politics-religion"),
             ("Stats verified", "stats"), ("Craft", "craft")]
    worst = {name: "pass" for name, _ in named}
    for _, rep in reports:
        for label, key in named:
            check = next((c for c in rep.checks if c.name == key), None)
            if check and not check.passed:
                worst[label] = "fail"

    page_run = {
        "id": run["run_id"],
        "variants": variants,
        "checks": [[label, worst[label]] for label, _ in named],
        "sources": [{
            "who": s["org"].split("—")[0].strip(),
            "what": f"{s['org'].split('—', 1)[-1].strip()}. {s['claim']}.",
            "geo": f"{s.get('geography', '')} · {s.get('year', '')}".strip(" ·"),
            "url": s["url"],
        } for s in run.get("sources", [])],
        "notes": run.get("notes", []),
    }

    html = TEMPLATE.read_text(encoding="utf-8")
    start = html.index("const RUN = {")
    end = html.index("\n};", start) + len("\n};")
    html = html[:start] + "const RUN = " + json.dumps(page_run, indent=2, ensure_ascii=False) + ";" + html[end:]

    # The target is resolved here, not promised. If the guard refuses, the page
    # is not built at all.
    target = pub.resolve_target()
    html = html.replace(
        '<span class="tval" id="ch-name">Resolved at publish time</span>',
        f'<span class="tval" id="ch-name">{target.name}</span>')
    html = html.replace(
        '<span class="tval mono" id="ch-id">from LINKEDIN_PLATFORM_ID</span>',
        f'<span class="tval mono" id="ch-id">{target.platform_id}</span>')
    html = html.replace(
        '<span class="tval">Immediately on approval <span style="font-weight:400;color:var(--ink-2)">(test run)</span></span>',
        f'<span class="tval">{run["scheduled_human"]}</span>')
    html = re.sub(
        r'<div class="eyebrow">.*?</div>',
        f'<div class="eyebrow">Run {run["run_id"]} &middot; {run["date"]} '
        f'&middot; Pillar {run["pillar"]}</div>',
        html, count=1, flags=re.S)
    return html, reports


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    ap.add_argument("-o", "--out", default="")
    args = ap.parse_args()

    html, reports = build(Path(args.manifest))
    print("SAFETY GATE")
    for label, rep in reports:
        print(f"\nVariant {label}:")
        print("  " + rep.render().replace("\n", "\n  "))
    if not html:
        print("\nBLOCKED — a check failed. No page is built, so nothing can be approved.")
        return 1

    out = Path(args.out) if args.out else Path(args.manifest).with_suffix(".html")
    out.write_text(html, encoding="utf-8")
    print(f"\nPage written to {out} ({len(html):,} bytes).")
    print("Publish it with the Artifact tool, capabilities {\"db\": {}}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
