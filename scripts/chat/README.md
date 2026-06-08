# AgentCore Google Chat Script

Programmatic direct-message send using Google Chat REST APIs.

## Auth

The script prefers AgentCore's repo-managed OAuth authorized-user token:

- `AGENTCORE_GMAIL_AUTHORIZED_USER_FILE`
- `AGENTCORE_GMAIL_AUTHORIZED_USER_JSON`

These credentials are produced by `npm run email:oauth` and must include:

- `https://www.googleapis.com/auth/chat.spaces.create`
- `https://www.googleapis.com/auth/chat.messages.create`

If repo OAuth credentials are unavailable, the script falls back to `gcloud` Application Default Credentials (ADC).

## Command

From repo root:

```sh
python3 scripts/chat/send_direct_message.py --to briandherbert@gmail.com --text "Test from AgentCore"
```

## Notes

- Uses the same authorized-user token as Gmail/Drive/Calendar automation by default.
- Creates or reuses a DM via `spaces:setup`.
- `--no-create-dm` uses `spaces:findDirectMessage` and may require an additional Chat read scope.
- Default recipient is `AGENTCORE_CLIENT_EMAIL` (fallback: `briandherbert@gmail.com`).
- For safety, sending is restricted to trusted client email unless `--allow-non-client` is supplied.
