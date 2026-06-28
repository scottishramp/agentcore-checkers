# Telegram Fast Router

## Architecture

**Fast layer (Vercel):** Gemini + repo context + Redis history → instant reply. No Cursor startup.

**Async layer (GitHub Actions):** Scheduled pull from Redis inbox → triage → Cursor tasks → Telegram notifications → Vercel redeploy.

## Setup

### 1. Bot

`@AgentCoreFam_bot` via `@BotFather`. Token in Vercel + GitHub as `TELEGRAM_BOT_TOKEN`.

### 2. Vercel env

- `TELEGRAM_BOT_TOKEN`
- `AGENTCORE_TELEGRAM_ALLOWED_USER_IDS` — required, comma-separated (fail closed)
- `KV_REST_API_URL` / `KV_REST_API_TOKEN` — Upstash (history + inbox queue)
- `GOOGLE_AI_STUDIO_API_KEY`, `AGENTCORE_FAST_MODEL` (optional)

### 3. GitHub Actions secrets

- `TELEGRAM_BOT_TOKEN`
- `AGENTCORE_TELEGRAM_ALLOWED_USER_IDS` or `AGENTCORE_TELEGRAM_NOTIFY_CHAT_IDS` (for scheduled messages + failure alerts)
- `KV_REST_API_URL` / `KV_REST_API_TOKEN` (same Upstash instance)
- `CURSOR_API_KEY`
- `VERCEL_TOKEN` (optional — redeploy bot after knowledge commits)

### 4. Deploy

```sh
npx vercel deploy --prod
TELEGRAM_BOT_TOKEN=... npm run telegram:setup-webhook
```

Webhook: `https://agentcore-fast-router.vercel.app/api/agentcore-telegram`

## Flow

1. User messages bot → Gemini classifies (`lightweight_answer`, `knowledge_update`, `task`, …).
2. Bot replies immediately; message queued to Redis with route metadata.
3. Every 30–60 min, Actions fetch + triage → tasks for `knowledge_update` / `task`.
4. Runner sends “Working on: …”, runs Cursor, commits, sends completion, redeploys Vercel.

## Versioning

Bump `chatbot-version.json`, deploy, verify with `version` in chat.

## Scripts

- `scripts/telegram/fetch_pending.py` — pull Redis inbox
- `scripts/telegram/triage_messages.py` — inbox + task queue
- `scripts/telegram/send_working_notice.py` — task start notification
- `scripts/telegram/send_task_response.py` — task completion
- `scripts/telegram/send_scheduled_messages.py` — food check-ins, morning prompts
