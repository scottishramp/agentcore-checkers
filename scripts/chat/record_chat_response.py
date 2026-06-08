#!/usr/bin/env python3
"""Record terminal Google Chat task response metadata."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
EMAIL_DIR = SCRIPT_DIR.parent / "email"
if str(EMAIL_DIR) not in sys.path:
    sys.path.insert(0, str(EMAIL_DIR))

from common import read_json, utc_now_iso, write_json  # noqa: E402
from task_queue import load_task  # noqa: E402

DEFAULT_LEDGER_PATH = "agentcore/knowledge/communications/chat-thread-ledger.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Record Chat task response in ledger.")
    parser.add_argument("--task-file", required=True, help="Task markdown file.")
    parser.add_argument("--result-json", default=".agentcore/state/task-run-result.json", help="Task result JSON path.")
    parser.add_argument(
        "--notification-json",
        default=".agentcore/state/task-notify-result.json",
        help="Notification send result JSON path.",
    )
    parser.add_argument("--ledger", default=DEFAULT_LEDGER_PATH, help="Ledger JSON path.")
    return parser.parse_args()


def load_ledger(path: Path) -> dict:
    payload = read_json(path, default={"version": 1, "messages": {}, "spaces": {}})
    if not isinstance(payload, dict):
        payload = {"version": 1, "messages": {}, "spaces": {}}
    payload.setdefault("version", 1)
    payload.setdefault("messages", {})
    payload.setdefault("spaces", {})
    return payload


def main() -> int:
    args = parse_args()
    task = load_task(Path(args.task_file))
    if str(task.meta.get("source_kind", "")).strip().lower() != "google_chat":
        payload = {"ledger": args.ledger, "status": "skipped", "reason": "not_google_chat_task"}
        print(json.dumps(payload, ensure_ascii=True))
        return 0

    result = read_json(Path(args.result_json), default={})
    notification = read_json(Path(args.notification_json), default={})
    ledger_path = Path(args.ledger)
    ledger = load_ledger(ledger_path)
    status = str(result.get("status", "")).strip().lower() or str(task.meta.get("status", "")).strip().lower()
    if status not in {"done", "snag"}:
        status = "snag"

    now = utc_now_iso()
    source_message = str(task.meta.get("chat_message_name", ""))
    response_message = str(notification.get("chat_message_name", ""))
    space_name = str(task.meta.get("chat_space", ""))
    messages = ledger.setdefault("messages", {})
    existing = messages.get(source_message, {}) if isinstance(messages.get(source_message), dict) else {}
    existing.update(
        {
            "chat_message_name": source_message,
            "chat_space": space_name,
            "status": status,
            "task_id": str(task.meta.get("task_id", "")),
            "response_chat_message_name": response_message,
            "note": str(result.get("summary", ""))[:240],
            "updated_at": now,
        }
    )
    existing.setdefault("created_at", now)
    if source_message:
        messages[source_message] = existing

    spaces = ledger.setdefault("spaces", {})
    space = spaces.get(space_name, {}) if isinstance(spaces.get(space_name), dict) else {}
    space.update(
        {
            "chat_space": space_name,
            "latest_client_message_name": source_message,
            "latest_status": status,
            "latest_task_id": str(task.meta.get("task_id", "")),
            "latest_response_chat_message_name": response_message,
            "updated_at": now,
        }
    )
    space.setdefault("created_at", now)
    if space_name:
        spaces[space_name] = space

    ledger["updated_at"] = now
    write_json(ledger_path, ledger)
    payload = {
        "ledger": args.ledger,
        "source_chat_message_name": source_message,
        "response_chat_message_name": response_message,
        "status": status,
    }
    print(json.dumps(payload, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
