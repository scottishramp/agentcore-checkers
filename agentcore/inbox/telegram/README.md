# Telegram Inbox

Normalized Telegram DM records from the fast router inbox queue.

Each file corresponds to one inbound Telegram message persisted by `scripts/telegram/triage_messages.py`.

Actionable routes (`knowledge_update`, `task`) also create task files under `agentcore/inbox/tasks/`.
