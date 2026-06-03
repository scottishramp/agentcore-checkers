# AgentCore Agent Runner

Utilities for running queued AgentCore tasks through Cursor Agent.

## Command

```sh
python3 scripts/agent/run_cursor_task.py --task-file agentcore/inbox/tasks/example.md
```

## Required Environment

- Local Cursor login or `CURSOR_API_KEY`
- In GitHub Actions, set `CURSOR_API_KEY` as a repository secret.

## Behavior

- Direct emails from Brian are treated as instructions and should produce an email-ready response.
- Forward-only emails are treated as source knowledge unless Brian added instructions above the forwarded message.
- Durable facts should be written into the AgentCore knowledge base.
