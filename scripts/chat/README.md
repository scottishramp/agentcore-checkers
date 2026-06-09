# AgentCore Google Chat Script

Programmatic direct-message send using Google Chat REST APIs.

## Auth

The script prefers AgentCore's repo-managed OAuth authorized-user token:

- `AGENTCORE_GMAIL_AUTHORIZED_USER_FILE`
- `AGENTCORE_GMAIL_AUTHORIZED_USER_JSON`

These credentials are produced by `npm run email:oauth` and must include:

- `https://www.googleapis.com/auth/chat.spaces.create`
- `https://www.googleapis.com/auth/chat.messages.create`
- `https://www.googleapis.com/auth/chat.messages.readonly`

If repo OAuth credentials are unavailable, the script falls back to `gcloud` Application Default Credentials (ADC).

## Commands

Send a direct message:

From repo root:

```sh
python3 scripts/chat/send_direct_message.py --to briandherbert@gmail.com --text "Test from AgentCore"
```

Fetch and triage inbound Chat messages:

```sh
npm run chat:sync
```

Reply to a completed Chat-origin task:

```sh
npm run chat:respond-task -- --task-file agentcore/inbox/tasks/task__chat__example.md --status done --result-json .agentcore/state/task-run-result.json
```

Maintain a bounded pseudo-synchronous session after a Chat-origin task:

```sh
npm run chat:sync-loop -- --seed-task-file agentcore/inbox/tasks/task__chat__example.md
```

## Notes

- Uses the same authorized-user token as Gmail/Drive/Calendar automation by default.
- Creates or reuses a DM via `spaces:setup`.
- `--no-create-dm` uses `spaces:findDirectMessage` and may require an additional Chat read scope.
- Fetching reads Brian's configured direct-message space (`AGENTCORE_CHAT_DM_SPACE`, default `spaces/6RZ69yAAAAE`) and skips AgentCore-authored messages (`AGENTCORE_CHAT_SELF_USER_NAME`).
- The GitHub Actions runner can keep a pseudo-synchronous Chat session open after a conversational Chat task. Defaults: enabled, `America/Chicago`, 9:00-20:00 local time, 15 minute max, 20 second poll interval.
- Default recipient is `AGENTCORE_CLIENT_EMAIL` (fallback: `briandherbert@gmail.com`).
- For safety, sending is restricted to trusted client email unless `--allow-non-client` is supplied.
