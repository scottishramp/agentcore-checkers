#!/usr/bin/env python3
"""Send proactive scheduled Telegram messages when they are due."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from send_task_response import send_message  # noqa: E402

SCHEDULE_PATH = SCRIPT_DIR / "scheduled_messages.json"
STATE_PATH = Path("agentcore/knowledge/communications/scheduled-messages-state.json")

STATE_KEY_ALIASES = {
    "food-checkin-lunch": "food-checkin-midday",
    "food-checkin-dinner": "food-checkin-evening",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send scheduled proactive Telegram messages.")
    parser.add_argument("--schedule", default=str(SCHEDULE_PATH), help="Schedule JSON path.")
    parser.add_argument("--state", default=str(STATE_PATH), help="Dedup state JSON path.")
    parser.add_argument("--dry-run", action="store_true", help="Print without sending.")
    return parser.parse_args()


def read_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def chat_ids() -> list[str]:
    raw = (
        __import__("os").getenv("AGENTCORE_TELEGRAM_NOTIFY_CHAT_IDS", "").strip()
        or __import__("os").getenv("AGENTCORE_TELEGRAM_ALLOWED_USER_IDS", "").strip()
    )
    return [part.strip() for part in raw.split(",") if part.strip()]


def migrate_state_keys(state: dict) -> dict:
    for old_key, new_key in STATE_KEY_ALIASES.items():
        old_entry = state.get(old_key)
        if not isinstance(old_entry, dict):
            continue
        new_entry = state.get(new_key)
        if not isinstance(new_entry, dict):
            state[new_key] = old_entry
        del state[old_key]
    return state


def is_due(schedule: dict, tz: ZoneInfo, window_minutes: int, last_sent_utc: str | None) -> bool:
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
            last_sent_local = datetime.fromisoformat(last_sent_utc).astimezone(tz)
            if last_sent_local.date() == now_local.date():
                return False
        except (ValueError, TypeError):
            pass
    return True


def main() -> int:
    args = parse_args()
    schedule_data = read_json(Path(args.schedule), {})
    tz = ZoneInfo(schedule_data.get("timezone", "America/Chicago"))
    messages = schedule_data.get("messages", [])
    state = migrate_state_keys(read_json(Path(args.state), {}))
    targets = chat_ids()
    if not targets:
        print(json.dumps({"status": "skipped", "reason": "no_telegram_chat_ids"}, ensure_ascii=True))
        return 0

    sent_count = 0
    results = []
    for msg in messages:
        msg_id = msg.get("id", "")
        if not msg.get("enabled", True) or not msg_id:
            continue
        if not is_due(msg["schedule"], tz, msg.get("window_minutes", 90), state.get(msg_id, {}).get("last_sent_utc")):
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
        message_ids = []
        for chat_id in targets:
            sent = send_message(chat_id, text)
            message_ids.append(str(((sent.get("result") or {}) if isinstance(sent, dict) else {}).get("message_id", "")))
        state[msg_id] = {
            "last_sent_utc": datetime.now(timezone.utc).isoformat(),
            "telegram_message_ids": message_ids,
        }
        results.append({"id": msg_id, "status": "sent", "targets": targets})
        sent_count += 1

    if not args.dry_run:
        write_json(Path(args.state), state)

    summary = {
        "status": "ok",
        "messages_checked": len(messages),
        "messages_sent": sent_count,
        "dry_run": args.dry_run,
        "results": results,
    }
    print(json.dumps(summary, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
