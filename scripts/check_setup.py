#!/usr/bin/env python3
"""STEP 1 — confirm the environment is complete. Prints presence, never values."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import config  # noqa: E402


def main() -> int:
    config.load()
    print("=" * 66)
    print("SETUP CHECK — presence only, no secret is ever printed")
    print("=" * 66)

    env_path = config.REPO_ROOT / ".env"
    print(f"\n.env file: {'found' if env_path.exists() else 'NOT FOUND'} ({env_path})")
    print("(values may also come from the environment, which is how Claude Code")
    print(" Remote injects them — a missing file is fine if the vars are set)\n")

    st = config.status()
    width = max(len(k) for k in st)
    for key, info in st.items():
        tag = "REQUIRED" if info["required"] else "optional"
        mark = "OK " if info["present"] else ("MISSING" if info["required"] else "-  ")
        shown = info.get("value", "")
        if key in config.SECRET_KEYS:
            shown = "<set, hidden>" if info["present"] else ""
        print(f"  [{mark:>7}] {key:<{width}}  {tag:<8} {shown}")

    mode = config.approval_mode()
    print("\n" + "-" * 66)
    if mode == "web":
        print("Approval mode: WEB — you approve on a published page.")
        print("  No IMAP password needed. SMTP is used only to send you the link.")
    else:
        print("Approval mode: EMAIL — you reply to the draft; IMAP reads it.")

    missing = config.missing_required()
    print("-" * 66)
    if missing:
        print(f"BLOCKED — {len(missing)} required setting(s) missing:")
        for k in missing:
            print(f"    {k}")
        print("\nNothing will be sent or published until these are set.")
        print("Copy .env.example to .env and fill it in, or set them as")
        print("environment variables on the Claude Code Remote environment.")
        return 1
    print("PASS — all required settings present. Proceed to step 2.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
