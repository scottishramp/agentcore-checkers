---
title: Brian Gmail mailbox access
type: playbook
status: active
created: 2026-08-16
updated: 2026-08-16
confidence: high
related:
  - ./email-ops.md
  - ../architecture/system-architecture.md
  - ../people/brian-herbert.md
---

# Playbook: Brian Gmail Mailbox Access

Use this playbook to read and organize `briandherbert@gmail.com` without mixing it with AgentCore's own mailbox (`scottishramp@gmail.com`).

## Authority

Brian granted AgentCore access to his personal Gmail on 2026-08-16:

- Read all mail
- Create labels
- Apply and remove labels
- Archive (remove `INBOX`)
- Trash (Gmail Trash, recoverable for about 30 days)

Do **not** send as Brian. Permanent skip-Trash deletion is not enabled. Do **not** copy full message bodies into git.

This is a separate OAuth token from AgentCore's own Gmail/Drive/Calendar token.

## Credentials

Local:

- `.secrets/brian-gmail-authorized-user.json` (gitignored)
- `.env`: `AGENTCORE_BRIAN_GMAIL_AUTHORIZED_USER_FILE=.secrets/brian-gmail-authorized-user.json`

GitHub Actions:

- Secret `AGENTCORE_BRIAN_GMAIL_AUTHORIZED_USER_JSON`

Scope:

- `https://www.googleapis.com/auth/gmail.modify`

## Authorize Or Refresh

1. Sign into Google as `briandherbert@gmail.com`, not `scottishramp@gmail.com`.
2. From repo root run:

```sh
npm run email:oauth:brian
```

3. Approve Gmail read, label, archive, and trash access.
4. Confirm the helper printed `Authorized account: briandherbert@gmail.com`.
5. Refresh the GitHub secret:

```sh
gh secret set AGENTCORE_BRIAN_GMAIL_AUTHORIZED_USER_JSON < .secrets/brian-gmail-authorized-user.json
```

The setup command refuses to save a token if a different Google account was used.

## Commands

From repo root:

```sh
npm run email:brian -- profile
npm run email:brian -- labels list
npm run email:brian -- labels ensure --name "AgentCore/Receipts"
npm run email:brian -- messages list --query "newer_than:7d" --max 10
npm run email:brian -- messages get --id MESSAGE_ID --body
npm run email:brian -- messages modify --id MESSAGE_ID --add-label AgentCore
npm run email:brian -- messages archive --id MESSAGE_ID
npm run email:brian -- messages trash --id MESSAGE_ID
```

`profile` also ensures the `AgentCore` label exists.

## Operating Rules

- Query live mail on demand. Do not ingest Brian's whole mailbox into `agentcore/inbox/email/`.
- Trusted-client tasking still uses mail Brian sends to `scottishramp@gmail.com`.
- Archive or trash only when Brian asked or the current task clearly requires it.
- Prefer labels under the `AgentCore/` namespace for AgentCore-created filing.
- Keep subjects, senders, dates, labels, and action notes in knowledge pages when useful; leave bodies in Gmail.
