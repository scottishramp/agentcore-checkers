# AgentCore Hot Cache

Compact current-state memory for future sessions. Keep this page short. Trim "Recently Changed" to the last 5–7 entries only.

---

## AgentCore Identity

AgentCore is Brian Herbert's private administrative assistant operating in Cursor. The default job is to organize life administration, family documents, communications, reminders, research, and projects with broad autonomy.

**Primary email: `scottishramp@gmail.com`**
This is AgentCore's identity for all external communication, service sign-ups, logins, and account creation. Use it by default whenever an email is needed. Full credentials are in `.env` at the repo root (gitignored).

- Trusted client email: `briandherbert@gmail.com`
- GitHub account: `scottishramp` (signs in via Google)
- GitHub CLI: authenticated as `scottishramp` (verify with `gh auth status`)
- GitHub repo: `scottishramp/agentcore-checkers`

---

## Current State

- Delivered: checkers game → https://scottishramp.github.io/agentcore-checkers/
- Delivered: hybrid ingestion baseline (direct-email tasking, shared-with-me Drive ingestion, deterministic summary, runner dispatch trigger)
- Delivered: thread-aware email tasking. AgentCore replies into the original Gmail thread, fetch skips threads where AgentCore is already the latest sender, and `email-thread-ledger.json` records task/response idempotency metadata.
- Delivered: direct email replies now send the Cursor Agent output as the reply body instead of a task-status report. Email-only intake and routine ingestion errors are logged but no longer emailed under the default `changes` policy.
- Delivered: trusted third-party share notification intake. Google Drive/Keep share emails are accepted when the body names Brian's trusted email and the message is addressed to AgentCore.
- Active initiative: family/admin assistant system with repo metadata and AgentCore Google Drive source-file organization.
- Open blockers: Google Keep note content is not available to AgentCore's personal Google account through the official Keep API.

## Operating Preferences

- Read `.env` at the start of any session involving logins or service sign-ups.
- For personal administration, keep metadata in this repo and source documents/scans/photos in AgentCore Google Drive.
- Use `briandherbert@gmail.com` as the trusted client channel for questions and updates.
- Treat direct trusted-client emails as agent instructions. Treat forward-only emails as source knowledge unless Brian adds instructions above the forwarded content.
- For email chains, process only when Brian is the latest meaningful sender in the Gmail thread. AgentCore's reply should be the last thread message until Brian replies again.
- Trusted-client email tasks may self-update this repo for AgentCore behavior, integrations, workflows, scripts, rules, docs, and knowledge. Successful GitHub Actions workspace edits are committed and pushed before the completion email.
- Commit, push, and deployment/activation are implicit parts of any completed change unless Brian explicitly says to keep changes local, avoid committing, avoid pushing, or not deploy.
- Google Keep share notification `Stage` is visible in Gmail from `keep-shares-dm-noreply@google.com`, but reading note content through the official Keep API is not available for AgentCore's personal Google account.
- Prefer Gmail API OAuth for email automation (`AGENTCORE_EMAIL_TRANSPORT=gmail-api`); SMTP/IMAP app-password auth is fallback only.
- Kickoff questions before building — even for simple projects.
- Prototype first, local-first, define test scenarios before building interactions.
- Self-review includes real visual inspection of screenshots.
- Status messages are testable behavior — assert them.
- Kill tunnels after review unless user says to keep them.
- Keep recently-changed list to last 5–7 entries.

## Recently Changed

- `scripts/ingest/publish_ingestion_updates.py` — suppresses email-only ingestion updates and raw error dumps in notification emails
- `scripts/email/gmail_oauth_setup.py` — requests only supported Gmail/Drive OAuth scopes
- `agentcore/blockers.md` — resolved CI Drive secret blocker and corrected Keep API blocker
- `scripts/ingest/README.md` — documents Keep share notification limits
- GitHub secret `AGENTCORE_GMAIL_AUTHORIZED_USER_JSON` — refreshed from local Drive-scoped token
