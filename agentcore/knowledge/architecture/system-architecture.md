# AgentCore System Architecture

Last updated: 2026-06-27

## Purpose

AgentCore is Brian Herbert's private administrative assistant. This repository is the durable control plane and memory: code, workflows, rules, metadata, ledgers, and synthesized knowledge live here. Source documents, scans, photos, and organized files should live in AgentCore-owned Google Drive when possible.

## Identities

- AgentCore Google identity: `scottishramp@gmail.com`.
- Brian trusted client identity: `briandherbert@gmail.com`.
- GitHub account/repo: `scottishramp/agentcore-checkers`.
- Primary fast chat: **Telegram bot** at `https://agentcore-fast-router.vercel.app/api/agentcore-telegram` (instant 1:1 DMs, shared repo knowledge). Setup blocked on BotFather token.
- Legacy Google Chat: human DM polling remains for async tasks; Google Chat app webhook blocked by Gmail visibility limits.

## Communication Surfaces

### Telegram Bot (Primary Fast Chat)

One shared bot; each family member gets their own 1:1 DM with instant replies.

Flow:

1. User sends a Telegram message to the AgentCore bot.
2. Telegram POSTs to `https://agentcore-fast-router.vercel.app/api/agentcore-telegram`.
3. Vercel verifies optional webhook secret, checks allowlist, routes via Gemini + repo context + Redis history.
4. Bot replies synchronously via Telegram `sendMessage`.
5. Knowledge updates/tasks dispatch to `.github/workflows/router-task.yml`; completion replies via `scripts/telegram/send_task_response.py`.

Playbook: `agentcore/knowledge/playbooks/telegram-fast-router.md`

Bot: `@AgentCoreFam_bot`

### Normal Google Chat DM

Brian currently messages the normal Google account `scottishramp@gmail.com`.

Flow:

1. Brian sends a normal Google Chat DM.
2. GitHub Actions polls the Chat API for `spaces/6RZ69yAAAAE`.
3. New Brian-authored messages become Markdown inbox records under `agentcore/inbox/chat/`.
4. Triage creates tasks under `agentcore/inbox/tasks/`.
5. `agent-runner.yml` runs Cursor/agent work, sends replies back to the same Chat DM, records ledgers, commits, and pushes.

Current cadence:

- `email-sync.yml`: scheduled at `0,30 * * * *`, fetches Chat with `bootstrap-window 0`.
- `agent-runner.yml`: scheduled at `5 * * * *`, fetches Chat with `bootstrap-window 30`.
- `email-sync.yml` can dispatch `agent-runner.yml` immediately when it creates tasks.
- After a completed Google Chat task, `agent-runner.yml` can keep a bounded pseudo-synchronous loop open for 15 minutes, polling every 20 seconds, during 09:00-20:00 `America/Chicago`.

Important constraint:

- Normal human-to-human Google Chat DMs do not call a webhook. They can only be seen by polling the Chat API.

### Google Chat Fast Router App

The Vercel fast router is intended for shallow, immediate replies from a Google Chat app/bot surface.

Flow:

1. User messages the Google Chat app.
2. Google Chat sends an HTTP event to `https://agentcore-fast-router.vercel.app/api/agentcore-chat`.
3. The Vercel function verifies the Google Chat OIDC bearer token.
4. The router builds compact context from repo files plus recent tracked Chat automation context.
5. Gemini classifies the message as `lightweight_answer`, `knowledge_update`, `task`, `needs_clarification`, or `ignore`.
6. Lightweight answers return synchronously to Chat.
7. Knowledge updates/tasks also dispatch GitHub `repository_dispatch` for async Cursor handling.

Current deployment:

- Vercel project: `agentcore/agentcore-fast-router`.
- Endpoint: `https://agentcore-fast-router.vercel.app/api/agentcore-chat`.
- Model: `gemini-2.5-flash`.
- Health check: `GET /api/agentcore-chat`.
- Code: `api/agentcore-chat.js`, `api/_agentcore/fast-router.js`, `api/_agentcore/context.js`, `api/_agentcore/store.js`.
- Async handoff workflow: `.github/workflows/router-task.yml`.
- Tests: `npm run router:test`.

Current blocker:

- Brian-facing Chat app verification is not complete. `scottishramp`-owned Chat app configs strip `briandherbert@gmail.com` from tester visibility. A Brian-owned project `agentcore-chat-brian` exists with Chat API enabled, but Cloud Console browser configuration needs Brian passkey sign-in.

Product direction:

- Keep the normal `scottishramp@gmail.com` DM as the family-friendly primary surface unless Brian chooses otherwise.
- Use the Chat app/router as optional instant mode, or continue adapting the normal DM path with faster polling/shallow-first behavior.

### Email

Flow:

1. Gmail API fetches trusted-client email.
2. Normalized records live under `agentcore/inbox/email/`.
3. Triage creates tasks under `agentcore/inbox/tasks/`.
4. Cursor runner replies into the original Gmail thread.
5. `email-thread-ledger.json` tracks idempotency and response state.

Important rule:

- For email chains, process only when Brian is the latest meaningful sender. AgentCore's reply should be the latest thread message until Brian replies again.

## Workflows

- `.github/workflows/email-sync.yml`: scheduled intake, deterministic publishing, and runner dispatch.
- `.github/workflows/agent-runner.yml`: task execution, scheduled Chat messages, pseudo-synchronous Chat loop, queue draining, commits, and notifications.
- `.github/workflows/router-task.yml`: async task creation/execution from the Vercel fast router.

## Data Stores

- `agentcore/hot-cache.md`: compact current state and operating preferences.
- `agentcore/index.md`: knowledge map.
- `agentcore/blockers.md`: major unresolved blockers.
- `agentcore/log.md`: append-only event log.
- `agentcore/inbox/`: normalized source records and queued tasks.
- `agentcore/knowledge/communications/`: ledgers and deterministic communication state.
- `.agentcore/state/`: transient local/runner state; do not rely on it for durable knowledge.
- Google Drive: preferred home for source docs, scans, photos, and organized files.

## Secrets And Auth

- `.env` and `.secrets/` are gitignored and must never be committed.
- GitHub Actions secrets hold Gmail/Chat OAuth material, Cursor API key, and runner configuration.
- Vercel production environment holds Gemini API key and GitHub dispatch token for the fast router.
- AgentCore should use `scottishramp@gmail.com` for external sign-ups unless Brian directs otherwise.

## Operational Invariants

- Keep secrets out of git.
- Commit, push, and activation/deployment are expected after successful changes unless Brian says not to.
- Preserve existing user changes; do not revert unrelated work.
- Update architecture docs when changing channels, workflows, hosted endpoints, OAuth scopes, queue semantics, or durable state locations.
- Update `agentcore/hot-cache.md`, `agentcore/index.md`, and `agentcore/log.md` after significant architecture changes.
- If architecture work is blocked by authority, login, passkey, 2FA, missing API access, or a major ambiguity, record it in `agentcore/blockers.md`.

## Related Docs

- `agentcore/knowledge/playbooks/google-chat-fast-router.md`
- `agentcore/knowledge/playbooks/email-ops.md`
- `agentcore/knowledge/playbooks/communication-intake-contracts.md`
- `agentcore/knowledge/projects/personal-operating-system.md`
