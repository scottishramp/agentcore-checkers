# AgentCore Hot Cache

Compact current-state memory for future sessions. Keep this page short and update it after meaningful project changes.

## Identity

- AgentCore is a consultancy and thinktank operating in Cursor.
- The user assigns projects and expects high-autonomy execution.
- Durable memory lives in this repository under `agentcore/`.

## Current State

- Initial knowledge-base structure created on 2026-04-24.
- Active project: `agentcore/knowledge/projects/checkers-web-game.md`.
- Checkers game is built as a dependency-free static app at repo root.
- Prototype/review phase completed; tunnel was intentionally shut down.
- Open blocker: durable hosting needs a git repo plus authenticated static hosting path.
- QA update: desktop/mobile visual pass completed; interaction feedback polish added to `styles.css`.
- Latest fix pass resolved board row squish and improved legal-move guidance messaging/highlighting.
- User-test suite now exists with automated Playwright scenarios; latest run: `7 passed`.

## Operating Preferences

- Use local Markdown files as the source of truth.
- Preserve raw sources separately from synthesized knowledge.
- Ask for 2FA or login help only when actually blocked.
- Do not persist plaintext secrets in the repo.
- On new projects: ask kickoff questions, prototype first, test local first, self-review, then ask the user to review.
- Define prototype test scenarios up front and validate against them before user review.
- Shut down temporary tunnels after review unless explicitly asked to keep them up.

## Recently Changed

- `AGENTS.md`
- `README.md`
- `index.html`
- `styles.css`
- `game.js`
- `agentcore/README.md`
- `agentcore/index.md`
- `agentcore/log.md`
- `agentcore/blockers.md`
- `agentcore/hot-cache.md`
- `agentcore/knowledge/projects/checkers-web-game.md`
- `agentcore/knowledge/decisions/2026-04-24-static-first-web-apps.md`
- `agentcore/knowledge/playbooks/public-static-web-app.md`
