# AgentCore System Architecture

Last updated: 2026-08-29

## Purpose

AgentCore is Brian Herbert's private administrative assistant. This repository is the durable control plane and memory: code, workflows, rules, metadata, ledgers, and synthesized knowledge live here. Source documents, scans, photos, and organized files should live in AgentCore-owned Google Drive when possible.

Operational goal:

- This repository is the canonical personal context store for Brian.
- New context can enter through trusted chat/email messages and shared Google docs.
- Fast Telegram chat should answer from the latest repo knowledge when possible.
- Fast Telegram has **no realtime write capability**; it may only queue messages. Brian (2026-08-18): the scheduled/nightly async job adds durable knowledge and refreshes awareness.
- The async Cursor agent is the authoritative worker that ingests new info, decides what is durable knowledge vs coding/action task, updates repo knowledge, and refreshes fast-layer deployment.

## Identities

- AgentCore Google identity: `scottishramp@gmail.com`.
- Brian trusted client identity: `briandherbert@gmail.com`.
- Brian personal Gmail access: separate `gmail.modify` OAuth token for `briandherbert@gmail.com` (read, label, archive, trash; no send).
- GitHub account/repo: `scottishramp/agentcore-checkers`.
- Public blog: `scottishramp/burningaltar` at https://burningaltar.com/ (Hugo + GitHub Pages; custom domain on GoDaddy DNS).
- Primary chat: **Telegram** `@AgentCoreFam_bot` at `https://agentcore-fast-router.vercel.app/api/agentcore-telegram`.

## Communication Surfaces

### Telegram (Primary)

Two layers: **fast chat** (Vercel + Gemini) and **async agent** (GitHub Actions + Cursor).

#### Fast chat (synchronous)

1. User DMs `@AgentCoreFam_bot`.
2. Telegram POSTs to the Vercel webhook.
3. Allowlist check (fail closed); unknown users dropped silently.
4. Gemini 3.7 Flash replies using a Brian/family knowledge snapshot (people pages, family-facts, food log, Life 2026, personal OS, 2026-27 roster) plus Upstash conversation history (20 messages, persistent). The snapshot is published to Redis (`agentcore:fast-context`) on every async runner cycle so new facts reach the bot without a Vercel redeploy; the deploy bundle is fallback only. For text questions the fast layer answers only when context has the fact; otherwise it returns `*DEFER* The slower, smarter agent might be able to help with this`. Photos receive a unique label (`{username}_{YYYYMMDDHHmmss}`), a detailed fast-agent vision description in the reply, and are queued with label + description metadata.
5. Every allowed message is appended to the Upstash inbox queue (`agentcore:telegram:inbox`) with route metadata and optional `media` — **no Cursor dispatch and no durable classification from Vercel**.

#### Async agent (scheduled)

1. Write-capable workflows (`agent-runner.yml` and `knowledge-content-ingest.yml`) pull pending messages from Upstash. `email-sync.yml` must not drain Telegram because it has read-only repo permissions.
2. `scripts/telegram/triage_messages.py` writes inbox records under `agentcore/inbox/telegram/`, appends the durable transcript at `agentcore/knowledge/communications/telegram-transcript.md`, and queues every allowed message as an async Cursor review item so Cursor can decide whether it is durable knowledge, actionable work, or no-op.
3. `scripts/telegram/materialize_media.py` downloads Telegram photos, uploads to Drive, writes `agentcore/inbox/photos/`, and updates `agentcore/knowledge/communications/telegram-photo-registry.json` (label → Drive URL + description).
4. Cursor photo tasks file knowledge from the fast-agent description and reply on Telegram with `Photo label:` and `Drive:` lines.
5. `agent-runner.yml` commits Telegram triage artifacts before claiming tasks, claims review tasks, sends **“Working on: …”** via Telegram, runs Cursor, commits knowledge, notifies completion via Telegram unless Cursor outputs `NO_TELEGRAM_REPLY`, and redeploys Vercel when `VERCEL_TOKEN` is set.
6. Morning prompts go to Telegram via `scripts/telegram/send_scheduled_messages.py` (food check-ins disabled 2026-07-05).

Playbook: `agentcore/knowledge/playbooks/telegram-fast-router.md`

### Email

1. Gmail API fetches trusted-client email.
2. Normalized records under `agentcore/inbox/email/`.
3. Triage creates tasks under `agentcore/inbox/tasks/`.
4. Cursor runner replies into the original Gmail thread.
5. `email-thread-ledger.json` tracks idempotency.

Brian's personal mailbox (`briandherbert@gmail.com`) is a separate Gmail API surface. AgentCore can read all mail there, create/apply labels, archive, and trash using `gmail.modify`. This is on-demand admin access, not an intake queue: do not copy Brian's mailbox into `agentcore/inbox/email/`. Playbook: `agentcore/knowledge/playbooks/brian-gmail-mailbox.md`.

Two scheduled jobs read that mailbox: the **school communications digest** (narrow query, school senders) and the nightly **mailbox learning loop** (whole mailbox, sender-level policy). The learning loop is read-only — it never labels, archives, or trashes.

### Google Calendar

Brian shared `briandherbert@googlemail.com` with `scottishramp@gmail.com` as `reader`, and AgentCore's OAuth token carries `calendar.readonly`. The nightly `ingest_calendar.py` step reads it and regenerates `agentcore/knowledge/calendar/upcoming.md` (7 days back through 60 days ahead) plus recurring-commitment facts. Read-only; nothing is written back to Google Calendar.

A daily **school communications digest** reads that mailbox, applies the `26-27 School` label and archives matching mail out of Inbox (Gmail drag-to-label behavior), rebuilds a shared Google Doc (Important / per kid / General / Suggestions, with this-week items bold and a hyperlinked Link on each bullet), and pings Telegram with the Important section plus the Doc link. Classification is **LLM-first**: `scripts/email/email_evaluator.py` evaluates each email once (prefilter for junk senders, batches of 12 with roster context) via Gemini REST (`GEMINI_API_KEY`, optional) or Cursor Agent CLI (`CURSOR_API_KEY` in CI), records the verdict in the committed ledger `agentcore/knowledge/email/eval-ledger.json` (60-day retention, metadata only), and falls back to the keyword classifier when no backend is available. LLM `learn` entries update the 2026-27 roster (teachers/sports/activities) and `agentcore/knowledge/people/family-facts.md` (general household facts). Playbooks: `agentcore/knowledge/playbooks/school-comms-digest.md`, `agentcore/knowledge/playbooks/agentic-jobs-cursor-cli.md`.

## Workflows

- `.github/workflows/email-sync.yml`: email inbox fetch/triage, Drive metadata ingest, runner dispatch (daily 6:00 AM America/Chicago). It intentionally does **not** consume Telegram.
- `.github/workflows/agent-runner.yml`: Telegram fetch/triage/transcript commit, school digest with LLM email evaluation (Cursor CLI installed before the digest step; `CURSOR_API_KEY` + optional `GEMINI_API_KEY`), task execution via Cursor CLI model `grok-4.6` (override with secret `AGENTCORE_CURSOR_MODEL`), Telegram notifications, Vercel redeploy (daily 8:30 AM America/Chicago, and after email-sync completes).
- `.github/workflows/knowledge-content-ingest.yml`: **knowledge content ingest** — Gmail bodies, Telegram inbox records, and allowlisted shared Drive doc exports; activates deferred content tasks; then runs the **mailbox and calendar learning loop** (answer resolution, calendar ingest, whole-mailbox sweep, question batch); commits exported text and ledgers; dispatches runner when content tasks or Telegram review tasks activate; attempts fast-router redeploy when `VERCEL_TOKEN` is present (daily 11:00 AM America/Chicago).

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

## Mailbox and Calendar Learning Loop

Runs at the end of the nightly knowledge-content-ingest workflow. Its job is continuous, unattended learning about Brian, with a human in the loop only where the machine is genuinely unsure.

1. `scripts/learn/resolve_answers.py` — parse Brian's Telegram replies and write them to sender policy.
2. `scripts/ingest/ingest_calendar.py` — rebuild the schedule page and record new recurring commitments.
3. `scripts/learn/mailbox_sweep.py` — sweep new mail, decide unknown senders, extract facts from `learn` senders, enqueue questions for low-confidence senders.
4. `scripts/learn/ask_questions.py` — send up to five questions as one numbered Telegram batch.

Decisions are made per **sender**, not per message, so each sender costs one model call ever and one question at most. Model verdicts at confidence ≥ 0.8 are recorded automatically; below that the sender becomes a question. **Brian's answers outrank model guesses and are never overwritten by a later model verdict.**

Answers arrive through the existing Telegram intake path, so no new inbound surface exists. Replies that the deterministic parser cannot read are left untouched and still reach Cursor as a normal Telegram review task.

Privacy: read-only against Gmail and Calendar; message bodies are read for extraction but never persisted; only distilled facts, senders, and subjects are committed.

Playbook: `agentcore/knowledge/playbooks/mailbox-learning-loop.md`

## Data Stores

- `agentcore/inbox/telegram/`: normalized Telegram messages from async triage.
- `agentcore/knowledge/communications/telegram-transcript.md`: durable append-only Telegram transcript for Cursor review context.
- `agentcore/inbox/photos/`: Telegram photo metadata after Drive materialization.
- `agentcore/knowledge/communications/telegram-photo-registry.json`: label → Drive URL, description, filing status.
- `agentcore/knowledge/communications/telegram-thread-ledger.json`: Telegram triage idempotency.
- `agentcore/knowledge/email/eval-ledger.json`: per-message LLM email verdicts (school digest), 60-day retention, metadata only.
- `agentcore/knowledge/email/sender-policy.json`: durable per-sender handling policy (`learn` / `info` / `ignore`) with source, rationale, and confidence. Brian-sourced entries are authoritative.
- `agentcore/knowledge/email/mailbox-sweep-state.json`: sweep watermark plus recently processed message ids.
- `agentcore/knowledge/communications/pending-questions.json`: questions awaiting Brian's answer, with batch id and number for reply matching.
- `agentcore/knowledge/people/brian-learned-facts.md`: dated facts about Brian learned by the nightly sweep and calendar ingest, filed by category.
- `agentcore/knowledge/calendar/upcoming.md`: regenerated near-term schedule from Brian's shared calendar.
- `agentcore/knowledge/calendar/calendar-state.json`: recurring series already turned into facts.
- `agentcore/knowledge/people/family-facts.md`: general household facts learned by the email evaluator (dated, deduped).
- Upstash Redis: conversation history + inbound inbox queue + `agentcore:fast-context` (Telegram bot knowledge snapshot, published each runner cycle).
- Standard repo stores: `hot-cache.md`, `index.md`, `blockers.md`, `log.md`, `inbox/tasks/`, etc.
- `.agentcore/state/drive-content/`: exported text bodies for allowlisted shared Drive docs (committed by knowledge-content-ingest workflow).
- `agentcore/knowledge/documents/content-ingest-allowlist.json`: Drive file ids for full-body export.

## Secrets

- **Vercel:** `TELEGRAM_BOT_TOKEN`, `AGENTCORE_TELEGRAM_ALLOWED_USER_IDS`, Gemini key, `KV_REST_API_*`.
- **GitHub Actions:** Gmail OAuth, Brian mailbox OAuth (`AGENTCORE_BRIAN_GMAIL_AUTHORIZED_USER_JSON`), `CURSOR_API_KEY`, `TELEGRAM_BOT_TOKEN`, `KV_REST_API_*`, optional `VERCEL_TOKEN` for bot context redeploy.

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

## Hosted Public Sites

- Checkers: https://scottishramp.github.io/agentcore-checkers/ (`scottishramp/agentcore-checkers`).
- Burning Altar blog: https://burningaltar.com/ (`scottishramp/burningaltar`). Apex A records and `www` CNAME on GoDaddy; GitHub Pages HTTPS enforced. Email DNS on the same domain left on GoDaddy `*.secureserver.net`.

## Related Docs

- `agentcore/knowledge/playbooks/telegram-fast-router.md`
- `agentcore/knowledge/playbooks/email-ops.md`
- `agentcore/knowledge/playbooks/brian-gmail-mailbox.md`
- `agentcore/knowledge/playbooks/school-comms-digest.md`
- `agentcore/knowledge/playbooks/mailbox-learning-loop.md`
- `agentcore/knowledge/playbooks/agentic-jobs-cursor-cli.md`
- `agentcore/knowledge/playbooks/communication-intake-contracts.md`
