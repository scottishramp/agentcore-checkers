# AgentCore Chatbot Version Registry

Canonical version record for the fast Telegram router.

## Current Version

| Field | Value |
| --- | --- |
| Name | AgentCore Fast Router |
| Router version | **2.5.6** |
| Context bundle version | **2.5.3** |
| Released | 2026-08-29 |
| Primary channel | Telegram `@AgentCoreFam_bot` |
| Endpoint | `https://agentcore-fast-router.vercel.app/api/agentcore-telegram` |

Machine-readable source: `chatbot-version.json`

## User Command

Send **`version`** (or `/version`) in Telegram to get the live deployed version.

## Versioning Rules

Bump **`router_version`** when changing:

- Deterministic commands (`version`, food-log lookup, etc.)
- Gemini system prompt / routing behavior
- Webhook handlers or async handoff logic
- Channel adapters (Telegram)

Bump **`context_bundle_version`** when changing:

- Files in the fast-router context bundle (`api/_agentcore/context.js` `DEFAULT_CONTEXT_FILES`)
- Material changes to what repo knowledge shallow chat can see

Semver:

- **PATCH** — fixes, copy tweaks, logging
- **MINOR** — new deterministic commands, new context files, new channel behavior
- **MAJOR** — breaking routing contract or channel swap

## Update Checklist

1. Edit `chatbot-version.json` (version fields + changelog entry).
2. Mirror the current version table in this file.
3. Deploy Vercel production (`npx vercel deploy --prod`).
4. Append `agentcore/log.md` and trim `agentcore/hot-cache.md` recently changed.
5. Verify in Telegram: send `version`.

## Changelog

### 2.5.6 — 2026-08-29

- Photo webhooks return 200 immediately, then Gemini describe continues in the background for up to 300s. Telegram no longer waits on vision, so a long look cannot 504 or abort at 35s.

### 2.5.5 — 2026-08-29

- Photo describe was aborting at 12s. Production logs show a successful photo webhook that finished in 13s with "vision description failed". Vision timeout is now 35s; photo/webhook budgets raised to match the 60s function limit.

### 2.5.4 — 2026-08-29

- Photo webhooks no longer 504. Telegram download and Gemini vision are time-boxed; if they run long the bot still replies and queues the file id instead of leaving Telegram waiting past Vercel's limit.

### 2.5.3 — 2026-08-23

- Fast context includes family medical providers, Aetna insurance, amoxicillin allergies, and compact history. Portal passwords are not in the snapshot.

### 2.5.2 — 2026-08-22

- Home address and important family contacts (Daniel, Nathan, Ezra, Kristin, Mom) in the fast context snapshot.

### 2.5.1 — 2026-08-22

- Fast context includes Life 2025 date index and household inventory from the newly shared Drive docs.

### 2.5.0 — 2026-08-22

- Fast context now includes the full Brian/family knowledge pack: people pages, family-facts, food log, Life 2026, personal OS, and the 2026-27 roster. Limit raised to 100k chars so it is not trimmed.
- Nightly runner publishes that snapshot to Redis (`agentcore:fast-context`). Live replies prefer the Redis snapshot so knowledge updates reach the bot without a Vercel redeploy.

### 2.4.2 — 2026-08-22

- Fast Telegram replies (and photo labeling) default to Gemini 3.7 Flash (`gemini-3.7-flash`). Override remains `AGENTCORE_FAST_MODEL`.

### 2.4.1 — 2026-08-18

- `knowledge_update` acknowledgments must say the fact is queued for the scheduled async/nightly agent.
- Never claim realtime durable knowledge writes (Brian clarification via Telegram).

### 2.4.0 context — 2026-08-16

- Fast-chat context includes 2026-27 schools and teacher roster facts from `herbert-children.md`.

### 2.4.0 — 2026-06-29

- Fast Telegram stays queue-only for async work; Cursor owns durable Telegram review from committed inbox records, `telegram-transcript.md`, and per-message review tasks.

### 2.3.1 — 2026-06-29

- Health endpoint exposes fast-context hash, files, length, and Nathan birthdate sentinel for deployment freshness checks.

### 2.3.0 — 2026-06-29

- Unanswered text questions now return exactly: `*DEFER* The slower, smarter agent might be able to help with this`.
- Removed the extra `Fast model routing fell back locally.` chat suffix to keep defer replies stable.

### 1.2.0 — 2026-06-27

- Runtime clock injected into Gemini prompts (`America/Chicago`).
- Deterministic food-log answers for today/yesterday.
- `version` command returns registry metadata.

### 1.1.0 — 2026-06-27

- Telegram bot `@AgentCoreFam_bot` live with Vercel webhook.

### 1.0.0 — 2026-06-27

- Initial Vercel fast router with Gemini + GitHub dispatch handoff.
