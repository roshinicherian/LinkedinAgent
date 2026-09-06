"""The safety gate. Every draft passes all four checks or it does not go out.

These are mechanical checks; they catch the obvious failures cheaply so the
human review is spent on judgement, not proofreading. A PASS here is a floor,
not a guarantee — the final "could a competitor identify an account?" read is
still done by hand.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field


@dataclass
class CheckResult:
    name: str
    passed: bool
    findings: list[str] = field(default_factory=list)

    def render(self) -> str:
        return f"{self.name}: {'PASS' if self.passed else 'FAIL'}" + (
            "" if self.passed else " — " + "; ".join(self.findings)
        )


@dataclass
class GateReport:
    checks: list[CheckResult]

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)

    def render(self) -> str:
        return "\n".join(c.render() for c in self.checks)

    def summary_line(self, n_stats: int) -> str:
        def mark(name: str) -> str:
            c = next((c for c in self.checks if c.name == name), None)
            return "PASS" if c and c.passed else "FAIL"
        return (f"client-scrub {mark('client-scrub')} | negativity {mark('negativity')} | "
                f"politics/religion {mark('politics-religion')} | "
                f"stats VERIFIED (n={n_stats})" if mark("stats") == "PASS"
                else f"client-scrub {mark('client-scrub')} | negativity {mark('negativity')} | "
                     f"politics/religion {mark('politics-religion')} | stats FAIL")


# ----------------------------------------------------------- 1. clients

# Phrases specific enough to narrow a client down by elimination.
_CLIENT_PATTERNS = [
    (r"\b(?:my|our|the)\s+client\b(?!\s+(?:relationships?|work|side|base|portfolio))",
     "names a specific client engagement"),
    (r"\b(?:regional|rural)\s+(?:NSW|QLD|VIC|WA|SA|NT|TAS|New South Wales|Queensland|Victoria)\b",
     "geographic detail narrow enough to identify an account"),
    (r"\b(?:CPL|ROAS|CPA|CTR)\s*(?:of|was|at|dropped to|rose to|:)?\s*\$?\d",
     "a dated campaign metric"),
    (r"\$\s?\d[\d,]*(?:\.\d+)?\s?(?:k|m)?\s*(?:in\s+)?(?:spend|budget|revenue|pipeline|ad\s?spend)",
     "client spend or revenue figure"),
    (r"\b\d+\s*(?:%|per cent|percent)\s+(?:lift|increase|uplift|improvement|drop|reduction)\s+in\s+"
     r"(?:leads?|conversions?|enquir|sales|revenue|traffic)",
     "a claimed client result"),
    (r"\b(?:conversion|lead)s?\s+(?:went|rose|jumped|climbed|fell)\s+(?:from|to)\s+\d",
     "a dated client outcome"),
    (r"\.com\.au\b|\bwww\.\S+", "a URL that could identify an account"),
]


def check_clients(text: str) -> CheckResult:
    findings = [f"{desc} → {m.group(0)!r}"
                for pat, desc in _CLIENT_PATTERNS
                for m in re.finditer(pat, text, re.I)]
    return CheckResult("client-scrub", not findings, findings)


# -------------------------------------------------------- 2. negativity

# Named actors that must never be criticised. Mentioning a tool neutrally is
# fine; the check fires when a name sits next to a pejorative.
_NAMED_ACTORS = [
    "google", "meta", "facebook", "linkedin", "openai", "anthropic", "hubspot",
    "salesforce", "semrush", "ahrefs", "wordpress", "elastic email", "ga4",
    "chatgpt", "claude", "gemini", "microsoft", "adobe", "canva", "mailchimp",
]
_PEJORATIVES = [
    "lazy", "useless", "garbage", "rubbish", "clueless", "incompetent", "scam",
    "ripoff", "rip-off", "joke", "pathetic", "terrible", "awful", "worst",
    "dishonest", "lying", "lies", "greedy", "broken promise", "cash grab",
    "stupid", "idiotic", "nonsense", "fraud",
]
_SUBTWEET = [
    r"\bsome (?:agencies|agency|people|recruiters|clients|colleagues)\b.{0,60}\b(?:still|just|never|apparently)\b",
    r"\byou know who you are\b",
    r"\bnot naming names\b",
    r"\bif you know, you know\b",
]
_EMPLOYMENT = [
    r"\b(?:looking for|open to)\s+(?:work|a new role|opportunities)\b",
    r"\b(?:laid off|redundan|resigned|quit my job|my notice period|new chapter)\b",
    r"\b(?:we're hiring|now hiring|join our team)\b",
]


def check_negativity(text: str) -> CheckResult:
    findings: list[str] = []
    lowered = text.lower()

    for actor in _NAMED_ACTORS:
        for m in re.finditer(re.escape(actor), lowered):
            window = lowered[max(0, m.start() - 90): m.end() + 90]
            hits = [p for p in _PEJORATIVES if p in window]
            if hits:
                findings.append(f"{actor!r} appears near {hits!r} — criticising a named actor")

    for pat in _SUBTWEET:
        if re.search(pat, lowered):
            findings.append(f"reads as subtweeting/vague-posting → {pat!r}")
    for pat in _EMPLOYMENT:
        if re.search(pat, lowered):
            findings.append(f"touches employment status → {pat!r}")

    return CheckResult("negativity", not findings, findings)


# ------------------------------------------------- 3. politics/religion

_FORBIDDEN_TOPICS = [
    "election", "labor party", "liberal party", "greens party", "referendum",
    "prime minister", "parliament", "senator", "immigration policy", "voting",
    "left-wing", "right-wing", "woke", "culture war", "gender politics",
    "abortion", "religion", "religious", "christian", "muslim", "jewish",
    "hindu", "buddhist", "church", "mosque", "temple", "prayer", "god's plan",
    "blessed by god", "tariff war", "geopolit",
    # AI-job-loss-as-blame framing
    "stealing jobs", "killing jobs", "destroying jobs", "ai took my job",
    "replacing humans", "made redundant by ai",
]


def check_politics_religion(text: str) -> CheckResult:
    lowered = text.lower()
    findings = [f"forbidden topic → {t!r}" for t in _FORBIDDEN_TOPICS if t in lowered]
    return CheckResult("politics-religion", not findings, findings)


# --------------------------------------------------------- 4. statistics

# Numbers that are allowed without a source: they are not claims about the world.
_BENIGN = re.compile(
    r"""(?x)
    \b\d{1,2}(?::\d{2})?\s?(?:am|pm)\b        # 7am, 4:30pm
  | \b(?:one|two|three|four|five|six|seven|eight|nine|ten)\b
  | \b\d{1,2}\s?(?:st|nd|rd|th)\b            # 3rd
  | \b(?:19|20)\d{2}(?:\s?[-–/]\s?\d{2,4})?\b        # 2024-25, 2026
  | \bversion\s?\d+\b
  | \bGA4\b | \bB2B\b
    """,
    re.I,
)
_NUMBER = re.compile(r"(?<![\w$])(\d[\d,]*(?:\.\d+)?)\s*(%|per cent|percent|x|k|m)?", re.I)


def check_stats(text: str, verified_numbers: list[str], allowed_personal: list[str] | None = None) -> CheckResult:
    """Every number that reads as a claim must be on the verified list.

    `verified_numbers` are strings confirmed by a live search THIS RUN.
    `allowed_personal` are facts from Roshini's own context block (e.g. "10").
    """
    allowed = {n.strip().lower().rstrip("%") for n in verified_numbers}
    allowed |= {n.strip().lower().rstrip("%") for n in (allowed_personal or [])}

    findings: list[str] = []
    scrubbed = _BENIGN.sub(" ", text)
    for m in _NUMBER.finditer(scrubbed):
        raw = m.group(1).replace(",", "")
        if raw.lower() in allowed:
            continue
        findings.append(
            f"unverified number {m.group(0).strip()!r} — verify it in-run or cut the claim"
        )

    n = len(verified_numbers)
    if n > 2:
        findings.append(f"{n} statistics; the cap is two (one is usually stronger)")
    return CheckResult("stats", not findings, findings)


# ------------------------------------------------------- craft / format

BANNED_PHRASES = [
    "let that sink in", "here's the thing", "game-changer", "game changer",
    "in today's fast-paced", "i was recently reminded", "unpopular opinion",
    "hot take", "the result?", "plot twist", "deep dive", "leverage",
    "fundamentally", "tag someone who", "stop scrolling", "let me be honest",
    "confession:", "what nobody tells you", "what most people miss",
    "the real question is", "it's not about", "needle-moving", "circle back",
]
_REVEAL_BRIDGE = re.compile(r"\b(?:the (?:result|outcome|answer|kicker|twist))\?\s", re.I)
_NOT_X_BUT_Y = re.compile(r"\bit(?:'s| is) not\b[^.?!]{3,60}\bit(?:'s| is)\b", re.I)
_STOP_X_START_Y = re.compile(r"\bstop\s+\w+ing\b[^.?!]{0,40}\bstart\s+\w+ing\b", re.I)


def check_craft(text: str) -> CheckResult:
    findings: list[str] = []
    lowered = text.lower()
    lines = [l for l in text.splitlines() if l.strip()]

    n = len(text)
    if n > 1600:
        findings.append(f"{n} chars — hard ceiling is 1,600")
    elif not (900 <= n <= 1300):
        findings.append(f"{n} chars — target is 900–1,300 (advisory)")

    for p in BANNED_PHRASES:
        if p in lowered:
            findings.append(f"banned phrase → {p!r}")
    if _REVEAL_BRIDGE.search(text):
        findings.append("reveal-bridge construction")
    if _NOT_X_BUT_Y.search(text):
        findings.append("'it's not X, it's Y' framing")
    if _STOP_X_START_Y.search(text):
        findings.append("'stop X, start Y' framing")

    if lines:
        hook = lines[0]
        if hook.rstrip().endswith("?"):
            findings.append("hook is a question (−34% median likes); move it to the close")
        if hook.isupper():
            findings.append("all-caps hook")
        if any(unicodedata.category(ch) == "So" for ch in hook):
            findings.append("emoji in the hook")
        if len(hook) > 210:
            findings.append(f"hook is {len(hook)} chars; it must survive the 210-char fold")

    tags = re.findall(r"(?<!\w)#\w+", text)
    if len(tags) > 3:
        findings.append(f"{len(tags)} hashtags — max 3")
    if re.search(r"https?://|www\.", text):
        findings.append("link in the post body — links go in the first comment")

    emoji = [ch for ch in text if unicodedata.category(ch) == "So"]
    if len(emoji) > 1:
        findings.append(f"{len(emoji)} emoji — max one, and only if it earns its place")

    # Australian English
    for us, au in [("optimize", "optimise"), ("personalize", "personalise"),
                   ("analyze", "analyse"), ("organize", "organise"),
                   ("realize", "realise"), ("behavior", "behaviour")]:
        if re.search(rf"\b{us}", lowered):
            findings.append(f"US spelling {us!r} — use {au!r}")

    return CheckResult("craft", not findings, findings)


def sanitise(text: str) -> str:
    """Strip smart quotes and non-breaking spaces before publishing."""
    for bad, good in [("‘", "'"), ("’", "'"), ("“", '"'),
                      ("”", '"'), (" ", " "), ("–", "-"),
                      ("…", "...")]:
        text = text.replace(bad, good)
    return text


def run_gate(text: str, verified_numbers: list[str],
             allowed_personal: list[str] | None = None) -> GateReport:
    return GateReport([
        check_clients(text),
        check_negativity(text),
        check_politics_religion(text),
        check_stats(text, verified_numbers, allowed_personal),
        check_craft(text),
    ])
