#!/usr/bin/env python3
"""Normalize fetched Telegram records and enqueue async tasks for knowledge/task routes."""

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

DEFAULT_INPUT_PATH = ".agentcore/state/telegram-fetch/latest.json"
DEFAULT_SUMMARY_PATH = ".agentcore/state/telegram-sync-summary.json"
DEFAULT_LEDGER_PATH = "agentcore/knowledge/communications/telegram-thread-ledger.json"
ACTIONABLE_ROUTES = {"knowledge_update", "task"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Triage Telegram inbox messages into repo records and tasks.")
    parser.add_argument("--input", default=DEFAULT_INPUT_PATH, help="Fetch output JSON.")
    parser.add_argument("--telegram-dir", default="agentcore/inbox/telegram", help="Telegram inbox markdown dir.")
    parser.add_argument("--task-dir", default="agentcore/inbox/tasks", help="Task queue dir.")
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_PATH, help="Machine-readable summary path.")
    parser.add_argument("--ledger", default=DEFAULT_LEDGER_PATH, help="Telegram idempotency ledger.")
    return parser.parse_args()


def read_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def quote_meta(value) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"')


def load_ledger(path: Path) -> dict:
    payload = read_json(path, default={"version": 1, "messages": {}})
    if not isinstance(payload, dict):
        payload = {"version": 1, "messages": {}}
    payload.setdefault("version", 1)
    payload.setdefault("messages", {})
    return payload


def save_ledger(path: Path, payload: dict) -> None:
    payload["updated_at"] = utc_now_iso()
    write_json(path, payload)


def normalized_telegram_filename(message_id: str) -> str:
    safe = sanitize_filename(message_id, fallback="telegram-message")
    return f"telegram__{safe}.md"


def normalized_task_filename(message_id: str) -> str:
    safe = sanitize_filename(message_id, fallback="telegram-message")
    return f"task__telegram__{safe}.md"


def record_media(record: dict) -> dict | None:
    media = record.get("media")
    return media if isinstance(media, dict) and media.get("telegram_file_id") else None


def write_telegram_record(path: Path, record: dict) -> bool:
    if path.exists():
        return False
    body = str(record.get("text", "")).strip()
    media = record_media(record)
    lines = [
        "---",
        f'message_id: "{quote_meta(record.get("message_id", ""))}"',
        f'telegram_chat_id: "{quote_meta(record.get("telegram_chat_id", ""))}"',
        f'telegram_user_id: "{quote_meta(record.get("telegram_user_id", ""))}"',
        f'telegram_username: "{quote_meta(record.get("telegram_username", ""))}"',
        f'sender_display_name: "{quote_meta(record.get("sender_display_name", ""))}"',
        f'conversation_key: "{quote_meta(record.get("conversation_key", ""))}"',
        f'route: "{quote_meta(record.get("route", ""))}"',
        f'received_at: "{quote_meta(record.get("received_at", ""))}"',
        f'triaged_at: "{quote_meta(utc_now_iso())}"',
    ]
    if media:
        lines.extend(
            [
                f'media_type: "{quote_meta(media.get("type", "photo"))}"',
                f'telegram_file_id: "{quote_meta(media.get("telegram_file_id", ""))}"',
                f'mime_type: "{quote_meta(media.get("mime_type", ""))}"',
                f'file_size: "{quote_meta(media.get("file_size", ""))}"',
            ]
        )
    photo_label = str(record.get("photo_label", "") or (media or {}).get("photo_label", "")).strip()
    photo_description = compact_whitespace(
        str(record.get("photo_description", "") or (media or {}).get("photo_description", ""))
    )
    if photo_label:
        lines.append(f'photo_label: "{quote_meta(photo_label)}"')
    if photo_description:
        lines.append(f'photo_description: "{quote_meta(photo_description)}"')
    lines.extend(
        [
            "---",
            "",
            "## Raw Telegram Message",
            "",
            body if body else "_No message text parsed._",
            "",
            "## Fast Router Reply",
            "",
            str(record.get("fast_response", "")).strip() or "_No fast reply recorded._",
            "",
        ]
    )
    if photo_description:
        lines.extend(
            [
                "## Fast-agent Photo Description",
                "",
                photo_description,
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")
    return True


def write_task_record(path: Path, record: dict) -> tuple[bool, str]:
    message_id = str(record.get("message_id", "")).strip()
    thread_key = str(record.get("conversation_key", "")).strip() or str(record.get("telegram_chat_id", ""))
    task_id = next_task_id(message_id, thread_key)
    if path.exists():
        return False, task_id

    body = str(record.get("async_task_body", "") or record.get("text", "")).strip()
    title = compact_whitespace(str(record.get("async_task_title", ""))) or compact_whitespace(body)[:72] or "Telegram request"
    photo_label = str(record.get("photo_label", "") or (record_media(record) or {}).get("photo_label", "")).strip()
    now = utc_now_iso()
    lines = [
        "---",
        f'task_id: "{quote_meta(task_id)}"',
        'status: "queued"',
        'priority: "normal"',
        f'source_message_id: "{quote_meta(message_id)}"',
        f'source_uid: "{quote_meta(message_id)}"',
        f'source_from: "telegram:{quote_meta(record.get("telegram_user_id", ""))}"',
        f'source_subject: "{quote_meta(title)}"',
        f'thread_key: "{quote_meta(thread_key)}"',
        f'telegram_chat_id: "{quote_meta(record.get("telegram_chat_id", ""))}"',
        f'telegram_user_id: "{quote_meta(record.get("telegram_user_id", ""))}"',
        f'telegram_username: "{quote_meta(record.get("telegram_username", ""))}"',
        'source_kind: "telegram"',
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
    ]
    if photo_label:
        lines.append(f'photo_label: "{quote_meta(photo_label)}"')
    lines.extend(
        [
            "---",
            "",
            f"# {title}",
            "",
            "## Requested Work",
            "",
            body if body else "_No message text parsed._",
            "",
            "## Intake Notes",
            "",
            f"- Source channel: Telegram",
            f"- Fast-router route: {record.get('route', '')}",
            f"- Message id: {message_id}",
        ]
    )
    media = record_media(record)
    if media:
        lines.extend(
            [
                f"- Media type: {media.get('type', 'photo')}",
                f"- Telegram file id: {media.get('telegram_file_id', '')}",
            ]
        )
        if photo_label:
            lines.append(f"- Photo label: {photo_label}")
        lines.extend(
            [
                "- Drive link: pending materialization",
                "",
            ]
        )
    else:
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return True, task_id


def is_actionable(record: dict, route: str) -> bool:
    return route in ACTIONABLE_ROUTES or bool(record_media(record))


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"Telegram fetch output not found: {input_path}")

    data = read_json(input_path, default={})
    messages = data.get("messages", []) if isinstance(data, dict) else []
    telegram_dir = Path(args.telegram_dir)
    task_dir = Path(args.task_dir)
    ensure_dir(telegram_dir)
    ensure_dir(task_dir)
    ledger = load_ledger(Path(args.ledger))

    created_records = 0
    created_tasks = 0
    skipped = 0

    for record in messages:
        if not isinstance(record, dict):
            continue
        message_id = str(record.get("message_id", "")).strip()
        if not message_id:
            continue
        if message_id in ledger.get("messages", {}):
            skipped += 1
            continue

        route = str(record.get("route", "lightweight_answer")).strip()
        telegram_path = telegram_dir / normalized_telegram_filename(message_id)
        if write_telegram_record(telegram_path, record):
            created_records += 1

        task_id = ""
        task_status = "ignored"
        if is_actionable(record, route):
            task_path = task_dir / normalized_task_filename(message_id)
            created, task_id = write_task_record(task_path, record)
            if created:
                created_tasks += 1
                task_status = "queued"
            else:
                task_status = "already_queued"
        else:
            task_status = "no_task"

        ledger.setdefault("messages", {})[message_id] = {
            "message_id": message_id,
            "route": route,
            "status": task_status,
            "task_id": task_id,
            "telegram_chat_id": str(record.get("telegram_chat_id", "")),
            "updated_at": utc_now_iso(),
        }

    save_ledger(Path(args.ledger), ledger)
    summary = {
        "status": "ok",
        "input_count": len(messages),
        "created_records": created_records,
        "created_tasks": created_tasks,
        "skipped_duplicates": skipped,
    }
    write_json(Path(args.summary_output), summary)
    print(json.dumps(summary, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
