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
- Delivered: Calendar readonly access. Brian shared `briandherbert@googlemail.com` with `scottishramp@gmail.com`; AgentCore can list it through Google Calendar API as `reader` and read upcoming events.
- Delivered: broad admin-assistant OAuth bundle. AgentCore has read access for shared Gmail/Drive/Calendar/Workspace/Contacts surfaces and write access for AgentCore-owned Drive/Docs/Sheets/Slides/Tasks/app-created Photos artifacts.
- Delivered: Google Chat browser/API send and polling baseline. AgentCore can send Chat DMs, fetch Brian's DM messages, queue them as async tasks, and reply back into Chat after runner completion.
- Delivered: bounded pseudo-synchronous Google Chat mode in GitHub Actions. For conversational Chat tasks during 09:00-20:00 `America/Chicago`, the runner can keep polling/replying for a short session.
- Delivered: runner notification hardening. If an async task's repo push is rejected, the runner should still send the Email/Chat response and continue ledger/finalization steps.
- Active initiative: family/admin assistant system with repo metadata and AgentCore Google Drive source-file organization.
- Brian family context: Brian was born 1983-09-10; married Kristin Herbert on 2006-05-27; children are Daniel, Nathan, Ezra, Silver, and Levi.
- Open blockers: Google Keep note content is not available to AgentCore's personal Google account through the official Keep API; broad unattended Google Photos library reads are no longer available through the official Library API.

## Operating Preferences

- Read `.env` at the start of any session involving logins or service sign-ups.
- For personal administration, keep metadata in this repo and source documents/scans/photos in AgentCore Google Drive.
- Google operating model: know what Brian shares with `scottishramp@gmail.com`, treat Brian-shared resources as read surfaces unless explicit edit authority is granted, and write/organize durable artifacts in AgentCore's own Google space.
- Use `briandherbert@gmail.com` and Brian's direct Google Chat with AgentCore as trusted client channels for questions, updates, and task requests.
- Treat direct trusted-client emails as agent instructions. Treat forward-only emails as source knowledge unless Brian adds instructions above the forwarded content.
- Treat direct Google Chat messages from Brian as agent instructions by default; jobs poll the Brian DM space `spaces/6RZ69yAAAAE`, skip AgentCore-authored messages, queue Brian-authored text as tasks, and reply naturally in Chat.
- For short conversational Chat messages during 09:00-20:00 `America/Chicago`, the runner may keep a bounded sync loop open (default 15 minutes, 20 second polling) to continue the conversation inside one GitHub Actions runtime.
- If Brian says exactly `sync`, use the project `github-sync` skill to sync local and remote GitHub state with Cursor agent judgment. Do not rely on a custom sync script.
- For email chains, process only when Brian is the latest meaningful sender in the Gmail thread. AgentCore's reply should be the last thread message until Brian replies again.
- Trusted-client email tasks may self-update this repo for AgentCore behavior, integrations, workflows, scripts, rules, docs, and knowledge. Successful GitHub Actions workspace edits are committed and pushed before the completion email.
- Commit, push, and deployment/activation are implicit parts of any completed change unless Brian explicitly says to keep changes local, avoid committing, avoid pushing, or not deploy.
- Google Keep share notification `Stage` is visible in Gmail from `keep-shares-dm-noreply@google.com`, but reading note content through the official Keep API is not available for AgentCore's personal Google account.
- Google Photos no longer permits broad unattended library reads through the official Library API; AgentCore can manage app-created Photos media, while Brian photo intake should use Drive/email/share workflows unless a future Photos Picker flow is built.
- Prefer Gmail API OAuth for email automation (`AGENTCORE_EMAIL_TRANSPORT=gmail-api`); SMTP/IMAP app-password auth is fallback only.
- Kickoff questions before building — even for simple projects.
- Prototype first, local-first, define test scenarios before building interactions.
- Self-review includes real visual inspection of screenshots.
- Status messages are testable behavior — assert them.
- Kill tunnels after review unless user says to keep them.
- Keep recently-changed list to last 5–7 entries.

## Recently Changed

- `.github/workflows/agent-runner.yml` — commit/push steps made non-blocking so Chat replies still send after push rejection.
- `.cursor/skills/github-sync/SKILL.md` — Cursor-based GitHub sync skill added.
- `.cursor/rules/admin-assistant.mdc` — bare `sync` command mapped to the GitHub sync skill.
- `scripts/chat/synchronous_loop.py` — bounded pseudo-synchronous Chat loop added.
- `scripts/email/claim_next_task.py` — optional `source_kind` filter added for Chat-only loop claims.
