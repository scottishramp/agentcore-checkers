#!/usr/bin/env python3
"""Read, label, archive, and trash mail in Brian's Gmail mailbox."""

from __future__ import annotations

import argparse
import json
import sys

import gmail_api
from common import load_env_file

ACCOUNT = gmail_api.ACCOUNT_BRIAN
EXPECTED_EMAIL = "briandherbert@gmail.com"
DEFAULT_AGENTCORE_LABEL = "AgentCore"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Operate on Brian Herbert's Gmail mailbox.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("profile", help="Show the authorized mailbox identity.")

    labels = sub.add_parser("labels", help="List, create, or ensure labels.")
    labels_sub = labels.add_subparsers(dest="labels_command", required=True)
    labels_sub.add_parser("list", help="List mailbox labels.")
    create = labels_sub.add_parser("create", help="Create a user label.")
    create.add_argument("--name", required=True, help="Label name, for example AgentCore/Receipts.")
    ensure = labels_sub.add_parser("ensure", help="Create a label if it does not already exist.")
    ensure.add_argument("--name", required=True, help="Label name to create or reuse.")

    messages = sub.add_parser("messages", help="List, read, label, archive, or trash messages.")
    messages_sub = messages.add_subparsers(dest="messages_command", required=True)
    listing = messages_sub.add_parser("list", help="List message metadata.")
    listing.add_argument("--query", default="", help="Gmail search query, for example newer_than:7d.")
    listing.add_argument("--max", type=int, default=20, help="Maximum messages to return.")
    get_msg = messages_sub.add_parser("get", help="Read one message.")
    get_msg.add_argument("--id", required=True, help="Gmail message id.")
    get_msg.add_argument("--body", action="store_true", help="Include the decoded text body.")
    modify = messages_sub.add_parser("modify", help="Add or remove labels on a message.")
    modify.add_argument("--id", required=True, help="Gmail message id.")
    modify.add_argument("--add-label", action="append", default=[], help="Label name or id to add. Repeatable.")
    modify.add_argument("--remove-label", action="append", default=[], help="Label name or id to remove. Repeatable.")
    archive = messages_sub.add_parser("archive", help="Remove the INBOX label from a message.")
    archive.add_argument("--id", required=True, help="Gmail message id.")
    trash = messages_sub.add_parser("trash", help="Move a message to Trash. Recoverable for 30 days.")
    trash.add_argument("--id", required=True, help="Gmail message id.")
    return parser.parse_args()


def _env_map() -> dict[str, str]:
    return load_env_file(".env")


def _print_json(payload: dict | list) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def _require_brian(env_map: dict[str, str]) -> dict:
    profile = gmail_api.get_profile(env_map=env_map, account=ACCOUNT)
    email = str(profile.get("emailAddress", "")).strip().lower()
    if email != EXPECTED_EMAIL:
        raise gmail_api.GmailApiError(
            f"Brian mailbox token is authorized as {email or 'unknown'}, expected {EXPECTED_EMAIL}."
        )
    return profile


def _summarize_message(message: dict) -> dict:
    headers = gmail_api.header_map(message)
    return {
        "id": message.get("id", ""),
        "thread_id": message.get("threadId", ""),
        "from": headers.get("from", ""),
        "to": headers.get("to", ""),
        "subject": headers.get("subject", ""),
        "date": headers.get("date", ""),
        "snippet": message.get("snippet", ""),
        "label_ids": message.get("labelIds", []),
    }


def cmd_profile(env_map: dict[str, str]) -> int:
    profile = _require_brian(env_map)
    labels = gmail_api.list_labels(env_map=env_map, account=ACCOUNT)
    agentcore_label = gmail_api.ensure_label(DEFAULT_AGENTCORE_LABEL, env_map=env_map, account=ACCOUNT)
    _print_json(
        {
            "email": profile.get("emailAddress", ""),
            "messages_total": profile.get("messagesTotal"),
            "threads_total": profile.get("threadsTotal"),
            "history_id": profile.get("historyId", ""),
            "label_count": len(labels),
            "agentcore_label": {
                "id": agentcore_label.get("id", ""),
                "name": agentcore_label.get("name", ""),
            },
        }
    )
    return 0


def cmd_labels_list(env_map: dict[str, str]) -> int:
    _require_brian(env_map)
    labels = gmail_api.list_labels(env_map=env_map, account=ACCOUNT)
    _print_json(
        [
            {
                "id": item.get("id", ""),
                "name": item.get("name", ""),
                "type": item.get("type", ""),
                "messages_total": item.get("messagesTotal"),
            }
            for item in sorted(labels, key=lambda row: str(row.get("name", "")).lower())
        ]
    )
    return 0


def cmd_labels_create(env_map: dict[str, str], name: str, ensure: bool) -> int:
    _require_brian(env_map)
    label = gmail_api.ensure_label(name, env_map=env_map, account=ACCOUNT) if ensure else gmail_api.create_label(
        name, env_map=env_map, account=ACCOUNT
    )
    _print_json({"id": label.get("id", ""), "name": label.get("name", ""), "type": label.get("type", "user")})
    return 0


def cmd_messages_list(env_map: dict[str, str], query: str, max_results: int) -> int:
    _require_brian(env_map)
    listing = gmail_api.list_messages(query=query, max_results=max_results, env_map=env_map, account=ACCOUNT)
    summaries = []
    for item in listing.get("messages") or []:
        message = gmail_api.get_message(str(item.get("id", "")), env_map=env_map, account=ACCOUNT, fmt="metadata")
        summaries.append(_summarize_message(message))
    _print_json(
        {
            "query": query,
            "result_size_estimate": listing.get("resultSizeEstimate"),
            "next_page_token": listing.get("nextPageToken", ""),
            "messages": summaries,
        }
    )
    return 0


def cmd_messages_get(env_map: dict[str, str], message_id: str, include_body: bool) -> int:
    _require_brian(env_map)
    fmt = "full" if include_body else "metadata"
    message = gmail_api.get_message(message_id, env_map=env_map, account=ACCOUNT, fmt=fmt)
    payload = _summarize_message(message)
    if include_body:
        payload["body_text"] = gmail_api.extract_text_body(message.get("payload") or {})
    _print_json(payload)
    return 0


def cmd_messages_modify(env_map: dict[str, str], message_id: str, add_labels: list[str], remove_labels: list[str]) -> int:
    _require_brian(env_map)
    catalog = gmail_api.list_labels(env_map=env_map, account=ACCOUNT)
    add_ids = [gmail_api.resolve_label_id(name, env_map=env_map, account=ACCOUNT, labels=catalog) for name in add_labels]
    remove_ids = [
        gmail_api.resolve_label_id(name, env_map=env_map, account=ACCOUNT, labels=catalog) for name in remove_labels
    ]
    updated = gmail_api.modify_message(
        message_id,
        add_label_ids=add_ids,
        remove_label_ids=remove_ids,
        env_map=env_map,
        account=ACCOUNT,
    )
    _print_json({"id": updated.get("id", message_id), "label_ids": updated.get("labelIds", [])})
    return 0


def cmd_messages_archive(env_map: dict[str, str], message_id: str) -> int:
    _require_brian(env_map)
    updated = gmail_api.archive_message(message_id, env_map=env_map, account=ACCOUNT)
    _print_json({"id": updated.get("id", message_id), "label_ids": updated.get("labelIds", []), "archived": True})
    return 0


def cmd_messages_trash(env_map: dict[str, str], message_id: str) -> int:
    _require_brian(env_map)
    updated = gmail_api.trash_message(message_id, env_map=env_map, account=ACCOUNT)
    _print_json({"id": updated.get("id", message_id), "label_ids": updated.get("labelIds", []), "trashed": True})
    return 0


def main() -> int:
    args = parse_args()
    env_map = _env_map()
    try:
        if args.command == "profile":
            return cmd_profile(env_map)
        if args.command == "labels":
            if args.labels_command == "list":
                return cmd_labels_list(env_map)
            return cmd_labels_create(env_map, args.name, ensure=args.labels_command == "ensure")
        if args.command == "messages":
            if args.messages_command == "list":
                return cmd_messages_list(env_map, args.query, args.max)
            if args.messages_command == "get":
                return cmd_messages_get(env_map, args.id, args.body)
            if args.messages_command == "modify":
                return cmd_messages_modify(env_map, args.id, args.add_label, args.remove_label)
            if args.messages_command == "archive":
                return cmd_messages_archive(env_map, args.id)
            if args.messages_command == "trash":
                return cmd_messages_trash(env_map, args.id)
        raise ValueError(f"Unsupported command: {args.command}")
    except (gmail_api.GmailApiError, ValueError, json.JSONDecodeError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
