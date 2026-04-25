---
title: GitHub Pages deployment playbook
type: playbook
status: active
created: 2026-04-24
updated: 2026-04-24
confidence: high
related:
  - ../projects/checkers-web-game.md
  - ./public-static-web-app.md
---

# Playbook: GitHub Pages Deployment

Use this to deploy a static site to GitHub Pages from a local repo.

## Pre-Deployment Checklist

- [ ] `gh auth status` confirms the right account is authenticated. Run `gh auth login --web --git-protocol https` if not.
- [ ] `git status` — repo is initialized. Run `git init && git checkout -b main` if not.
- [ ] `.gitignore` excludes `node_modules/`, `test-results/`, `.DS_Store`.
- [ ] All files are committed.

## Steps

```sh
# 1. Commit everything
git add -A
git commit -m "Initial release"

# 2. Create public repo and push
gh repo create REPO-NAME --public --source=. --remote=origin --push --description "Short description"

# 3. Enable Pages
gh api repos/OWNER/REPO-NAME/pages -X POST -f "build_type=workflow" --silent 2>&1 || true

# 4. Configure Pages source (main branch, root)
gh api repos/OWNER/REPO-NAME/pages -X PUT \
  -f "build_type=legacy" \
  -F "source[branch]=main" \
  -F "source[path]=/"

# 5. Trigger first build
gh api repos/OWNER/REPO-NAME/pages/builds -X POST

# 6. Poll until built (usually 30–60 seconds)
gh api repos/OWNER/REPO-NAME/pages/builds/latest --jq '{status, created_at}'

# 7. Verify live
curl -s -o /dev/null -w "HTTP: %{http_code}\n" "https://OWNER.github.io/REPO-NAME/"
```

## Ongoing Updates

```sh
git add -A && git commit -m "Description" && git push
```

GitHub Pages rebuilds automatically on every push to `main`.

## Common Problems

**403 on push after `gh auth login`**
- Another GitHub account is wired into git's credential helper.
- Fix: `gh auth setup-git`, then push again.

**Pages returns 404 after enabling**
- The first build takes up to 60 seconds after triggering.
- Trigger manually: `gh api repos/OWNER/REPO/pages/builds -X POST`
- Then poll `pages/builds/latest` until `status` is `"built"`.

**Pages not serving updated files**
- Check that `build_type` is `"legacy"` (serves directly from branch), not `"workflow"` (requires a GitHub Actions file).

## Account Context

- AgentCore GitHub account: `scottishramp`
- GitHub CLI currently authenticated as: `scottishramp` (verify with `gh auth status`)
