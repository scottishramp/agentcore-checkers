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
  - ./brian-gmail-mailbox.md
---

# Playbook: Kids' School Communications Digest

Daily compact digest of school mail from Brian's Gmail, sent on Telegram with the morning AgentCore runner.

## Goal

Brian should see **what needs a decision or bag/calendar change**, not every Edmond blast.

## Sources

- Mailbox: `briandherbert@gmail.com`
- Label: `26-27 School` (auto-applied to matching mail)
- Query window: last 24 hours of Edmond Schools, Remind, Seesaw, and already-labeled mail
- Roster: `agentcore/knowledge/school/2026-27-roster.json`

Do not copy full message bodies into git.

## Delivery

- Channel: Telegram `@AgentCoreFam_bot`
- Cadence: daily with `agent-runner.yml` (8:30 AM America/Chicago)
- Command: `python3 scripts/email/school_digest.py --hours 24 --apply-label --send-telegram`
- Local preview: `npm run email:school-digest -- --hours 48 --dry-run`

Empty windows do not send.

## Importance model (v1, iterate with Brian)

**Show**

- Direct teacher emails
- Child-named schedule/class changes
- Action verbs: due, form, fee, supplies, conference, detention, no school, early release, missing homework
- Seesaw posts (one line)

**Skip unless Brian says otherwise**

- School-wide newsletters (Husky Pride, Mustang Round-Up, Falcon News Flash)
- PTO fundraisers, candy grams, staff-appreciation food signups
- Duplicate Kristin forwards of the same school message
- District OSDE blasts
- Before/after-care marketing

## Filing

`school_digest.py --apply-label` adds `26-27 School` to matching messages. Older years stay in `KidSchoolArchive/YYYY`.

## Learning loop

When Brian says a digest item was noise or a skipped item mattered, update this playbook and the classifier in `scripts/email/school_digest.py`. Record durable teacher/school facts on `herbert-children.md` and the roster JSON.
