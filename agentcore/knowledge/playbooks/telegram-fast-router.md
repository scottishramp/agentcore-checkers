# Telegram Fast Router

## Purpose

Instant 1:1 family chat with shared AgentCore knowledge. Each person DMs the same Telegram bot; replies come from the Vercel fast router (Gemini + repo context). Deeper work dispatches to Cursor async.

## Setup

### 1. Create the bot

1. In Telegram, open `@BotFather`.
2. Send `/newbot`.
3. Name it `AgentCore`.
4. Pick a username like `AgentCoreFamilyBot` (must end in `bot`).
5. Copy the bot token.

### 2. Configure Vercel

Set production env vars on `agentcore-fast-router`:

- `TELEGRAM_BOT_TOKEN` — token from BotFather
- `AGENTCORE_TELEGRAM_WEBHOOK_SECRET` — optional random secret for webhook verification
- `AGENTCORE_TELEGRAM_ALLOWED_USER_IDS` — optional comma-separated Telegram user ids (empty = open to anyone who finds the bot)

Existing Gemini/GitHub vars stay the same.

### 3. Deploy and register webhook

```sh
npx vercel deploy --prod
TELEGRAM_BOT_TOKEN=... npm run telegram:setup-webhook
```

Webhook URL: `https://agentcore-fast-router.vercel.app/api/agentcore-telegram`

### 4. Start chatting

Search for **`@AgentCoreFam_bot`** in Telegram and send a message. Replies should arrive in 1–3 seconds.

## Family sharing

One bot, many 1:1 DMs. Everyone shares the same repo-backed knowledge context. Optional allowlist via `AGENTCORE_TELEGRAM_ALLOWED_USER_IDS`.

To find a Telegram user id: message `@userinfobot` or read webhook logs after the first message.

## Endpoint

- `GET /api/agentcore-telegram` — health check
- `POST /api/agentcore-telegram` — Telegram webhook

## Async handoff

Knowledge updates and tasks dispatch to `.github/workflows/router-task.yml`. Completion replies go back via `scripts/telegram/send_task_response.py`.
