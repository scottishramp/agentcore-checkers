#!/usr/bin/env python3
"""Pull pending Telegram messages from Upstash into a fetch JSON file."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from redis_client import TELEGRAM_INBOX_KEY, redis_command  # noqa: E402

DEFAULT_OUTPUT = ".agentcore/state/telegram-fetch/latest.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch pending Telegram inbox messages from Redis.")
    parser.add_argument("--limit", type=int, default=100, help="Max messages to pull.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output JSON path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    end = max(0, args.limit - 1)
    fetched = redis_command(["LRANGE", TELEGRAM_INBOX_KEY, "0", str(end)])
    if not fetched.get("configured"):
        payload = {"status": "skipped", "reason": "redis_not_configured", "messages": []}
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        print(json.dumps(payload, ensure_ascii=True))
        return 0

    raw_items = fetched.get("result") or []
    messages = []
    for item in raw_items:
        try:
            messages.append(json.loads(item))
        except json.JSONDecodeError:
            continue

    if messages:
        redis_command(["LTRIM", TELEGRAM_INBOX_KEY, str(len(raw_items)), "-1"])

    payload = {
        "status": "ok",
        "count": len(messages),
        "messages": messages,
    }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ok", "count": len(messages)}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
