# AgentCore Ingestion Scripts

Cross-channel ingestion utilities for Drive documents and Android photo uploads.

## Commands

- Drive + photo ingest:
  - `npm run ingest:drive`
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
  - OAuth consent must include `https://www.googleapis.com/auth/drive.readonly`
  - Google Keep ingestion requires `https://www.googleapis.com/auth/keep.readonly`

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
