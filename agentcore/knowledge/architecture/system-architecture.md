# AgentCore System Architecture

Last updated: 2026-06-29

## Purpose

AgentCore is Brian Herbert's private administrative assistant. This repository is the durable control plane and memory: code, workflows, rules, metadata, ledgers, and synthesized knowledge live here. Source documents, scans, photos, and organized files should live in AgentCore-owned Google Drive when possible.

Operational goal:

- This repository is the canonical personal context store for Brian.
- New context can enter through trusted chat/email messages and shared Google docs.
- Fast Telegram chat should answer from the latest repo knowledge when possible.
- The async Cursor agent is the authoritative worker that ingests new info, decides what is durable knowledge vs coding/action task, updates repo knowledge, and refreshes fast-layer deployment.

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
4. Gemini replies using repo context bundle + Upstash conversation history (20 messages, persistent). For text questions the fast layer answers only when context has the fact; otherwise it returns `*DEFER* The slower, smarter agent might be able to help with this`. Photos receive a unique label (`{username}_{YYYYMMDDHHmmss}`), a detailed fast-agent vision description in the reply, and are queued with label + description metadata.
5. Every allowed message is appended to the Upstash inbox queue (`agentcore:telegram:inbox`) with route metadata and optional `media` — **no Cursor dispatch and no durable classification from Vercel**.

#### Async agent (scheduled)

1. Write-capable workflows (`agent-runner.yml` and `knowledge-content-ingest.yml`) pull pending messages from Upstash. `email-sync.yml` must not drain Telegram because it has read-only repo permissions.
2. `scripts/telegram/triage_messages.py` writes inbox records under `agentcore/inbox/telegram/`, appends the durable transcript at `agentcore/knowledge/communications/telegram-transcript.md`, and queues every allowed message as an async Cursor review item so Cursor can decide whether it is durable knowledge, actionable work, or no-op.
3. `scripts/telegram/materialize_media.py` downloads Telegram photos, uploads to Drive, writes `agentcore/inbox/photos/`, and updates `agentcore/knowledge/communications/telegram-photo-registry.json` (label → Drive URL + description).
4. Cursor photo tasks file knowledge from the fast-agent description and reply on Telegram with `Photo label:` and `Drive:` lines.
5. `agent-runner.yml` commits Telegram triage artifacts before claiming tasks, claims review tasks, sends **“Working on: …”** via Telegram, runs Cursor, commits knowledge, notifies completion via Telegram unless Cursor outputs `NO_TELEGRAM_REPLY`, and redeploys Vercel when `VERCEL_TOKEN` is set.
6. Food check-ins and morning prompts go to Telegram via `scripts/telegram/send_scheduled_messages.py`.

Playbook: `agentcore/knowledge/playbooks/telegram-fast-router.md`

### Email

1. Gmail API fetches trusted-client email.
2. Normalized records under `agentcore/inbox/email/`.
3. Triage creates tasks under `agentcore/inbox/tasks/`.
4. Cursor runner replies into the original Gmail thread.
5. `email-thread-ledger.json` tracks idempotency.

## Workflows

- `.github/workflows/email-sync.yml`: email inbox fetch/triage, Drive metadata ingest, runner dispatch (every 30 min). It intentionally does **not** consume Telegram.
- `.github/workflows/agent-runner.yml`: Telegram fetch/triage/transcript commit, task execution, Telegram notifications, Vercel redeploy (hourly and after email-sync completes).
- `.github/workflows/knowledge-content-ingest.yml`: **knowledge content ingest** — Gmail bodies, Telegram inbox records, and allowlisted shared Drive doc exports; activates deferred content tasks; commits exported text; dispatches runner when content tasks or Telegram review tasks activate; attempts fast-router redeploy when `VERCEL_TOKEN` is present (every 4 hours).

**Removed:** Google Chat polling, Google Chat HTTP app (`/api/agentcore-chat`), and `router-task.yml` live `repository_dispatch`.

## Knowledge Content Ingest

Separate from fast email/Telegram triage (which creates tasks) and Drive metadata ingest (which records file metadata only). Runs on a slower cadence because full document bodies and cross-channel fact extraction are heavier and change less often.

### Sources

1. **Gmail** — fetch + triage trusted-client and share-notification email; normalized records under `agentcore/inbox/email/`.
2. **Telegram** — fetch Upstash inbox queue + triage; normalized records under `agentcore/inbox/telegram/` (includes `knowledge_update` and `task` routes).
3. **Shared Drive docs** — metadata via `ingest_drive_updates.py`; **full body export** for allowlisted docs via `export_flagged_docs.py` into `.agentcore/state/drive-content/{file_id}.txt`.

Allowlist: `agentcore/knowledge/documents/content-ingest-allowlist.json`

### Pipeline

1. `scripts/ingest/knowledge_content_ingest.py` orchestrates fetch/triage/export/activate.
2. `scripts/ingest/export_flagged_docs.py` exports Google Docs/Sheets/Slides via Drive API.
3. `scripts/ingest/activate_content_tasks.py` flips `deferred` content-ingest tasks to `queued` when exported text is present.
4. Workflow commits exported text + inbox updates; dispatches async runner when tasks activate.
5. Cursor tasks (e.g. Life 2026 birthdates) extract durable facts into `agentcore/knowledge/` pages.

Playbook: `agentcore/knowledge/playbooks/knowledge-content-ingest.md`

## Data Stores

- `agentcore/inbox/telegram/`: normalized Telegram messages from async triage.
- `agentcore/knowledge/communications/telegram-transcript.md`: durable append-only Telegram transcript for Cursor review context.
- `agentcore/inbox/photos/`: Telegram photo metadata after Drive materialization.
- `agentcore/knowledge/communications/telegram-photo-registry.json`: label → Drive URL, description, filing status.
- `agentcore/knowledge/communications/telegram-thread-ledger.json`: Telegram triage idempotency.
- Upstash Redis: conversation history + inbound inbox queue.
- Standard repo stores: `hot-cache.md`, `index.md`, `blockers.md`, `log.md`, `inbox/tasks/`, etc.
- `.agentcore/state/drive-content/`: exported text bodies for allowlisted shared Drive docs (committed by knowledge-content-ingest workflow).
- `agentcore/knowledge/documents/content-ingest-allowlist.json`: Drive file ids for full-body export.

## Secrets

- **Vercel:** `TELEGRAM_BOT_TOKEN`, `AGENTCORE_TELEGRAM_ALLOWED_USER_IDS`, Gemini key, `KV_REST_API_*`.
- **GitHub Actions:** Gmail OAuth, `CURSOR_API_KEY`, `TELEGRAM_BOT_TOKEN`, `KV_REST_API_*`, optional `VERCEL_TOKEN` for bot context redeploy.

## Vercel Deployment Modes

Production fast-router deploys currently happen through **local Vercel CLI session auth**, not GitHub Actions:

1. Local command: `npx vercel deploy --prod --yes`
2. This works because the local machine is logged into Vercel CLI and the repo is linked via `.vercel/project.json`.
3. Current linked project metadata: project `agentcore-fast-router`, org/team id `team_in3HNh0USnTggSAU4DyssUKT`.

This is separate from headless CI redeploy:

- GitHub Actions requires repository secret `VERCEL_TOKEN` to run `scripts/deploy/redeploy_fast_router.sh`.
- If `VERCEL_TOKEN` is unset, workflow commits update GitHub but do not refresh Vercel production.

## Fast Context Freshness

The Telegram health endpoint (`GET /api/agentcore-telegram`) exposes deployment freshness fields:

- `router_version`
- `context_bundle_version`
- `context_hash`
- `context_length`
- `context_files`
- `has_nathan_birthdate`

Knowledge propagation is not complete until Vercel production reports a current router version and a context hash/sentinel matching the repo snapshot. `has_nathan_birthdate` is a current canary for whether the Life 2026 family facts reached Gemini's bundled context.

## Chatbot Versioning

- Registry: `agentcore/knowledge/architecture/chatbot-version.json`
- User command: `version` in Telegram
- After runner knowledge commits, redeploy refreshes the bundled context files on Vercel

## Related Docs

- `agentcore/knowledge/playbooks/telegram-fast-router.md`
- `agentcore/knowledge/playbooks/email-ops.md`
- `agentcore/knowledge/playbooks/communication-intake-contracts.md`
