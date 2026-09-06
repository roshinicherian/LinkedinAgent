"""Builds the approval email exactly to the brief's format."""
from __future__ import annotations

import html
from dataclasses import dataclass, field

from .safety import GateReport


@dataclass
class Variant:
    label: str
    formula: str
    goal: str
    text: str


@dataclass
class Source:
    claim: str
    org: str
    year: str
    url: str
    geography: str = ""


@dataclass
class ApprovalEmail:
    run_id: str
    date: str
    pillar: str
    channel_name: str
    channel_id: str
    channel_kind: str
    scheduled: str
    variants: list[Variant]
    first_comment: str
    sources: list[Source]
    gate: GateReport
    image_line: str = "none"
    round_no: int = 1
    notes: list[str] = field(default_factory=list)

    def subject(self) -> str:
        base = f"[LI-DRAFT {self.date} #{self.run_id}] {self.pillar} — approval needed"
        return base if self.round_no == 1 else f"{base} (round {self.round_no})"

    # ---------------------------------------------------------------- top

    def _checks_line(self) -> str:
        return self.gate.summary_line(len(self.sources))

    def _target_line(self) -> str:
        ok = "✅" if self.channel_kind == "personal" else "⛔"
        return (f"🔒 Target: {self.channel_name} — {self.channel_id} — "
                f"{self.channel_kind.upper()} {ok}")

    # --------------------------------------------------------------- text

    def text_body(self) -> str:
        out = [
            self._target_line(),
            f"📅 Scheduled: {self.scheduled}",
            f"📌 Pillar: {self.pillar} | Hook formulas: "
            + " / ".join(f"{v.label}={v.formula}" for v in self.variants),
            f"✅ Checks: {self._checks_line()}",
            f"🖼️ Image: {self.image_line}",
            "",
        ]
        if self.notes:
            out += ["--- NOTES ---"] + [f"- {n}" for n in self.notes] + [""]
        for v in self.variants:
            out += [f"--- VARIANT {v.label} --- ({v.formula}, goal: {v.goal}, "
                    f"{len(v.text)} chars)", "", v.text, ""]
        out += ["--- FIRST COMMENT ---", "", self.first_comment, ""]
        out += ["--- SOURCES ---", ""]
        if self.sources:
            for s in self.sources:
                out.append(f"- {s.org} ({s.year}{', ' + s.geography if s.geography else ''}): "
                           f"{s.claim}\n  {s.url}")
        else:
            out.append("- none: this variant makes no statistical claim.")
        out += ["", "--- HOW TO REPLY ---", "",
                "Reply with ONE of these on the first line. Keep the subject token.",
                "",
                "  A                    approve Variant A and publish",
                "  B                    approve Variant B and publish",
                "  EDIT                 then your final copy on the following lines.",
                "                       Your words are treated as final — the safety",
                "                       gate runs, but nothing is rewritten. If a check",
                "                       fails you get told which line and why, and asked.",
                "  REWRITE <what>       revise and resend",
                "  HOOK <what>          new hook, resend",
                "  SHORTER              tighten and resend",
                "  IMAGE <what>         refine the image and resend",
                "  SKIP                 no post this week",
                "",
                "Max 3 revision rounds, then you get the best version and a yes/no.",
                "No reply by Thursday 06:30 AEST = nothing is published.",
                ]
        return "\n".join(out)

    # --------------------------------------------------------------- html

    def html_body(self) -> str:
        e = html.escape
        mono = ("font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;"
                "white-space:pre-wrap;background:#f6f8fa;border:1px solid #d0d7de;"
                "border-radius:6px;padding:14px;font-size:13px;line-height:1.55;")
        ok = self.channel_kind == "personal"
        banner_bg = "#e6f4ea" if ok else "#fce8e6"
        banner_bd = "#137333" if ok else "#c5221f"

        parts = [
            f'<div style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;'
            f'font-size:14px;line-height:1.6;color:#1f2328;max-width:720px">',
            f'<div style="background:{banner_bg};border-left:4px solid {banner_bd};'
            f'padding:12px 16px;border-radius:4px;margin-bottom:18px">',
            f'<div><b>🔒 Target:</b> {e(self.channel_name)} — '
            f'<code>{e(self.channel_id)}</code> — '
            f'<b>{e(self.channel_kind.upper())}</b> {"✅" if ok else "⛔"}</div>',
            f'<div><b>📅 Scheduled:</b> {e(self.scheduled)}</div>',
            f'<div><b>📌 Pillar:</b> {e(self.pillar)} | <b>Hook formula:</b> '
            + e(" / ".join(f"{v.label}={v.formula}" for v in self.variants)) + '</div>',
            f'<div><b>✅ Checks:</b> {e(self._checks_line())}</div>',
            f'<div><b>🖼️ Image:</b> {self.image_line}</div>',
            '</div>',
        ]
        if self.notes:
            parts.append("<p><b>Notes</b></p><ul>"
                         + "".join(f"<li>{e(n)}</li>" for n in self.notes) + "</ul>")
        for v in self.variants:
            parts.append(
                f'<h3 style="margin:22px 0 6px">VARIANT {e(v.label)}</h3>'
                f'<div style="color:#57606a;font-size:12px;margin-bottom:8px">'
                f'{e(v.formula)} · goal: {e(v.goal)} · {len(v.text)} chars</div>'
                f'<div style="{mono}">{e(v.text)}</div>'
            )
        parts.append(f'<h3 style="margin:22px 0 6px">FIRST COMMENT</h3>'
                     f'<div style="{mono}">{e(self.first_comment)}</div>')

        parts.append('<h3 style="margin:22px 0 6px">SOURCES</h3>')
        if self.sources:
            parts.append("<ul>" + "".join(
                f'<li><b>{e(s.org)}</b> ({e(s.year)}'
                f'{", " + e(s.geography) if s.geography else ""}) — {e(s.claim)}<br>'
                f'<a href="{e(s.url)}">{e(s.url)}</a></li>' for s in self.sources) + "</ul>")
        else:
            parts.append("<p>None — this variant makes no statistical claim.</p>")

        parts.append(
            '<h3 style="margin:22px 0 6px">HOW TO REPLY</h3>'
            '<p>Reply with <b>one</b> of these on the first line. Keep the subject token.</p>'
            '<table style="border-collapse:collapse;font-size:13px">'
            + "".join(
                f'<tr><td style="padding:3px 14px 3px 0"><code>{e(c)}</code></td>'
                f'<td style="padding:3px 0;color:#57606a">{e(d)}</td></tr>'
                for c, d in [
                    ("A", "approve Variant A and publish"),
                    ("B", "approve Variant B and publish"),
                    ("EDIT", "…then your final copy below. Your words are final — "
                             "the gate runs but nothing is rewritten."),
                    ("REWRITE <what>", "revise and resend"),
                    ("HOOK <what>", "new hook, resend"),
                    ("SHORTER", "tighten and resend"),
                    ("IMAGE <what>", "refine the image and resend"),
                    ("SKIP", "no post this week"),
                ])
            + '</table>'
            '<p style="color:#57606a;font-size:12px;margin-top:14px">'
            'Max 3 revision rounds, then you get the best version and a yes/no.<br>'
            '<b>No reply by Thursday 06:30 AEST means nothing is published.</b> '
            'Silence is never treated as approval.</p></div>'
        )
        return "".join(parts)
