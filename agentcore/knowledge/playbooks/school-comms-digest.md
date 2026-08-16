---
title: School communications digest
type: playbook
status: active
created: 2026-08-16
updated: 2026-08-16
confidence: medium
related:
  - ../people/herbert-children.md
  - ../school/2026-27-roster.json
  - ../school/digest-doc.json
  - ./brian-gmail-mailbox.md
---

# Playbook: Kids' School Communications Digest

Living Google Doc of school mail from Brian's Gmail, rebuilt each morning. Telegram only pings the Important section plus the Doc link.

## Goal

Brian should see **what needs a decision or bag/calendar change**, with kid-specific notes and non-urgent school announcements in one shared Doc.

## Doc layout

1. **Important** — action items for any kid, with date and child name
2. **Per child** — Daniel, Nathan, Ezra, Silver, Levi: other specific notes
3. **General** — school announcements that are not urgent

## Sources

- Mailbox: `briandherbert@gmail.com`
- Label: `26-27 School` (auto-applied to matching mail)
- Query window: last 7 days
- Roster: `agentcore/knowledge/school/2026-27-roster.json`
- Google Doc registry: `agentcore/knowledge/school/digest-doc.json`

The Doc lives in AgentCore Drive (`scottishramp@gmail.com`), folder `School`, shared writer with `briandherbert@gmail.com`. Do not copy full message bodies into git.

## Delivery

- Primary: Google Doc, replaced in place each run
- Ping: Telegram `@AgentCoreFam_bot` with Important items + Doc link
- Cadence: daily with `agent-runner.yml` (8:30 AM America/Chicago)
- Command: `python3 scripts/email/school_digest.py --hours 168 --apply-label --update-doc --send-telegram`
- Local preview: `npm run email:school-digest -- --hours 168 --dry-run`

## Importance model (v2)

**Important**

- Action verbs: due, form, fee, supplies, conference, detention, no school, early release, missing homework, schedule change

**Per child**

- Direct teacher emails that are not action
- Seesaw / classroom app posts

**General**

- School-wide newsletters (Husky Pride, Mustang Round-Up, Falcon News)
- PTO and similar non-urgent announcements

## Filing

`school_digest.py --apply-label` adds `26-27 School` to matching messages.

## Learning loop

When Brian says an item was in the wrong section, update this playbook and the classifier in `scripts/email/school_digest.py`. Record durable teacher/school facts on `herbert-children.md` and the roster JSON.
