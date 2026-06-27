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

## [2026-06-04] ops | Direct email reply cleanup

- Investigated Brian's report that parsed emails received log-style responses rather than natural AI replies.
- Confirmed Cursor Agent did run successfully for the smoke-test email, but `send_task_status.py` wrapped the LLM output in a task-completion template.
- Updated direct email `done` replies to send the Cursor Agent output as the email body and use the original Gmail thread subject.
- Removed the runner's separate "running" notification email to reduce operational noise.
- Changed ingestion summary email policy so recurring errors alone are logged but not emailed under the default `changes` policy.
- Recorded CI Drive ingestion's missing Drive readonly OAuth scope as an open blocker; this is separate from Gmail/LLM email answering.

## [2026-06-04] ops | Repair deployment default

- Added a standing operating instruction: when Brian reports a bug, weird behavior, or asks to fix an operating workflow, commit/push/deploy are implicit parts of the repair unless Brian explicitly says to keep changes local or not deploy.
- Recorded the instruction in both `.cursor/rules/admin-assistant.mdc` and `AGENTS.md`, with hot-cache updated for future sessions.

## [2026-06-05] ops | Completed-change deployment default

- Confirmed local repository state was behind `origin/main` by two bot-authored task-result commits and fast-forwarded local `main` to match remote.
- Broadened the standing operating instruction: commit, push, and deployment/activation are implicit parts of any completed change unless Brian explicitly says to keep changes local, avoid committing, avoid pushing, or not deploy.
- Updated `.cursor/rules/admin-assistant.mdc`, `AGENTS.md`, and hot-cache so future sessions inherit this default.

## [2026-06-05] ops | Trusted email self-update runner

- Updated `agent-runner.yml` so successful Cursor Agent runs commit and push non-ignored workspace changes before sending completion email.
- Updated the Cursor Agent prompt to allow trusted-client email tasks to edit AgentCore behavior, integrations, workflows, scripts, rules, docs, and knowledge.
- Documented self-update behavior in `AGENTS.md`, `.cursor/rules/admin-assistant.mdc`, `scripts/agent/README.md`, and the email-to-Cursor bridge playbook.
- Kept destructive actions, credential disclosure, billing actions, and 2FA/fresh-consent account actions outside automatic email execution.

## [2026-06-05] ops | Google Keep share investigation

- Found Brian's Google Keep share notification in Gmail from `keep-shares-dm-noreply@google.com`; the body says Brian shared note `Stage` with `scottishramp@gmail.com`.
- Confirmed the current trusted-client-only Gmail fetch policy would miss or reject service-sender share notifications even when Brian initiated the share.
- Tested note access: the Keep share URL redirects to Google sign-in without browser session, and the official Keep API returns `ACCESS_TOKEN_SCOPE_INSUFFICIENT` for the current OAuth token.
- Updated Gmail fetch/triage to accept verified Google Drive/Keep share notifications when the body names Brian's trusted email and the message is addressed to AgentCore.
- Added `https://www.googleapis.com/auth/keep.readonly` to OAuth setup for the next token refresh and recorded the Keep scope blocker.

## [2026-06-07] ops | Suppress ingestion-summary email noise

- Diagnosed user-facing ingestion emails with `NEW_EMAIL_TASKS` and `RUNNER_SNAG`: the default `changes` policy was still sending summary emails when direct email tasks were queued, and the email body included raw Drive API errors.
- Updated ingestion notification behavior so direct-email task intake relies on the natural task reply path instead of sending a second operational summary email.
- Removed raw error arrays from ingestion summary email bodies; detailed errors remain in runner logs and the ingestion ledger.
- Verified the local OAuth token includes Drive readonly scope and refreshed the GitHub Actions `AGENTCORE_GMAIL_AUTHORIZED_USER_JSON` secret from the local authorized-user JSON.
- Removed the invalid Google Keep readonly scope from the OAuth helper and corrected docs/blockers to reflect that Keep note content is not available to AgentCore's personal Google account through the official API.

## [2026-06-07] ops | Calendar access verified

- Found Brian's Google Calendar share notification in Gmail: Brian added `scottishramp@gmail.com` to shared calendar `briandherbert@googlemail.com` with event-detail visibility.
- Added supported `https://www.googleapis.com/auth/calendar.readonly` scope to the OAuth helper, completed Google consent for `scottishramp@gmail.com`, and refreshed `.secrets/gmail-authorized-user.json`.
- Enabled `calendar-json.googleapis.com` on Google Cloud project `agentcore-495202` using the `scottishramp@gmail.com` gcloud account.
- Verified the Calendar API lists two calendars: AgentCore's primary `scottishramp@gmail.com` calendar as owner and Brian's `briandherbert@googlemail.com` calendar as reader.
- Probed upcoming events for Brian's shared calendar without printing private details; the API returned a successful sample of upcoming events.
- Refreshed GitHub Actions secret `AGENTCORE_GMAIL_AUTHORIZED_USER_JSON` with the Gmail/Drive/Calendar-scoped authorized-user token.

## [2026-06-07] ops | Broad admin-assistant OAuth bundle

- Recorded Brian's operating model: AgentCore should know the materials Brian shares, treat Brian-shared Google resources as read surfaces unless explicitly granted edit authority, write durable artifacts in AgentCore's own Google account, and continue using email as the main async interaction channel until synchronous chat exists.
- Expanded the OAuth helper to request Gmail read/send, Drive readonly plus app-created file management, Calendar readonly, Docs/Sheets/Slides write scopes for AgentCore-owned working files, Contacts readonly, Tasks, and app-created Google Photos scopes.
- Enabled Gmail, Drive, Calendar, Docs, Sheets, Slides, People, Tasks, and Photos Library APIs on Google Cloud project `agentcore-495202`.
- Completed Google consent for `scottishramp@gmail.com`; tokeninfo confirmed all 13 requested scopes were granted.
- Smoke-tested Gmail profile, Drive file listing, Calendar list, People connections, Tasks lists, and app-created Photos album listing without printing private content.
- Verified AgentCore-owned Drive write access by creating and deleting a temporary test folder through the Drive API.
- Refreshed GitHub Actions secret `AGENTCORE_GMAIL_AUTHORIZED_USER_JSON` with the broad-scope authorized-user token.
- Noted Google Photos limitation: broad unattended library reads are no longer available through the official Library API, so Brian photo intake should use Drive/email/share flows unless a future interactive Photos Picker path is built.

## [2026-06-08] intake | Brian calendar share acknowledged

- Processed queued task for Brian's Google Calendar share notification (`briandherbert@googlemail.com` → `scottishramp@gmail.com`, reader with event details).
- Recorded shared calendar on Brian's people page and the family admin system scope.
- Replied to Brian confirming calendar access is active and will be used for scheduling context and deadline awareness.

## [2026-06-08] ops | Google Chat send test

- Added Google Chat OAuth scopes `chat.spaces.create` and `chat.messages.create` to the admin-assistant OAuth helper.
- Enabled the Google Chat API on Google Cloud project `agentcore-495202`, completed OAuth consent for `scottishramp@gmail.com`, and refreshed the GitHub Actions `AGENTCORE_GMAIL_AUTHORIZED_USER_JSON` secret.
- Tried user-authenticated Chat API DM setup to `briandherbert@gmail.com`; initial response said Google Chat was turned off, and after accepting the web request the API returned `404 Google Chat app not found`.
- Confirmed the browser Chat UI works for `scottishramp@gmail.com`, accepted Brian's message request, and sent a test DM: "Test from AgentCore in Google Chat. If you see this, the synchronous chat channel works."
- Recorded the remaining programmatic blocker: the Cloud project needs a configured Chat app profile before unattended Chat API sends can work.

## [2026-06-08] ops | Google Chat API send working

- Configured the Google Chat API app profile in Cloud Console for project `agentcore-495202`.
- App profile values: name `AgentCore`, avatar `https://developers.google.com/chat/images/quickstart-app-avatar.png`, description `Private admin assistant for Brian.`, interactive features disabled, logging enabled.
- Retried user-authenticated Chat API setup for `briandherbert@gmail.com`; `spaces.setup` succeeded and returned existing DM space `spaces/6RZ69yAAAAE`.
- Sent a programmatic Chat API test message to Brian: "Programmatic Google Chat test from AgentCore. Sent through Chat API at <UTC timestamp>."
- Updated `scripts/chat/send_direct_message.py` to prefer AgentCore's repo-managed OAuth authorized-user token and use `spaces.setup` directly, then verified `npm run chat:send` sends through the reusable helper.
- Marked the Chat app profile blocker resolved.

## [2026-06-08] ops | Google Chat intake and replies

- Recorded Brian's instruction that Google Chat should be an inbound task channel alongside email.
- Added Chat fetch/triage scripts that read Brian's DM space `spaces/6RZ69yAAAAE`, skip AgentCore-authored messages, normalize Brian-authored messages under `agentcore/inbox/chat/`, and queue them under `agentcore/inbox/tasks/` with `source_kind: google_chat`.
- Added Chat task response and ledger scripts so completed Chat-origin tasks reply back into the same Chat space and update `agentcore/knowledge/communications/chat-thread-ledger.json`.
- Wired Chat fetch/triage into `email-sync.yml` and `agent-runner.yml`; runner notifications now route email-origin tasks to email and Chat-origin tasks to Google Chat.
- Added `https://www.googleapis.com/auth/chat.messages.readonly` to the OAuth helper, refreshed local OAuth consent for `scottishramp@gmail.com`, verified Chat message reads, and refreshed GitHub secret `AGENTCORE_GMAIL_AUTHORIZED_USER_JSON`.
- Set first-run Chat fetch behavior to mark existing history seen without queueing old messages, preventing backlog replies to old setup/test messages.

## [2026-06-08] intake | Google Keep note "Stage" share

- Processed Brian's Google Keep share notification for note `Stage` (Gmail `19e946e3abff9515`).
- Logged metadata at `agentcore/sources/web/keep-note-stage.md` and updated Brian's shared-resources page.
- Confirmed prior blocker still applies: Keep note body is not readable through AgentCore's supported Google APIs.

## [2026-06-08] knowledge | Brian family basics

- Recorded Brian Herbert's date of birth as 1983-09-10.
- Recorded Brian's spouse as Kristin Herbert and marriage date as 2006-05-27.
- Recorded Brian and Kristin's children: Daniel, Nathan, Ezra, Silver, and Levi.
- Created lightweight people/context pages for Kristin Herbert and the Herbert children, and linked them from the AgentCore index.

## [2026-06-09] ops | Bounded Google Chat sync loop

- Added a pseudo-synchronous Google Chat loop for GitHub Actions: after a Chat-origin task is answered, the runner can keep polling Brian's DM space for follow-up messages and process/reply inside the same workflow run.
- Gated the loop to short conversational Chat tasks, `America/Chicago` local time between 09:00 and 20:00, and a configurable hard cap (default 15 minutes, 20 second poll interval).
- Added `scripts/chat/synchronous_loop.py` to orchestrate fetch, triage, Chat-only claim, Cursor task execution, finalization, Chat response send, ledger recording, and commits for follow-up Chat tasks.
- Added `--source-kind` filtering to `scripts/email/claim_next_task.py` so the sync loop cannot accidentally claim email or Drive tasks.
- Wired the loop into `agent-runner.yml` after Chat response ledger commits and added summary/artifact output for loop entry, stop reason, and processed task count.

## [2026-06-09] ops | Cursor-based GitHub sync command

- Added the project skill `.cursor/skills/github-sync/SKILL.md` so a bare `sync` request means to inspect, pull, push, and reconcile GitHub state using Cursor agent judgment.
- Updated the administrative-assistant rule and hot cache to prefer the skill over a custom programmatic sync routine.

## [2026-06-23] intake | Brian food log — breakfast

- Logged Brian's 2026-06-23 breakfast via Google Chat: 2 eggs, small club sandwich (sourdough/ham), handful of Fritos Flavor Twists (~620 cal estimated).
- Updated `agentcore/knowledge/people/brian-herbert-food-log.md`.

## [2026-06-20] intake | Brian food log — breakfast and lunch

- Logged Brian's 2026-06-20 intake via Google Chat: 2 eggs and sourdough for breakfast; cheeseburger and bratwurst for lunch (~910 cal estimated day total so far).
- Updated `agentcore/knowledge/people/brian-herbert-food-log.md`.

## [2026-06-18] intake | Brian food log — afternoon snack

- Logged Brian's afternoon intake for 2026-06-18: biscuit with chicken breast, small hummus portion, and one cookie (~490 cal estimated).
- Consolidated earlier breakfast entry (eggs, coffee, 3 cookies) into `agentcore/knowledge/people/brian-herbert-food-log.md`.
- Brian asked for internal-only logging with no report-back.

## [2026-06-10] ops | Preserve replies after runner push rejection

- Investigated a missed Google Chat response for Brian's location-sharing request. Chat intake and the Cursor task ran successfully, but `agent-runner.yml` stopped at `Commit agent workspace changes` because GitHub rejected a workflow-file update from the default Actions token.
- Made the runner's workspace and communication-ledger commit steps non-blocking so Email/Chat response delivery is not skipped when a push fails.
- The underlying workflow-write limitation remains: GitHub Actions' default token cannot push workflow-file changes without elevated workflow permission, so workflow self-updates may still need local Cursor or a differently scoped token.

## [2026-06-22] fix | Proactive scheduled Chat messaging

- Diagnosed missing Google Chat check-ins: the Cursor agent (running in Actions) promised scheduled food check-ins 3 times (June 18, 19, 20) but never committed any code. Zero scripts or workflow changes existed. The system was purely reactive.
- Built proactive outbound messaging system:
  - `scripts/chat/scheduled_messages.json` — config for recurring messages (noon + 6 PM food check-ins, 90-minute delivery windows, `America/Chicago` timezone).
  - `scripts/chat/send_scheduled_messages.py` — checks schedule, tracks state to avoid duplicates, sends due messages via Chat API.
  - Wired into both `email-sync.yml` and `agent-runner.yml` workflows.
- Bumped email-sync cron from hourly (`0 * * * *`) to every 30 minutes (`0,30 * * * *`) for more reliable delivery timing.
- Remaining caveat: GitHub Actions free-tier cron can still be delayed 1-2 hours; messages will arrive within 90 minutes of target time on normal days, potentially later if Actions has a delay spike.

## [2026-06-23] enhancement | Chat assistant responsiveness overhaul

- **Instant acknowledgment:** added `scripts/chat/send_intake_ack.py` — when email-sync triages new Chat messages, it immediately sends "Got it — working on this" before the runner even starts, so Brian gets instant feedback.
- **Multi-task drain loop:** added `scripts/agent/drain_task_queue.py` — after the first task completes, the runner loops through ALL remaining queued tasks in one invocation (up to 25 min budget). No more one-task-per-30-min-cycle bottleneck.
- **Dynamic scheduled messages:** upgraded to v2 config with a morning check-in (8:30 AM CT) and rotating message variants so check-ins don't repeat the same text.
- **Failure notification:** added a catch-all workflow failure step that sends a Chat message if the runner crashes, so Brian never gets silent failures.
- Combined effect: messages Brian sends should now be acknowledged within seconds of the next sync cycle, processed within minutes, and any failures are visible immediately.

## [2026-06-24] fix | Duplicate Google Chat messages

- **Diagnosed:** Brian was getting the same proactive check-in multiple times. Confirmed in logs: on 2026-06-24 the morning check-in was sent by `email-sync` at 13:37 UTC (`X0XRb3r8ADg`) and again 22s later by `agent-runner` at 13:38 UTC (`kWQTHsu4es0`).
- **Root cause:** the dedup state file (`scheduled-messages-state.json`) lived under gitignored `.agentcore/state/`. `email-sync.yml` had no cache, and `agent-runner.yml`'s cache list didn't include it, so neither workflow remembered a message was already sent. Every run landing in the 90-minute delivery window re-sent — and BOTH workflows ran the send step, so duplicates multiplied.
- **Fix:**
  - Moved dedup state to a durable, git-tracked file: `agentcore/knowledge/communications/scheduled-messages-state.json`.
  - Made proactive Chat sends single-owner: only `agent-runner.yml` (which has `contents: write`) sends scheduled messages. Removed the scheduled-send and the dead intake-ack steps from `email-sync.yml` (read-only; never queued chat anyway).
  - Added a dedicated commit/push of the dedup state right after the send (autostash rebase), plus the state file to the runner's cache restore/save as a backup guard.
  - Deleted the now-unused `scripts/chat/send_intake_ack.py`.
- **Result:** each scheduled check-in is sent at most once per day, from one workflow, with the "already sent" record committed to git so it survives across runs.

## [2026-06-24] fix | Missed successive Chat messages + simpler food prompt

- **Diagnosed (with live API probe):** the Google Chat `spaces.messages.list` endpoint returns messages oldest-first with pagination. With `pageSize=50` and the space now holding >50 messages, page 1 covered only 2026-06-08 → 2026-06-23 and carried a `nextPageToken`. Brian's most recent messages (including "You're sending messages twice. Just ask what I ate") were on later pages and were never fetched, so successive/recent messages went unanswered.
- **Fix (newest-first):** added an `order_by` parameter to `chat_api.list_messages` and set `fetch_messages.py` to request `orderBy=createTime desc`. The newest messages are now always on page 1; messages are sorted ascending locally for incremental processing against the cursor. Verified via a read-only probe that recent Brian messages now surface.
- **Hardened cache loss:** changed the agent-runner chat fetch from `--bootstrap-window 0` (which silently dropped everything if the cursor cache was lost) to `--bootstrap-window 30`. The git-tracked `chat-thread-ledger.json` dedups already-answered messages, so recovering recent messages cannot produce duplicate replies.
- **Simplified food check-ins:** replaced the lunch/dinner-specific variant messages with a single generic prompt "What'd you eat?" at noon and 6 PM CT (ids `food-checkin-midday`, `food-checkin-evening`).
- Known limitation: fetch still only pulls the newest 50 per run; if Brian ever sends >50 messages between runs, the oldest of that batch could be missed. Pagination is a future improvement.

## [2026-06-25] fix | Food check-in prompt + dedup key migration

- Brian reported duplicate food check-ins and asked for "what I ate since last time" instead of the generic prompt; logged tacos for 2026-06-23 dinner.
- **Root cause (duplicates):** scheduled-message dedup state still used the legacy id `food-checkin-dinner` after the config was renamed to `food-checkin-midday` / `food-checkin-evening`, so the new ids had no "already sent today" record and could re-send on every runner pass inside the delivery window.
- **Fix:** prompt is now "What'd you eat since last time?"; `send_scheduled_messages.py` migrates legacy dedup keys; state file updated to `food-checkin-evening`.

## [2026-06-25] intake | Brian food log — dinner + earlier meals

- Brian reported via Google Chat: oatmeal bowl with banana, 2 eggs with shredded cheese, sourdough slice, and 5 slices of pizza for dinner.
- Updated `agentcore/knowledge/people/brian-herbert-food-log.md` for 2026-06-24.

## [2026-06-25] ops | Personal operating hub

- Created `agentcore/knowledge/projects/personal-operating-system.md` as the durable operating hub for helping Brian with diet, scheduling, kid school logistics, app ideas, personal management, intake defaults, and sensitivity defaults.
- Linked the hub from `agentcore/index.md` and `agentcore/hot-cache.md` so future sessions can find it quickly.

## [2026-06-25] ops | Google access inventory

- Took stock of current Google access using metadata-only live probes.
- Confirmed active Gmail, Google Chat, Calendar, and Drive/Docs access for AgentCore's `scottishramp@gmail.com` account.
- Confirmed Google Maps real-time location share notification emails are visible in Gmail, but no supported live-location API or repo integration is available yet.
- Reconfirmed existing Keep and Photos limitations.

## [2026-06-25] ops | Google blocked-surface research

- Researched official unblock paths for Google Maps location sharing, Google Keep, and Google Photos.
- Confirmed Google Maps personal live-location sharing has no supported API; Maps Platform Journey Sharing/Fleet Engine is for app-managed trips/fleets, not Brian's personal Maps share. Timeline/history access is also not available through a public API; current practical route is a manual phone export for backfill.
- Confirmed Google Keep API remains Workspace/admin-oriented and is not a supported path for Brian's personal shared Keep note body.
- Found a supported partial unblock for Google Photos: the newer Photos Picker API supports user-selected media. Added `photospicker.mediaitems.readonly` to the OAuth helper and created `scripts/photos/picker_session.py` to create, poll, list, and delete Picker sessions once OAuth is refreshed.

## [2026-06-26] preference | Don't repeat food back

- Brian asked (Google Chat): in the future don't repeat his food back to him.
- Recorded the food-log reply-style preference in `brian-herbert-food-log.md`, `personal-operating-system.md`, and `hot-cache.md`: when Brian reports a meal, log it and reply with totals/notes only — never echo the items he just reported.

## [2026-06-27] ops | Google Chat fast router deployed

- Deployed the Vercel fast router for Google Chat at `https://agentcore-fast-router.vercel.app/api/agentcore-chat`.
- Enabled Google AI Studio/Gemini API access for project `agentcore-495202`, created a restricted Gemini API key, and stored required Vercel production environment variables for Gemini and GitHub `repository_dispatch` handoff.
- Saved Google Chat API configuration to use the Vercel HTTP endpoint with common trigger URL and endpoint-audience OIDC verification.
- Verified production health (`GET` returns `200`) and auth behavior (unauthenticated `POST` returns `401`).
- Remaining caveat: Brian-facing live HTTP Chat app verification is blocked because the Chat app visibility field appears locked to `scottishramp@gmail.com`, and the Apps marketplace UI could not be reliably automated from Cursor. Existing Brian DM polling remains the verified channel.

## [2026-06-27] ops | Fast router context and Brian-owned Chat app attempt

- Added structured Vercel request logging for the Chat router and expanded fast-router context with recent tracked Brian DM messages plus scheduled-message state, so shallow replies can understand automation prompts like food check-ins.
- Redeployed `https://agentcore-fast-router.vercel.app/api/agentcore-chat` with the logging/context changes.
- Confirmed a message sent in the existing Brian <-> `scottishramp` DM does not reach the Vercel router; that DM still uses the async polling workflow.
- Created new Google Cloud project `agentcore-chat-brian` under `briandherbert@gmail.com` and enabled Chat API. Browser configuration is blocked until Brian completes Google Cloud Console sign-in with his passkey.

## [2026-06-27] ops | Telegram fast router added

- Added `api/agentcore-telegram.js` webhook, Telegram adapter, async task handoff, and router-task Telegram completion notifications.
- Documented setup in `agentcore/knowledge/playbooks/telegram-fast-router.md`.
- Live activation blocked on BotFather bot token from Brian.

- Created `agentcore/knowledge/architecture/system-architecture.md` as the primary architecture map for communication surfaces, workflows, hosted endpoints, polling cadence, data stores, secrets, blockers, and update invariants.
- Added `.cursor/rules/architecture-memory.mdc` so future Cursor sessions read and maintain the architecture map when AgentCore systems change.
- Linked the architecture docs from `agentcore/index.md`, surfaced them in `agentcore/hot-cache.md`, and updated `AGENTS.md` to require architecture-doc maintenance for system changes.
