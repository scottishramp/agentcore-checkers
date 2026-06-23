#!/usr/bin/env python3
"""Send proactive scheduled Chat messages when they are due.

Reads scheduled_messages.json for recurring message definitions,
checks a state file to avoid duplicates, and sends any that are
overdue within their configured window.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import chat_api

SCRIPT_DIR = Path(__file__).resolve().parent
SCHEDULE_PATH = SCRIPT_DIR / "scheduled_messages.json"
STATE_PATH = Path(".agentcore/state/scheduled-messages-state.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send scheduled proactive Chat messages.")
    parser.add_argument("--schedule", default=str(SCHEDULE_PATH), help="Path to schedule JSON.")
    parser.add_argument("--state", default=str(STATE_PATH), help="Path to state JSON tracking last sends.")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be sent without sending.")
    return parser.parse_args()


def read_json(path: Path, default: dict | list) -> dict | list:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def is_due(schedule: dict, tz: ZoneInfo, window_minutes: int, last_sent_utc: str | None) -> bool:
    """Check if a message is due: current local time is past the scheduled time
    but within the delivery window, and it hasn't been sent today already."""
    now_local = datetime.now(tz)
    target_today = now_local.replace(
        hour=schedule["hour"],
        minute=schedule.get("minute", 0),
        second=0,
        microsecond=0,
    )
    window_end = target_today + timedelta(minutes=window_minutes)

    if not (target_today <= now_local <= window_end):
        return False

    if last_sent_utc:
        try:
            last_sent = datetime.fromisoformat(last_sent_utc)
            last_sent_local = last_sent.astimezone(tz)
            if last_sent_local.date() == now_local.date():
                return False
        except (ValueError, TypeError):
            pass

    return True


def main() -> int:
    args = parse_args()
    env_map = chat_api.load_env_file(".env")

    schedule_path = Path(args.schedule)
    state_path = Path(args.state)

    if not schedule_path.exists():
        print(json.dumps({"status": "no_schedule_file", "path": str(schedule_path)}))
        return 0

    schedule_data = read_json(schedule_path, {})
    tz_name = schedule_data.get("timezone", "America/Chicago")
    tz = ZoneInfo(tz_name)
    messages = schedule_data.get("messages", [])

    state = read_json(state_path, {})
    if not isinstance(state, dict):
        state = {}

    space_name = chat_api.default_space_name(env_map=env_map)
    if not space_name:
        print(json.dumps({"status": "skipped", "reason": "no_chat_space"}))
        return 0

    sent_count = 0
    results = []

    for msg in messages:
        msg_id = msg.get("id", "")
        if not msg.get("enabled", True):
            continue
        if not msg_id:
            continue

        last_sent_utc = state.get(msg_id, {}).get("last_sent_utc")
        window_minutes = msg.get("window_minutes", 90)

        if not is_due(msg["schedule"], tz, window_minutes, last_sent_utc):
            continue

        variants = msg.get("variants", [])
        if variants:
            day_seed = datetime.now(tz).strftime("%Y-%m-%d") + msg_id
            idx = int(hashlib.md5(day_seed.encode()).hexdigest(), 16) % len(variants)
            text = variants[idx].strip()
        else:
            text = msg.get("text", "").strip()
        if not text:
            continue

        if args.dry_run:
            results.append({"id": msg_id, "status": "would_send", "text": text})
            continue

        try:
            token = chat_api.access_token(env_map=env_map)
            sent = chat_api.send_message(token=token, space_name=space_name, text=text)
            now_utc = datetime.now(timezone.utc).isoformat()
            state[msg_id] = {
                "last_sent_utc": now_utc,
                "last_message_name": sent.get("name", ""),
            }
            results.append({"id": msg_id, "status": "sent", "message_name": sent.get("name", "")})
            sent_count += 1
        except chat_api.ChatApiError as err:
            results.append({"id": msg_id, "status": "error", "details": err.payload})

    write_json(state_path, state)

    summary = {
        "status": "ok",
        "timezone": tz_name,
        "messages_checked": len(messages),
        "messages_sent": sent_count,
        "dry_run": args.dry_run,
        "results": results,
    }
    print(json.dumps(summary, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
