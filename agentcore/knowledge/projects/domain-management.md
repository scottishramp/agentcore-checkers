---
title: Domain Management
type: project
status: active
created: 2026-08-16
updated: 2026-08-16
client: Brian Herbert
owner: AgentCore
confidence: high
related:
  - agentcore/knowledge/playbooks/godaddy-delegate-access.md
  - agentcore/knowledge/projects/personal-operating-system.md
  - agentcore/knowledge/projects/burningaltar-blog.md
---

# Project: Domain Management

## Objective

Manage Brian's domains as his administrative assistant: DNS, nameservers, forwarding, renewals awareness, and related GoDaddy products. Do not purchase, transfer, or delete domains unless Brian explicitly asks.

## Status

- Phase: access live; `burningaltar.com` pointed at the new blog.
- GoDaddy delegate access accepted 2026-08-16 for `scottishramp@gmail.com`.
- Access level: **Products & Domains** (no purchase).
- AgentCore GoDaddy account: `scottishramp@gmail.com`, customer `#743698597`, signed in via Google SSO.
- Brian's GoDaddy account: Brian Herbert, customer `#34804617`.
- Blog project: `agentcore/knowledge/projects/burningaltar-blog.md`. Live URL: https://burningaltar.com/

## Inventory (GoDaddy, 4 domains)

| Domain | Registrar | Notes (2026-08-16) |
| --- | --- | --- |
| `burningaltar.com` | GoDaddy | Public blog at https://burningaltar.com/ (Hugo on GitHub Pages). Renews Mar 16, 2027 at $22.99/yr. Domain lock on. Domain Privacy on. GoDaddy nameservers `ns23.domaincontrol.com` / `ns24.domaincontrol.com`. Apex A records `185.199.108.153` / `185.199.109.153` / `185.199.110.153`. `www` CNAME `scottishramp.github.io`. Domain forwarding removed. GoDaddy email CNAMEs/MX left in place. |
| `burningaltar.org` | GoDaddy | Same account. Products list showed "2 Domains, Website" under My Business / burningaltar.org. |
| `cleansane.com` | GoDaddy | Same account. Products list showed Domain + Website. Auto-renew noted around 2026-09-08 with a billing-details validation prompt. |
| `notverydeep.com` | GoDaddy | Same account. Products list showed Domain + Website. |

Brian originally mentioned "a couple" of domains; this GoDaddy account currently holds the four above. Treat all four as in-scope unless he restricts them.

## Access Path

Playbook: `agentcore/knowledge/playbooks/godaddy-delegate-access.md`

## Operating Rules

- Keep Brian as account owner. Do not transfer domains off his account.
- Do not use **Products, Domains, & Purchase**. AgentCore cannot charge his card.
- Ask before irreversible actions: transfer, delete, unlock for transfer, WHOIS privacy off, or listing a domain for sale.
- DNS and nameserver changes are in-scope when Brian asks to point a domain at a host, email, or site.
- Do not store street address, phone, PIN, or payment details in git. Registrant contact on file for `burningaltar.com` uses Domain Privacy (Domains by Proxy).

## Next Actions

- Optional: add the fourth GitHub Pages A record `185.199.111.153`.
- Confirm whether `burningaltar.org`, `cleansane.com`, and `notverydeep.com` should stay in AgentCore's management scope.
