---
title: Mailbox and calendar learning loop
type: playbook
status: active
created: 2026-08-29
updated: 2026-08-29
confidence: high
related:
  - ./brian-gmail-mailbox.md
  - ./knowledge-content-ingest.md
  - ./school-comms-digest.md
  - ../architecture/system-architecture.md
---

# Playbook: Mailbox and Calendar Learning Loop

How AgentCore keeps learning about Brian on its own: it reads his shared calendar, sweeps
his whole personal mailbox for durable facts, and asks him about the senders it cannot
confidently judge. His answers become permanent policy, so the same question is never
asked twice and each night starts smarter than the last.

Runs inside the nightly `knowledge-content-ingest` workflow (11:00 AM America/Chicago).

## Why Sender-Level, Not Message-Level

The school digest evaluates each *message*. This loop decides each *sender* once. Most
mail is repetitive, so one decision about `noreply@example.com` handles every future
message from them with no model call and no question. That keeps nightly cost roughly
flat as volume grows, and it means a question to Brian buys lasting value rather than a
one-time answer.

## Nightly Order

1. **`resolve_answers.py`** — apply any Telegram answers Brian sent since the last run.
2. **`ingest_calendar.py`** — rebuild the schedule page, record new recurring commitments.
3. **`mailbox_sweep.py`** — classify new senders, extract facts, enqueue new questions.
4. **`ask_questions.py`** — send at most five questions as one numbered Telegram batch.
5. Workflow commits every ledger and knowledge change.

Answers are applied *before* the sweep so a sender Brian just decided is treated correctly
in the very same run.

## Sender Policies

| Policy | Meaning | Effect |
|--------|---------|--------|
| `learn` | Mail regularly carries durable facts | Bodies are read and facts extracted |
| `info` | Legitimate but transient | Sender remembered, no extraction |
| `ignore` | Marketing, promos, spam | Skipped entirely |

Ledger: `agentcore/knowledge/email/sender-policy.json`

Each entry records the policy, who decided it (`brian`, `llm`, or `seed`), a
human-readable rationale, model confidence, sample subjects, and a message count.
**Brian's answers outrank model guesses** and are never silently overwritten — a later
model verdict cannot change a sender he decided himself.

A `domains` map supports blanket rules for a whole domain when per-sender entries would
be pointless.

## When AgentCore Asks

The model returns a confidence with every sender verdict. At **0.8 or higher** the policy
is recorded automatically. Below that, the sender becomes a question instead of a guess.
In practice this catches exactly the cases a person would have to answer: an unfamiliar
personal name, a small business that might be his barber or contractor, a youth-sports
league for a sport none of the kids play.

Questions are capped at **five per night**, ordered by how many messages that sender
sent, so the highest-volume unknowns get resolved first.

## Answering

Brian replies to the numbered batch in Telegram. All of these parse:

```
1 learn, 2 ignore
1l 2i 3s
1) learn. 2) spam.
learn 1, spam 2
all ignore
```

Synonyms: `learn` / `keep` / `important` / `remember`; `info` / `fyi`; `ignore` / `spam` /
`junk` / `skip`.

A reply is matched to the newest batch that was already outstanding when it arrived.
Numbers outside that batch are dropped rather than guessed at. If the reply is prose
("the barber one is mine, drop the rest"), the parser deliberately does nothing: the
questions stay open and the message still reaches Cursor as a normal Telegram review
task, so a person-level answer is never lost — it just resolves on the slower path.

Unanswered questions expire after 21 days so the nightly batch stays current.

Ledger: `agentcore/knowledge/communications/pending-questions.json`

## What Gets Written

- `agentcore/knowledge/people/brian-learned-facts.md` — dated facts under category
  headings (finance, health, home, work, family, travel, subscriptions, commitments, other).
- `agentcore/knowledge/calendar/upcoming.md` — regenerated each run, 7 days back through
  60 days ahead. Do not hand-edit; it is overwritten.
- `agentcore/knowledge/calendar/calendar-state.json` — recurring series already recorded.
- `agentcore/knowledge/email/mailbox-sweep-state.json` — watermark plus recent message ids.

Facts dedupe on a normalized fingerprint, including containment, so a later email
restating a known fact with extra words does not create a second bullet.

## Privacy Rules

- **Read-only against Gmail.** Nothing is labelled, archived, or trashed by this loop.
- Message bodies are read for extraction but **never written to the repo**. Only distilled
  facts, sender addresses, display names, and subjects are persisted.
- The extraction prompt forbids copying passwords, full account or card numbers, and
  authentication codes.
- Calendar access is read-only; nothing is written back to Google.

## Local Commands

```sh
npm run ingest:calendar                       # rebuild the schedule page
npm run learn:sweep -- --dry-run              # classify without persisting
npm run learn:sweep -- --no-llm --dry-run     # Gmail plumbing check, no model calls
npm run learn:ask -- --dry-run                # preview the Telegram batch
npm run learn:resolve                         # apply answers from Telegram records
npm run test:learn                            # logic tests, no network
```

Useful flags on the sweep: `--hours` (lookback when no watermark exists), `--backfill-days`
for a one-time historical pass, `--max-messages`, `--extract-limit`, `--ask-limit`.

## Backfill

Brian skipped a 90-day historical backfill on 2026-08-29, then asked for a **7-day
backfill** the same day. That 7-day pass ran locally and is complete. Longer backfills
remain optional and should be run off-schedule, since they are much heavier than a
nightly pass:

```sh
npm run learn:sweep -- --backfill-days 90 --max-messages 800 --extract-limit 60 --ask-limit 5
```

The backfill does not move the watermark backwards, so the nightly cadence is unaffected.

## Backends

Same selection as the school digest: Gemini REST when `GEMINI_API_KEY` is set, otherwise
the Cursor Agent CLI (`CURSOR_API_KEY` in CI). The workflow installs the Cursor CLI before
the sweep. A backend failure degrades gracefully — known policies still apply, and the run
records the error instead of aborting.

## Extending to Other Question Types

`questions.py` is not email-specific. Any job can enqueue a question with a `kind`, a
`subject_key`, a prompt, and answer options; it will be batched into the same nightly
Telegram message. Only `sender_policy` answers currently write policy automatically, so a
new kind needs a matching handler in `resolve_answers.py`.
