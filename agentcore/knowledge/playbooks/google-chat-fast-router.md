# Google Chat Fast Router

## Purpose

Give AgentCore a synchronous Google Chat app endpoint for fast replies while preserving the repo-backed Cursor agent for durable knowledge updates and deeper tasks.

## Endpoint

- Vercel function: `api/agentcore-chat.js`
- Production URL: `https://agentcore-fast-router.vercel.app/api/agentcore-chat`
- Health check: `GET /api/agentcore-chat`
- Google Chat HTTP endpoint: `POST /api/agentcore-chat`

## Current Deployment

- Vercel project: `agentcore/agentcore-fast-router`
- Production alias: `https://agentcore-fast-router.vercel.app`
- Configured model: `gemini-2.5-flash`
- Google Chat API configuration: saved in Cloud Console for project `agentcore-495202` with connection setting `HTTP endpoint URL` and common trigger URL `https://agentcore-fast-router.vercel.app/api/agentcore-chat`.
- Health verification: `GET /api/agentcore-chat` returns `200`; unauthenticated `POST` returns `401`.
- Live Chat verification: not yet complete for Brian. `scottishramp`-owned Chat app configs strip `briandherbert@gmail.com` from tester visibility. A Brian-owned project `agentcore-chat-brian` exists with Chat API enabled, but Cloud Console configuration is blocked on Brian browser passkey sign-in.
- Fast context now includes compact recent Brian DM messages and scheduled-message state from the repo so shallow replies understand recent automation prompts.

## Runtime Model

1. Google Chat sends a `MESSAGE` event to the HTTP endpoint.
2. The endpoint verifies Google Chat's OIDC bearer token unless `AGENTCORE_CHAT_VERIFY_AUTH=false`.
3. The endpoint builds compact context from key repo files.
4. Gemini classifies the message as:
   - `lightweight_answer`
   - `knowledge_update`
   - `task`
   - `needs_clarification`
   - `ignore`
5. Lightweight messages get a synchronous reply.
6. Updates and tasks get a synchronous acknowledgement plus a GitHub `repository_dispatch` to run Cursor asynchronously.

## Environment Variables

### Required For Live Fast Replies

- `GOOGLE_AI_STUDIO_API_KEY` or `GEMINI_API_KEY`: Google AI Studio API key.
- `AGENTCORE_FAST_MODEL`: Gemini model id. Default: `gemini-2.5-flash`.
- `AGENTCORE_CHAT_AUDIENCE`: exact deployed endpoint URL, for example `https://example.vercel.app/api/agentcore-chat`.

### Required For Async Cursor Handoff

- `GITHUB_DISPATCH_TOKEN`: GitHub token with permission to call `repository_dispatch`.
- `GITHUB_REPOSITORY`: repository slug, for example `scottishramp/agentcore-checkers`.
- `AGENTCORE_ROUTER_EVENT_TYPE`: default `agentcore-router-task`.

### Optional Conversation Memory

- `UPSTASH_REDIS_REST_URL`
- `UPSTASH_REDIS_REST_TOKEN`
- `AGENTCORE_FAST_HISTORY_TURNS`: default `6`.
- `AGENTCORE_FAST_HISTORY_TTL_SECONDS`: default `21600`.

## Rollout

1. Deploy the repo to Vercel.
2. Set the required Vercel environment variables.
3. Configure the Google Chat app connection setting to HTTP endpoint URL.
4. Use the deployed `/api/agentcore-chat` URL as both the Chat endpoint and `AGENTCORE_CHAT_AUDIENCE`.
5. Send a direct test message to the Chat app.
6. After synchronous replies are verified, decide whether to disable the old Chat polling path to avoid duplicate handling.

## Notes

- Existing human-account Chat polling uses `spaces/6RZ69yAAAAE`; a Google Chat app HTTP endpoint can create a different interaction surface.
- Do not disable the existing polling workflow until the HTTP app is verified live for Brian.
- The fast router must not write durable knowledge directly. It should acknowledge updates and dispatch the Cursor agent for repo writes.
- If Brian cannot see or add the `AgentCore` Chat app, finish configuring the Brian-owned project `agentcore-chat-brian` after Brian signs into Cloud Console in the browser. Use the same Vercel endpoint and HTTP endpoint audience.
