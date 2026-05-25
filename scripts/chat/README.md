# AgentCore Google Chat Script

Programmatic direct-message send using Google Chat REST APIs and `gcloud` Application Default Credentials (ADC).

## One-time auth setup

Run from repo root and complete browser consent:

```sh
gcloud auth application-default login --scopes="openid,https://www.googleapis.com/auth/userinfo.email,https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/chat.spaces,https://www.googleapis.com/auth/chat.messages.create"
```

## Command

From repo root:

```sh
python3 scripts/chat/send_direct_message.py --to briandherbert@gmail.com --text "Test from AgentCore"
```

## Notes

- Uses `gcloud auth application-default print-access-token` on each run.
- Finds existing DM via `spaces:findDirectMessage`.
- If DM does not exist, creates it via `spaces:setup` (unless `--no-create-dm` is set).
- Default recipient is `AGENTCORE_CLIENT_EMAIL` (fallback: `briandherbert@gmail.com`).
- For safety, sending is restricted to trusted client email unless `--allow-non-client` is supplied.
