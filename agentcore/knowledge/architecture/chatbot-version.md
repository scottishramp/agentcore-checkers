# AgentCore Chatbot Version Registry

Canonical version record for the fast Telegram router.

## Current Version

| Field | Value |
| --- | --- |
| Name | AgentCore Fast Router |
| Router version | **2.4.0** |
| Context bundle version | **2.3.0** |
| Released | 2026-06-29 |
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
