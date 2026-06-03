#!/usr/bin/env python3
"""Record terminal email task response metadata in the thread ledger."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import read_json
from email_ledger import load_ledger, save_ledger, upsert_message
from task_queue import load_task


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Record task response in email thread ledger.")
    parser.add_argument("--task-file", required=True, help="Task markdown file.")
    parser.add_argument("--result-json", default=".agentcore/state/task-run-result.json", help="Task result JSON path.")
    parser.add_argument(
        "--notification-json",
        default=".agentcore/state/task-notify-result.json",
        help="Notification send result JSON path.",
    )
    parser.add_argument(
        "--ledger",
        default="agentcore/knowledge/communications/email-thread-ledger.json",
        help="Ledger JSON path.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    task = load_task(Path(args.task_file))
    result = read_json(Path(args.result_json), default={})
    notification = read_json(Path(args.notification_json), default={})
    ledger = load_ledger(args.ledger)

    status = str(result.get("status", "")).strip().lower() or str(task.meta.get("status", "")).strip().lower()
    if status not in {"done", "snag"}:
        status = "snag"

    ledger = upsert_message(
        ledger,
        gmail_message_id=str(task.meta.get("gmail_message_id", "")),
        gmail_thread_id=str(task.meta.get("gmail_thread_id", "")),
        rfc_message_id=str(task.meta.get("rfc_message_id", "")) or str(task.meta.get("source_message_id", "")),
        status=status,
        task_id=str(task.meta.get("task_id", "")),
        response_gmail_message_id=str(notification.get("gmail_message_id", "")),
        note=str(result.get("summary", ""))[:240],
    )
    save_ledger(ledger, args.ledger)
    payload = {
        "ledger": args.ledger,
        "source_gmail_message_id": str(task.meta.get("gmail_message_id", "")),
        "response_gmail_message_id": str(notification.get("gmail_message_id", "")),
        "status": status,
    }
    print(json.dumps(payload, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
