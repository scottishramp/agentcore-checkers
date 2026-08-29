---
title: Burning Altar Blog
type: project
status: live
created: 2026-08-16
updated: 2026-08-29
client: Brian Herbert
owner: AgentCore
confidence: high
related:
  - agentcore/knowledge/projects/domain-management.md
  - agentcore/knowledge/playbooks/godaddy-delegate-access.md
  - agentcore/knowledge/playbooks/github-pages-deployment.md
---

# Project: Burning Altar Blog

## Objective

Host Brian Herbert's public writing at `burningaltar.com` as a simple self-hosted static blog.

## Current Status

- Live: https://burningaltar.com/
- Alternate: https://scottishramp.github.io/burningaltar/
- Delivery repo: https://github.com/scottishramp/burningaltar (public, Hugo + vendored hugo-bearblog, GitHub Actions Pages)
- Custom domain HTTPS enforced on GitHub Pages.

## Draft source

Brian writes new posts in the shared Google Doc [Blog thoughts](https://docs.google.com/document/d/1qkV4rFFANZ8ybZl3dKRsfyOtTFIC_hyyLlYTJuAA_JQ/edit) (`1qkV4rFFANZ8ybZl3dKRsfyOtTFIC_hyyLlYTJuAA_JQ`), shared with `scottishramp@gmail.com` as commenter.

Expected structure:

- Dated section (`Aug 24, 2026`)
- Title line
- Optional `Core ideas:` bullets
- Body
- Scratch at the bottom under `-- Don't publish this, just thoughts. --` is never published

Do not persist full draft bodies in git. Publish ready dated sections to `scottishramp/burningaltar` `content/blog/*.md`.

In-doc grammar comments are blocked: AgentCore has commenter access on the file, but OAuth is `drive.readonly` + `drive.file` (app-created files only). Leave grammar notes in the client reply unless Brian grants editor and a broader Drive comment/write scope.

## Content

- [Why AI is the biggest deal since the wheel](https://burningaltar.com/ai-and-the-wheel/) (2025-02-23) — source [Bear](https://briandherbert.bearblog.dev/ai-and-the-wheel/)
- [What the abacus predicts for AI](https://burningaltar.com/ai-and-the-abacus/) (2025-03-01) — source [Bear](https://briandherbert.bearblog.dev/ai-and-the-abacus/)
- [Bet on getting Sherlocked](https://burningaltar.com/bet-on-getting-sherlocked/) (2026-08-24) — from Blog thoughts
- [AI is the engine to build around, not drop in](https://burningaltar.com/ai-is-the-engine-to-build-around/) (2026-08-23) — from Blog thoughts

## DNS (GoDaddy, 2026-08-16)

- Removed domain forwarding (`burningaltar.com` → `www`) so apex A records could be edited.
- Apex A: `185.199.108.153`, `185.199.109.153`, `185.199.110.153` (GitHub Pages). Fourth GitHub IP `185.199.111.153` not added yet.
- `www` CNAME: `scottishramp.github.io`
- Left GoDaddy email records alone (`email`/`e`/`imap`/`mail`/`mobilemail`/MX to `*.secureserver.net`).
- Did not change `burningaltar.org`, `cleansane.com`, or `notverydeep.com`.

## Operating Notes

- Posts are Markdown in the delivery repo, not this control repo.
- New posts: dated sections in Blog thoughts, or add `content/blog/*.md` in `scottishramp/burningaltar` and push `main`.
- Do not purchase, transfer, or delete the domain. Keep Brian as GoDaddy owner.
