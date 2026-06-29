# Communications Knowledge

Deterministic summaries and ledgers derived from automated communication ingestion.

- `ingestion-ledger.md` stores run-by-run structured updates.
- `email-thread-ledger.json` stores small idempotency metadata for email messages/threads. It intentionally stores IDs and statuses, not email bodies.
- `telegram-thread-ledger.json` stores idempotency metadata for Telegram messages.
- `telegram-transcript.md` stores allowed Telegram message text, fast-router replies, and inbox record links for async Cursor review.
- `telegram-photo-registry.json` stores Telegram photo labels, Drive links, fast-agent descriptions, and filing status.
