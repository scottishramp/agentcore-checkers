# AgentCore Log

Append-only chronological record of important AgentCore knowledge-base activity.

## [2026-08-23] ingest | Shared Drive doc: Medical and Drs

- Brian shared `Medical and Drs`. Allowlisted, exported locally, extracted providers/insurance/allergies/compact history to `knowledge/people/medical-and-drs.md`.
- Portal passwords in the source were **not** copied into git. Kristin's pediatric-portal email `kristinherbert@gmail.com` recorded on her people page.
- Fast context bundle `2.5.3`.

## [2026-08-23] ops | Morning runner failed on corrupt Telegram ledger cache

- Scheduled 8:30 AM CT `agent-runner` (run 32643824053) failed at Telegram triage: `JSONDecodeError` on `telegram-thread-ledger.json` after Actions cache restore.
- The 6:17 AM CT runner after email-sync had already succeeded (digest Doc updated). Pages "failures" overnight were cancelled superseded builds, not real job failures.
- Repair script did not include the Telegram ledger. Added it (plus eval-ledger) to `repair_cached_json_state.py`, and Telegram triage now falls back instead of crashing the rest of the job.

## [2026-08-22] knowledge | Home address and important contacts

- Brian: home is 2905 Overland Way, Edmond, OK 73012.
- Important contacts from his phone favorites: Daniel, Nathan, Ezra (email + phone); Kristin and Mom (phone). Silver and Levi were not in that list.
- Stored on people pages plus `knowledge/people/important-contacts.md`; fast context bundle `2.5.2`.

## [2026-08-22] ingest | Shared Drive docs: Life 2025 and Stuff we own

- Brian shared `Life 2025` and `Stuff we own appliances cars` with `scottishramp@gmail.com`.
- Added both to the content-ingest allowlist, exported bodies locally, created Drive inbox records, and extracted durable facts.
- New pages: `knowledge/documents/life-2025.md` (family/work dates, Mom's Royersford address) and `knowledge/household/stuff-we-own.md` (house, vehicles, appliances). Full journal text stays in Drive.
- Fast-router context bundle bumped to `2.5.1` so Telegram can see the new pages.

## [2026-08-22] architecture | Telegram bot gets a regularly refreshed Brian knowledge snapshot

- Brian asked whether the Telegram bot has a regularly updated snapshot of AgentCore knowledge about him in context. It had a partial, deploy-frozen bundle (and was trimming at 24k chars).
- Context bundle `2.5.0` now includes people pages, family-facts, food log, Life 2026, personal OS, and the 2026-27 roster; max raised to 100k so the pack is not trimmed.
- Nightly runner publishes the snapshot to Redis (`agentcore:fast-context`); live replies prefer that over the Vercel file bundle so new facts land without `VERCEL_TOKEN` redeploys.

## [2026-08-22] architecture | Fast Telegram router uses Gemini 3.7 Flash

- Brian asked to change the Telegram bot model from Gemini 2.5 Flash to Gemini 3.7 Flash.
- Default is now `gemini-3.7-flash` in `fast-router.js`, photo labeling, health/version replies. Router version `2.4.2`.

## [2026-08-22] ops | School digest archives mail out of Inbox

- Brian asked that school mail leave Inbox the same way as dragging it onto the `26-27 School` label in Gmail.
- `school_digest.py --apply-label` now adds the label and removes `INBOX`, and also archives leftover labeled mail still sitting in Inbox.
- Live pass: labeled 0 new, archived 26; follow-up query `label:"26-27 School" in:inbox` returned 0. Mail remains under the school label and All Mail.

## [2026-08-18] knowledge | Nathan football + fast-router no realtime writes

- Brian (Telegram): Nathan plays school football with daily practice; stored on children page, `2026-27-roster.json`, and `family-facts.md`.
- Brian clarified fast Telegram has no realtime knowledge-write capability; scheduled/nightly async Cursor review adds facts and refreshes awareness.
- Fast router bumped to `2.4.1`: `knowledge_update` acknowledgments must say queued for async ingest, never that knowledge was already saved.

## [2026-08-16] knowledge | School digest v5: distilled actionables only

- Each bullet is now one distilled line — Need (quoting the ask), FYI (key fact), or No action (topic) — with no raw email excerpts.
- Important contains only items with a real parent to-do; no-action items route to kid sections or General. Stale needs are relabeled "Past need (likely done)".
- The sweep re-syncs `herbert-children.md` from the roster after every ingest, so the knowledge base keeps learning teachers, sports, and activities per kid.

## [2026-08-16] knowledge | School digest items now include Need/FYI thinking

- Each digest bullet has a second line that says whether we have something to do after reading the full email.
- Excitement-only notes (for example a track welcome with no parent to-do) drop out of Important.

## [2026-08-16] knowledge | School digest: full sentences, Link, this-week bold, sports ingest

- Digest bullets now paraphrase complete sentences instead of clipping Gmail snippets mid-word.
- Each item ends with a hyperlinked Link (form/Smore/RankOne/Seesaw when present, otherwise Gmail).
- Items due this week in America/Chicago are bold.
- Each child's section includes standing sports/teams (Daniel: basketball and track). The morning sweep writes new teachers and sports onto `2026-27-roster.json`.

## [2026-08-16] knowledge | School digest is a shared Google Doc; Levi's teacher is Mrs. Scott

- Brian confirmed all 2026-27 teacher assignments and named Levi's 1st-grade teacher as Mrs. Scott.
- Digest primary artifact is now an AgentCore Drive Google Doc: Important (action + date + kid), one section per child, then General.
- Telegram only pings Important items plus the Doc link. Morning runner rebuilds the Doc over a 7-day window.

## [2026-08-16] knowledge | 2026-27 schools, teachers, and school digest v1

- Brian confirmed 2026-27 schools: Daniel at Edmond North; Nathan and Ezra at Cheyenne Middle; Silver and Levi at Frontier Elementary.
- Pulled teacher names from Infinite Campus schedule-release emails and teacher welcome messages in Brian's Gmail. Levi's 1st-grade teacher is not in mail yet.
- `26-27 School` Gmail label only had 2 messages (both Corbin Byford / North basketball); most current school mail was unlabeled.
- Added roster JSON, children-page school section, digest script, morning Telegram send, and auto-labeling.
- Importance model v1: show teacher/action items and Seesaw; skip school-wide newsletters/PTO until Brian corrects it.

## [2026-08-16] deploy | burningaltar.com blog live with two Bear posts

- Copied only two Bear posts onto the Hugo site: [Why AI is the biggest deal since the wheel](https://briandherbert.bearblog.dev/ai-and-the-wheel/) and [What the abacus predicts for AI](https://briandherbert.bearblog.dev/ai-and-the-abacus/). Did not clone the rest of the Bear site.
- Delivery repo: https://github.com/scottishramp/burningaltar. Theme: vendored hugo-bearblog. Pages via GitHub Actions.
- Removed GoDaddy domain forwarding, pointed apex A records at GitHub Pages, set `www` CNAME to `scottishramp.github.io`, left email DNS alone.
- Live: https://burningaltar.com/ (HTTPS enforced). Project page: `agentcore/knowledge/projects/burningaltar-blog.md`.

## [2026-08-16] access | Brian Gmail mailbox read/label/archive/trash

- Brian authorized AgentCore to read all mail in `briandherbert@gmail.com`, create labels, archive, and trash.
- Added a separate `gmail.modify` OAuth profile so this token does not overwrite AgentCore's own mailbox credentials.
- CLI: `npm run email:oauth:brian` then `npm run email:brian`.
- Live verify: profile `briandherbert@gmail.com`, 7271 messages, 48 labels, `AgentCore` label present.
- GitHub Actions secret: `AGENTCORE_BRIAN_GMAIL_AUTHORIZED_USER_JSON`.
- Playbook: `agentcore/knowledge/playbooks/brian-gmail-mailbox.md`.
- Full message bodies stay in Gmail; they are not ingested into git.

## [2026-08-16] access | Accepted GoDaddy delegate access for Brian's domains

- Brian invited `scottishramp@gmail.com` as a GoDaddy delegate at Products & Domains.
- AgentCore created a GoDaddy account via Google SSO (`scottishramp@gmail.com`, customer `#743698597`) and confirmed access to Brian Herbert's account (customer `#34804617`).
- Visible domains: `burningaltar.com`, `burningaltar.org`, `cleansane.com`, `notverydeep.com`.
- `burningaltar.com` renews 2027-03-16, lock and privacy on, GoDaddy nameservers, 21 DNS records.
- Recorded project page and playbook; street address/phone/PIN kept out of git.

## [2026-06-29] knowledge | Recorded Herbert children full/middle names

- Telegram review task `task-telegram-407016341` asked "What's his middle name"; preceding message asked Ezra's age, so "his" = Ezra.
- Extracted full names (with middle names) from the Life 2026 milestone section and added a Full Names table to `herbert-children.md`: Daniel Shawn, Nathan Titus, Ezra Matthias, Silver Annalin, Levi Silas Herbert.
- Replied on Telegram with Ezra's middle name (Matthias).

## [2026-06-29] ingest | Re-verified Life 2026 important dates against fresh export

- Processed queued task `task-internal-life-2026-content-ingest` against this cycle's credentialed export of the Life 2026 doc.
- Re-validated all five children's birthdates from the doc's important-dates header — unchanged and correct: Daniel 2011-09-27, Nathan 2013-02-26, Ezra 2015-04-09, Silver 2017-01-25, Levi 2020-02-10.
- `herbert-children.md`, `life-2026.md`, and `hot-cache.md` already held accurate values from the 2026-06-28 ingest; no content changes required. Full journal body was not stored in-repo.

## [2026-06-29] ops | Added fast-router context freshness health fields

- Root signal: Telegram production still reported router v2.2.1 after repo had v2.3.x knowledge/context changes, proving Vercel was serving a stale snapshot.
- Added fast-router health fields: `context_hash`, `context_length`, `context_files`, and `has_nathan_birthdate`.
- Updated docs to define propagation complete only when Vercel production health matches the repo context snapshot.

## [2026-06-29] architecture | Async Cursor is the authoritative Telegram reviewer

- Captured architecture goal: repo is Brian's canonical context memory; new context can come from chat, email, and shared docs.
- Updated Telegram ingest contract so async Cursor (not fast router heuristics) decides whether queued messages are durable knowledge, action tasks, or no-op.
- Updated `triage_messages.py` to queue all non-ignore Telegram routes for async review.
- Updated `knowledge-content-ingest.yml` to attempt fast-router redeploy after ingest runs when `VERCEL_TOKEN` is available.

## [2026-06-29] architecture | Clarified Vercel deploy path for fast router

- Recorded that fast-router production deploys have been running from local Vercel CLI session auth (`npx vercel deploy --prod --yes`) with linked project metadata in `.vercel/project.json` (`agentcore-fast-router`).
- Documented separation between manual/local deploys and headless GitHub Actions redeploys that require `VERCEL_TOKEN`.
- Updated `system-architecture.md`, `telegram-fast-router.md`, `hot-cache.md`, and `blockers.md` to prevent future confusion about what actually updates production.

## [2026-06-29] router | Stable defer reply for unanswered Telegram questions

- Updated `api/_agentcore/fast-router.js` so fallback/unanswered text questions use fixed reply: `*DEFER* The slower, smarter agent might be able to help with this`.
- Removed the extra local-fallback explanatory suffix from user-visible chat replies.
- Updated router tests (`test_fast_router.js`, `test_telegram_router.js`) to lock the defer behavior.
- Updated fast-router docs/version registry (`chatbot-version.json`, `chatbot-version.md`, `telegram-fast-router.md`, `system-architecture.md`).

## [2026-06-28] architecture | Knowledge content ingest pipeline

- Root cause: Life 2026 content ingest was deferred because `export_flagged_docs.py`, allowlist, and workflow step were designed but never implemented; runner only claims `queued` tasks.
- Added: `content-ingest-allowlist.json`, `export_flagged_docs.py`, `activate_content_tasks.py`, `knowledge_content_ingest.py`, `.github/workflows/knowledge-content-ingest.yml` (every 4h).
- Ingested Life 2026 birthdates: Daniel 2011-09-27, Nathan 2013-02-26, Ezra 2015-04-09, Silver 2017-01-25, Levi 2020-02-10.
- Updated `herbert-children.md`, `life-2026.md`, `system-architecture.md`, playbook `knowledge-content-ingest.md`.

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

## [2026-06-27] ops | Chatbot versioning system

- Added `agentcore/knowledge/architecture/chatbot-version.json` and `chatbot-version.md` as the canonical fast-router semver registry.
- Implemented deterministic `version` / `/version` command; injected version into Gemini prompts and health endpoints.
- Current release: router v1.2.0, context bundle v1.1.0.

## [2026-06-27] ops | Telegram fast router added

- Added `api/agentcore-telegram.js` webhook, Telegram adapter, async task handoff, and router-task Telegram completion notifications.
- Documented setup in `agentcore/knowledge/playbooks/telegram-fast-router.md`.
- Live activation complete: bot `@AgentCoreFam_bot`, webhook registered, secrets stored in Vercel/GitHub only.

## [2026-06-27] feature | Telegram photo labels + registry (v2.2.0)

- Fast agent assigns `{username}_{YYYYMMDDHHmmss}` labels and detailed vision descriptions in chat replies.
- `telegram-photo-registry.json` maps labels to Drive URLs; Cursor tasks reply with label + Drive link.

## [2026-06-27] feature | Telegram photo+caption support (v2.1.0)

- Fast router parses `message.photo` + caption; optional Gemini vision via Telegram file download.
- Redis inbox records include `media` metadata; triage queues photo messages; runner uploads to Drive and writes `agentcore/inbox/photos/`.

## [2026-06-27] architecture | Telegram-only async agent (v2.0.0)

- Removed Google Chat polling, HTTP app endpoint, and live `repository_dispatch` / `router-task.yml`.
- Telegram fast router queues every message to Upstash; GitHub Actions triage + Cursor on schedule.
- Runner notifies via Telegram (working + done), redeploys Vercel when `VERCEL_TOKEN` set.

## [2026-06-27] ops | Telegram conversation history via Upstash Redis

- Provisioned free Upstash Redis `agentcore-chat-history` through Vercel marketplace integration; connected to `agentcore-fast-router` production with `KV_REST_API_URL` / `KV_REST_API_TOKEN`.
- Router v1.3.0: health checks report `history_configured`; last ~6 turn pairs per chat user, 6-hour TTL.

## [2026-06-27] ops | AgentCore architecture memory
- Added `.cursor/rules/architecture-memory.mdc` so future Cursor sessions read and maintain the architecture map when AgentCore systems change.
- Linked the architecture docs from `agentcore/index.md`, surfaced them in `agentcore/hot-cache.md`, and updated `AGENTS.md` to require architecture-doc maintenance for system changes.

## [2026-06-29] architecture | Telegram transcript and Cursor review ownership

- Corrected the Telegram intake contract: Vercel fast bot answers from a repo-context snapshot and queues messages only; it does not decide durable knowledge or action ownership.
- Moved Telegram queue consumption out of read-only `email-sync.yml`; write-capable workflows now own Redis draining so normalized records, review tasks, and transcript updates can be committed.
- Added durable `agentcore/knowledge/communications/telegram-transcript.md` and made every allowed Telegram message a Cursor review item with inbox/transcript context.
- Fixed Telegram reply plumbing so Cursor can post back through `send_task_response.py` and can intentionally suppress duplicate replies with `NO_TELEGRAM_REPLY`.

## [2026-07-14] knowledge | YouVersion app key is public

- Brian clarified via Telegram `telegram:407016345` that the YouVersion Platform app key is not a secret and may be hardcoded in repo source.
- Added `agentcore/knowledge/projects/youversion-verse-of-the-day.md` and noted the policy on `agentcore/knowledge/people/brian-herbert.md`.
- Prior redaction of the key from `telegram:407016344` inbox/transcript remains until the value is recovered or Brian re-sends it.

## [2026-07-05] preference | Stop scheduled food check-ins

- Brian asked to stop the recurring "What'd you eat since last time?" prompts.
- Removed `food-checkin-midday` and `food-checkin-evening` from `scripts/telegram/scheduled_messages.json` and `scripts/chat/scheduled_messages.json`; cleared their dedup state from `scheduled-messages-state.json`.
- Food log remains on-demand only when Brian reports meals.

## [2026-07-10] architecture | Daily GitHub Actions schedule

- Brian asked to run async workflows once per day instead of every 30 minutes / hourly / every 4 hours.
- `email-sync.yml`: `0 11 * * *` (6:00 AM America/Chicago).
- `agent-runner.yml`: `30 13 * * *` (8:30 AM America/Chicago; still triggered after email-sync completes).
- `knowledge-content-ingest.yml`: `0 16 * * *` (11:00 AM America/Chicago).
- Updated `system-architecture.md`, `knowledge-content-ingest.md`, and `hot-cache.md`.

## [2026-07-20] architecture | Async runner uses Grok 4.5

- Brian asked the GitHub Actions async job to choose a smarter model: Grok 4.5.
- Default `AGENTCORE_CURSOR_MODEL` changed from `auto` to `grok-4.5` in `agent-runner.yml` and `scripts/agent/run_cursor_task.py`.
- Optional override remains via GitHub secret `AGENTCORE_CURSOR_MODEL`.

## [2026-08-16] architecture | School digest email ingest is LLM-first

- Brian: stop keyword classification; an LLM with repo knowledge must evaluate and classify each email, track what has been evaluated, and skip obvious junk cheaply. Long-term: full family assistant (self-knowledge, action items, unsubscribe recommendations).
- New `scripts/email/email_evaluator.py`: prefilter → LLM batch verdicts (relevant, category, children, distilled line, need, due_date, learn facts, unsubscribe) → eval ledger `agentcore/knowledge/email/eval-ledger.json` (60-day retention, metadata only, committed by runner).
- Backends: Gemini REST when `GEMINI_API_KEY` is set; otherwise Cursor Agent CLI (`CURSOR_API_KEY` in CI). Keyword classifier remains as fallback (`--no-llm` or backend failure).
- Learn entries: kid teachers/sports/activities → roster; general household facts → new `agentcore/knowledge/people/family-facts.md`. Unsubscribe recommendations render in a Suggestions section of the Doc.
- `agent-runner.yml`: Cursor CLI install moved before the digest step; digest step gets `CURSOR_API_KEY`/`GEMINI_API_KEY`; persist step commits ledger + family facts.
- New playbook `agentcore/knowledge/playbooks/agentic-jobs-cursor-cli.md`: how the nightly runner uses Cursor CLI headless, plus the recipe for creating new agentic jobs from Brian's asks.

## [2026-08-17] feature | School digest Important items are checkable in the Doc

- Brian asked for checkboxes in the digest Doc with smart carry-forward of what he checks off.
- Important items render as native Google Docs checklist items (`BULLET_CHECKBOX` via `createParagraphBullets`).
- The Docs API does not expose checked state, so each run exports the Doc as HTML via Drive and treats struck-through (`text-decoration:line-through`) checklist lines as done; matches use the `doc_line` text stored per eval-ledger entry; done verdicts drop the item from all future rebuilds.
- Verified end-to-end: browser subagent checked the English I syllabus item; next run logged "checked off in Doc: English I: North" and rebuilt Important with 3 items.
- Local `cursor-agent` is now logged in (Brian approved the browser flow), so local LLM evaluation works; today it evaluated 4 new emails and learned 3 more facts.

## [2026-08-22] architecture | Async runner uses Grok 4.6

- Brian asked to switch the GitHub Actions async job from Grok 4.5 to Grok 4.6 (same $2/$6 Cursor Models pool rate).
- Default `AGENTCORE_CURSOR_MODEL` changed from `grok-4.5` to `grok-4.6` in `agent-runner.yml`, `scripts/agent/run_cursor_task.py`, and `scripts/email/email_evaluator.py`.
- Optional override remains via GitHub secret `AGENTCORE_CURSOR_MODEL`.
## [2026-08-29] feature | Nightly mailbox and calendar learning loop

- Brian: keep learning about me — read my calendar in the nightly job, ingest info from all my mail, and ask when unsure whether a sender is important, informational, or spam, then learn from the answers.
- Kickoff answers: questions on Telegram; max 5 per night; rolling window plus a one-time 90-day backfill; read-only mail for now (no labeling, archiving, or trashing).
- **Calendar is now automated for the first time.** `scripts/ingest/ingest_calendar.py` reads Brian's shared `briandherbert@googlemail.com` calendar (AgentCore has `reader` + `calendar.readonly`), regenerates `agentcore/knowledge/calendar/upcoming.md` (7 days back / 60 ahead), and records recurring series as commitment facts. Previously the scope existed but nothing read it.
- **Sender-level mailbox sweep.** `scripts/learn/mailbox_sweep.py` sweeps the whole personal mailbox and decides each *sender* once into `learn` / `info` / `ignore` in `agentcore/knowledge/email/sender-policy.json`. Deciding per sender rather than per message keeps nightly cost flat as volume grows and makes each question to Brian permanently valuable.
- **Ask-Brian loop.** New `agentcore/knowledge/communications/pending-questions.json` ledger. Model verdicts at confidence >= 0.8 are auto-recorded; below that the sender becomes a numbered Telegram question. `ask_questions.py` batches up to five; `resolve_answers.py` parses replies ("1 learn, 2 ignore", "1l 2i 3s", "all ignore") out of the existing Telegram inbox records. Brian-sourced policy outranks model verdicts and is never overwritten. Unparseable prose replies are left alone and still reach Cursor as a normal Telegram review task.
- Facts land in `agentcore/knowledge/people/brian-learned-facts.md`, dated and filed by category, deduped by fingerprint including containment so restated facts do not duplicate.
- Privacy: read-only against Gmail and Calendar; bodies read for extraction but never committed; prompt forbids passwords, full account numbers, and auth codes.
- Wired into `knowledge-content-ingest.yml` (11:00 AM CT) in order: resolve answers, calendar, sweep, ask. Cursor CLI install added to that workflow. Step summary now reports the learning-loop numbers.
- Verified live: calendar returned 21 events and 2 recurring series; a 60-message sweep classified 20 senders (15 auto: 4 learn / 5 info / 6 ignore) and raised 5 questions on genuinely ambiguous senders (barber, volunteer newsletter, youth hockey, Compassion, a YouVersion colleague's prayer list). Extracted Capital One and Pershing/BlackRock account facts.
- New `tests/test_learning_loop.py` (40 assertions, no network) covers answer parsing, policy precedence, question lifecycle, and fact-page writing. Wired into `npm test` as `test:learn`.
- Playbook: `agentcore/knowledge/playbooks/mailbox-learning-loop.md`. Architecture, index, and hot-cache updated.
- Open: the one-time 90-day backfill has not been run yet.
