# Google Chat Fast Router

## Purpose

Give AgentCore instant Google Chat replies via a Chat app (bot). Shallow questions get synchronous Gemini answers; deeper work dispatches to the repo-backed Cursor agent.

## How To Chat

1. Open Google Chat.
2. Search for **AgentCore** and start a DM with the app.
3. Send a message — you get an instant reply.

Do **not** message `scottishramp@gmail.com` directly. That human-DM polling path is disabled.

## Endpoint

- Production URL: `https://agentcore-fast-router.vercel.app/api/agentcore-chat`
- Health check: `GET /api/agentcore-chat`
- Vercel project: `agentcore/agentcore-fast-router`
- Model: `gemini-2.5-flash`
- Cloud project: `agentcore-495202`

## Runtime Model

1. Google Chat sends a `MESSAGE` event to the HTTP endpoint.
2. The endpoint verifies Google Chat's OIDC bearer token.
3. Gemini classifies: `lightweight_answer`, `knowledge_update`, `task`, `needs_clarification`, or `ignore`.
4. Lightweight messages get a synchronous reply.
5. Updates and tasks get an acknowledgement plus GitHub `repository_dispatch` to `.github/workflows/router-task.yml`.

## Environment Variables (Vercel Production)

- `GOOGLE_AI_STUDIO_API_KEY` — Gemini API key
- `AGENTCORE_FAST_MODEL` — default `gemini-2.5-flash`
- `AGENTCORE_CHAT_AUDIENCE` — `https://agentcore-fast-router.vercel.app/api/agentcore-chat`
- `GITHUB_DISPATCH_TOKEN` — GitHub token for `repository_dispatch`
- `GITHUB_REPOSITORY` — `scottishramp/agentcore-checkers`
- `AGENTCORE_ROUTER_EVENT_TYPE` — default `agentcore-router-task`

Optional conversation memory: `UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN`.

## Family Members

Each person searches for **AgentCore** in Google Chat and opens a DM with the app. They may need to approve/install the app the first time.

## Notes

- The fast router does not write durable repo knowledge directly; it acknowledges updates and dispatches Cursor for repo writes.
- Outbound scheduled check-ins (morning, food) still use the Chat API separately until migrated to the bot DM space.
