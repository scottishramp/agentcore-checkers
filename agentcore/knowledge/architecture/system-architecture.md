# AgentCore System Architecture

Last updated: 2026-06-27

## Purpose

AgentCore is Brian Herbert's private administrative assistant. This repository is the durable control plane and memory: code, workflows, rules, metadata, ledgers, and synthesized knowledge live here. Source documents, scans, photos, and organized files should live in AgentCore-owned Google Drive when possible.

## Identities

- AgentCore Google identity: `scottishramp@gmail.com`.
- Brian trusted client identity: `briandherbert@gmail.com`.
- GitHub account/repo: `scottishramp/agentcore-checkers`.
- Primary Chat surface: the **AgentCore Google Chat app** (bot), not the human `scottishramp@gmail.com` DM.

## Communication Surfaces

### Google Chat App (Primary)

This is the intended interface for fast, shallow chat and task handoff.

Flow:

1. User messages the AgentCore Chat app in Google Chat.
2. Google Chat POSTs an HTTP event to `https://agentcore-fast-router.vercel.app/api/agentcore-chat`.
3. The Vercel function verifies Google Chat's OIDC bearer token.
4. Gemini classifies the message and returns a synchronous reply (typically 1–3 seconds).
5. Knowledge updates and deeper tasks also dispatch GitHub `repository_dispatch` to `.github/workflows/router-task.yml` for async Cursor handling.

Deployment:

- Endpoint: `https://agentcore-fast-router.vercel.app/api/agentcore-chat`
- Model: `gemini-2.5-flash`
- Code: `api/agentcore-chat.js`, `api/_agentcore/fast-router.js`, `api/_agentcore/context.js`, `api/_agentcore/store.js`
- Cloud project: `agentcore-495202` (Chat API configured with HTTP endpoint URL)
- Playbook: `agentcore/knowledge/playbooks/google-chat-fast-router.md`

How to use it:

1. Open Google Chat.
2. Search for **AgentCore** and open a DM with the app.
3. Send a message — replies are instant from the fast router.

Do **not** message `scottishramp@gmail.com` directly for chat; that old human-DM path is disabled.

### Legacy Human DM (Disabled)

The previous path polled Brian's human-to-human DM with `scottishramp@gmail.com` every 30–60 minutes via GitHub Actions. That was slow and unreliable for conversation. Inbound DM polling and the pseudo-synchronous runner loop are **removed** from workflows as of 2026-06-27.

Outbound scheduled check-ins (morning, food) still use the Chat API to send proactive messages to a configured space until migrated to the bot DM space.

### Email

Flow:

1. Gmail API fetches trusted-client email.
2. Normalized records live under `agentcore/inbox/email/`.
3. Triage creates tasks under `agentcore/inbox/tasks/`.
4. Cursor runner replies into the original Gmail thread.
5. `email-thread-ledger.json` tracks idempotency and response state.

## Workflows

- `.github/workflows/email-sync.yml`: email + Drive intake only (no Chat polling).
- `.github/workflows/agent-runner.yml`: queued task execution, scheduled Chat sends, queue draining.
- `.github/workflows/router-task.yml`: async task execution from the Chat app fast router.

## Data Stores

- `agentcore/hot-cache.md`: compact current state.
- `agentcore/index.md`: knowledge map.
- `agentcore/blockers.md`: major unresolved blockers.
- `agentcore/log.md`: append-only event log.
- `agentcore/inbox/`: normalized source records and queued tasks.
- `agentcore/knowledge/communications/`: ledgers and communication state.

## Operational Invariants

- Chat inbound = bot webhook only. No DM polling.
- Keep secrets out of git.
- Update this doc when communication channels, workflows, or hosted endpoints change.

## Related Docs

- `agentcore/knowledge/playbooks/google-chat-fast-router.md`
- `agentcore/knowledge/playbooks/email-ops.md`
- `agentcore/knowledge/projects/personal-operating-system.md`
