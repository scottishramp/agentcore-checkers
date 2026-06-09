---
name: github-sync
description: Sync this repository with GitHub using Cursor agent judgment. Use when the user says "sync" or asks to sync local and remote GitHub changes.
---

# GitHub Sync

When the user says exactly `sync`, treat it as: "sync this repo with GitHub."

Use Cursor agent judgment, not a custom sync script.

## Routine

1. Inspect local state with `git status --short --branch`.
2. Fetch remote state with `git fetch origin main`.
3. If local is behind and clean, pull with `git pull --ff-only origin main`.
4. If local has uncommitted changes, review `git diff` and decide whether they belong in a commit. Do not discard user changes.
5. If local commits are ahead, push them with `git push origin main`.
6. If branches diverged or conflicts appear, inspect the changed files and resolve deliberately using the repo's current intent. Do not use destructive commands.
7. Finish by reporting whether local and remote are synced, what changed, and any unresolved blockers.

Keep the final answer short.
