# AgentCore System Architecture

Last updated: 2026-06-27

## Purpose

AgentCore is Brian Herbert's private administrative assistant. This repository is the durable control plane and memory: code, workflows, rules, metadata, ledgers, and synthesized knowledge live here. Source documents, scans, photos, and organized files should live in AgentCore-owned Google Drive when possible.

## Identities

- AgentCore Google identity: `scottishramp@gmail.com`.
- Brian trusted client identity: `briandherbert@gmail.com`.
- GitHub account/repo: `scottishramp/agentcore-checkers`.
- Primary chat: **Telegram** `@AgentCoreFam_bot` at `https://agentcore-fast-router.vercel.app/api/agentcore-telegram`.

## Communication Surfaces

### Telegram (Primary)

Two layers: **fast chat** (Vercel + Gemini) and **async agent** (GitHub Actions + Cursor).

#### Fast chat (synchronous)

1. User DMs `@AgentCoreFam_bot`.
2. Telegram POSTs to the Vercel webhook.
3. Allowlist check (fail closed); unknown users dropped silently.
4. Gemini replies using repo context bundle + Upstash conversation history (20 messages, persistent). Photos receive a unique label (`{username}_{YYYYMMDDHHmmss}`), a detailed fast-agent vision description in the reply, and are queued with label + description metadata.
5. Every allowed message is appended to the Upstash inbox queue (`agentcore:telegram:inbox`) with route metadata and optional `media` — **no Cursor dispatch from Vercel**.

#### Async agent (scheduled)

1. `email-sync.yml` (every 30 min) and `agent-runner.yml` (hourly) pull pending messages from Upstash.
2. `scripts/telegram/triage_messages.py` writes inbox records under `agentcore/inbox/telegram/` and queues tasks for `knowledge_update` / `task` routes (photos always queue).
3. `scripts/telegram/materialize_media.py` downloads Telegram photos, uploads to Drive, writes `agentcore/inbox/photos/`, and updates `agentcore/knowledge/communications/telegram-photo-registry.json` (label → Drive URL + description).
4. Cursor photo tasks file knowledge from the fast-agent description and reply on Telegram with `Photo label:` and `Drive:` lines.
5. `agent-runner.yml` claims tasks, sends **“Working on: …”** via Telegram, runs Cursor, commits knowledge, notifies completion via Telegram, redeploys Vercel when `VERCEL_TOKEN` is set.
6. Food check-ins and morning prompts go to Telegram via `scripts/telegram/send_scheduled_messages.py`.

Playbook: `agentcore/knowledge/playbooks/telegram-fast-router.md`

### Email

1. Gmail API fetches trusted-client email.
2. Normalized records under `agentcore/inbox/email/`.
3. Triage creates tasks under `agentcore/inbox/tasks/`.
4. Cursor runner replies into the original Gmail thread.
5. `email-thread-ledger.json` tracks idempotency.

## Workflows

- `.github/workflows/email-sync.yml`: email + Telegram inbox fetch/triage, Drive ingest, runner dispatch.
- `.github/workflows/agent-runner.yml`: Telegram triage, task execution, Telegram notifications, Vercel redeploy.

**Removed:** Google Chat polling, Google Chat HTTP app (`/api/agentcore-chat`), and `router-task.yml` live `repository_dispatch`.

## Data Stores

- `agentcore/inbox/telegram/`: normalized Telegram messages from async triage.
- `agentcore/inbox/photos/`: Telegram photo metadata after Drive materialization.
- `agentcore/knowledge/communications/telegram-photo-registry.json`: label → Drive URL, description, filing status.
- `agentcore/knowledge/communications/telegram-thread-ledger.json`: Telegram triage idempotency.
- Upstash Redis: conversation history + inbound inbox queue.
- Standard repo stores: `hot-cache.md`, `index.md`, `blockers.md`, `log.md`, `inbox/tasks/`, etc.

## Secrets

- **Vercel:** `TELEGRAM_BOT_TOKEN`, `AGENTCORE_TELEGRAM_ALLOWED_USER_IDS`, Gemini key, `KV_REST_API_*`.
- **GitHub Actions:** Gmail OAuth, `CURSOR_API_KEY`, `TELEGRAM_BOT_TOKEN`, `KV_REST_API_*`, optional `VERCEL_TOKEN` for bot context redeploy.

## Chatbot Versioning

- Registry: `agentcore/knowledge/architecture/chatbot-version.json`
- User command: `version` in Telegram
- After runner knowledge commits, redeploy refreshes the bundled context files on Vercel

## Related Docs

- `agentcore/knowledge/playbooks/telegram-fast-router.md`
- `agentcore/knowledge/playbooks/email-ops.md`
- `agentcore/knowledge/playbooks/communication-intake-contracts.md`
