# AgentCore Blockers

Use this file for major ambiguities, external dependencies, or questions that materially affect a project. Do not use it for small choices where a reasonable default is obvious.

## Open Blockers

- None currently.

## Blocker Template

```markdown
### YYYY-MM-DD | Project or area | Short blocker title

- Status: open
- Blocker:
- Why it matters:
- Proposed default:
- Needed from user:
- Resolution:
```

## Resolved Blockers

### 2026-05-31 | Async agent runner | Cursor API key needed for cloud replies

- Status: resolved
- Blocker: The GitHub Actions runner could install Cursor Agent and had a default task command, but needed `CURSOR_API_KEY` as a repository secret.
- Resolution: Stored `CURSOR_API_KEY` as a GitHub Actions repository secret and verified it appears in `gh secret list`.

### 2026-05-25 | Family admin system | Drive shared-with-me ingestion

- Status: resolved
- Blocker: Drive/photo ingestion scripts originally needed explicit folder ids before live ingestion could run.
- Resolution: Shifted default model to `sharedWithMe` ingestion, set `AGENTCORE_DRIVE_INCLUDE_SHARED_WITH_ME=true`, and verified Drive API ingestion with the shared `Life 2026` document.

### 2026-05-25 | Email operations | OAuth app still in testing mode

- Status: resolved
- Blocker: The Gmail OAuth client was initially in testing mode, which risked periodic refresh token expiry for unattended runs.
- Resolution: Switched app audience/publishing to production, reran `npm run email:oauth`, rotated the authorized-user credentials, and re-verified live Gmail API send.

### 2026-05-25 | Email operations | Gmail API OAuth credentials needed

- Status: resolved
- Blocker: AgentCore now supports Gmail API OAuth for send/fetch in local Cursor CLI and GitHub Actions, but still needed OAuth client credentials and a refresh token for `scottishramp@gmail.com`.
- Resolution: Added OAuth client credentials securely under `.secrets/`, completed OAuth consent flow, stored authorized-user JSON under `.secrets/gmail-authorized-user.json`, configured `.env` for `gmail-api` transport, and verified live send via Gmail API.

### 2026-04-25 | Async comms | Outbound email send from agent

- Status: resolved
- Blocker: Automated email send attempts failed (`Mail` Apple Events authorization denied; Gmail SMTP rejected credentials).
- Resolution: Switched to Gmail app-password auth and implemented SMTP/IMAP automation scripts (`scripts/email/`) with local + scheduled GitHub Actions inbox sync.

### 2026-04-24 | Checkers web game | Durable public hosting

- Status: resolved
- Blocker: Workspace was not a git repo and GitHub CLI was unauthenticated.
- Resolution: Authenticated `gh` as `scottishramp`, created public repo `agentcore-checkers`, enabled GitHub Pages. Live at https://scottishramp.github.io/agentcore-checkers/
