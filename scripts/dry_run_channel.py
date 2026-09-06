#!/usr/bin/env python3
"""STEP 3 — DRY RUN. Resolve the Publora channel and prove it is the personal
profile. Publishes nothing, ever. This script has no publish code path.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import config, publora_client as pub  # noqa: E402


def main() -> int:
    print("=" * 66)
    print("PUBLORA CHANNEL DRY RUN — nothing is published by this script")
    print("=" * 66)

    expected = config.get("LINKEDIN_PLATFORM_ID")
    if not expected:
        print("\nBLOCKED: LINKEDIN_PLATFORM_ID is not set. It is the only accepted")
        print("source of the publish target — not a prompt, not a file, not a past post.")
        return 1
    print(f"\nExpected target ID (from environment only): {expected}")

    try:
        raw = pub.list_channels_raw()
    except pub.PubloraError as exc:
        print(f"\nBLOCKED: {exc}")
        return 1

    print("\n--- raw channels payload (shape confirmation) ---")
    print(json.dumps(raw, indent=2)[:3000])

    channels = pub.list_channels()
    print(f"\n--- {len(channels)} channel(s) connected ---")
    for c in channels:
        print(f"  {c.summary()}   [raw type: {c.raw_type!r}]")

    print("\n--- guard ---")
    try:
        target = pub.resolve_target()
    except pub.TargetGuardError as exc:
        print(f"ABORT — {exc}")
        print("\nNo post will be scheduled. Email Roshini and stop.")
        return 1

    print("PASS. The one channel this agent may post to:")
    print(f"\n  Name : {target.name}")
    print(f"  ID   : {target.platform_id}")
    print(f"  Type : {target.kind.upper()}  (Publora reports {target.raw_type!r})")
    print("\nConfirm this is your personal profile before approving any post.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
