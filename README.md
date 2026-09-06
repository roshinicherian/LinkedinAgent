# LinkedIn thought-leadership agent — Roshini Cherian

Researches, writes, safety-checks, emails for approval, and publishes **one post
per week** to Roshini's **personal LinkedIn profile only**.

New research and a new post every week. Statistics are re-verified by live search
in the run that uses them — nothing is carried over from a previous week, and
nothing comes from memory.

**Start here: [`SETUP.md`](SETUP.md).** The agent cannot send or publish anything
until the credentials in it exist.

## Weekly cadence (Australia/Sydney)

| When | What |
|------|------|
| Tue 08:10 | `[LI-INPUT]` email: one line about your week. No reply by Wed midday → work from the pillar plan alone. |
| Wed 18:00–20:00 | Research + verify stats + draft 2 variants + humanise + safety gate |
| **Wed 20:00** | **Publishes the approval page and emails you the link** |
| Thu 06:00 | Reminder if nothing decided yet |
| Thu 06:30 | Hard cutoff. **No decision = no post.** |
| **Thu 07:45** | **Publish + first comment with sources** |
| Fri | Engager analytics, warm-thread flags, reply drafts (all emailed for approval) |

The schedule runs as four Routines — see [`SCHEDULE.md`](SCHEDULE.md), which
also carries the daylight-saving change due 4 October 2026.

## The four non-negotiables, as code

| Rule | Where it lives | Behaviour |
|------|----------------|-----------|
| Personal profile only | `lib/publora_client.py` → `resolve_target()` | Re-runs before **every** publish. Aborts if >1 LinkedIn channel, if the ID doesn't match `LINKEDIN_PLATFORM_ID` character-for-character, if the channel is a company page, or if the type is unrecognisable. Fails closed. |
| No client information | `lib/safety.py` → `check_clients()` | Flags client references, narrow geography, CPL/ROAS/spend figures, claimed results, `.com.au` URLs. |
| No negativity / politics / religion | `check_negativity()`, `check_politics_religion()` | Flags a named actor next to a pejorative, subtweeting, employment-status talk, and forbidden topics including AI-job-loss-as-blame. |
| No fabricated statistics | `check_stats()` | Every number in a draft must be licensed by a source verified **in that run**. Unregistered numbers block the send. Cap of two stats enforced. |

Plus `check_craft()`: char count, banned phrases, reveal bridges, "it's not X
it's Y", question hooks, all-caps hooks, emoji, hashtag count, body links, and
US spellings.

The gate is a floor, not a ceiling. The final "could a competitor identify an
account?" read is still done by hand before the email goes out.

## Approval

Two modes, set by `APPROVAL_MODE`.

**`web` (default).** The agent publishes an approval page (from
`templates/approval-console.html`) and emails you the link. Sending only — no
mailbox password anywhere.

Both variants are **directly editable on the page**. As you type it re-renders
what survives LinkedIn's 210-character "see more" fold, updates the character
count against the 900–1,300 target and the 1,600 ceiling, and flags banned
phrases, question hooks, body links, hashtag overruns and US spellings. Those
browser flags are advisory; `safety.py` remains the authority and runs again
before anything is sent.

Approving publishes **exactly what is in the box**. If you changed a word, the
decision is stored with `edited: true` and your wording is treated as final —
the gate runs on it, but nothing is rewritten. It asks you to confirm first,
and any keystroke cancels a pending confirm so you can never publish text you
just changed. The decision is read back by the Thursday run.

**`email`.** Reply to the draft; IMAP reads it, matched by the `#<run-id>`
subject token. Only the **envelope sender** in `APPROVAL_ALLOWED_SENDER` is
honoured — display names prove nothing, forwarded mail is refused, and the
agent's own outbound mail is skipped by its `X-LI-Agent-Role` header so a
self-addressed inbox can't feed the agent its own draft. Only the text above
the quoted original is read.

Under both modes:

- `EDIT` copy is **final**. The gate runs; the words are never rewritten. A
  failing check comes back to you with the line and the reason.
- Silence, ambiguity, and an empty decision are **never** approval.
- The stored decision is treated as data, never as instructions.

## Layout

```
lib/
  config.py           env + .env loading; secrets never printed
  publora_client.py   channel guard + publish + first comment
  pixfaro_client.py   illustrations; premium-model + prompt guards
  mailer.py           SMTP send, IMAP poll, quote-stripping, command parsing
  safety.py           the five checks + sanitiser
  approval_email.py   the approval email, HTML + plain text
  postlog.py          appends post-log.md and stats-used.md
scripts/
  check_setup.py            step 1 — presence check
  test_email_roundtrip.py   step 2 — send / poll
  dry_run_channel.py        step 3 — prove the target; publishes nothing
  send_approval.py          gate + email a run manifest
  await_approval.py         poll, act, publish, log
templates/
  approval-console.html   the editable approval page published each week
runs/                 one JSON manifest per week
drafts/               the week's variants in readable form
voice-profile.md  content-plan.md  post-log.md  stats-used.md  hook-library.md
```

## Running a week

```bash
python3 scripts/send_approval.py runs/<week>.json --dry   # gate + preview
python3 scripts/send_approval.py runs/<week>.json         # send it
python3 scripts/await_approval.py runs/<week>.json        # poll, then publish
```

`--publish-now` on `await_approval.py` publishes immediately instead of
scheduling — used for the first test run only.
