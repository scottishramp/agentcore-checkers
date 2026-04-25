# AgentCore Blockers

Use this file for major ambiguities, external dependencies, or questions that materially affect a project. Do not use it for small choices where a reasonable default is obvious.

## Open Blockers

### 2026-04-24 | Checkers web game | Durable public hosting

- Status: open
- Blocker: The game is currently local-only after the temporary tunnel was shut down, and the workspace is not a git repo while the GitHub CLI is unauthenticated for durable publishing.
- Why it matters: The game is no longer publicly reachable until a durable host is configured.
- Proposed default: Use GitHub Pages for durable hosting once GitHub authentication is available, unless the user prefers Netlify, Vercel, Cloudflare Pages, or another static host.
- Needed from user: Confirm preferred durable host or provide/login through the selected service when ready.
- Resolution:

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

No resolved blockers yet.
