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

## 4. Tell the agent the values

**If you're running this in Claude Code on the web** (recommended, since the
schedule needs to survive this session): add them as **environment variables on
the environment**, not as a file. A fresh cloud session clones the repo but will
not have a local `.env`.

  claude.ai/code → your environment → **Environment variables** → add each key.

**If you're running locally:**

    cp .env.example .env
    # fill it in, then:
    pip install -r requirements.txt

`.env` is gitignored. Never commit it, and the agent never prints, logs or
emails a credential.

## 5. Fill in two blanks in `voice-profile.md`

Section 6 needs your **brand colour (hex)** and **LinkedIn handle** before any
image is generated. The agent will not invent them.

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
