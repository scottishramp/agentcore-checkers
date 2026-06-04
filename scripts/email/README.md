# AgentCore Email Scripts

Lightweight Python scripts for outbound messaging, inbound inbox triage, and async queue execution.

## Recommended Transport

Use Gmail API OAuth for durable local, Cursor CLI, and GitHub Actions operation. SMTP/IMAP app-password auth remains available as a fallback, but Gmail API is preferred because it does not depend on mailbox password login.

## Environment Variables

- `AGENTCORE_EMAIL` (fallback: `GOOGLE_EMAIL`)
- `AGENTCORE_CLIENT_EMAIL` (trusted client email, default: `briandherbert@gmail.com`)
- `AGENTCORE_EMAIL_TRANSPORT` (`auto`, `gmail-api`, `smtp`, or `imap`; default `auto`)
- Gmail API OAuth:
  - `AGENTCORE_GMAIL_CLIENT_ID`
  - `AGENTCORE_GMAIL_CLIENT_SECRET`
  - `AGENTCORE_GMAIL_REFRESH_TOKEN`
  - or `AGENTCORE_GMAIL_AUTHORIZED_USER_JSON`
  - or `AGENTCORE_GMAIL_AUTHORIZED_USER_FILE`
- SMTP/IMAP fallback:
  - `AGENTCORE_EMAIL_APP_PASSWORD` (fallback: `GOOGLE_PASSWORD`)
- Optional:
  - `AGENTCORE_SMTP_HOST` (default `smtp.gmail.com`)
  - `AGENTCORE_SMTP_PORT` (default `465`)
  - `AGENTCORE_IMAP_HOST` (default `imap.gmail.com`)
  - `AGENTCORE_IMAP_PORT` (default `993`)
  - `AGENTCORE_TASK_RUN_COMMAND` (adapter command; include `{{TASK_FILE}}`)
  - `AGENTCORE_TASK_RUN_TIMEOUT_SECONDS` (default `900`)

## Commands

From repo root:

- Create a Gmail OAuth refresh token:
  - `npm run email:oauth`
  - or explicitly: `npm run email:oauth -- --client-file .secrets/google-oauth-client.json`
  - default writes authorized-user JSON to `.secrets/gmail-authorized-user.json` with restricted permissions
- Send question/update/ack:
  - `npm run email:ask -- --project "ProjectName" --kind question --subject "..." --body "..."`
- Fetch inbound mail from checkpoint:
  - `npm run email:fetch`
- Triage latest fetch payload:
  - `npm run email:triage`
- Run fetch + triage:
  - `npm run email:sync`
- Run cross-channel ingest summary pipeline:
  - `npm run email:sync && npm run ingest:drive && npm run ingest:summary && npm run ingest:publish -- --send-policy changes`
- Claim oldest queued task:
  - `npm run email:claim -- --output .agentcore/state/task-claim.json`
- Run claimed task via adapter:
  - `npm run email:run-task -- --task-file agentcore/inbox/tasks/task__uid-123__example.md`
- Run claimed task through Cursor Agent directly:
  - `npm run agent:run-task -- --task-file agentcore/inbox/tasks/task__uid-123__example.md`
- Finalize claimed task to `done`/`snag`:
  - `npm run email:finalize-task -- --task-file ... --result-json .agentcore/state/task-run-result.json`
- Send task status email (`running`, `done`, `snag`):
  - `npm run email:notify-task -- --task-file ... --status running`
- Record terminal email response metadata:
  - `npm run email:record-response -- --task-file ... --result-json ... --notification-json ...`

## Notes

- In `auto` mode, send/fetch use Gmail API when OAuth refresh-token credentials are present. Otherwise send falls back to SMTP and fetch falls back to IMAP.
- For CI, either store the three discrete Gmail OAuth secrets or store one `AGENTCORE_GMAIL_AUTHORIZED_USER_JSON` secret containing the authorized-user JSON emitted by `npm run email:oauth`.
- `npm run email:oauth` auto-reads `.secrets/google-oauth-client.json` when present, so the client secret does not need to live in `.env`.
- `npm run email:oauth` redacts token output by default; pass `--print-secrets` only when you explicitly need raw values in terminal output.
- Checkpoint file: `.agentcore/state/email-last-uid.json`
- Fetch payload: `.agentcore/state/email-fetch/latest.json`
- Triage summary: `.agentcore/state/email-sync-summary.json`
- Inbound processing only accepts messages from `AGENTCORE_CLIENT_EMAIL`.
- Outbound sending is locked to `AGENTCORE_CLIENT_EMAIL`.
- Direct trusted-client emails queue as tasks by default.
- Forward-only emails are classified as `document_shared`; if Brian adds text above the forwarded content, that text is treated as instructions and the email queues as a task.
- GitHub Actions agent replies require `CURSOR_API_KEY` to be set as a repository secret.
- Queue lock file: `.agentcore/state/task-queue.lock`
- Claim output: `.agentcore/state/task-claim.json`
- Run output: `.agentcore/state/task-run-result.json`
- Run logs: `.agentcore/state/task-runs/`
- Email thread idempotency ledger: `agentcore/knowledge/communications/email-thread-ledger.json`
- Task completion replies are sent into the original Gmail thread when Gmail thread metadata is available. Future fetches skip threads where AgentCore is already the latest sender.
- For direct Gmail tasks, final `done`/`snag` notifications are formatted as human replies in the original thread. Operational task IDs, run IDs, and logs stay in artifacts/ledgers instead of the email body.

## Async Chat Loop (Email + GitHub Actions)

1. Inbox sync fetches inbound trusted-client messages.
2. Triage normalizes messages and writes queued tasks under `agentcore/inbox/tasks/`.
3. Runner claims one queued task (`status: in_progress`) with stale-lock recovery.
4. Runner sends a `running` status email.
5. Adapter executes `AGENTCORE_TASK_RUN_COMMAND` with `{{TASK_FILE}}`.
6. Runner finalizes task as `done` or `snag`, then emails completion/snag.

### Adapter Contract

- Runner command is sourced from `AGENTCORE_TASK_RUN_COMMAND`.
- Supported placeholders:
  - `{{TASK_FILE}}`
  - `{{TASK_ID}}`
  - `{{THREAD_KEY}}`
- If command is missing, the run is explicitly marked `snag` and a snag notification is sent.
