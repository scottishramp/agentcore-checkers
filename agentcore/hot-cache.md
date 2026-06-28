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
- Delivered: Telegram-only chat via `@AgentCoreFam_bot`. Fast Gemini replies on Vercel; every message queued to Upstash; GitHub Actions triage + Cursor on schedule; Telegram working/done notifications; optional Vercel redeploy after knowledge commits. Google Chat removed.
- Delivered: runner notification hardening. If an async task's repo push is rejected, the runner should still send the Email/Chat response and continue ledger/finalization steps.
- Active initiative: Brian personal operating system and family/admin assistant system with repo metadata and AgentCore Google Drive source-file organization.
- Operating hub: `agentcore/knowledge/projects/personal-operating-system.md` covers diet, scheduling, kid school logistics, app ideas, and personal management defaults.
- System architecture hub: `agentcore/knowledge/architecture/system-architecture.md` documents communication surfaces, workflows, hosted endpoints, polling cadence, data stores, secrets, blockers, and architecture update requirements.
- Google access inventory: Gmail, Brian shared Calendar, and shared Drive/Docs are live. Maps/Keep/Photos limitations unchanged.
- Open blockers: Google Keep note content unavailable; broad Google Photos library reads unavailable.

## Operating Preferences

- Read `.env` at the start of any session involving logins or service sign-ups.
- For personal administration, keep metadata in this repo and source documents/scans/photos in AgentCore Google Drive.
- Google operating model: know what Brian shares with `scottishramp@gmail.com`, treat Brian-shared resources as read surfaces unless explicit edit authority is granted, and write/organize durable artifacts in AgentCore's own Google space.
- Use `briandherbert@gmail.com` and Brian's direct Google Chat with AgentCore as trusted client channels for questions, updates, and task requests.
- Treat direct trusted-client emails as agent instructions. Treat forward-only emails as source knowledge unless Brian adds instructions above the forwarded content.
- Fast chat via `@AgentCoreFam_bot`; send `version` for live router semver (currently v2.2.0). Async agent runs on GitHub Actions schedule, not per message.
- If Brian says exactly `sync`, use the project `github-sync` skill to sync local and remote GitHub state with Cursor agent judgment. Do not rely on a custom sync script.
- For email chains, process only when Brian is the latest meaningful sender in the Gmail thread. AgentCore's reply should be the last thread message until Brian replies again.
- Trusted-client email tasks may self-update this repo for AgentCore behavior, integrations, workflows, scripts, rules, docs, and knowledge. Successful GitHub Actions workspace edits are committed and pushed before the completion email.
- For substantial AgentCore system work, read and maintain `agentcore/knowledge/architecture/system-architecture.md`; update it whenever communication channels, workflows, hosted endpoints, OAuth scopes, polling cadence, queue semantics, data stores, or durable knowledge locations change.
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

- Telegram photo+caption support (v2.2.0): fast agent assigns photo labels, writes detailed descriptions, registry maps label→Drive; Cursor replies with label+URL.
- Architecture v2.0.0: Telegram-only chat; async Cursor via scheduled inbox triage; Google Chat removed.
- Upstash Redis conversation history live for Telegram fast router (v1.3.0); health check reports `history_configured`.
- Added chatbot versioning (`chatbot-version.json`, `version` command → v1.2.0) with architecture docs and health-check injection.
- Added fast-router request logging and compact recent Chat automation context; deployed to Vercel. Created Brian-owned Cloud project `agentcore-chat-brian`; setup is paused at Brian browser passkey sign-in.
- Deployed Google Chat fast router to Vercel: `https://agentcore-fast-router.vercel.app/api/agentcore-chat`, set production secrets, saved Google Chat API HTTP endpoint config, and documented the remaining visibility/live-test blocker.
- Added Google Photos Picker support path: OAuth helper requests `photospicker.mediaitems.readonly`, `scripts/photos/picker_session.py` can create/get/list/delete Picker sessions after consent refresh, and docs/blockers explain the interactive flow.
- `agentcore/knowledge/projects/personal-operating-system.md` and `agentcore/knowledge/people/brian-herbert.md` — recorded current Google access inventory: Gmail, Chat, Calendar, Drive/Docs active; Maps share emails visible but no live-location API; Keep/Photos limitations remain.
- `agentcore/knowledge/projects/personal-operating-system.md` — created operating hub for diet, scheduling, kid school logistics, app ideas, personal management, intake defaults, and sensitivity defaults.
- `agentcore/knowledge/people/brian-herbert-food-log.md` — logged 2026-06-26 breakfast (2 eggs, Colby jack, sourdough) + lunch (4 slices pepperoni bread, Twix, Fritos Twists, cookie); ~2,030 cal so far.
- Food check-ins at noon and 6 PM ask "What'd you eat since last time?" (ids `food-checkin-midday`/`food-checkin-evening`). `send_scheduled_messages.py` migrates legacy dedup keys (`food-checkin-dinner` → `food-checkin-evening`) so renamed ids do not re-send within the same window.
- Food-log reply style (Brian, 2026-06-26): do NOT repeat Brian's food back to him. Log the meal and reply with totals/notes only — never echo the items he just reported.
- Fixed duplicate Chat messages: proactive sends now owned ONLY by agent-runner; dedup state is git-tracked.

## Operating Note: proactive Chat sends

- Only `agent-runner.yml` may send proactive/scheduled Chat messages. It has `contents: write` and commits the git-tracked dedup state `agentcore/knowledge/communications/scheduled-messages-state.json`.
- `email-sync.yml` is `contents: read` and must NOT send proactive messages (it cannot persist dedup state, which caused duplicates).
