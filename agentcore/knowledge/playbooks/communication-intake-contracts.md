# Communication Intake Contracts

## Purpose

Define one canonical intake contract across chat, email, Drive documents, and Android photo uploads so automation can classify work consistently and update the knowledge base deterministically.

## Channel Contracts

### Cursor Chat

- Channel id: `cursor_chat`
- Source of truth: chat transcript and resulting repo changes
- Contract output: knowledge updates and task files only when explicitly converted to executable work

### Email

- Channel id: `email`
- Intake source: trusted sender mailbox (`AGENTCORE_CLIENT_EMAIL`)
- Required record fields:
  - `uid`
  - `message_id`
  - `thread_key`
  - `from_email`
  - `subject`
  - `received_at`
  - `classification`
  - `requires_response`
  - `triaged_at`

### Google Drive Documents

- Channel id: `drive_document`
- Intake source: shared docs folders and optional `sharedWithMe`
- Required record fields:
  - `drive_file_id`
  - `title`
  - `mime_type`
  - `modified_time`
  - `created_time`
  - `owner_email`
  - `web_view_link`
  - `source_folder_id`
  - `recorded_at`
  - `requires_review`

### Android Photo Uploads

- Channel id: `photo_upload`
- Intake source: Drive photo landing folder (default expected: `Inbox-Scans`)
- Required record fields:
  - `drive_file_id`
  - `title`
  - `mime_type`
  - `modified_time`
  - `created_time`
  - `owner_email`
  - `web_view_link`
  - `source_folder_id`
  - `recorded_at`
  - `requires_review`

## Intent Classes

- `task`: explicit request to do work
- `question`: direct question requiring reply
- `answer`: response to prior question
- `update`: context update that may not require immediate response
- `document_shared`: document or file shared for organization/review
- `photo_batch`: one or more uploaded photos/scans to process

## Deterministic Reply Reason Codes

Use one reason code per outbound ingestion summary:

- `NO_NEW_ITEMS`
- `NEW_EMAIL_TASKS`
- `NEW_DOCUMENTS`
- `NEW_PHOTOS`
- `REQUIRES_CLARIFICATION`
- `RUNNER_SNAG`

## Knowledge Update Contract

Every automated ingestion run should create:

1. A machine-readable summary under `.agentcore/state/`.
2. A ledger update entry under `agentcore/knowledge/communications/ingestion-ledger.md`.
3. Optional outbound email summary to the trusted client channel when new items or errors are detected.

## Safety Rules

- Do not persist raw sensitive document content in git.
- Store links and metadata in repo; store source files in Drive.
- Keep trusted-sender enforcement for inbound mail.
- Skip non-client senders unless an explicit policy update is made.
