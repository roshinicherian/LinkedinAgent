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

**Not into the Claude chat** — anything pasted there is stored in the
conversation and lost when the container recycles.

It is **not** under Settings, which is why it's hard to find. There is no
settings page and no direct URL for it. The path is:

1. Go to **https://claude.ai/code**
2. Look at the **row directly above the message box** where you type.
3. Click the small **cloud icon showing the environment's name** — it will say
   **Default**. That opens the environment selector.
4. **Hover over "Default"** in that menu — a **gear / settings icon** appears on
   the right. Click it.
5. The dialog has a **Environment variables** box. It takes `.env` format —
   one `KEY=value` per line, so paste the whole block below at once rather than
   adding them one at a time.
6. Save.

Paste exactly this, replacing the three bracketed values:

```
PUBLORA_API_KEY=<your Publora API key>
LINKEDIN_PLATFORM_ID=<the LinkedIn channel ID from Publora>
APPROVAL_MODE=web
APPROVAL_EMAIL=roshiniaiagent@gmail.com
APPROVAL_FROM=roshiniaiagent@gmail.com
APPROVAL_ALLOWED_SENDER=roshiniaiagent@gmail.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=roshiniaiagent@gmail.com
SMTP_PASSWORD=<your 16-character Gmail App Password, no spaces>
TIMEZONE=Australia/Sydney
```

That is the complete list — eight real settings. **No IMAP password and no IMAP
setting appears anywhere**, because of section 4b.

Two things worth knowing:

- Anyone who can use the environment can read these values. That is fine for a
  Gmail app password scoped to one throwaway account, and it is why the app
  password (revocable in one click) is the right credential rather than your
  Google password.
- A running session copies the values **once, at startup**. This session will
  not see them until it is restarted or a new session starts, so after saving,
  start a fresh session or tell me and I'll work around it.

### Option B — a local `.env` (only if you run this on your own machine)

    cp .env.example .env      # most values are already filled in
    pip install -r requirements.txt

`.env` is gitignored and must never be committed.

## 4b. Approving on a web page instead of by email

You do not need IMAP at all. Approval happens on a **published approval page**:

1. Wednesday night the agent researches, drafts, safety-gates, then publishes an
   approval page and **emails you the link** (sending only — that is what
   `SMTP_*` is for, and it needs no mailbox reading).
2. You open the link on your phone. The page shows the resolved publish target,
   both variants rendered with LinkedIn's 210-character "see more" fold drawn in,
   the safety-gate results, the sources, and the first comment.
3. You tap **Approve A**, **Approve B**, **Skip**, or paste your own copy. It
   asks you to confirm, because approving publishes for real.
4. Your decision is written to the page's own store.
5. Thursday 07:45 AEST the agent reads that decision and publishes.

Nothing is published without a decision recorded on that page. Silence still
means no post.

If you ever want the email-reply route back, set `APPROVAL_MODE=email` and add
the four `IMAP_*` settings. The same Gmail app password covers both; IMAP just
needs enabling under Gmail → See all settings → Forwarding and POP/IMAP.

## 5. Brand assets

Done — brand colour is `#0F4C81` (deep blue, deliberately not LinkedIn's own
blue so assets read as yours), handle `roshini-cherian`. Change either any time.

## 6. Then run, in order

    python3 scripts/check_setup.py            # all eight settings green?
    python3 scripts/send_test_email.py        # one email lands in your inbox
    python3 scripts/dry_run_channel.py        # publishes nothing, ever

The last one prints the connected channel's name, ID and type, and refuses to
continue unless exactly one LinkedIn channel is connected, its ID matches
`LINKEDIN_PLATFORM_ID` character-for-character, and it is a personal profile.
**Confirm the name it prints is you.** Only then does anything get published.

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
