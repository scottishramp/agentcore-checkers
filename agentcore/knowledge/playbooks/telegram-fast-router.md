# Telegram Fast Router

## Architecture

**Fast layer (Vercel):** Gemini 3.6 Flash + a Brian/family knowledge snapshot + Redis history → instant reply. The snapshot is the people pages, family-facts, food log, Life 2026, personal OS, and 2026-27 roster. The nightly runner publishes it to Redis (`agentcore:fast-context`); live replies read that first so new facts show up without a Vercel redeploy. No Cursor startup, no durable classification, and **no realtime knowledge writes**. Acknowledgments for `knowledge_update` must say the item is queued for the scheduled async agent — never that knowledge was already saved.

**Async layer (GitHub Actions):** Write-capable scheduled pull from Redis inbox → transcript + per-message Cursor review tasks → durable knowledge updates / awareness refresh → Telegram notifications when useful → Vercel redeploy. This is the path that actually adds facts Brian asked to store.

## Setup

### 1. Bot

`@AgentCoreFam_bot` via `@BotFather`. Token in Vercel + GitHub as `TELEGRAM_BOT_TOKEN`.

### 2. Vercel env

- `TELEGRAM_BOT_TOKEN`
- `AGENTCORE_TELEGRAM_ALLOWED_USER_IDS` — required, comma-separated (fail closed)
- `KV_REST_API_URL` / `KV_REST_API_TOKEN` — Upstash (history + inbox queue)
- `GOOGLE_AI_STUDIO_API_KEY`, `AGENTCORE_FAST_MODEL` (optional; default `gemini-3.6-flash`)

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

### 6. Verify context propagation

After deploying, verify production health:

```sh
curl -sS https://agentcore-fast-router.vercel.app/api/agentcore-telegram | python3 -m json.tool
```

The response must show the expected `router_version`, `context_hash`, `context_files`, and `has_nathan_birthdate: true` when Life 2026 family facts are expected in Gemini context.

## Flow

1. User messages bot (text or photo + caption) → for photos, the webhook ACKs Telegram immediately, then the fast agent assigns label `{username}_{YYYYMMDDHHmmss}`, describes the image (up to ~290s), and replies with label + description.
2. Bot queues message to Redis with `photo_label`, `photo_description`, and media metadata.
3. Write-capable Actions fetch + triage and write normalized inbox records plus `agentcore/knowledge/communications/telegram-transcript.md`; every allowed message is queued for async Cursor review.
4. Cursor reads the review task, matching inbox record, transcript, and repo knowledge, then decides per message whether it is durable knowledge, coding/action work, or no-op; applies updates, then replies if needed. Cursor may output `NO_TELEGRAM_REPLY` to suppress a duplicate Telegram response when the fast bot already handled the turn.
5. For photos, runner uploads to Drive and updates `agentcore/knowledge/communications/telegram-photo-registry.json`; Cursor can file follow-on knowledge from the description.

### Photo intake (what actually happens)

- **Who looks at the image:** only Gemini 3.6 Flash on Vercel (`AGENTCORE_FAST_MODEL`, default `gemini-3.6-flash`). The later Cursor review does **not** reopen the photo; it files from the written description and caption.
- **Immediate path:** webhook returns 200 as soon as a photo arrives (`waitUntil` + `maxDuration` 300s). Gemini describes in the background, replies with `Photo label:` + prose, and queues Redis (`photo_label`, `photo_description`, Telegram `file_id`). Image bytes never go in git.
- **Durable path:** `agent-runner.yml` (8:30 AM America/Chicago, and after email-sync completes) — not `knowledge-content-ingest.yml`. Fetch Redis → triage inbox/transcript/Cursor task → `materialize_media.py` downloads from Telegram and uploads to AgentCore Drive → registry + `agentcore/inbox/photos/` → Cursor files facts and may reply with `Photo label:` / `Drive:` or `NO_TELEGRAM_REPLY`.
- **Describe contract (2.5.8+):** plain prose (not JSON), `thinkingLevel: minimal`, `maxOutputTokens: 4096`, recover truncated JSON if the model still emits it, one retry on 503/429. Gemini 3.6 Flash defaults to **medium** thinking; those tokens count against the output cap.

### Diagnose photo failures

1. Production health: `curl -sS https://agentcore-fast-router.vercel.app/api/agentcore-telegram` — check `router_version` and `fast_model`.
2. `npx vercel logs --environment production --since 2h --expand` is the source of truth. Labels: `telegram_message_received` (`has_media`), `photo_describe_error`, `telegram_message_routed`.
3. Telegram `getWebhookInfo.last_error_message` is often **stale**. A leftover `504 Gateway Timeout` from an earlier send does not mean the latest photo failed.
4. Classify the failure from the log, not Telegram’s red icon:
   - Webhook 504 / held HTTP response → Telegram waited ~60s and never got 200. Photos must ACK first.
   - `The operation was aborted due to timeout` → our vision/photo budget aborted Gemini.
   - Gemini `503` / `UNAVAILABLE` → model overloaded (3.7 Flash did this; we stepped down to 3.6).
   - `Unterminated string in JSON` → output cap + thinking truncated JSON. Do not treat as a webhook timeout.
   - `"vision description failed"` in chat is the **fallback reply** after a describe error, not a Telegram 504.
5. Changing the code default is not enough if Vercel `AGENTCORE_FAST_MODEL` is set (it is a production secret). Update that env and redeploy.
6. Local `.env` does not have the Gemini key; production does. Clear leftover photo-budget `setTimeout`s or `npm run router:test` hangs for the full budget (was 290s).

### Defer contract for unanswered questions

- If the fast layer cannot answer a text question from context, it replies exactly:
  - `*DEFER* The slower, smarter agent might be able to help with this`
- The original message is still queued to Redis for scheduled async triage.
- The fast layer should not invent task-specific assignment text in chat for deferred questions; async Cursor decides what to do.

## Scripts

- `scripts/telegram/fetch_pending.py` — pull Redis inbox
- `scripts/telegram/triage_messages.py` — inbox + transcript + Cursor review task queue
- `scripts/telegram/materialize_media.py` — Telegram photo → Drive + photo inbox records
- `scripts/telegram/send_working_notice.py` — task start notification
- `scripts/telegram/send_task_response.py` — task completion
- `scripts/telegram/send_scheduled_messages.py` — morning prompts (food check-ins disabled 2026-07-05)
- `scripts/telegram/publish_fast_context.js` — publish the current repo knowledge snapshot to Redis for live Telegram replies (`npm run telegram:publish-context`)
