---
title: Email to Cursor CLI bridge
type: playbook
status: active
created: 2026-04-25
updated: 2026-05-25
confidence: medium
related:
  - ./email-ops.md
---

# Playbook: Email to Cursor CLI Bridge

Use this playbook to safely convert trusted-client email intents into Cursor Agent task execution.

## Goal

Allow controlled automation from client emails while preventing arbitrary command execution.

## Safety Model

1. Parse inbound emails into structured intents (`task`, `answer`, `update`, `document_shared`).
2. Queue direct trusted-client emails as task records by default.
3. Treat forward-only emails as source knowledge unless Brian adds instructions above the forwarded content.
4. Run Cursor Agent through a fixed command adapter, not arbitrary email-provided shell.
5. Allow trusted-client email tasks to self-update this repository for AgentCore behavior, workflow, script, rule, docs, and knowledge changes.
6. Require explicit confirmation before destructive external actions, credential disclosure, billing actions, or sensitive data sharing.

## Allowlist Categories

These categories may auto-enqueue:

- `direct-client-email`
- `project-kickoff`
- `doc-update`
- `agentcore-self-update`
- `workflow-update`
- `integration-request`
- `research-brief`
- `status-digest`
- `test-run-non-destructive`

Blocked categories (must stay manual):

- credential disclosure, billing actions, destructive external actions, destructive data/repo operations, and user-account actions requiring 2FA or fresh consent

## Proposed Queue Schema

```json
{
  "intent_id": "email-uid-1234",
  "source_message_id": "<...>",
  "intent_type": "doc-update",
  "project_key": "agentcore",
  "dry_run": true,
  "requires_approval": true,
  "created_at": "2026-04-25T00:00:00Z"
}
```

## Execution Lifecycle

1. Intake script writes queue item under `agentcore/inbox/tasks/`.
2. Claim script marks one task `in_progress`.
3. Runner invokes `scripts/agent/run_cursor_task.py` through `run_task_adapter.py`.
4. Cursor Agent processes the task, may edit the repository, and prints an email-ready result.
5. The runner commits and pushes successful non-ignored workspace changes before sending the completion email.
6. Notification script emails the natural reply or snag back to Brian.

## Current Repository Implementation Notes

- Queue artifacts are markdown task files under `agentcore/inbox/tasks/`.
- Claim logic lives in `scripts/email/claim_next_task.py` and supports stale requeue.
- Runner adapter lives in `scripts/email/run_task_adapter.py` and returns `done`/`snag`.
- Cursor Agent wrapper lives in `scripts/agent/run_cursor_task.py`.
- Notification templates live in `scripts/email/send_task_status.py`.
- Terminal state writes are handled by `scripts/email/finalize_task.py`.
- Successful Cursor Agent workspace edits are committed by `agent-runner.yml` using `git add -A`; `.gitignore` prevents `.env`, `.secrets/`, and `.agentcore/state/` from being committed.

## Rollout Sequence

1. Add `CURSOR_API_KEY` as a GitHub Actions repository secret.
2. Send a direct test email: `just say hi and tell me the current date`.
3. Verify the runner claims the task, Cursor Agent returns a concise answer, and the notification email contains the response.
4. Expand policies only after observing low-risk direct-email behavior.
