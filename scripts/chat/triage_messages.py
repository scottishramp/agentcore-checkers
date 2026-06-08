#!/usr/bin/env python3
"""Normalize fetched Google Chat records and enqueue task files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
EMAIL_DIR = SCRIPT_DIR.parent / "email"
if str(EMAIL_DIR) not in sys.path:
    sys.path.insert(0, str(EMAIL_DIR))

from common import compact_whitespace, ensure_dir, sanitize_filename, utc_now_iso, write_json  # noqa: E402
from task_queue import next_task_id  # noqa: E402

DEFAULT_INPUT_PATH = ".agentcore/state/chat-fetch/latest.json"
DEFAULT_SUMMARY_PATH = ".agentcore/state/chat-sync-summary.json"
DEFAULT_LEDGER_PATH = "agentcore/knowledge/communications/chat-thread-ledger.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Classify and store fetched Google Chat messages.")
    parser.add_argument("--input", default=DEFAULT_INPUT_PATH, help="Path to chat fetch output JSON.")
    parser.add_argument("--chat-dir", default="agentcore/inbox/chat", help="Markdown output directory for chat records.")
    parser.add_argument("--task-dir", default="agentcore/inbox/tasks", help="Markdown output directory for task queue records.")
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_PATH, help="Path for machine-readable triage summary.")
    parser.add_argument("--ledger", default=DEFAULT_LEDGER_PATH, help="Durable Chat idempotency ledger.")
    return parser.parse_args()


def read_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def quote_meta(value) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"')


def load_ledger(path: Path) -> dict:
    payload = read_json(path, default={"version": 1, "messages": {}, "spaces": {}})
    if not isinstance(payload, dict):
        payload = {"version": 1, "messages": {}, "spaces": {}}
    payload.setdefault("version", 1)
    payload.setdefault("messages", {})
    payload.setdefault("spaces", {})
    return payload


def save_ledger(path: Path, payload: dict) -> None:
    payload["updated_at"] = utc_now_iso()
    write_json(path, payload)


def is_terminal_message(ledger: dict, message_name: str) -> bool:
    item = (ledger.get("messages") or {}).get(message_name, {})
    status = str(item.get("status", "")) if isinstance(item, dict) else ""
    return status in {"queued", "done", "snag", "ignored"}


def upsert_message(ledger: dict, record: dict, status: str, task_id: str = "", response_name: str = "") -> dict:
    message_name = str(record.get("chat_message_name", ""))
    if not message_name:
        return ledger
    now = utc_now_iso()
    messages = ledger.setdefault("messages", {})
    existing = messages.get(message_name, {}) if isinstance(messages.get(message_name), dict) else {}
    existing.update(
        {
            "chat_message_name": message_name,
            "chat_space": str(record.get("chat_space", "")),
            "sender_name": str(record.get("sender_name", "")),
            "status": status,
            "task_id": task_id or existing.get("task_id", ""),
            "response_chat_message_name": response_name or existing.get("response_chat_message_name", ""),
            "updated_at": now,
        }
    )
    existing.setdefault("created_at", now)
    messages[message_name] = existing
    space_name = str(record.get("chat_space", ""))
    if space_name:
        spaces = ledger.setdefault("spaces", {})
        space = spaces.get(space_name, {}) if isinstance(spaces.get(space_name), dict) else {}
        space.update(
            {
                "chat_space": space_name,
                "latest_client_message_name": message_name,
                "latest_status": status,
                "latest_task_id": task_id or space.get("latest_task_id", ""),
                "latest_response_chat_message_name": response_name
                or space.get("latest_response_chat_message_name", ""),
                "updated_at": now,
            }
        )
        space.setdefault("created_at", now)
        spaces[space_name] = space
    return ledger


def normalized_chat_filename(record: dict) -> str:
    message_name = sanitize_filename(str(record.get("chat_message_name", "")), fallback="chat-message")
    return f"chat__{message_name}.md"


def normalized_task_filename(record: dict) -> str:
    message_name = sanitize_filename(str(record.get("chat_message_name", "")), fallback="chat-message")
    return f"task__chat__{message_name}.md"


def write_chat_record(path: Path, record: dict) -> bool:
    if path.exists():
        return False
    body = str(record.get("text", "")).strip()
    lines = [
        "---",
        f'chat_message_name: "{quote_meta(record.get("chat_message_name", ""))}"',
        f'chat_space: "{quote_meta(record.get("chat_space", ""))}"',
        f'sender_name: "{quote_meta(record.get("sender_name", ""))}"',
        f'sender_display_name: "{quote_meta(record.get("sender_display_name", ""))}"',
        f'created_at: "{quote_meta(record.get("create_time", ""))}"',
        'classification: "task"',
        "requires_response: true",
        f'triaged_at: "{quote_meta(utc_now_iso())}"',
        "---",
        "",
        "## Raw Chat Message",
        "",
        body if body else "_No chat text parsed._",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return True


def write_task_record(path: Path, record: dict) -> tuple[bool, str]:
    message_name = str(record.get("chat_message_name", ""))
    thread_key = str(record.get("chat_space", ""))
    task_id = next_task_id(message_name, thread_key)
    if path.exists():
        return False, task_id

    body = str(record.get("text", "")).strip()
    task_title = compact_whitespace(body)[:72] or "Google Chat request"
    now = utc_now_iso()
    lines = [
        "---",
        f'task_id: "{quote_meta(task_id)}"',
        'status: "queued"',
        'priority: "normal"',
        f'source_message_id: "{quote_meta(message_name)}"',
        f'source_uid: "{quote_meta(message_name)}"',
        f'source_from: "google_chat:{quote_meta(record.get("sender_name", ""))}"',
        f'source_subject: "{quote_meta(task_title)}"',
        f'thread_key: "{quote_meta(thread_key)}"',
        f'chat_message_name: "{quote_meta(message_name)}"',
        f'chat_space: "{quote_meta(record.get("chat_space", ""))}"',
        f'chat_sender_name: "{quote_meta(record.get("sender_name", ""))}"',
        'source_kind: "google_chat"',
        'reply_style: "natural"',
        f'queued_at: "{quote_meta(now)}"',
        f'updated_at: "{quote_meta(now)}"',
        "attempts: 0",
        'claimed_at: ""',
        'run_id: ""',
        'completed_at: ""',
        'snagged_at: ""',
        'last_error: ""',
        'result_path: ""',
        "---",
        "",
        f"# {task_title}",
        "",
        "## Requested Work",
        "",
        body if body else "_No chat text parsed._",
        "",
        "## Intake Notes",
        "",
        f"- Source channel: Google Chat",
        f"- Chat space: {record.get('chat_space', '')}",
        f"- Chat message: {message_name}",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return True, task_id


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"Chat fetch output not found: {input_path}")

    data = read_json(input_path, default={})
    messages = data.get("messages", [])
    if not isinstance(messages, list):
        messages = []

    chat_dir = Path(args.chat_dir)
    task_dir = Path(args.task_dir)
    ensure_dir(chat_dir)
    ensure_dir(task_dir)
    ledger_path = Path(args.ledger)
    ledger = load_ledger(ledger_path)

    normalized_count = 0
    tasks_created = 0
    skipped_ledger = 0
    for record in messages:
        if not isinstance(record, dict):
            continue
        message_name = str(record.get("chat_message_name", ""))
        if is_terminal_message(ledger, message_name):
            skipped_ledger += 1
            continue
        if write_chat_record(chat_dir / normalized_chat_filename(record), record):
            normalized_count += 1
        created, task_id = write_task_record(task_dir / normalized_task_filename(record), record)
        if created:
            tasks_created += 1
        ledger = upsert_message(ledger, record, status="queued", task_id=task_id)

    summary = {
        "triaged_at": utc_now_iso(),
        "source_file": str(input_path),
        "fetch_status": data.get("status", ""),
        "messages_in_payload": len(messages),
        "normalized_count": normalized_count,
        "tasks_created": tasks_created,
        "skipped_ledger": skipped_ledger,
    }
    write_json(Path(args.summary_output), summary)
    save_ledger(ledger_path, ledger)
    print(json.dumps(summary, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
