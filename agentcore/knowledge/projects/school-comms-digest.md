# School Communications Digest

## Objective

Give Brian a daily, child-grouped digest of school communications that is short enough to read, biased toward action, and willing to be wrong in public so he can correct what "important" means.

## Status

- Phase: first live loop (2026-08-16).
- Gmail label `26-27 School` is the filing home.
- Telegram digest runs with the morning async runner.
- Teacher roster for 2026-27 is in `agentcore/knowledge/school/2026-27-roster.json`.

## Why this shape

Brian already files some school mail, but the 2026-27 label only had two messages when access started. Most current school mail was unlabeled in Inbox / `KidSchoolArchive/2026`. A daily Gmail dump would be unreadable. The digest should:

1. Auto-label matching 2026-27 school mail.
2. Route messages to kids from the roster.
3. Show teacher/action items; collapse newsletters.
4. Ask Brian to correct misses instead of guessing a perfect taxonomy up front.

## Deliverables

- Roster and children-page school facts
- `scripts/email/school_digest.py`
- Morning Telegram send from `agent-runner.yml`
- Playbook `school-comms-digest.md`

## Next

- Confirm Levi's 1st-grade teacher.
- Confirm Silver's homeroom is Mrs. Trofemuk.
- Tighten skip/show rules from Brian's first few digest reactions.
