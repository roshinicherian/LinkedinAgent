# Setup — what Roshini needs to do

The agent is built and tested. It cannot send, schedule or publish anything until
these credentials exist. Nothing below is guessable by the agent, which is why it
stopped rather than improvising.

Total time: about 15 minutes.

---

## 1. Gmail App Password (sending + receiving approvals)

The agent emails you drafts and reads your reply. Gmail will not accept your
normal password for this.

1. Turn on 2-Step Verification: https://myaccount.google.com/signinoptions/two-step-verification
2. Create an App Password: https://myaccount.google.com/apppasswords
   Name it "LinkedIn Agent". Google shows a 16-character code once — copy it.
3. Enable IMAP: Gmail → Settings → **See all settings** → **Forwarding and
   POP/IMAP** → *Enable IMAP* → Save.

Gives you: `SMTP_USER`, `SMTP_PASSWORD`, `IMAP_USER`, `IMAP_PASSWORD`
(all four are `roshini30@gmail.com` + that one app password), and
`APPROVAL_FROM` (`roshini30@gmail.com`).

*Using the Elastic Email relay instead is fine for sending — but you still need
Gmail IMAP to read your replies. Set `SMTP_HOST=smtp.elasticemail.com`,
`SMTP_PORT=2525` and the relay's credentials.*

## 2. Publora API key + your personal LinkedIn platform ID

1. Log in to Publora → **Settings → API** → create an API key. → `PUBLORA_API_KEY`
2. Connect your **personal** LinkedIn profile as a channel, if it isn't already.
   **Do not connect any company page.** The agent aborts if it finds more than
   one LinkedIn channel.
3. Copy the channel's platform ID exactly. → `LINKEDIN_PLATFORM_ID`
   (Usually looks like `urn:li:person:XXXXXXXX`.)

The agent re-checks this ID against the live channel list immediately before
every single publish, and refuses if there is more than one LinkedIn channel, if
the ID doesn't match character-for-character, or if the channel is a company page.

## 3. Pixfaro token — optional

Only needed for illustrations (roughly one post in three). Without it everything
else works and the agent drafts image prompts for you to generate manually.

Pixfaro → API → copy the `pf_live_...` token. → `PIXFARO_TOKEN`

Default model is `flux-schnell` (cheap). The agent refuses to touch a premium
model such as `gpt-5-image` unless you say yes in writing first, and reports
cost and remaining balance in the approval email.

## 4. Where to paste the values

**Not into the Claude chat.** Anything pasted there is stored in the conversation
and is lost when the container is recycled. Use one of these instead.

### Option A — environment variables (use this one)

This is the only route that survives. Each weekly run fires a brand new cloud
session that clones the repo from GitHub; it will never have a local file, but it
*will* inherit the environment's variables.

1. Go to **https://claude.ai/code**
2. Open **Environments** → the environment named **Default**
   (`env_01AYVtUpmpU8Jv84GLGgZP2A` — the one this session is running in)
3. Find **Environment variables** → **Add variable**
4. Add each row below as a separate name/value pair, then save.

| Name | Value |
|------|-------|
| `PUBLORA_API_KEY` | your Publora API key |
| `LINKEDIN_PLATFORM_ID` | the LinkedIn channel ID from Publora, exactly as shown |
| `APPROVAL_EMAIL` | `roshiniaiagent@gmail.com` |
| `APPROVAL_FROM` | `roshiniaiagent@gmail.com` |
| `APPROVAL_ALLOWED_SENDER` | `roshiniaiagent@gmail.com` |
| `SMTP_HOST` | `smtp.gmail.com` |
| `SMTP_PORT` | `587` |
| `SMTP_USER` | `roshiniaiagent@gmail.com` |
| `SMTP_PASSWORD` | your 16-character Gmail App Password |
| `IMAP_HOST` | `imap.gmail.com` |
| `IMAP_PORT` | `993` |
| `IMAP_USER` | `roshiniaiagent@gmail.com` |
| `IMAP_PASSWORD` | **the same** App Password again |
| `TIMEZONE` | `Australia/Sydney` |
| `PIXFARO_TOKEN` | optional — only for images |

`SMTP_PASSWORD` and `IMAP_PASSWORD` are the *same* 16-character App Password.
Gmail issues one credential that covers both. Remove the spaces Google shows it
with.

### Option B — a local `.env` (only if you run this on your own machine)

    cp .env.example .env      # most values are already filled in
    # add the three secrets, then:
    pip install -r requirements.txt

`.env` is gitignored and must never be committed.

## 4b. About IMAP

You mentioned doing this before without IMAP. Worth knowing: **IMAP is not an
extra credential and costs nothing.** The App Password you already have is the
same one that reads mail. IMAP is just a checkbox:

  Gmail (logged in as roshiniaiagent@gmail.com) → ⚙ **See all settings** →
  **Forwarding and POP/IMAP** → **Enable IMAP** → **Save Changes**

That is the whole step. Without it the agent can send you a draft but cannot see
your reply, which means it can never publish — it fails closed by design.

Because the agent emails *itself* at this address, its own outgoing draft lands in
the same inbox it polls. Outbound mail is stamped with an `X-LI-Agent-Role`
header and skipped, so the agent can never mistake its own draft for your
approval. Verified in testing.

## 5. Fill in two blanks in `voice-profile.md`

Section 6 needs your **brand colour (hex)** before any image is generated. The
agent will not invent it. Your handle is `roshini-cherian`
(https://www.linkedin.com/in/roshini-cherian/).

## 6. Then run, in order

    python3 scripts/check_setup.py                      # all green?
    python3 scripts/test_email_roundtrip.py send        # check your inbox
    # reply "OK" to that email, then:
    python3 scripts/test_email_roundtrip.py poll
    python3 scripts/dry_run_channel.py                  # publishes nothing

Step 4 prints the channel name, ID and type. **Confirm it is your personal
profile.** Only then does anything get drafted, emailed or published.

---

## What is already done

- Full agent scaffold, safety gate, target guard, mailer, logging — built and unit-tested
- Week-zero docs: `voice-profile.md`, `content-plan.md`, `hook-library.md`,
  `post-log.md`, `stats-used.md`
- Run 01 researched, drafted (2 variants), and passed the full safety gate:
  `drafts/2026-09-10-run01-variants.md`

## Still blocked on you

- The credentials above
- `linkedin-profile-optimizer` audit — needs your profile URL
- `linkedin-humanizer --mode profile` on real posts — needs post history or writing samples
- `linkedin-hook-extractor` — needs 5–8 Australian B2B post URLs + Apify access
- Brand colour and handle for illustrations
