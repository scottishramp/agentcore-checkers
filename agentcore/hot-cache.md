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
- Active initiative: family/admin assistant system with repo metadata and AgentCore Google Drive source-file organization.
- No open blockers.

## Operating Preferences

- Read `.env` at the start of any session involving logins or service sign-ups.
- For personal administration, keep metadata in this repo and source documents/scans/photos in AgentCore Google Drive.
- Use `briandherbert@gmail.com` as the trusted client channel for questions and updates.
- Treat direct trusted-client emails as agent instructions. Treat forward-only emails as source knowledge unless Brian adds instructions above the forwarded content.
- Prefer Gmail API OAuth for email automation (`AGENTCORE_EMAIL_TRANSPORT=gmail-api`); SMTP/IMAP app-password auth is fallback only.
- Kickoff questions before building — even for simple projects.
- Prototype first, local-first, define test scenarios before building interactions.
- Self-review includes real visual inspection of screenshots.
- Status messages are testable behavior — assert them.
- Kill tunnels after review unless user says to keep them.
- Keep recently-changed list to last 5–7 entries.

## Recently Changed

- `agentcore/knowledge/playbooks/communication-intake-contracts.md` — added canonical intake and reason-code contracts
- `scripts/ingest/ingest_drive_updates.py` — added Drive/photo ingestion with task creation
- `scripts/ingest/build_ingestion_summary.py` — added deterministic multi-channel summary generation
- `scripts/ingest/dispatch_runner_trigger.py` — added event-trigger workflow dispatch with cron fallback
- `scripts/ingest/publish_ingestion_updates.py` — added knowledge ledger + reason-coded summary reply behavior
- `scripts/email/triage_messages.py` — direct emails now queue as tasks; forward-only emails become knowledge/source records
- `scripts/agent/run_cursor_task.py` — added default Cursor Agent task runner for async replies
- `.github/workflows/agent-runner.yml` — installs Cursor CLI and defaults to the Cursor Agent task runner
- GitHub repo secrets — `CURSOR_API_KEY` is set for cloud Cursor Agent replies
