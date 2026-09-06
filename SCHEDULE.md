# Schedule

Four Routines run the weekly cycle. They fire a fresh Claude session each time,
so they survive this container being reclaimed. Manage them at
claude.ai → Routines.

| Routine | Sydney time | UTC cron | Trigger ID |
|---------|-------------|----------|------------|
| Ask for your week — `[LI-INPUT]` | Tue 08:10 | `10 22 * * 1` | `trig_01XTH9eYf5UsG3xoUnUjxu16` |
| **Research, draft, email — `[LI-DRAFT]`** | **Wed 20:00** | `0 10 * * 3` | `trig_01RPX1r3qY2yyw78P8B4XvUS` |
| Reminder if no reply — `[REMINDER]` | Thu 06:00 | `0 20 * * 3` | `trig_01BJFzgJSwSWr9SczqKXV5Yd` |
| **Publish on approval only** | **Thu 07:45** | `45 21 * * 3` | `trig_01GTFSsajxvGdGikFp551nus` |

Approval cutoff is Thu 06:30 AEST. The publish routine checks for a valid reply
and does nothing if there isn't one. Silence is never approval.

Every routine's first action is `scripts/check_setup.py`. Until the credentials
in `SETUP.md` exist, each firing stops there and sends nothing — no half-runs.

## ⚠️ Daylight saving — action needed 4 October 2026

Routine crons are evaluated in **UTC**, and the times above are converted from
**AEST (UTC+10)**. Sydney moves to **AEDT (UTC+11)** on **Sunday 4 October 2026**.
Without a change, every routine would fire an hour late in local terms (the draft
email at 21:00, publishing at 08:45).

On or before 4 October, shift each cron **one hour earlier in UTC**:

| Routine | AEDT cron (from 4 Oct) |
|---------|------------------------|
| `[LI-INPUT]` | `10 21 * * 1` |
| `[LI-DRAFT]` | `0 9 * * 3` |
| `[REMINDER]` | `0 19 * * 3` |
| Publish | `45 20 * * 3` |

Reverse it when AEST returns on **Sunday 5 April 2027**.
