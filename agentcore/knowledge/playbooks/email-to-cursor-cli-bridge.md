---
title: Email to Cursor CLI bridge (guarded phase-2)
type: playbook
status: draft
created: 2026-04-25
updated: 2026-04-25
confidence: medium
related:
  - ./email-ops.md
---

# Playbook: Email to Cursor CLI Bridge (Guarded Phase-2)

Use this playbook to safely convert approved inbound email intents into Cursor CLI task execution.

## Goal

Allow controlled automation from client emails while preventing arbitrary command execution.

## Safety Model

1. Parse inbound emails into structured intents (`task`, `question`, `update`).
2. Match task intents against an explicit allowlist of operation types.
3. Convert valid intents into a machine-readable queue item.
4. Run Cursor CLI in dry-run mode first and publish planned actions.
5. Require explicit confirmation before executing high-impact intents.

## Allowlist Categories

Only these categories may auto-enqueue for phase-2:

- `project-kickoff`
- `doc-update`
- `research-brief`
- `status-digest`
- `test-run-non-destructive`

Blocked categories (must stay manual):

- deployment, credential changes, billing actions, destructive data/repo operations

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

1. Intake script writes queue item to `.agentcore/queue/pending/*.json`.
2. Validation script rejects items missing required fields.
3. Bridge runner invokes Cursor CLI with a fixed template prompt per intent type.
4. Runner stores transcript metadata and outcome in `.agentcore/queue/history/`.
5. Runner emails acknowledgement/update back to client.

## Current Repository Implementation Notes

- Queue artifacts are markdown task files under `agentcore/inbox/tasks/`.
- Claim logic lives in `scripts/email/claim_next_task.py` and supports stale requeue.
- Runner adapter lives in `scripts/email/run_task_adapter.py` and returns `done`/`snag`.
- Notification templates live in `scripts/email/send_task_status.py`.
- Terminal state writes are handled by `scripts/email/finalize_task.py`.

## Rollout Sequence

1. Implement queue generation in dry-run mode only.
2. Add workflow/manual command to render planned execution without running.
3. Enable one low-risk category (`status-digest`) in execute mode.
4. Expand categories only after two successful review cycles.
