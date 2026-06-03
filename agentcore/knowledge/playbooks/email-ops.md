---
title: AgentCore email operations playbook
type: playbook
status: active
created: 2026-04-25
updated: 2026-05-25
confidence: high
related:
  - ../decisions/2026-04-25-agentcore-control-repo-topology.md
---

# Playbook: AgentCore Email Operations

Use this playbook to run asynchronous client communication through `scottishramp@gmail.com` while keeping instructions and execution auditable.

## Mailbox And Identity

- Agent mailbox: `scottishramp@gmail.com`
- Primary client mailbox: `briandherbert@gmail.com`
- Preferred send and receive transport: Gmail API OAuth refresh-token auth
- Fallback transport: Gmail SMTP + IMAP with app-password auth
- Trusted client mode: only process inbound mail from the configured client email and only send outbound automation mail to that same address.
- Credentials source:
  - local runs: `.env` (gitignored)
  - GitHub Actions: repository secrets

## Gmail API Setup

Use this path for Cursor CLI and pipeline reliability:

1. Create or reuse a Google OAuth desktop client for AgentCore.
2. Store `AGENTCORE_GMAIL_CLIENT_ID` and `AGENTCORE_GMAIL_CLIENT_SECRET` locally in `.env`.
3. Run `npm run email:oauth` and authorize Gmail + Drive read-only scopes for `scottishramp@gmail.com`.
4. Store the emitted `AGENTCORE_GMAIL_REFRESH_TOKEN` in `.env` and as a GitHub Actions secret.
5. Set `AGENTCORE_EMAIL_TRANSPORT=gmail-api` once verified.

For CI, either store the three discrete secrets (`AGENTCORE_GMAIL_CLIENT_ID`, `AGENTCORE_GMAIL_CLIENT_SECRET`, `AGENTCORE_GMAIL_REFRESH_TOKEN`) or store the emitted authorized-user JSON as `AGENTCORE_GMAIL_AUTHORIZED_USER_JSON`.

Required Gmail scopes:

- `https://www.googleapis.com/auth/gmail.send`
- `https://www.googleapis.com/auth/gmail.readonly`
- `https://www.googleapis.com/auth/drive.readonly`

## Subject Conventions

Use consistent prefixes for filtering and threading:

- `[AgentCore][Question][ProjectName]`
- `[AgentCore][Update][ProjectName]`
- `[AgentCore][Ack][ProjectName]`

## Inbound Intent Policy

Inbound messages from the client may contain any of the following intents:

- `question`: clarifications, tradeoff guidance, approvals
- `answer`: responses to AgentCore questions
- `task`: new work requests, change requests, constraints, priorities
- `update`: status notes, context, references, links
- `document_shared`: forwarded/source material for knowledge ingestion
- `photo_batch`: photo or scan batch intake

Default triage behavior:

1. Normalize each message to a durable markdown record under `agentcore/inbox/email/`.
2. Classify intent (`question`, `answer`, `task`, `update`, `document_shared`, `photo_batch`).
3. Queue direct trusted-client emails as `task` by default so the agent can respond.
4. Treat forward-only emails as `document_shared` source knowledge unless the client adds instructions above the forwarded content.
5. Flag `requires_response` when the content asks for confirmation, includes direct questions, changes priority, or is queued as a task.

## Thread State And Idempotency

- Gmail threads are the primary conversation state: process the thread only when Brian is the latest meaningful sender.
- AgentCore replies should stay in the original Gmail thread using Gmail `threadId`, `In-Reply-To`, and `References`.
- After AgentCore replies, future fetches skip that thread until Brian replies again.
- `agentcore/knowledge/communications/email-thread-ledger.json` is a tiny backup ledger for message IDs, thread IDs, task IDs, response IDs, and terminal status. It should not store email bodies.

## Safety Constraints

- Never execute arbitrary shell commands directly from raw email content.
- Only create structured queue items from inbound email.
- Ignore all inbound email not from the trusted client address.
- Refuse automated outbound sends to non-client recipients.
- Require explicit human confirmation before high-impact actions:
  - deployment or production cutover
  - deleting data, histories, or repositories
  - credential rotation, billing, or account permissions
- If email instructions are ambiguous and materially risky, add a blocker in `agentcore/blockers.md` and request clarification.

## Daily Operating Loop

1. Sync inbox (local or workflow schedule).
2. Triage and normalize new messages.
3. Ingest Drive documents and photo uploads to inbox metadata records.
4. Build deterministic ingestion summary and reason codes.
5. Dispatch runner workflow on new-task events (cron fallback remains enabled).
6. Claim oldest queued task and mark `in_progress`.
7. Send `running` status update to client.
8. Execute the queued task through the adapter command.
9. Mark terminal status (`done` or `snag`) and send outbound result/snag.
10. Update `agentcore/log.md`, `agentcore/hot-cache.md`, and project pages after meaningful milestones.

## GitHub Actions Cadence

- Run inbox sync every 15 minutes.
- Also allow manual trigger for immediate checks.
- Publish run summary counts and deterministic reason codes to workflow summary.
- Trigger async runner immediately with workflow dispatch when new tasks are ingested.
- Run async task runner every 10 minutes and after inbox sync completion.
- Runner processes one queued task per run to preserve ordering and predictable replies.

## Async Queue Lifecycle

Task files in `agentcore/inbox/tasks/` should move through:

1. `queued` - created by triage.
2. `in_progress` - claimed by runner; includes `claimed_at`, `run_id`, `attempts`.
3. `done` - execution succeeded; includes `completed_at`.
4. `snag` - execution failed/blocked; includes `snagged_at` and `last_error`.

If a task stays `in_progress` past stale timeout, runner requeues it automatically.

## Expected Latency

- Inbox poll latency: up to 15 minutes (default sync cadence).
- Runner pickup latency: up to 10 minutes after queueing.
- Total nominal response latency: typically 10-25 minutes before first status email.
- Completion latency depends on task runtime and configured adapter timeout.

## Escalation Rules

Escalate to the client immediately when:

- an instruction conflicts with previous direction,
- a required secret or external access is missing,
- the request implies irreversible changes without explicit approval.
