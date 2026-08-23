---
title: School communications digest
type: playbook
status: active
created: 2026-08-16
updated: 2026-08-22
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

1. **Important** — action items for any kid, with date and child name. Items due this week (America/Chicago, today through +6 days) are **bold**.
2. **Per child** — Daniel, Nathan, Ezra, Silver, Levi: standing sports/teams, then other specific notes
3. **General** — school announcements that are not urgent

Each bullet is one distilled line — **Need:** (the to-do, quoting the ask when useful), **FYI:** (the key fact), or **No action (topic)** — plus a hyperlinked **Link**. No raw email excerpts. Stale needs are relabeled "Past need (likely done)".

**Important items are clickable checkboxes.** Brian checks off handled items in the Doc; the next
run detects them and drops them permanently (ledger `done: true`). Mechanism: the Docs API cannot
read checked state, so `detect_done_items` exports the Doc as HTML via Drive
(`export_document_html`) and treats checklist lines with `text-decoration:line-through` as
checked, matching them to ledger entries via the stored `doc_line` text. Verified end-to-end
2026-08-17.

## Sources

- Mailbox: `briandherbert@gmail.com`
- Label: `26-27 School` (auto-applied to matching mail, then archived out of Inbox)
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

## Evaluation model (v3 — LLM-first)

Every email is evaluated **once** by an LLM (`scripts/email/email_evaluator.py`) and the verdict is
stored in `agentcore/knowledge/email/eval-ledger.json` (committed by the runner, pruned after 60
days, metadata only — no bodies). Pipeline per run:

1. **Ledger check** — already-evaluated message ids reuse their stored verdict (`--reeval` forces
   re-evaluation).
2. **Prefilter** — obviously irrelevant senders (mailer-daemon, calendar notifications, Drive
   share bots) are ledgered as skipped without an LLM call.
3. **LLM batch evaluation** — new emails go to the LLM in batches of 12 with household context
   (kids, grades, schools, teachers, sports from the roster). Backends: Gemini REST if
   `GEMINI_API_KEY` is set, else Cursor Agent CLI (`CURSOR_API_KEY` in CI). Verdict per email:
   relevant, category, children, one distilled `line` ("Need:"/"FYI:"), `need`, `due_date`,
   `learn` facts, `unsubscribe` recommendation.
4. **Keyword fallback** — if no backend is available or the call fails, the old keyword
   classifier still renders the digest (`--no-llm` forces this).

**Important** holds only verdicts with a real `need` whose `due_date` is not past. Irrelevant
verdicts are dropped from the Doc entirely. Unsubscribe recommendations render in a
**Suggestions** section at the bottom.

**Per child**

- Standing sports / teams from the roster, even when there is no new mail
- Direct teacher emails that are not action
- Seesaw / classroom app posts
- Sports mail that is informational rather than an action

**General**

- School-wide newsletters (Husky Pride, Mustang Round-Up, Falcon News)
- PTO and similar non-urgent announcements

## Filing

`school_digest.py --apply-label` adds `26-27 School` to matching messages and removes the `INBOX` label (same as dragging the message onto the school label in Gmail). Already-labeled school mail still sitting in Inbox is archived on the same pass. Mail stays findable under All Mail and the `26-27 School` label.

## Learning loop

When Brian says an item was in the wrong section, tighten the evaluator prompt in
`scripts/email/email_evaluator.py` (and re-run with `--reeval` if the stored verdict is wrong).

The morning sweep is also the learning loop for family facts. LLM `learn` entries flow to:

- child-scoped teachers/sports/activities → `2026-27-roster.json` (then `herbert-children.md` is
  re-synced);
- everything else (e.g. "Brian has a Netflix subscription") → appended, dated and deduped, to
  `agentcore/knowledge/people/family-facts.md`.

The runner commits roster, children page, family facts, and the eval ledger. Do not invent facts
for a child who is not named in the mail. Full email bodies stay in Gmail; they are not copied
into git.

Long-term direction (Brian, 2026-08-16): this ingest grows into a full family assistant —
constantly improving self-knowledge, surfacing action items, recommending unsubscribes — beyond
just school mail.
