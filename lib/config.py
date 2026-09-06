"""Configuration loader.

Secrets are read from the process environment first (how Claude Code Remote
injects them) and fall back to a local .env file.

Nothing in this module ever returns a secret in a printable summary. Use
`redact()` before putting any config-derived value in a log or an email.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent

# Keys whose values must never be printed, logged, or emailed.
SECRET_KEYS = {
    "PUBLORA_API_KEY",
    "PIXFARO_TOKEN",
    "SMTP_PASSWORD",
    "IMAP_PASSWORD",
}

# (key, required?) — required keys block the run when missing.
REQUIRED = [
    "PUBLORA_API_KEY",
    "LINKEDIN_PLATFORM_ID",
    "APPROVAL_EMAIL",
    "APPROVAL_FROM",
    "SMTP_HOST",
    "SMTP_PORT",
    "SMTP_USER",
    "SMTP_PASSWORD",
]

# IMAP is only needed for APPROVAL_MODE=email. The default, web, uses a
# published approval page instead — no mailbox password at all.
IMAP_KEYS = ["IMAP_HOST", "IMAP_PORT", "IMAP_USER", "IMAP_PASSWORD"]

OPTIONAL = [
    "APPROVAL_MODE",
    *IMAP_KEYS,
    "PIXFARO_TOKEN",
    "PUBLORA_BASE_URL",
    "PIXFARO_BASE_URL",
    "PIXFARO_DEFAULT_MODEL",
    "APPROVAL_ALLOWED_SENDER",
    "IMAP_FOLDER",
    "SMTP_STARTTLS",
    "TIMEZONE",
]

_loaded = False


def load(env_file: str | os.PathLike | None = None) -> None:
    """Load .env once. Process env always wins over the file."""
    global _loaded
    if _loaded:
        return
    path = Path(env_file) if env_file else REPO_ROOT / ".env"
    if path.exists():
        load_dotenv(path, override=False)
    _loaded = True


def get(key: str, default: str | None = None) -> str | None:
    load()
    val = os.environ.get(key, default)
    return val.strip() if isinstance(val, str) else val


def require(key: str) -> str:
    val = get(key)
    if not val:
        raise MissingConfig(
            f"{key} is not set. Add it to .env (see .env.example) or to the "
            f"environment. The run is stopping rather than guessing."
        )
    return val


def redact(value: str | None, keep: int = 4) -> str:
    """Render a secret safely: last `keep` chars only."""
    if not value:
        return "<unset>"
    if len(value) <= keep:
        return "*" * len(value)
    return "*" * (len(value) - keep) + value[-keep:]


def status() -> dict[str, dict[str, object]]:
    """Presence-only report. Never exposes a secret value."""
    load()
    out: dict[str, dict[str, object]] = {}
    for key in REQUIRED + OPTIONAL:
        raw = os.environ.get(key)
        present = bool(raw and raw.strip())
        entry: dict[str, object] = {
            "present": present,
            "required": key in REQUIRED,
        }
        if present and key not in SECRET_KEYS:
            entry["value"] = raw.strip()
        elif present:
            entry["value"] = "<set, hidden>"
        out[key] = entry
    return out


def approval_mode() -> str:
    """'web' (approval page + db) or 'email' (IMAP reply). Defaults to web."""
    return (get("APPROVAL_MODE") or "web").strip().lower()


def missing_required() -> list[str]:
    missing = [k for k in REQUIRED if not get(k)]
    if approval_mode() == "email":
        missing += [k for k in IMAP_KEYS if not get(k)]
    return missing


class MissingConfig(RuntimeError):
    """Raised when a required setting is absent. Never fall back to a guess."""
