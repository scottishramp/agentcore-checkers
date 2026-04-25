---
title: Checkers Web Game
type: project
status: prototype-reviewed
created: 2026-04-24
updated: 2026-04-25
client: Brian Herbert
owner: AgentCore
confidence: high
related:
  - ../../knowledge/decisions/2026-04-24-static-first-web-apps.md
  - ../../knowledge/playbooks/public-static-web-app.md
---

# Project: Checkers Web Game

## Objective

Create a two-player checkers game that is publicly available on the web.

## Current Status

- Built a dependency-free static web app at the repository root.
- Local server: `python3 -m http.server 4173`
- Public tunnel: stopped per user request after review phase.

Durable hosting is still tracked in `../../blockers.md`.

## Deliverables

- `../../../index.html`: app shell and game controls.
- `../../../styles.css`: responsive visual design.
- `../../../game.js`: checkers game logic.
- `../../../README.md`: local run and deployment notes.

## Rules Implemented

- Red moves first from the bottom of the board.
- Black moves from the top of the board.
- Captures are mandatory.
- Multi-jumps are supported and must continue with the same piece.
- Kings move and capture diagonally in both directions.
- Undo and restart are available.

## Verification

- `node --check game.js` passed.
- `curl -I http://localhost:4173/index.html` returned HTTP 200.
- Tunnel verification before shutdown returned HTTP 200.
- Tunnel verification after shutdown returned `503 Tunnel Unavailable`.
- Cursor diagnostics reported no linter errors for the app files.
- Headless visual QA completed for desktop and mobile viewports using Playwright screenshots.
- Post-QA style polish added subtle hover and press feedback for better interaction feel.
- Board layout bug fixed by forcing `grid-template-rows: repeat(8, 1fr)` in `.board`.
- Move guidance bug improved by highlighting movable origins and replacing misleading blocked-piece text.
- Removed stale phrasing risk by eliminating "has no legal moves" status wording from interaction guidance.
- Added cache-busting query strings on CSS/JS asset links to reduce stale-browser behavior.
- Automated user-scenario test run: `npm test` passed (`7 passed`).
- Refined guidance classification:
  - blocked piece -> "That piece is blocked. Select a highlighted piece."
  - mandatory capture elsewhere -> "A capture is required. Select a highlighted capturing piece."

## Prototype Test Scenarios

- Initial board state and counts are correct.
- Any movable piece can be selected and legal destination markers appear.
- Clicking a blocked piece gives guided feedback to choose a highlighted movable piece.
- Turn changes after a legal move.
- Mandatory capture, multi-jump continuation, kinging, undo, and restart all behave correctly.
- Desktop and mobile layout maintain readable controls and board proportions.

## User Test Suite Artifacts

- Manual suite: `../../../tests/user-test-suite.md`
- Automated suite: `../../../tests/checkers.user.spec.js`
- Test runner setup: `../../../playwright.config.js` and `../../../package.json`

## Hurdles And Inefficiencies

- Durable publishing was slowed by missing repository/auth state: the workspace was not a git repo and `gh` was not authenticated.
- The static-first implementation avoided package setup and made temporary public hosting fast.
- For future web tasks, AgentCore should establish the deployment target at kickoff or maintain a pre-authenticated static hosting path.

## Next Actions

- If durable hosting is required, initialize a repo and publish via GitHub Pages, Netlify, Vercel, or Cloudflare Pages after login/auth is available.
