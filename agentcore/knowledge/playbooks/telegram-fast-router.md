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

### 5. Deploy auth model (important)

- Local/manual deploys can use Vercel CLI session auth (`npx vercel deploy --prod --yes`) when this repo is linked to the project in `.vercel/project.json`.
- Current local project link points at `agentcore-fast-router` (team/org id `team_in3HNh0USnTggSAU4DyssUKT`).
- GitHub Actions redeploy is separate and requires `VERCEL_TOKEN` repo secret; without it, CI will not update Vercel production.

## Flow

1. User messages bot (text or photo + caption) → for photos, fast agent assigns label `{username}_{YYYYMMDDHHmmss}`, describes the image in detail, and replies with label + description.
2. Bot queues message to Redis with `photo_label`, `photo_description`, and media metadata.
3. Actions fetch + triage → tasks for photos; runner uploads to Drive and writes `agentcore/knowledge/communications/telegram-photo-registry.json`.
4. Cursor files knowledge from the description, updates the registry, and replies with `Photo label:` + `Drive:` lines.

### Defer contract for unanswered questions

- If the fast layer cannot answer a text question from context, it replies exactly:
  - `*DEFER* The slower, smarter agent might be able to help with this`
- The original message is still queued to Redis for scheduled async triage.
- The fast layer should not invent task-specific assignment text in chat for deferred questions.

## Scripts

- `scripts/telegram/fetch_pending.py` — pull Redis inbox
- `scripts/telegram/triage_messages.py` — inbox + task queue
- `scripts/telegram/materialize_media.py` — Telegram photo → Drive + photo inbox records
- `scripts/telegram/send_working_notice.py` — task start notification
- `scripts/telegram/send_task_response.py` — task completion
- `scripts/telegram/send_scheduled_messages.py` — food check-ins, morning prompts
