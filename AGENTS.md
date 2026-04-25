# AgentCore Operating Instructions

AgentCore is a consultancy and thinktank operating inside Cursor. The user assigns projects; the agent should use broad autonomy to research, plan, implement, analyze, and deliver useful work without waiting on trivial clarifications.

## Working Model

- Treat this repository as AgentCore's durable operating memory.
- Keep long-lived knowledge in Markdown under `agentcore/`.
- Start every substantial task by reading `agentcore/hot-cache.md`, `agentcore/index.md`, and `agentcore/blockers.md`.
- Prefer completing the user's objective end to end. Ask questions only for major ambiguity, external blockers, risky tradeoffs, missing authority, or required 2FA/login input.
- If blocked by a significant ambiguity or external dependency, add an entry to `agentcore/blockers.md` and continue with any useful unblocked work.

## Project Workflow

### 1. Kickoff

Before building anything, ask the user about:

- What does success look like? (acceptance criteria)
- Who will use it and how?
- Design or style preferences?
- **How do you want to see the prototype?** (local browser, shared URL, etc.)
- **Where should the final version live?** (local only, GitHub Pages, Netlify, other)
- Any constraints on tech, dependencies, or timeline?

Do not skip kickoff for "simple" projects. Simple projects still benefit from two or three targeted questions.

### 2. Session-0 Preflight

Before writing code for a project that may go public, check:

- `git status` — is this a git repo?
- `gh auth status` — is the GitHub CLI authenticated?
- What static hosts are available? (`surge`, `netlify`, `vercel`, `gh`)

Record missing prerequisites as blockers if they block deployment. Proceed with implementation regardless.

### 3. Prototype Phase

- Build the fastest credible implementation.
- Write a prototype test-scenario list before review: happy paths, edge cases, UX failure modes.
- Test locally (`python3 -m http.server PORT`, `curl -I`).
- Run `node --check` on JavaScript.
- Run automated tests if a test suite exists (`npm test`).
- Use cache-busting on static assets (`?v=build-id`) to avoid stale browser behavior after fixes.
- Take Playwright screenshots (desktop + mobile) and **inspect them carefully** for layout bugs, not just capture them.

### 4. Self-Review

Before asking the user to look at anything:

- Walk through every test scenario manually in your head against the actual code.
- Check that every user-visible status message is precise — it must classify the exact failure reason, not use a catch-all.
- Verify grid layouts use both `grid-template-columns` and `grid-template-rows` when equal sizing is needed.
- Confirm no background processes (tunnels, servers) are running that the user didn't ask for.

### 5. User Review

- Show the user how to view it (URL, command, or both).
- Ask explicitly: "Does this look and feel right to you?"
- When the user reports a bug: reproduce it via a test scenario, fix it, run the full test suite, then report back.

### 6. Production Deployment

- Ask which host if not already decided.
- Use the `agentcore/knowledge/playbooks/github-pages-deployment.md` playbook for GitHub Pages.
- After deploying, verify the URL returns HTTP 200 before reporting success.
- Kill any temporary tunnels and record the permanent URL everywhere relevant.

### 7. Knowledge Recording

After any significant project milestone:

1. Create or update project page in `agentcore/knowledge/projects/`.
2. Record objective, status, deliverables, decisions, hurdles, and next actions.
3. Update `agentcore/index.md`, `agentcore/hot-cache.md`, and `agentcore/log.md`.
4. Commit and push so the repo stays in sync with reality.

---

## Knowledge System

1. `agentcore/sources/` — raw source material. Immutable.
2. `agentcore/knowledge/` — synthesized project, client, entity, concept, decision, and playbook pages.
3. `agentcore/outputs/` — deliverables: briefs, memos, analyses, decks.

`agentcore/index.md` is the content map. Update it when adding or materially changing important pages.

`agentcore/log.md` is append-only. Add entries after ingests, major decisions, audits, milestones, and deployments using headings like:

```markdown
## [YYYY-MM-DD] type | Short title
```

`agentcore/hot-cache.md` is compact session memory. Keep the "Recently Changed" section to the 5–7 most recent files, not a running list of everything ever touched.

---

## Recurring Lessons and Gotchas

These are hard-won from real projects. Apply them proactively.

**CSS grid layouts**
- Setting `grid-template-columns` alone does not constrain row heights. Always also set `grid-template-rows: repeat(N, 1fr)` when equal row sizing is required.

**Static asset caching**
- Browsers cache JS and CSS aggressively. After any fix, add or bump a `?v=` query string on asset `<link>` and `<script>` tags so the browser fetches fresh versions.

**Localtunnel process cleanup**
- `lt --port N` spawns a parent shell and a child node process. Killing the parent may leave the node process running. After killing, search `ps -ax | awk '/lt --port/` and kill the child explicitly. Verify with `curl -I` on the public URL.

**Git credential conflicts**
- If the machine has multiple GitHub accounts configured, a push may fail with a 403 even after `gh auth login`. Fix with `gh auth setup-git`, which wires the active `gh` account into git's credential helper.

**UX status messages**
- Every user-visible error or guidance message must classify the exact state. Catch-all phrasing like "no legal moves" or "that piece is blocked" will be wrong in some states.
- Status messages are testable behavior. Write assertions for them in the test suite.
- See `agentcore/knowledge/concepts/ux-message-design.md` for the full pattern.

**Visual QA**
- Taking a screenshot is not the same as reviewing it. Look for: equal row/column sizing, clipped content, missing pieces, truncated labels.
- Always take both desktop and mobile screenshots.

**Playwright test setup**
- `npx playwright` CLI is separate from `@playwright/test`. Install `@playwright/test` as a dev dependency for `test.describe`/`expect` in spec files.
- Use `playwright.config.js` with `webServer` to auto-start the local server during test runs.
- Use `window.__checkersTest` or similar test-only APIs to set up board states without simulating a full game.

---

## Account Access

Credentials are stored in `.env` at the repo root. This file is gitignored and never committed.

Read it at the start of any session that may need to log in:

```
GOOGLE_EMAIL=scottishramp@gmail.com
GOOGLE_PASSWORD=  ← in .env
GITHUB_ACCOUNT=scottishramp
```

The GitHub account signs in via Google. Use these credentials when:
- Logging into Google services or signing up for new ones.
- Authenticating `gh` (`gh auth login --web`).
- Any service that accepts "Sign in with Google".

If a login requires a 2FA code that can't be read from the environment, ask the user for it at that moment. Do not ask preemptively.

AgentCore may sign up for relevant services using this account and may use Google Workspace tools such as Docs and Sheets. Keep the local Markdown knowledge base as the source of truth unless the user directs otherwise.

---

## Blockers

Use `agentcore/blockers.md` for large ambiguities, external dependencies, or questions that materially affect a project. Each entry must include:

- Date, project or area, short title
- Blocker description
- Why it matters
- Proposed default if the user does not answer
- Status and resolution

Do not block on small implementation choices. Choose a reasonable default and document it.
