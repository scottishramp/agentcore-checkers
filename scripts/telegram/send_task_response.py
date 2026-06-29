#!/usr/bin/env python3
"""Send queued task results back to Telegram for Telegram-origin tasks."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
EMAIL_DIR = SCRIPT_DIR.parent / "email"
if str(EMAIL_DIR) not in sys.path:
    sys.path.insert(0, str(EMAIL_DIR))

from common import compact_whitespace, read_json, utc_now_iso  # noqa: E402
from task_queue import load_task  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send task status to Telegram.")
    parser.add_argument("--task-file", required=True, help="Task file path.")
    parser.add_argument("--status", required=True, choices=("done", "snag"), help="Task status.")
    parser.add_argument("--result-json", default=".agentcore/state/task-run-result.json", help="Runner result JSON.")
    return parser.parse_args()


def bot_token() -> str:
    return (
        os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        or os.getenv("AGENTCORE_TELEGRAM_BOT_TOKEN", "").strip()
    )


def direct_done_body(summary: str) -> str:
    return (summary.strip() or "Done.") + "\n"


def direct_snag_body(summary: str, error: str) -> str:
    detail = summary or error or "The async task did not complete cleanly."
    return (
        "I hit a snag while trying to handle that Telegram message.\n\n"
        f"{detail}\n\n"
        "Send any extra context here and I will try again.\n"
    )


def send_message(chat_id: str, text: str) -> dict:
    token = bot_token()
    if not token:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN.")
    payload = json.dumps({"chat_id": chat_id, "text": text}, ensure_ascii=True).encode("utf-8")
    request = urllib.request.Request(
        url=f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw_error = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Telegram sendMessage failed: {exc.code} {raw_error}") from exc


def main() -> int:
    args = parse_args()
    task = load_task(Path(args.task_file))
    if str(task.meta.get("source_kind", "")).strip().lower() != "telegram":
        payload = {"status": "skipped", "reason": "not_telegram_task", "task_file": args.task_file}
        print(json.dumps(payload, ensure_ascii=True))
        return 0

    result = read_json(Path(args.result_json), default={})
    summary = str(result.get("summary", "")).strip()
    error = compact_whitespace(str(result.get("error", "")))
    if args.status == "done" and summary == "NO_TELEGRAM_REPLY":
        payload = {
            "status": "skipped",
            "reason": "no_telegram_reply_requested",
            "task_file": args.task_file,
            "task_id": str(task.meta.get("task_id", "")),
            "sent_at": utc_now_iso(),
        }
        print(json.dumps(payload, ensure_ascii=True))
        return 0
    body = direct_done_body(summary) if args.status == "done" else direct_snag_body(compact_whitespace(summary), error)
    chat_id = str(task.meta.get("telegram_chat_id", "")).strip()
    if not chat_id:
        raise ValueError("Telegram task is missing telegram_chat_id metadata.")

    sent = send_message(chat_id, body)
    payload = {
        "status": "sent",
        "task_file": args.task_file,
        "task_id": str(task.meta.get("task_id", "")),
        "notify_status": args.status,
        "telegram_chat_id": chat_id,
        "telegram_message_id": str(((sent.get("result") or {}) if isinstance(sent, dict) else {}).get("message_id", "")),
        "sent_at": utc_now_iso(),
    }
    print(json.dumps(payload, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
