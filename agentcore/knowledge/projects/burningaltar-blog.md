---
title: Burning Altar Blog
type: project
status: live
created: 2026-08-16
updated: 2026-08-16
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

## Content

Only two posts were copied from Bear. The site is not a Bear clone beyond the theme and those posts:

- [Why AI is the biggest deal since the wheel](https://burningaltar.com/ai-and-the-wheel/) (2025-02-23) — source [Bear](https://briandherbert.bearblog.dev/ai-and-the-wheel/)
- [What the abacus predicts for AI](https://burningaltar.com/ai-and-the-abacus/) (2025-03-01) — source [Bear](https://briandherbert.bearblog.dev/ai-and-the-abacus/)

## DNS (GoDaddy, 2026-08-16)

- Removed domain forwarding (`burningaltar.com` → `www`) so apex A records could be edited.
- Apex A: `185.199.108.153`, `185.199.109.153`, `185.199.110.153` (GitHub Pages). Fourth GitHub IP `185.199.111.153` not added yet.
- `www` CNAME: `scottishramp.github.io`
- Left GoDaddy email records alone (`email`/`e`/`imap`/`mail`/`mobilemail`/MX to `*.secureserver.net`).
- Did not change `burningaltar.org`, `cleansane.com`, or `notverydeep.com`.

## Operating Notes

- Posts are Markdown in the delivery repo, not this control repo.
- New posts: add `content/blog/*.md` in `scottishramp/burningaltar` and push `main`.
- Do not purchase, transfer, or delete the domain. Keep Brian as GoDaddy owner.
