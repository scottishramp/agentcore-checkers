#!/usr/bin/env python3
"""Send a brief acknowledgment for newly triaged Chat messages.

Run immediately after triage in the email-sync workflow so Brian
gets instant feedback that his message was received, before the
runner picks it up and processes the full task.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import chat_api

SUMMARY_PATH = Path(".agentcore/state/chat-sync-summary.json")


def main() -> int:
    env_map = chat_api.load_env_file(".env")
    space_name = chat_api.default_space_name(env_map=env_map)

    if not SUMMARY_PATH.exists():
        print(json.dumps({"status": "no_summary", "acks_sent": 0}))
        return 0

    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    tasks_created = summary.get("tasks_created", 0)

    if tasks_created == 0:
        print(json.dumps({"status": "no_new_tasks", "acks_sent": 0}))
        return 0

    if not space_name:
        print(json.dumps({"status": "no_space", "acks_sent": 0}))
        return 0

    try:
        token = chat_api.access_token(env_map=env_map)
        if tasks_created == 1:
            text = "Got it — working on this now."
        else:
            text = f"Got {tasks_created} messages — working through them now."
        chat_api.send_message(token=token, space_name=space_name, text=text)
        print(json.dumps({"status": "sent", "acks_sent": 1, "tasks_created": tasks_created}))
    except chat_api.ChatApiError as err:
        print(json.dumps({"status": "error", "details": err.payload}), file=sys.stderr)
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
