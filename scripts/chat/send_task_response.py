#!/usr/bin/env python3
"""Send queued task results back to Google Chat for Chat-origin tasks."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
EMAIL_DIR = SCRIPT_DIR.parent / "email"
if str(EMAIL_DIR) not in sys.path:
    sys.path.insert(0, str(EMAIL_DIR))

import chat_api  # noqa: E402
from common import compact_whitespace, read_json, utc_now_iso  # noqa: E402
from task_queue import load_task  # noqa: E402

DEFAULT_RESULT_PATH = ".agentcore/state/task-run-result.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send task status to Google Chat.")
    parser.add_argument("--task-file", required=True, help="Task file path.")
    parser.add_argument("--status", required=True, choices=("done", "snag"), help="Task status.")
    parser.add_argument("--result-json", default=DEFAULT_RESULT_PATH, help="Runner result JSON.")
    return parser.parse_args()


def direct_done_body(summary: str) -> str:
    return (summary.strip() or "Done.") + "\n"


def direct_snag_body(summary: str, error: str) -> str:
    detail = summary or error or "The async task did not complete cleanly."
    return (
        "I hit a snag while trying to handle that Chat message.\n\n"
        f"{detail}\n\n"
        "Send any extra context here and I will try again.\n"
    )


def main() -> int:
    args = parse_args()
    task = load_task(Path(args.task_file))
    if str(task.meta.get("source_kind", "")).strip().lower() != "google_chat":
        payload = {"status": "skipped", "reason": "not_google_chat_task", "task_file": args.task_file}
        print(json.dumps(payload, ensure_ascii=True))
        return 0

    result = read_json(Path(args.result_json), default={})
    summary = str(result.get("summary", "")).strip()
    error = compact_whitespace(str(result.get("error", "")))
    body = direct_done_body(summary) if args.status == "done" else direct_snag_body(compact_whitespace(summary), error)
    space_name = str(task.meta.get("chat_space", "")).strip()
    if not space_name:
        raise ValueError("Chat task is missing chat_space metadata.")

    env_map = chat_api.load_env_file(".env")
    token = chat_api.access_token(env_map=env_map)
    sent = chat_api.send_message(token=token, space_name=space_name, text=body)
    payload = {
        "status": "sent",
        "task_file": args.task_file,
        "task_id": str(task.meta.get("task_id", "")),
        "notify_status": args.status,
        "chat_space": space_name,
        "source_chat_message_name": str(task.meta.get("chat_message_name", "")),
        "chat_message_name": str(sent.get("name", "")),
        "sent_at": utc_now_iso(),
    }
    print(json.dumps(payload, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
