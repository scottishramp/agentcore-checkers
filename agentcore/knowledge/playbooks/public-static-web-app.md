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
  - ./github-pages-deployment.md
  - ../concepts/ux-message-design.md
---

# Playbook: Public Static Web App

Use this for small public web deliverables (games, tools, demos) that do not need accounts, persistence, or a backend.

## Kickoff Questions

Ask these before building:

1. What does the user want to see and do? (acceptance criteria)
2. How do you want to view the prototype? (local browser, shared URL)
3. Where should the final version live? (local only, GitHub Pages, Netlify, other)
4. Design preferences? (style, color scheme, layout)

## Session-0 Preflight

Check before writing code:

```sh
git status          # is this already a git repo?
gh auth status      # is gh authenticated as the right account?
which gh netlify vercel surge   # what deploy tools are available?
```

## Build Phase

1. `index.html`, `styles.css`, focused JavaScript — no framework unless clearly needed.
2. Write a test-scenario list (happy path, edge cases, UX failure modes) before building UI interactions.
3. Add `?v=BUILD-ID` to `<link>` and `<script>` tags so browser cache is invalidated on each fix:
   ```html
   <link rel="stylesheet" href="styles.css?v=20260424a">
   <script src="game.js?v=20260424a"></script>
   ```
4. `node --check game.js` for syntax.

## CSS Layout Checklist

- Set **both** `grid-template-columns` and `grid-template-rows` when using CSS Grid with equal cell sizing.
- Use `aspect-ratio: 1` on square containers.
- Use `min()` and `clamp()` for responsive sizing.

## Local Verification

```sh
python3 -m http.server 4173
curl -I http://localhost:4173/index.html
```

## Visual QA (do this, don't just take the screenshot)

Take screenshots at:

- Desktop (1280×900 or similar)
- Mobile (390×844 or similar)

Then **look at them** and check:

- [ ] All rows and columns equal-sized
- [ ] No clipped or overflowing content
- [ ] Pieces/elements are correctly placed
- [ ] Status messages are present and readable
- [ ] Controls (buttons) are visible and reachable
- [ ] Tip/hint text is not cut off

## Automated Test Suite

Install once per project:

```sh
npm install -D @playwright/test && npx playwright install chromium
```

Wire a test API into the page for state injection (board positions, game state) so scenarios can be set up without playing through full games.

Run before every user review:

```sh
npm test
```

## Status Messages

All user-facing messages must:

- Classify the **exact** failure reason (not a catch-all).
- Tell the user what to do next.
- Have an automated assertion.

See `agentcore/knowledge/concepts/ux-message-design.md`.

## User Review

- Tell the user the local URL and how to hard refresh.
- Ask: "Does this look and feel right?"
- When a bug is reported: reproduce it as a test scenario, fix it, run full suite, then report back.

## Temporary Public Preview (if needed)

```sh
lt --port 4173   # localtunnel
```

After review, kill all tunnel processes:

```sh
# Kill parent and child
ps -ax | awk '/lt --port/ { print $1 }' | xargs kill 2>/dev/null
curl -I https://YOUR-URL.loca.lt   # should return 503
```

## Durable Deployment

See `agentcore/knowledge/playbooks/github-pages-deployment.md` for GitHub Pages (preferred when `gh` is authenticated).

Alternatives when `gh` is not available:
- Netlify: `npx netlify-cli deploy --prod`
- Surge: `npx surge ./`
- Vercel: `npx vercel --prod`
