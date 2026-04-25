---
title: Public static web app playbook
type: playbook
status: active
created: 2026-04-24
updated: 2026-04-24
confidence: high
related:
  - ../projects/checkers-web-game.md
  - ../decisions/2026-04-24-static-first-web-apps.md
---

# Playbook: Public Static Web App

Use this for small public web deliverables that do not need accounts, persistence, or a backend.

## Fast Path

1. Start with kickoff questions: acceptance criteria, design preferences, and deployment expectation (temporary preview vs durable hosting).
2. Build a prototype first with `index.html`, `styles.css`, and focused JavaScript.
3. Write a prototype test-scenarios list (happy path, edge cases, and obvious UX failure modes).
4. Verify syntax with `node --check` when JavaScript is present.
5. Serve locally with `python3 -m http.server PORT`.
6. Verify local response with `curl -I http://localhost:PORT/index.html`.
7. Perform a self-review pass (visual and interaction checks) against the scenarios before sharing.
8. Build an executable user-test suite when feasible (for example Playwright scenarios) and run it.
9. Ask the user to review local/prototype quality.
10. Expose temporarily with `lt --port PORT` only when external access is needed.
11. Verify the public URL with `curl -I`.
12. Kill the tunnel after review unless the user explicitly wants it left on.

## Durable Publishing

Use one of these when authentication is available:

- GitHub Pages for repo-backed static sites.
- Netlify, Vercel, or Cloudflare Pages for quick static deployments.
- Object storage with website hosting for simple permanent URLs.

## AgentCore Improvement

At the start of public web projects, check whether:

- The workspace is a git repo.
- `gh` is authenticated if GitHub Pages is the likely target.
- A preferred static host exists.
- The user expects a durable URL or a temporary live preview is acceptable.
- The prototype can be fully tested locally before any public exposure.

During UX feedback passes:

- Treat status messages as testable behavior, not cosmetic text.
- Prefer precise guidance that explains *why* an action is rejected (for example, blocked path vs mandatory capture rule).
- Add or update automated assertions when message logic changes.
