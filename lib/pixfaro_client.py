"""Pixfaro image layer.

Two guards matter here:
  - Never silently use a premium model. `illustrate` refuses unless the caller
    passes allow_premium=True, which only happens after Roshini says yes.
  - Never generate a real person's face, a client-lookalike product, or a fake
    dashboard/chart. Prompts are screened before they are sent.
"""
from __future__ import annotations

import re
from typing import Any

import requests

from . import config

TIMEOUT = 120

ASPECT = {
    "wide": "1200:628", "link": "1200:628",
    "portrait": "4:5", "carousel": "4:5", "quote": "4:5",
    "square": "1:1",
}

PREMIUM_MODELS = {"gpt-5-image", "gemini-pro-image", "dall-e-3-hd", "midjourney"}
DEFAULT_MODEL = "flux-schnell"

_FORBIDDEN_PROMPT = [
    (r"\b(?:photo|photograph|portrait|headshot|realistic face|real person)\b",
     "no real people's faces"),
    (r"\b(?:dashboard|analytics screen|google ads (?:screenshot|interface)|ga4 screen|"
     r"search console|screenshot)\b",
     "no fake dashboards or screenshots"),
    (r"\b(?:bar chart|line graph|pie chart|graph showing|chart showing)\b",
     "no invented charts — build a chart from a verified stat and label the source"),
    (r"\b(?:logo of|branded|brand mark of)\b", "no client-resembling branding"),
]


class PixfaroError(RuntimeError):
    pass


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {config.require('PIXFARO_TOKEN')}",
        "Content-Type": "application/json",
    }


def _base() -> str:
    return (config.get("PIXFARO_BASE_URL") or "https://api.pixfaro.com").rstrip("/")


def backend() -> str:
    """'pixfaro' when a token is present, otherwise 'manual'."""
    return "pixfaro" if config.get("PIXFARO_TOKEN") else "manual"


def screen_prompt(prompt: str) -> list[str]:
    return [why for pat, why in _FORBIDDEN_PROMPT if re.search(pat, prompt, re.I)]


def illustrate(prompt: str, *, kind: str = "wide", model: str | None = None,
               overlay: dict[str, Any] | None = None,
               allow_premium: bool = False) -> dict[str, Any]:
    violations = screen_prompt(prompt)
    if violations:
        raise PixfaroError("Prompt refused: " + "; ".join(violations))

    model = model or config.get("PIXFARO_DEFAULT_MODEL") or DEFAULT_MODEL
    if model in PREMIUM_MODELS and not allow_premium:
        raise PixfaroError(
            f"{model!r} is a premium model. Ask Roshini first, then pass "
            f"allow_premium=True. Defaulting silently to a paid tier is not allowed."
        )

    if backend() == "manual":
        return {
            "backend": "manual",
            "url": None,
            "cost": 0.0,
            "message": (
                "No PIXFARO_TOKEN set. Generate this manually and paste the URL:\n"
                f"  prompt: {prompt}\n  aspect: {ASPECT.get(kind, '1200:628')}"
            ),
        }

    body: dict[str, Any] = {
        "prompt": prompt,
        "model": model,
        "aspect_ratio": ASPECT.get(kind, "1200:628"),
        "resolution": "1K",
    }
    if overlay:
        body["overlay"] = overlay

    resp = requests.post(f"{_base()}/v1/images", headers=_headers(), json=body, timeout=TIMEOUT)
    if not resp.ok:
        raise PixfaroError(f"Pixfaro {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    data.setdefault("backend", "pixfaro")
    data["premium"] = model in PREMIUM_MODELS
    return data


def refine(image_id: str, instruction: str) -> dict[str, Any]:
    """Edit an existing image by id. Cheaper and more consistent than regenerating."""
    if backend() == "manual":
        raise PixfaroError("No PIXFARO_TOKEN — cannot refine. Regenerate manually.")
    resp = requests.post(
        f"{_base()}/v1/images/{image_id}/edit",
        headers=_headers(), json={"instruction": instruction}, timeout=TIMEOUT,
    )
    if not resp.ok:
        raise PixfaroError(f"Pixfaro {resp.status_code} on refine: {resp.text[:300]}")
    return resp.json()


def fetch_bytes(url: str) -> bytes:
    """Download a generated image so it can be embedded inline in the approval email."""
    r = requests.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    return r.content
