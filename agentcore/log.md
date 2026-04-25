# AgentCore Log

Append-only chronological record of important AgentCore knowledge-base activity.

## [2026-04-24] setup | Initial AgentCore structure

- Created the initial Markdown knowledge-base structure for AgentCore.
- Established root agent instructions, source/knowledge/output layers, templates, index, log, blockers, and hot cache.

## [2026-04-24] project | Checkers web game

- Built a dependency-free two-player checkers game at the repository root.
- Verified JavaScript syntax, local static serving, public tunnel serving, and Cursor diagnostics.
- Published a temporary public URL: https://tiny-dolls-fly.loca.lt/
- Added project, decision, and playbook pages to capture deployment lessons.
- Recorded durable hosting as an open blocker because the workspace is not a git repo and `gh` is not authenticated.

## [2026-04-24] qa | Checkers look-and-feel pass

- Ran visual QA on desktop and mobile viewports using Playwright screenshots.
- Confirmed typography, spacing, board readability, and control hierarchy were in good shape.
- Added interaction polish in `styles.css` (button press motion, square brightness feedback, and subtle piece hover lift).

## [2026-04-24] process | Prototype-first workflow update

- Incorporated user feedback into AgentCore workflow: ask kickoff questions, run prototype phase first, test local first, self-review, then request user review.
- Updated `AGENTS.md` and `agentcore/knowledge/playbooks/public-static-web-app.md` to codify the workflow.
- Terminated active localtunnel process chain and confirmed tunnel endpoint returned `503 Tunnel Unavailable`.

## [2026-04-24] fix | Checkers board and move guidance

- Fixed board row sizing by setting explicit grid rows to prevent middle-row squish.
- Improved move guidance by highlighting movable pieces when none is selected.
- Updated blocked-piece feedback text to reduce false-error perception.
- Added explicit prototype test scenarios for this project and to the default workflow.

## [2026-04-24] qa | Automated user test suite

- Added executable user-scenario tests in `tests/checkers.user.spec.js`.
- Added manual acceptance checklist in `tests/user-test-suite.md`.
- Set up Playwright test runner (`playwright.config.js`) and npm scripts.
- Ran `npm test` and got `7 passed`.

## [2026-04-24] fix | Message precision for move guidance

- Adjusted interaction guidance to distinguish two cases:
  - blocked piece
  - mandatory capture with another piece
- Updated automated scenario assertion for mandatory-capture guidance.
- Re-ran `npm test` with `7 passed`.
