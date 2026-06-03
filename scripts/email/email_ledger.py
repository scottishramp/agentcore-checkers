"""Tiny idempotency ledger for email thread processing."""

from __future__ import annotations

from pathlib import Path

from common import read_json, utc_now_iso, write_json

DEFAULT_LEDGER_PATH = "agentcore/knowledge/communications/email-thread-ledger.json"


def load_ledger(path: str = DEFAULT_LEDGER_PATH) -> dict:
    payload = read_json(Path(path), default={"version": 1, "messages": {}, "threads": {}})
    if not isinstance(payload, dict):
        payload = {"version": 1, "messages": {}, "threads": {}}
    payload.setdefault("version", 1)
    payload.setdefault("messages", {})
    payload.setdefault("threads", {})
    return payload


def save_ledger(payload: dict, path: str = DEFAULT_LEDGER_PATH) -> None:
    payload["updated_at"] = utc_now_iso()
    write_json(Path(path), payload)


def message_status(payload: dict, gmail_message_id: str) -> str:
    if not gmail_message_id:
        return ""
    item = (payload.get("messages") or {}).get(gmail_message_id, {})
    return str(item.get("status", "")) if isinstance(item, dict) else ""


def is_terminal_message(payload: dict, gmail_message_id: str) -> bool:
    return message_status(payload, gmail_message_id) in {"done", "snag", "ignored", "source_only"}


def upsert_message(
    payload: dict,
    *,
    gmail_message_id: str,
    gmail_thread_id: str,
    rfc_message_id: str,
    status: str,
    task_id: str = "",
    response_gmail_message_id: str = "",
    note: str = "",
) -> dict:
    if not gmail_message_id:
        return payload
    now = utc_now_iso()
    messages = payload.setdefault("messages", {})
    existing = messages.get(gmail_message_id, {}) if isinstance(messages.get(gmail_message_id), dict) else {}
    existing.update(
        {
            "gmail_message_id": gmail_message_id,
            "gmail_thread_id": gmail_thread_id,
            "rfc_message_id": rfc_message_id,
            "status": status,
            "task_id": task_id or existing.get("task_id", ""),
            "response_gmail_message_id": response_gmail_message_id or existing.get("response_gmail_message_id", ""),
            "note": note or existing.get("note", ""),
            "updated_at": now,
        }
    )
    existing.setdefault("created_at", now)
    messages[gmail_message_id] = existing

    if gmail_thread_id:
        threads = payload.setdefault("threads", {})
        thread = threads.get(gmail_thread_id, {}) if isinstance(threads.get(gmail_thread_id), dict) else {}
        thread.update(
            {
                "gmail_thread_id": gmail_thread_id,
                "latest_client_message_id": gmail_message_id,
                "latest_status": status,
                "latest_task_id": task_id or thread.get("latest_task_id", ""),
                "latest_response_gmail_message_id": response_gmail_message_id
                or thread.get("latest_response_gmail_message_id", ""),
                "updated_at": now,
            }
        )
        thread.setdefault("created_at", now)
        threads[gmail_thread_id] = thread
    return payload
