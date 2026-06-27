# AgentCore Blockers

Use this file for major ambiguities, external dependencies, or questions that materially affect a project. Do not use it for small choices where a reasonable default is obvious.

## Open Blockers

### 2026-06-25 | Travel/flight research | No live web access in async runner

- Status: open
- Blocker: The GitHub Actions async-task runner cannot reach the live web (WebSearch and WebFetch are rejected in the unattended environment), so AgentCore cannot pull real-time flight fares, schedules, or booking data when processing queued Chat/email tasks.
- Why it matters: Brian asked for live American Airlines prices/stops/travel time (OKC→PHL/TTN/ABE, Jul 23-26). AgentCore can supply routing/airport knowledge and search links, but cannot quote current fares from this environment.
- Proposed default: Reply with airline/airport routing guidance plus ready-to-tap search links; quote live fares only when run interactively with web access, or wire a flight-data API (e.g., Amadeus/Kiwi/Travelpayouts) with a secret key for unattended fare lookups.
- Needed from user: Decision on whether to provision a flight-search API key for AgentCore, or to have AgentCore answer travel-research tasks interactively where web access is available.
- Resolution:

### 2026-06-27 | Telegram fast router | Bot token needed

- Status: open
- Blocker: Telegram webhook endpoint is implemented and ready to deploy, but AgentCore does not have a Telegram account session and cannot create a bot without Brian messaging `@BotFather`.
- Why it matters: Live instant 1:1 family chat requires a bot token stored in Vercel/GitHub secrets and a webhook registration.
- Proposed default: Brian creates the bot via `@BotFather`, sends the token, AgentCore sets Vercel/GitHub secrets and runs `npm run telegram:setup-webhook`.
- Needed from user: Bot token from `@BotFather` after `/newbot`.
- Resolution:

### 2026-06-27 | Google Chat fast router | Brian-facing HTTP app visibility not verified

- Status: open
- Blocker: The Vercel fast router is deployed and the Google Chat API configuration for project `agentcore-495202` is saved to the HTTP endpoint, but `scottishramp`-owned Chat app configs strip `briandherbert@gmail.com` from the tester visibility list. A Brian-owned Google Cloud project `agentcore-chat-brian` has been created with Chat API enabled, but browser configuration is blocked on Brian completing Google Cloud Console passkey sign-in.
- Why it matters: The new synchronous HTTP endpoint cannot replace the existing Brian DM polling workflow until Brian can directly message the Chat app and receive a live synchronous reply.
- Proposed default: Keep the existing Brian DM polling workflow active. After Brian completes Cloud Console sign-in in the browser, finish configuring `agentcore-chat-brian` as the Brian-facing HTTP Chat app using the Vercel endpoint.
- Needed from user: Complete the visible Google passkey sign-in prompt for `briandherbert@gmail.com` in the Cursor browser.
- Resolution:

### 2026-06-25 | Google Maps location sharing | No personal live-location API

- Status: open
- Blocker: Google Maps location-sharing emails are visible in Gmail, but Google does not provide a supported API for personal real-time Maps location sharing. Google Maps Platform Journey Sharing/Fleet Engine APIs apply to app-managed trips, deliveries, and fleets, not Brian's personal Maps share.
- Why it matters: AgentCore cannot reliably record Brian's live Maps location unattended through an official API even though the share notification exists.
- Proposed default: Use non-Maps alternatives for automation: Brian can send/share location through Chat when needed, upload/export Timeline data from his phone for historical backfill, or use a separate purpose-built location logging app/workflow if live automation becomes important.
- Needed from user: Choose whether location support should be manual/contextual only, Timeline-export based, or implemented through a separate location logging workflow.
- Resolution:

### 2026-06-07 | Google Photos intake | Broad library reads unavailable; Picker path pending consent

- Status: open
- Blocker: Google Photos no longer permits broad unattended reads of an entire user's photo library through the official Library API. AgentCore can manage app-created Photos media and now has repo support for Google Photos Picker sessions, but the current OAuth token does not yet include `https://www.googleapis.com/auth/photospicker.mediaitems.readonly`.
- Why it matters: Brian's desired Android photo/scanning intake cannot rely on background Photos library polling. User-selected photo intake is available, but it requires an interactive Picker flow and refreshed OAuth consent before the helper can create sessions.
- Proposed default: Continue using Google Drive upload/share folders, email attachments, or direct Drive sharing for unattended document-photo intake. Use `npm run photos:picker -- create --max-items N` after OAuth refresh when Brian wants to select items from Google Photos.
- Needed from user: OAuth re-consent for the new Picker scope and manual item selection in Google Photos Picker when using that flow.
- Resolution:

### 2026-06-05 | Google Keep ingestion | OAuth token lacks Keep scope

- Status: open
- Blocker: The Google Keep share notification for note `Stage` is visible in Gmail, but Google Keep note content is not available to this personal account through the official API.
- Why it matters: AgentCore can recognize Brian-initiated Keep share notifications as trusted source material, but cannot programmatically read the note body from Keep.
- Proposed default: Treat Keep share emails as intake signals and ask Brian to copy/export/share the note content through email or Drive when the content itself is needed.
- Needed from user: None for share notification intake; Brian must provide the note content through another channel if AgentCore needs to ingest it.
- Resolution:

## Blocker Template

```markdown
### YYYY-MM-DD | Project or area | Short blocker title

- Status: open
- Blocker:
- Why it matters:
- Proposed default:
- Needed from user:
- Resolution:
```

## Resolved Blockers

### 2026-06-08 | Google Chat API | Chat app profile not configured

- Status: resolved
- Blocker: Google Chat browser messaging worked for `scottishramp@gmail.com`, but Google Chat API `spaces.setup` returned `404 Google Chat app not found` until the Cloud project had a configured Chat app profile.
- Resolution: Configured the Google Chat API app profile in Cloud Console for project `agentcore-495202` with app name `AgentCore`, avatar `https://developers.google.com/chat/images/quickstart-app-avatar.png`, description `Private admin assistant for Brian.`, interactive features disabled, and logging enabled. Retried user-authenticated `spaces.setup` and `messages.create`; both succeeded for Brian's DM space `spaces/6RZ69yAAAAE`.

### 2026-06-04 | Drive ingestion CI | GitHub OAuth secret lacks Drive scope

- Status: resolved
- Blocker: GitHub Actions Drive ingestion was returning `ACCESS_TOKEN_SCOPE_INSUFFICIENT` for `drive.files.list`, which meant the `AGENTCORE_GMAIL_AUTHORIZED_USER_JSON` secret available to CI did not include `https://www.googleapis.com/auth/drive.readonly`.
- Resolution: Verified the local authorized-user token includes Drive readonly scope and refreshed the GitHub Actions `AGENTCORE_GMAIL_AUTHORIZED_USER_JSON` secret from `.secrets/gmail-authorized-user.json` on 2026-06-07.

### 2026-05-31 | Async agent runner | Cursor API key needed for cloud replies

- Status: resolved
- Blocker: The GitHub Actions runner could install Cursor Agent and had a default task command, but needed `CURSOR_API_KEY` as a repository secret.
- Resolution: Stored `CURSOR_API_KEY` as a GitHub Actions repository secret and verified it appears in `gh secret list`.

### 2026-05-25 | Family admin system | Drive shared-with-me ingestion

- Status: resolved
- Blocker: Drive/photo ingestion scripts originally needed explicit folder ids before live ingestion could run.
- Resolution: Shifted default model to `sharedWithMe` ingestion, set `AGENTCORE_DRIVE_INCLUDE_SHARED_WITH_ME=true`, and verified Drive API ingestion with the shared `Life 2026` document.

### 2026-05-25 | Email operations | OAuth app still in testing mode

- Status: resolved
- Blocker: The Gmail OAuth client was initially in testing mode, which risked periodic refresh token expiry for unattended runs.
- Resolution: Switched app audience/publishing to production, reran `npm run email:oauth`, rotated the authorized-user credentials, and re-verified live Gmail API send.

### 2026-05-25 | Email operations | Gmail API OAuth credentials needed

- Status: resolved
- Blocker: AgentCore now supports Gmail API OAuth for send/fetch in local Cursor CLI and GitHub Actions, but still needed OAuth client credentials and a refresh token for `scottishramp@gmail.com`.
- Resolution: Added OAuth client credentials securely under `.secrets/`, completed OAuth consent flow, stored authorized-user JSON under `.secrets/gmail-authorized-user.json`, configured `.env` for `gmail-api` transport, and verified live send via Gmail API.

### 2026-04-25 | Async comms | Outbound email send from agent

- Status: resolved
- Blocker: Automated email send attempts failed (`Mail` Apple Events authorization denied; Gmail SMTP rejected credentials).
- Resolution: Switched to Gmail app-password auth and implemented SMTP/IMAP automation scripts (`scripts/email/`) with local + scheduled GitHub Actions inbox sync.

### 2026-04-24 | Checkers web game | Durable public hosting

- Status: resolved
- Blocker: Workspace was not a git repo and GitHub CLI was unauthenticated.
- Resolution: Authenticated `gh` as `scottishramp`, created public repo `agentcore-checkers`, enabled GitHub Pages. Live at https://scottishramp.github.io/agentcore-checkers/
