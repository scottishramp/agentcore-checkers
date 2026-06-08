# Communications Knowledge

Deterministic summaries and ledgers derived from automated communication ingestion.

- `ingestion-ledger.md` stores run-by-run structured updates.
- `email-thread-ledger.json` stores small idempotency metadata for email messages/threads. It intentionally stores IDs and statuses, not email bodies.
- `chat-thread-ledger.json` stores small idempotency metadata for Google Chat messages/spaces. It intentionally stores IDs and statuses, not full Chat histories.
