#!/usr/bin/env python3
"""Create a temporary Chat-origin task from a fast-router repository_dispatch payload."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
EMAIL_DIR = SCRIPT_DIR.parent / "email"
if str(EMAIL_DIR) not in sys.path:
    sys.path.insert(0, str(EMAIL_DIR))

from common import compact_whitespace, ensure_dir, sanitize_filename, utc_now_iso, write_json  # noqa: E402
from task_queue import next_task_id  # noqa: E402

DEFAULT_OUTPUT = ".agentcore/state/router-task.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a task file from fast-router payload JSON.")
    parser.add_argument("--payload-json", default="", help="Raw JSON payload. Defaults to ROUTER_PAYLOAD_JSON.")
    parser.add_argument("--task-dir", default="agentcore/inbox/tasks", help="Task output directory.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Machine-readable result path.")
    return parser.parse_args()


def quote_meta(value) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"')


def load_payload(raw: str) -> dict:
    text = raw or os.getenv("ROUTER_PAYLOAD_JSON", "")
    if not text:
        raise ValueError("Missing router payload JSON.")
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("Router payload must be a JSON object.")
    return payload


def main() -> int:
    args = parse_args()
    payload = load_payload(args.payload_json)
    task_dir = Path(args.task_dir)
    ensure_dir(task_dir)

    original_text = str(payload.get("original_text") or payload.get("async_task_body") or "").strip()
    route = str(payload.get("route", "task")).strip() or "task"
    chat_message_name = str(payload.get("chat_message_name", "")).strip()
    chat_space = str(payload.get("chat_space", "")).strip()
    sender_name = str(payload.get("chat_sender_name", "")).strip()
    conversation_key = str(payload.get("conversation_key", chat_space or sender_name or "router")).strip()
    source_uid = chat_message_name or f"router-{sanitize_filename(conversation_key)}-{utc_now_iso()}"
    task_id = next_task_id(source_uid, conversation_key)
    title = compact_whitespace(str(payload.get("async_task_title", ""))) or (
        "Ingest Google Chat update" if route == "knowledge_update" else "Handle Google Chat task"
    )
    safe = sanitize_filename(task_id, fallback="router-task")
    task_file = task_dir / f"task__router__{safe}.md"
    now = utc_now_iso()
    body = str(payload.get("async_task_body", "")).strip() or original_text or "_No message text provided._"

    lines = [
        "---",
        f'task_id: "{quote_meta(task_id)}"',
        'status: "in_progress"',
        'priority: "normal"',
        f'source_message_id: "{quote_meta(chat_message_name or source_uid)}"',
        f'source_uid: "{quote_meta(source_uid)}"',
        f'source_from: "google_chat:{quote_meta(sender_name)}"',
        f'source_subject: "{quote_meta(title)}"',
        f'thread_key: "{quote_meta(conversation_key)}"',
        f'chat_message_name: "{quote_meta(chat_message_name)}"',
        f'chat_space: "{quote_meta(chat_space)}"',
        f'chat_sender_name: "{quote_meta(sender_name)}"',
        'source_kind: "google_chat"',
        'reply_style: "natural"',
        f'queued_at: "{quote_meta(now)}"',
        f'updated_at: "{quote_meta(now)}"',
        "attempts: 1",
        f'claimed_at: "{quote_meta(now)}"',
        f'run_id: "{quote_meta(os.getenv("GITHUB_RUN_ID", ""))}"',
        'completed_at: ""',
        'snagged_at: ""',
        'last_error: ""',
        'result_path: ""',
        "---",
        "",
        f"# {title}",
        "",
        "## Requested Work",
        "",
        body,
        "",
        "## Router Context",
        "",
        f"- Route: {route}",
        f"- Fast response already sent: {payload.get('response', '')}",
        f"- Source channel: Google Chat HTTP endpoint",
        f"- Chat space: {chat_space}",
        f"- Chat message: {chat_message_name}",
        f"- Sender: {sender_name or payload.get('sender_display_name', '')}",
        "",
        "## Instructions",
        "",
        "- If this is a knowledge update, ingest it holistically into the appropriate AgentCore knowledge pages.",
        "- If this is a task, complete the useful repo-backed work and send a concise natural follow-up.",
        "- Preserve sensitive source content boundaries and update hot-cache/log/index only when appropriate.",
        "",
    ]
    task_file.write_text("\n".join(lines), encoding="utf-8")
    result = {
        "status": "created",
        "task_file": str(task_file),
        "task_id": task_id,
        "source_kind": "google_chat",
        "route": route,
    }
    write_json(Path(args.output), result)
    print(json.dumps(result, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
