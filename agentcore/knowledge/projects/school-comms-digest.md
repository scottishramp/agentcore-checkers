# School Communications Digest

## Objective

Give Brian a daily, child-grouped digest of school communications. The durable artifact is a shared Google Doc. Telegram only pings action items.

## Status

- Phase: Google Doc loop (2026-08-16).
- Gmail label `26-27 School` is the filing home.
- Google Doc in AgentCore Drive, shared with Brian as writer.
- Telegram sends Important items plus the Doc link with the morning async runner.
- Teacher roster for 2026-27 is in `agentcore/knowledge/school/2026-27-roster.json`.
- Levi's 1st-grade teacher: Mrs. Scott (Brian, 2026-08-16).
- Digest bullets are single distilled lines (Need / FYI / No action) with a hyperlinked Link; no raw email excerpts. Items due this week are bold.
- Important contains only real to-dos; no-action items go to kid sections or General.
- Morning sweep is the learning loop: it ingests new teachers, sports, and activities onto the roster and re-syncs `herbert-children.md`.

## Why this shape

Brian asked for a Drive Doc with:

1. **Important** — action items, with dates and which kid; due-this-week items bold
2. **Per child** — standing sports/teams plus other specific notes
3. **General** — school announcements that are not urgent

## Deliverables

- Roster and children-page school facts
- `scripts/email/school_digest.py` plus `scripts/docs/google_docs.py`
- Morning Doc rebuild + Telegram ping from `agent-runner.yml`
- Playbook `school-comms-digest.md`

## Next

- Tighten Important vs per-kid vs General from Brian's Doc reactions.
- Add Mrs. Scott's email when it appears in Gmail.
- Record Nathan / Silver / Levi sports if they join teams.
