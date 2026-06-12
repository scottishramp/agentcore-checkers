# Task Queue Records

This folder stores queue-ready tasks derived from inbound email intent classification.

## Filename Format

- `task__uid-<uid>__<sanitized-subject>.md`

## Required Metadata

Each task file includes:

- `task_id` (deterministic from source UID/thread)
- `status` (`queued` | `in_progress` | `done` | `snag`)
- `priority`
- `source_message_id`
- `source_uid`
- `source_from`
- `source_subject`
- `thread_key`
- `queued_at`
- `updated_at`
- `attempts`
- `claimed_at`
- `run_id`
- `completed_at`
- `snagged_at`
- `last_error`
- `result_path`

## Processing Flow

1. `triage_messages.py` creates `queued` task files for inbound `task` intent.
2. Queue runner claims oldest `queued` task and marks it `in_progress`.
3. After the first task completes, `queue_drain_loop.py` can poll for new inbound messages and process additional queued tasks in the same runner session (default up to 10 tasks or 20 minutes).
4. Runner marks terminal status as `done` or `snag`.
5. Active working sessions review and either:
   - convert to project work in `agentcore/knowledge/projects/`, or
   - clarify with client by outbound email question.
5. Keep source linkage intact so each task can be traced to the originating message.
