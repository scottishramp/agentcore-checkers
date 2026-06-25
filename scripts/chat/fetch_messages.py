#!/usr/bin/env python3
"""Fetch new Google Chat messages from Brian's AgentCore DM."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import chat_api

DEFAULT_OUTPUT_PATH = ".agentcore/state/chat-fetch/latest.json"
DEFAULT_STATE_PATH = ".agentcore/state/chat-last-message.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch Google Chat DM messages.")
    parser.add_argument("--space", default="", help="Chat space name. Defaults to AGENTCORE_CHAT_DM_SPACE.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH, help="Output JSON path.")
    parser.add_argument("--state", default=DEFAULT_STATE_PATH, help="Last processed message state path.")
    parser.add_argument("--limit", type=int, default=50, help="Maximum messages to inspect.")
    parser.add_argument(
        "--bootstrap-window",
        type=int,
        default=0,
        help="Initial number of recent messages to inspect. Use 0 to mark existing history seen without queueing.",
    )
    return parser.parse_args()


def read_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def message_sort_key(message: dict) -> tuple[str, str]:
    return str(message.get("createTime", "")), str(message.get("name", ""))


def main() -> int:
    args = parse_args()
    env_map = chat_api.load_env_file(".env")
    output_path = Path(args.output)
    state_path = Path(args.state)
    space_name = (args.space or chat_api.default_space_name(env_map=env_map)).strip()
    self_user = chat_api.self_user_name(env_map=env_map)
    state = read_json(state_path, default={})
    last_seen_name = str(state.get("last_seen_message_name", ""))
    last_seen_create_time = str(state.get("last_seen_create_time", ""))

    if not space_name:
        summary = {
            "status": "skipped",
            "reason": "missing_chat_space",
            "messages": [],
            "space": "",
        }
        write_json(output_path, summary)
        print(json.dumps(summary, ensure_ascii=True))
        return 0

    try:
        token = chat_api.access_token(env_map=env_map)
        # Request newest-first. The Chat API defaults to oldest-first with
        # pagination, so once a space has more than `limit` messages the most
        # recent ones fall off page 1 and are never fetched. Ordering by
        # createTime desc keeps the latest (and successive) messages on page 1.
        payload = chat_api.list_messages(
            token=token,
            space_name=space_name,
            page_size=max(1, args.limit),
            order_by="createTime desc",
        )
    except chat_api.ChatApiError as err:
        status = "auth_scope_error" if chat_api.error_has_scope_issue(err.payload) else "chat_api_error"
        summary = {
            "status": status,
            "space": space_name,
            "messages": [],
            "error": err.payload,
        }
        write_json(output_path, summary)
        print(json.dumps(summary, ensure_ascii=True))
        return 0

    raw_messages = payload.get("messages", [])
    if not isinstance(raw_messages, list):
        raw_messages = []
    raw_messages = sorted(raw_messages, key=message_sort_key)
    newest = {"name": last_seen_name, "createTime": last_seen_create_time}
    if not last_seen_name:
        if args.bootstrap_window > 0:
            raw_messages = raw_messages[-args.bootstrap_window :]
        else:
            newest_message = raw_messages[-1] if raw_messages else {}
            newest = {
                "name": str(newest_message.get("name", "")),
                "createTime": str(newest_message.get("createTime", "")),
            }
            raw_messages = []

    new_messages = []
    for message in raw_messages:
        message_name = str(message.get("name", ""))
        create_time = str(message.get("createTime", ""))
        if last_seen_create_time and (create_time, message_name) <= (last_seen_create_time, last_seen_name):
            continue
        sender_name = str((message.get("sender") or {}).get("name", ""))
        if sender_name and sender_name == self_user:
            newest = {"name": message_name, "createTime": create_time}
            continue
        text = str(message.get("text", "")).strip()
        if not text:
            newest = {"name": message_name, "createTime": create_time}
            continue
        new_messages.append(
            {
                "chat_message_name": message_name,
                "chat_space": space_name,
                "sender_name": sender_name,
                "sender_display_name": str((message.get("sender") or {}).get("displayName", "")),
                "text": text,
                "create_time": create_time,
                "thread_name": str((message.get("thread") or {}).get("name", "")),
                "source_kind": "google_chat",
                "reply_style": "natural",
            }
        )
        newest = {"name": message_name, "createTime": create_time}

    if newest.get("name"):
        write_json(
            state_path,
            {
                "space": space_name,
                "last_seen_message_name": newest["name"],
                "last_seen_create_time": newest["createTime"],
            },
        )

    summary = {
        "status": "ok",
        "space": space_name,
        "self_user_name": self_user,
        "messages_in_payload": len(raw_messages),
        "new_messages": len(new_messages),
        "messages": new_messages,
    }
    write_json(output_path, summary)
    print(json.dumps(summary, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
