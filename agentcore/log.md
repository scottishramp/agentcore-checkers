# AgentCore Log

Append-only chronological record of important AgentCore knowledge-base activity.

## [2026-04-24] setup | Initial AgentCore structure

- Created the initial Markdown knowledge-base structure for AgentCore.
- Established root agent instructions, source/knowledge/output layers, templates, index, log, blockers, and hot cache.

## [2026-04-24] project | Checkers web game

- Built a dependency-free two-player checkers game at the repository root.
- Verified JavaScript syntax, local static serving, public tunnel serving, and Cursor diagnostics.
- Published a temporary public URL: https://tiny-dolls-fly.loca.lt/
- Added project, decision, and playbook pages to capture deployment lessons.
- Recorded durable hosting as an open blocker because the workspace is not a git repo and `gh` is not authenticated.

## [2026-04-24] qa | Checkers look-and-feel pass

- Ran visual QA on desktop and mobile viewports using Playwright screenshots.
- Confirmed typography, spacing, board readability, and control hierarchy were in good shape.
- Added interaction polish in `styles.css` (button press motion, square brightness feedback, and subtle piece hover lift).

## [2026-04-24] process | Prototype-first workflow update

- Incorporated user feedback into AgentCore workflow: ask kickoff questions, run prototype phase first, test local first, self-review, then request user review.
- Updated `AGENTS.md` and `agentcore/knowledge/playbooks/public-static-web-app.md` to codify the workflow.
- Terminated active localtunnel process chain and confirmed tunnel endpoint returned `503 Tunnel Unavailable`.

## [2026-04-24] fix | Checkers board and move guidance

- Fixed board row sizing by setting explicit grid rows to prevent middle-row squish.
- Improved move guidance by highlighting movable pieces when none is selected.
- Updated blocked-piece feedback text to reduce false-error perception.
- Added explicit prototype test scenarios for this project and to the default workflow.

## [2026-04-24] qa | Automated user test suite

- Added executable user-scenario tests in `tests/checkers.user.spec.js`.
- Added manual acceptance checklist in `tests/user-test-suite.md`.
- Set up Playwright test runner (`playwright.config.js`) and npm scripts.
- Ran `npm test` and got `7 passed`.

## [2026-04-24] fix | Message precision for move guidance

- Adjusted interaction guidance to distinguish two cases:
  - blocked piece
  - mandatory capture with another piece
- Updated automated scenario assertion for mandatory-capture guidance.
- Re-ran `npm test` with `7 passed`.

## [2026-04-24] retrospective | Checkers project learnings applied to AgentCore

Synthesized all learnings from the checkers project into AgentCore:

- Rewrote `AGENTS.md` with kickoff questions, session-0 preflight, self-review standards, and a "Recurring Lessons" section covering CSS grid, asset cache-busting, tunnel process cleanup, git credential conflicts, and UX message design.
- Created `agentcore/knowledge/concepts/ux-message-design.md`: precise failure classification pattern for user-facing messages.
- Created `agentcore/knowledge/playbooks/github-pages-deployment.md`: exact steps with preflight checks, common error fixes, and account context.
- Rewrote `agentcore/knowledge/playbooks/public-static-web-app.md` to be more concrete: CSS layout checklist, visual QA checklist, cache-busting instructions, message design link, tunnel cleanup commands.
- Pruned `agentcore/hot-cache.md`: added account state section, trimmed recently-changed to last 5, added operating preferences.
- Updated `agentcore/index.md` with new concept and playbook entries.

## [2026-04-24] deploy | GitHub Pages production deployment

- Authenticated GitHub CLI as `scottishramp`.
- Initialized git repo, created public repo `scottishramp/agentcore-checkers`, pushed to `main`.
- Enabled GitHub Pages from `main` branch root.
- Confirmed live at https://scottishramp.github.io/agentcore-checkers/ (HTTP 200).
- Resolved durable hosting blocker.

## [2026-04-25] system | AgentCore email ops baseline

- Added policy and architecture docs for async communication:
  - `agentcore/knowledge/playbooks/email-ops.md`
  - `agentcore/knowledge/playbooks/email-to-cursor-cli-bridge.md`
  - `agentcore/knowledge/decisions/2026-04-25-agentcore-control-repo-topology.md`
- Implemented email automation scripts:
  - `scripts/email/send_message.py`
  - `scripts/email/fetch_inbox.py`
  - `scripts/email/triage_messages.py`
- Added durable inbox/task schemas under `agentcore/inbox/email/` and `agentcore/inbox/tasks/`.
- Added scheduled GitHub Actions workflow `.github/workflows/email-sync.yml` (every 15 minutes + manual trigger).
- Added npm command entrypoints (`email:ask`, `email:fetch`, `email:triage`, `email:sync`) and ignored local state under `.agentcore/state/`.
- Verified local send, fetch, and triage command paths; resolved async email blocker with Gmail app-password flow.

## [2026-04-25] policy | Trusted client email enforcement

- Enforced strict trusted-client behavior for email automation.
- Updated `scripts/email/send_message.py` to reject outbound recipients other than `AGENTCORE_CLIENT_EMAIL` (default `briandherbert@gmail.com`).
- Updated `scripts/email/fetch_inbox.py` to only ingest messages from `AGENTCORE_CLIENT_EMAIL`.
- Updated `agentcore/knowledge/playbooks/email-ops.md` and `scripts/email/README.md` to document the policy.

## [2026-05-25] system | Admin assistant pivot

- Reframed AgentCore's default role as Brian Herbert's private administrative assistant.
- Added persistent guidance for the repo/Drive split: metadata and operating memory in this repository, source documents and scans in AgentCore Google Drive.
- Created family/admin knowledge pages:
  - `agentcore/knowledge/people/brian-herbert.md`
  - `agentcore/knowledge/projects/family-admin-system.md`
  - `agentcore/knowledge/playbooks/drive-document-organization.md`
- Added `.cursor/rules/admin-assistant.mdc` so the role persists in Cursor sessions.
- Attempted to send the admin setup questions to `briandherbert@gmail.com`; Gmail SMTP rejected the stored credential because an app-specific password is required.
- Recorded the outbound email credential issue and the missing Drive/Docs programmatic access path as open blockers.

## [2026-05-25] system | Gmail API email transport

- Added dependency-free Gmail API OAuth helpers for send and fetch automation.
- Added `scripts/email/gmail_oauth_setup.py` to generate a refresh token through a local browser consent flow.
- Updated `send_message.py`, `fetch_inbox.py`, and `send_task_status.py` to use Gmail API in `auto` mode when OAuth credentials are configured, with SMTP/IMAP fallback preserved.
- Updated GitHub Actions workflows to pass Gmail API OAuth secrets for Cursor CLI / pipeline operation.
- Updated email operations docs and blocker status to make OAuth credentials the remaining intervention point.

## [2026-05-25] security | OAuth credential hardening and live verification

- Moved Google OAuth client credentials into `.secrets/google-oauth-client.json` and set restrictive permissions (`700` directory, `600` files).
- Stored authorized-user refresh-token payload in `.secrets/gmail-authorized-user.json` and configured `.env` to use `AGENTCORE_EMAIL_TRANSPORT=gmail-api` with file-based credentials.
- Hardened `scripts/email/gmail_oauth_setup.py` to write authorized-user JSON to disk and redact refresh tokens from default terminal output.
- Verified outbound Gmail API transport by sending a real update email to `briandherbert@gmail.com` (message id captured by script output).
- Marked the OAuth-credential blocker resolved and recorded the remaining testing-mode durability risk.

## [2026-05-25] ops | OAuth app published and token rotated

- Confirmed OAuth app publishing change to production in Google Auth Platform.
- Re-ran `npm run email:oauth -- --client-file .secrets/google-oauth-client.json` and rotated refresh-token credentials.
- Re-verified live Gmail API send after rotation (`status: sent` with Gmail message id).
- Updated blockers/hot-cache to resolve the testing-mode durability risk.

## [2026-05-25] ops | Pipeline secrets aligned to Gmail API

- Verified `gh auth` for account `scottishramp`.
- Set repository secrets for CI email transport:
  - `AGENTCORE_EMAIL`
  - `AGENTCORE_CLIENT_EMAIL`
  - `AGENTCORE_EMAIL_TRANSPORT`
  - `AGENTCORE_GMAIL_AUTHORIZED_USER_JSON`
- Confirmed secrets are present with `gh secret list`.

## [2026-05-25] system | Communication ingestion hybridization

- Defined canonical communication intake contracts across Cursor chat, email, Drive docs, and Android photo uploads:
  - `agentcore/knowledge/playbooks/communication-intake-contracts.md`
- Added normalized intake structures for new channels:
  - `agentcore/inbox/drive/`
  - `agentcore/inbox/photos/`
- Implemented Drive/photo ingestion with queue-task generation:
  - `scripts/ingest/ingest_drive_updates.py`
- Added deterministic multi-channel aggregation and routing:
  - `scripts/ingest/build_ingestion_summary.py`
  - `scripts/ingest/dispatch_runner_trigger.py`
  - `scripts/ingest/publish_ingestion_updates.py`
- Added communication knowledge ledger:
  - `agentcore/knowledge/communications/ingestion-ledger.md`
- Updated CI workflows for hybrid trigger behavior:
  - `email-sync.yml` now runs email triage + drive ingest + summary publish + event dispatch.
  - `agent-runner.yml` now ingests drive/photo channels and preserves state in cache.
- Preserved polling fallback with existing cron schedules while adding event dispatch for low-latency pickup.

## [2026-05-25] system | Direct email agent tasking

- Updated email triage policy so direct trusted-client emails queue as tasks by default.
- Added forward-only detection so forwarded emails are stored as source knowledge (`document_shared`) unless Brian adds instructions above the forwarded message.
- Added `scripts/agent/run_cursor_task.py` to run queued tasks through Cursor Agent and produce an email-ready response.
- Updated `agent-runner.yml` to install Cursor CLI and use the Cursor Agent runner by default.
- Set Drive ingestion default to `sharedWithMe` in workflows and repository secret `AGENTCORE_DRIVE_INCLUDE_SHARED_WITH_ME=true`.
- Recorded `CURSOR_API_KEY` as the remaining blocker for cloud agent replies.

## [2026-05-31] ops | Cursor API key configured

- Stored `CURSOR_API_KEY` as a GitHub Actions repository secret.
- Resolved the async-agent-runner blocker so queued direct emails can be processed by Cursor Agent in cloud workflows.

## [2026-06-02] ops | Thread-aware email idempotency

- Added Gmail thread metadata fetches so email ingestion only queues work when Brian is the latest meaningful sender in the thread.
- Updated task status replies to use Gmail `threadId`, `In-Reply-To`, and `References`, making AgentCore's reply the latest thread message until Brian responds again.
- Added `agentcore/knowledge/communications/email-thread-ledger.json` for ID/status audit metadata without storing email bodies.
- Added scripts to skip terminal ledger entries during triage and record final task responses after notifications.
- Updated the async runner workflow to commit terminal email ledger/task status changes back to the repo.
