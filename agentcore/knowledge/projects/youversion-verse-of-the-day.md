# YouVersion Verse of the Day

## Objective

Send Brian the YouVersion verse of the day via Telegram using the [YouVersion Platform](https://platform.youversion.com/) API.

## Status

- Phase: discovery / blocked on key recovery.
- Requested: Brian via Telegram `telegram:407016344` (2026-07-13).
- Policy clarified: Brian via Telegram `telegram:407016345` (2026-07-14) — the YouVersion app key is **not a secret** and may be **hardcoded in repo source** (scripts, API helpers, config constants). Do not store it only in `.env`, GitHub Secrets, or `.secrets/` unless a specific deployment surface requires it.

## App Key Handling

- Brian provided the app key inline in `telegram:407016344`.
- A prior async pass redacted the key from inbox records and the durable transcript before this policy was recorded.
- **Next unblock:** recover the key value from the original Telegram message (Brian's chat history) or ask Brian to paste it once more, then hardcode it in the integration source (for example `scripts/integrations/youversion_config.py` or an API helper constant).
- After recovery, update the redacted inbox copy in `agentcore/inbox/telegram/telegram__telegram-407016344.md` and the matching transcript line so future sessions have the value in repo context.

## Delivery Target

- Channel: Brian's Telegram DM (`telegram:dm:8983527816`).
- Likely mechanism: extend `scripts/telegram/scheduled_messages.json` with a daily fetch-and-send job, or a small standalone script invoked from `agent-runner.yml`.

## Open Actions

1. Recover or re-collect the YouVersion app key.
2. Confirm the correct YouVersion Platform endpoint and response shape for verse-of-the-day (or today's reading).
3. Implement fetch + Telegram send; hardcode the app key per Brian's instruction.
4. Add schedule cadence once Brian confirms preferred time (morning default is reasonable).

## Source Messages

- `telegram:407016344` — initial build request with app key.
- `telegram:407016345` — app key is public; hardcode it.
