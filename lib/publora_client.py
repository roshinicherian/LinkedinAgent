"""Publora client with a fail-closed publish target guard.

The single most important rule in this repo: posts go to Roshini's PERSONAL
LinkedIn profile and nowhere else. `resolve_target()` is the chokepoint. It
must be called immediately before every publish, and it aborts rather than
guesses.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from typing import Any

import requests

from . import config

TIMEOUT = 30


class PubloraError(RuntimeError):
    pass


class TargetGuardError(PubloraError):
    """Raised when the publish target cannot be proven safe. Never caught-and-continued."""


# --- vocabulary for classifying a channel -------------------------------

# Anything in here means "this is an organisation / company page" -> refuse.
ORG_MARKERS = {
    "organization", "organisation", "org", "company", "company_page",
    "companypage", "business", "business_page", "page", "showcase",
    "group", "school", "brand",
}
# Anything in here means "this is a personal profile" -> allowed.
PERSON_MARKERS = {
    "person", "personal", "profile", "personal_profile", "personalprofile",
    "member", "user", "individual", "creator",
}


@dataclass(frozen=True)
class Channel:
    platform_id: str
    name: str
    platform: str
    raw_type: str
    kind: str  # "personal" | "organisation" | "unknown"
    raw: dict[str, Any]

    def summary(self) -> str:
        return f"{self.name} — {self.platform_id} — {self.kind.upper()} ({self.platform})"


def _headers() -> dict[str, str]:
    return {
        "x-publora-key": config.require("PUBLORA_API_KEY"),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _base() -> str:
    """Base URL including Publora's /api/v1 prefix."""
    root = (config.get("PUBLORA_BASE_URL") or "https://api.publora.com").rstrip("/")
    return root if root.endswith("/api/v1") else f"{root}/api/v1"


def _first(d: dict[str, Any], *keys: str) -> Any:
    """Pull the first present key. Publora's exact field names are confirmed
    against a live key on first run (scripts/dry_run_channel.py dumps the raw
    payload); until then we accept the plausible spellings."""
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return None


def _classify(raw_type: str, blob: dict[str, Any]) -> str:
    """Classify a channel as personal / organisation / unknown.

    Fails closed: an unrecognised type is 'unknown', and unknown never publishes.
    """
    haystack = raw_type.lower().replace("-", "_")
    tokens = set(haystack.replace("/", "_").split("_")) | {haystack}

    if tokens & ORG_MARKERS:
        return "organisation"
    if tokens & PERSON_MARKERS:
        return "personal"

    # Some APIs signal it with a boolean rather than a type string.
    for key in ("isOrganization", "is_organization", "isCompany", "is_company", "isPage"):
        if blob.get(key) is True:
            return "organisation"
    for key in ("isPersonal", "is_personal", "isProfile", "is_profile", "isMember"):
        if blob.get(key) is True:
            return "personal"

    # Publora's platform-connections payload carries no type field, but the
    # profile URL says it plainly: /in/ is a member, /company/ is a page.
    url = str(_first(blob, "profileUrl", "profile_url", "url", "permalink") or "").lower()
    if url:
        if "/company/" in url or "/showcase/" in url or "/school/" in url:
            return "organisation"
        if "/in/" in url:
            return "personal"
    return "unknown"


def _normalise(blob: dict[str, Any]) -> Channel:
    pid = _first(blob, "platformId", "platform_id", "id", "channelId", "channel_id")
    name = _first(blob, "name", "displayName", "display_name", "title", "handle", "username")
    platform = _first(blob, "platform", "network", "provider", "type") or ""
    # Publora identifies the network in the ID itself: "linkedin-yuV7gdcpIY".
    if not platform and pid and "-" in str(pid):
        platform = str(pid).split("-", 1)[0]
    raw_type = _first(
        blob, "accountType", "account_type", "channelType", "channel_type",
        "entityType", "entity_type", "kind", "subtype",
    ) or ""
    return Channel(
        platform_id=str(pid) if pid is not None else "",
        name=str(name) if name is not None else "<unnamed>",
        platform=str(platform).lower(),
        raw_type=str(raw_type),
        kind=_classify(str(raw_type), blob),
        raw=blob,
    )


def list_channels_raw() -> Any:
    """Return the untouched channels payload, for shape inspection."""
    url = f"{_base()}/platform-connections"
    try:
        resp = requests.get(url, headers=_headers(), timeout=TIMEOUT)
    except requests.RequestException as exc:
        raise PubloraError(f"Could not reach Publora at {url}: {exc}") from exc
    if resp.status_code == 401:
        raise PubloraError("Publora rejected the API key (401). Check PUBLORA_API_KEY.")
    if resp.status_code == 404:
        raise PubloraError(
            f"{url} returned 404. The channels endpoint path differs on this "
            f"account — confirm it and set PUBLORA_BASE_URL / the path before publishing."
        )
    if not resp.ok:
        raise PubloraError(f"Publora {resp.status_code} from {url}: {resp.text[:400]}")
    return resp.json()


def list_channels() -> list[Channel]:
    payload = list_channels_raw()
    if isinstance(payload, dict):
        for key in ("connections", "channels", "data", "results", "items", "accounts"):
            if isinstance(payload.get(key), list):
                payload = payload[key]
                break
    if not isinstance(payload, list):
        raise PubloraError(
            "Unexpected channels payload shape; refusing to interpret it. "
            f"Got: {json.dumps(payload)[:400]}"
        )
    return [_normalise(b) for b in payload if isinstance(b, dict)]


def resolve_target() -> Channel:
    """THE GUARD. Returns the one channel we are allowed to post to, or raises.

    Rules, all of which must hold:
      1. The target ID comes from LINKEDIN_PLATFORM_ID in the environment only.
      2. Exactly one connected LinkedIn channel exists.
      3. Its platform ID matches LINKEDIN_PLATFORM_ID by exact string equality.
      4. It is a personal profile, not an organisation/company page.
    """
    expected = config.require("LINKEDIN_PLATFORM_ID")

    channels = list_channels()
    linkedin = [c for c in channels if "linkedin" in c.platform or "linkedin" in c.raw_type.lower()]

    if not linkedin:
        raise TargetGuardError(
            "No LinkedIn channel is connected to this Publora account. Nothing to post to."
        )

    if len(linkedin) > 1:
        listing = "\n".join(f"  - {c.summary()}" for c in linkedin)
        raise TargetGuardError(
            f"{len(linkedin)} LinkedIn channels are connected. The brief says abort "
            f"rather than choose. Disconnect the extras, or confirm in writing which "
            f"one to keep.\n{listing}"
        )

    channel = linkedin[0]

    if channel.platform_id != expected:
        raise TargetGuardError(
            "The connected LinkedIn channel's platform ID does not match "
            "LINKEDIN_PLATFORM_ID exactly.\n"
            f"  connected: {channel.platform_id!r} ({channel.name})\n"
            f"  expected:  {expected!r}\n"
            "Refusing to publish."
        )

    if channel.kind == "organisation":
        raise TargetGuardError(
            f"{channel.name} ({channel.platform_id}) is an organisation/company page "
            f"(type={channel.raw_type!r}). This agent only ever posts to a personal profile."
        )

    if channel.kind != "personal":
        raise TargetGuardError(
            f"Could not prove {channel.name} ({channel.platform_id}) is a personal "
            f"profile — Publora reported type {channel.raw_type!r}, which this guard "
            f"does not recognise. Failing closed rather than assuming."
        )

    return channel


def publish(
    draft_text: str,
    *,
    scheduled_time: str | None = None,
    media_urls: list[str] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Publish (or schedule) a post, after re-running the target guard."""
    channel = resolve_target()  # re-verified immediately before every send

    body: dict[str, Any] = {
        "content": draft_text,
        "platforms": [channel.platform_id],
    }
    if scheduled_time:
        body["scheduledTime"] = scheduled_time
    if media_urls:
        body["mediaUrls"] = list(media_urls)

    if dry_run:
        return {"dry_run": True, "target": asdict(channel) | {"raw": "<omitted>"}, "body": body}

    url = f"{_base()}/create-post"
    try:
        resp = requests.post(url, headers=_headers(), json=body, timeout=TIMEOUT)
    except requests.RequestException as exc:
        raise PubloraError(f"Publish request failed: {exc}") from exc
    if not resp.ok:
        raise PubloraError(f"Publora {resp.status_code} on publish: {resp.text[:400]}")
    return resp.json()


# There is deliberately no comment() here. Publora cannot create comments (its
# LinkedIn comment API is read-only), so the sources that used to go out as a
# first comment are part of the post body, editable on the approval page.
