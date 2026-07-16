# Knowledge Content Ingest

Periodic cross-channel ingest that pulls **full content** from Gmail, Telegram, and allowlisted shared Drive docs into durable knowledge. Runs separately from fast triage (email-sync / agent-runner) on a slower cadence.

## Schedule

- GitHub Actions: `.github/workflows/knowledge-content-ingest.yml`
- Cron: daily 11:00 AM America/Chicago (`0 16 * * *` UTC during CDT)
- Manual: `workflow_dispatch` or `npm run ingest:knowledge-content`

## Sources

| Channel | What gets ingested | Where it lands |
|---------|-------------------|----------------|
| Gmail | Trusted-client and share-notification bodies (7-day lookback) | `agentcore/inbox/email/` |
| Telegram | Async triage records, transcript entries, and per-message Cursor review tasks | `agentcore/inbox/telegram/` + `agentcore/knowledge/communications/telegram-transcript.md` |
| Shared Drive | Metadata via `ingest_drive_updates.py`; **full body** for allowlisted docs | `agentcore/inbox/drive/` + `.agentcore/state/drive-content/` |

## Allowlist

`agentcore/knowledge/documents/content-ingest-allowlist.json` lists Drive file ids whose bodies should be exported. Each entry may reference a `deferred_task_id` that activates once export succeeds.

## Pipeline

1. `scripts/ingest/knowledge_content_ingest.py` — orchestrator
2. `scripts/ingest/export_flagged_docs.py` — Drive API export to text
3. `scripts/ingest/activate_content_tasks.py` — flip `deferred` → `queued`
4. Workflow commits exports + inbox updates; dispatches async runner when content tasks activate or Telegram review tasks are created
5. Cursor tasks extract durable facts into `agentcore/knowledge/` pages

## Local Commands

```sh
npm run ingest:knowledge-content   # full pipeline + runner dispatch
npm run ingest:export-docs         # Drive exports only
npm run ingest:activate-content-tasks
```

## Why Separate from Email Sync

Email-sync (daily 6:00 AM CT) and agent-runner (daily 8:30 AM CT, plus after email-sync) handle routine inbox triage and task execution. Knowledge content ingest is heavier (Drive exports, multi-channel sweep) and targets facts that change slowly (family dates, shared doc content). A once-daily cadence is sufficient.

## Adding a New Doc to Content Ingest

1. Add an entry to `content-ingest-allowlist.json` with `drive_file_id`, `title`, `index_page`, and optional `deferred_task_id`.
2. Optionally create a deferred task under `agentcore/inbox/tasks/` that references `.agentcore/state/drive-content/{file_id}.txt`.
3. Next ingest cycle exports the body and activates the task.
