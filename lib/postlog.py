"""Append-only run logging for post-log.md and stats-used.md."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .config import REPO_ROOT

POST_LOG = REPO_ROOT / "post-log.md"
STATS_LOG = REPO_ROOT / "stats-used.md"


def append_run(*, date: str, run_id: str, pillar: str, hook_formula: str,
               opening_line: str, topic: str, stats: list[dict[str, str]],
               image_cost: str, rounds: int, live_url: str, notes: str = "") -> None:
    stat_cell = "; ".join(f"{s['org']} {s['year']} ({s['url']})" for s in stats) or "none"
    row = (f"| {date} | {run_id} | {pillar} | {hook_formula} | "
           f"{opening_line[:60].replace('|', '/')} | {topic} | {stat_cell} | "
           f"{image_cost} | {rounds} | {live_url} | | | {notes} |\n")
    with POST_LOG.open("a", encoding="utf-8") as fh:
        fh.write(row)


def append_stats(stats: list[dict[str, str]]) -> None:
    stamp = datetime.now().strftime("%Y-%m-%d")
    with STATS_LOG.open("a", encoding="utf-8") as fh:
        for s in stats:
            fh.write(f"| {stamp} | {s['claim']} | {s['org']} | {s['year']} | "
                     f"{s['geography']} | {s['url']} | {s.get('verified_how','live search')} |\n")


def recent_hooks(weeks: int = 8) -> list[str]:
    """Hook formulas used in the last N logged posts — nothing repeats inside 8 weeks."""
    if not POST_LOG.exists():
        return []
    rows = [l for l in POST_LOG.read_text(encoding="utf-8").splitlines()
            if l.startswith("| 20")]
    out = []
    for line in rows[-weeks:]:
        cells = [c.strip() for c in line.split("|")]
        if len(cells) > 4:
            out.append(cells[4])
    return out
