# AgentCore Ingestion Scripts

Cross-channel ingestion utilities for Drive documents and Android photo uploads.

## Commands

- Drive + photo ingest:
  - `npm run ingest:drive`
- Google Photos Picker session helper:
  - `npm run photos:picker -- create --max-items 20`
  - After Brian completes the picker link, poll with `npm run photos:picker -- get SESSION_ID` and list selected items with `npm run photos:picker -- list SESSION_ID`.
- Build combined ingestion summary:
  - `npm run ingest:summary`
- Dispatch async runner from new-ingest event:
  - `npm run ingest:dispatch`
- Publish deterministic ledger + optional summary email:
  - `npm run ingest:publish`
  - Default `changes` policy emails only when new records/tasks are created. Errors alone are logged to the ledger/artifacts to avoid recurring operational email noise.

## Environment Variables

- `AGENTCORE_DRIVE_INCLUDE_SHARED_WITH_ME` (`true` to ingest docs/folders shared with `scottishramp@gmail.com`; default in workflows)
- `AGENTCORE_TRUSTED_SHARE_SENDERS` optional comma-separated extension list for service share-notification senders. Defaults include Google Drive and Google Keep share notifications.
- Optional explicit folder watches:
  - `AGENTCORE_DRIVE_DOCS_FOLDER_ID` (Drive folder id for shared docs intake)
  - `AGENTCORE_DRIVE_PHOTOS_FOLDER_ID` (Drive folder id for Android photo/scans intake)
- Optional:
  - `AGENTCORE_GMAIL_AUTHORIZED_USER_FILE` (OAuth authorized-user JSON path)
  - `AGENTCORE_GMAIL_AUTHORIZED_USER_JSON` (OAuth authorized-user JSON inline)
  - OAuth consent uses the admin-assistant bundle in `scripts/email/gmail_oauth_setup.py`: read access for Brian-shared Gmail/Drive/Calendar/Workspace/Contacts surfaces and write access for AgentCore-owned Drive files, Workspace docs, Tasks, app-created Photos media, and user-selected Google Photos Picker sessions.
  - Google Keep share notifications can be recognized through Gmail, but Google Keep note content is not available to this personal account through the official API.
  - Google Photos no longer permits broad unattended library reads; AgentCore can manage app-created Photos media through the Library API and can ingest user-selected items through the Picker API after OAuth is refreshed with `photospicker.mediaitems.readonly`.

## Third-Party Share Notifications

Some services send share notifications from service-owned addresses instead of Brian's email address. Gmail fetch treats a default allowlist of Google share senders as trusted only when the email body names Brian's trusted email and is addressed to AgentCore. Verified share notifications are queued as source-processing tasks.

## Outputs

- State checkpoint: `.agentcore/state/drive-ingest-state.json`
- Run summary: `.agentcore/state/drive-ingest-summary.json`
- Combined summary: `.agentcore/state/ingestion-summary.json`
- Knowledge ledger: `agentcore/knowledge/communications/ingestion-ledger.md`
- Document records: `agentcore/inbox/drive/`
- Photo records: `agentcore/inbox/photos/`
- Queue tasks: `agentcore/inbox/tasks/`
