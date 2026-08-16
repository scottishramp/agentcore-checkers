---
title: GoDaddy Delegate Access
type: playbook
status: active
created: 2026-08-16
updated: 2026-08-16
---

# Playbook: GoDaddy Delegate Access

Use this to manage Brian's GoDaddy products from AgentCore's own account. Do not ask Brian for his GoDaddy password.

## Identities

- AgentCore: `scottishramp@gmail.com` (GoDaddy customer `#743698597`). Sign in with **Google**, not a GoDaddy password.
- Owner: Brian Herbert (GoDaddy customer `#34804617`).
- Access level: Products & Domains.

## Sign in and switch accounts

1. Open [GoDaddy sign-in](https://sso.godaddy.com/) and choose **Sign in with Google**.
2. Select **Scottish Ramp / scottishramp@gmail.com**.
3. Open [Delegate Access](https://account.godaddy.com/access).
4. Under **Accounts I can access**, open **Brian Herbert** with **Access Now**.
5. Confirm the blue bar: `Scottish logged in as: Brian Herbert`.
6. Domain list: [Domain Portfolio](https://dcc.godaddy.com/control/portfolio).
7. DNS for a domain: `https://dcc.godaddy.com/control/dnsmanagement?domainName=EXAMPLE.com`.
8. Settings for a domain: `https://dcc.godaddy.com/control/portfolio/EXAMPLE.com/settings`.
9. When finished, **Exit access**.

## Guardrails

- Allowed without extra confirmation: inspect DNS/settings, report status, plan a change.
- Ask Brian first: purchases, transfers, deletes, domain unlock for transfer, turning privacy off, listing for sale.
- DNS edits are allowed when Brian asked to connect a site, email, or host.
