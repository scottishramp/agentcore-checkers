#!/usr/bin/env python3
"""Notify a Telegram user that AgentCore started working on a task."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
EMAIL_DIR = SCRIPT_DIR.parent / "email"
if str(EMAIL_DIR) not in sys.path:
    sys.path.insert(0, str(EMAIL_DIR))

from common import compact_whitespace  # noqa: E402
from task_queue import load_task  # noqa: E402
from send_task_response import send_message  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send Telegram working notice for a claimed task.")
    parser.add_argument("--task-file", required=True, help="Task file path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    task = load_task(Path(args.task_file))
    if str(task.meta.get("source_kind", "")).strip().lower() != "telegram":
        print(json.dumps({"status": "skipped", "reason": "not_telegram_task"}, ensure_ascii=True))
        return 0

    chat_id = str(task.meta.get("telegram_chat_id", "")).strip()
    if not chat_id:
        raise ValueError("Telegram task is missing telegram_chat_id metadata.")

    title = compact_whitespace(str(task.meta.get("source_subject", ""))) or "your request"
    body = f"Working on: {title}"
    sent = send_message(chat_id, body)
    payload = {
        "status": "sent",
        "task_file": args.task_file,
        "telegram_chat_id": chat_id,
        "message_id": str(((sent.get("result") or {}) if isinstance(sent, dict) else {}).get("message_id", "")),
    }
    print(json.dumps(payload, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
