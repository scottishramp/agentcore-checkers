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
- Delivered: direct email replies now send the Cursor Agent output as the reply body instead of a task-status report. Routine ingestion errors are logged but no longer emailed under the default `changes` policy.
- Active initiative: family/admin assistant system with repo metadata and AgentCore Google Drive source-file organization.
- Open blocker: CI Drive ingestion OAuth secret lacks Drive readonly scope; email answering still works.

## Operating Preferences

- Read `.env` at the start of any session involving logins or service sign-ups.
- For personal administration, keep metadata in this repo and source documents/scans/photos in AgentCore Google Drive.
- Use `briandherbert@gmail.com` as the trusted client channel for questions and updates.
- Treat direct trusted-client emails as agent instructions. Treat forward-only emails as source knowledge unless Brian adds instructions above the forwarded content.
- For email chains, process only when Brian is the latest meaningful sender in the Gmail thread. AgentCore's reply should be the last thread message until Brian replies again.
- Commit, push, and deployment/activation are implicit parts of any completed change unless Brian explicitly says to keep changes local, avoid committing, avoid pushing, or not deploy.
- Prefer Gmail API OAuth for email automation (`AGENTCORE_EMAIL_TRANSPORT=gmail-api`); SMTP/IMAP app-password auth is fallback only.
- Kickoff questions before building — even for simple projects.
- Prototype first, local-first, define test scenarios before building interactions.
- Self-review includes real visual inspection of screenshots.
- Status messages are testable behavior — assert them.
- Kill tunnels after review unless user says to keep them.
- Keep recently-changed list to last 5–7 entries.

## Recently Changed

- `scripts/email/send_task_status.py` — direct email `done`/`snag` replies are human replies, not status reports
- `.github/workflows/agent-runner.yml` — removed per-task running notification email to reduce noise
- `scripts/agent/run_cursor_task.py` — prompts Cursor Agent to output only the email body for direct email tasks
- `scripts/ingest/publish_ingestion_updates.py` — default `changes` policy no longer emails on errors alone
- `agentcore/blockers.md` — reopened Drive CI OAuth scope blocker
- `.cursor/rules/admin-assistant.mdc` and `AGENTS.md` — broadened standing instruction so completed changes should be committed, pushed, and deployed/activated unless Brian says otherwise
- `agentcore/knowledge/communications/email-thread-ledger.json` — stores message/thread/task/response IDs without email bodies
