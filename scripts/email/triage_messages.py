#!/usr/bin/env python3
"""Normalize fetched email records and enqueue task files."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from common import (
    compact_whitespace,
    ensure_dir,
    make_thread_key,
    read_json,
    sanitize_filename,
    utc_now_iso,
    write_json,
)
from email_ledger import is_terminal_message, load_ledger, save_ledger, upsert_message
from task_queue import next_task_id


DEFAULT_INPUT_PATH = ".agentcore/state/email-fetch/latest.json"
DEFAULT_SUMMARY_PATH = ".agentcore/state/email-sync-summary.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Classify and store fetched inbox emails.")
    parser.add_argument("--input", default=DEFAULT_INPUT_PATH, help="Path to fetch output JSON.")
    parser.add_argument("--email-dir", default="agentcore/inbox/email", help="Markdown output directory for email records.")
    parser.add_argument("--task-dir", default="agentcore/inbox/tasks", help="Markdown output directory for task queue records.")
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_PATH, help="Path for machine-readable triage summary.")
    parser.add_argument(
        "--ledger",
        default="agentcore/knowledge/communications/email-thread-ledger.json",
        help="Durable message/thread idempotency ledger.",
    )
    return parser.parse_args()


TASK_HINTS = (
    "please",
    "just",
    "implement",
    "build",
    "create",
    "fix",
    "set up",
    "start",
    "ship",
    "deploy",
    "work on",
)

QUESTION_HINTS = ("?", "can you", "could you", "what", "how", "when", "why", "should we")
ANSWER_HINTS = ("yes", "no", "approved", "sounds good", "do this", "that works")
UPDATE_HINTS = ("fyi", "for context", "status", "update", "heads up")
FORWARD_MARKERS = (
    "---------- forwarded message ---------",
    "-----original message-----",
    "begin forwarded message:",
    "forwarded message",
)


def _forward_start_index(body: str) -> int:
    lowered = body.lower()
    indexes = [lowered.find(marker) for marker in FORWARD_MARKERS if lowered.find(marker) >= 0]
    return min(indexes) if indexes else -1


def _has_user_instruction_before_forward(body: str) -> bool:
    forward_idx = _forward_start_index(body)
    if forward_idx < 0:
        return False
    preface = compact_whitespace(body[:forward_idx])
    if not preface:
        return False
    if len(preface) < 8:
        return False
    return True


def is_forward_only(subject: str, body: str) -> bool:
    subject_l = subject.lower().strip()
    forward_idx = _forward_start_index(body)
    looks_forwarded = subject_l.startswith(("fwd:", "fw:")) or forward_idx >= 0
    if not looks_forwarded:
        return False
    return not _has_user_instruction_before_forward(body)


def classify_message(subject: str, body: str) -> str:
    haystack = f"{subject}\n{body}".lower()
    normalized = compact_whitespace(haystack)

    if is_forward_only(subject, body):
        return "document_shared"
    if _has_user_instruction_before_forward(body):
        return "task"
    if any(hint in normalized for hint in TASK_HINTS):
        return "task"
    if any(hint in normalized for hint in QUESTION_HINTS):
        return "task"
    if subject.lower().startswith("re:") and any(hint in normalized for hint in ANSWER_HINTS):
        return "answer"
    if any(hint in normalized for hint in UPDATE_HINTS):
        return "update"
    # Direct trusted-client email should get an agent run/reply unless it is
    # clearly a forward-only source item.
    return "task"


def classify_record(record: dict) -> str:
    if record.get("trusted_share_notification"):
        return "document_shared"
    return classify_message(str(record.get("subject", "")), str(record.get("body_text", "")))


def requires_response(classification: str, subject: str, body: str) -> bool:
    text = f"{subject}\n{body}".lower()
    if classification in {"task", "question", "answer"}:
        return True
    if classification == "document_shared":
        return False
    return any(token in text for token in ("?", "please confirm", "let me know"))


def summarize_body(body: str, limit: int = 220) -> str:
    summary = compact_whitespace(body)
    return summary[:limit] + ("..." if len(summary) > limit else "")


def quote_meta(value) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"')


def normalized_email_filename(record: dict) -> str:
    uid = record.get("uid", "unknown")
    message_id = sanitize_filename(str(record.get("message_id", "")), fallback=f"uid-{uid}")
    return f"email__uid-{uid}__{message_id}.md"


def write_email_record(path: Path, record: dict, classification: str, needs_response: bool) -> bool:
    if path.exists():
        return False

    metadata = {
        "uid": record.get("uid", ""),
        "message_id": record.get("message_id", ""),
        "thread_key": make_thread_key(
            str(record.get("message_id", "")),
            str(record.get("subject", "")),
        ),
        "from_email": record.get("from_email", ""),
        "subject": record.get("subject", ""),
        "received_at": record.get("received_at", ""),
        "classification": classification,
        "requires_response": needs_response,
        "triaged_at": utc_now_iso(),
    }

    body = str(record.get("body_text", "")).strip()
    lines = [
        "---",
        f'uid: "{quote_meta(metadata["uid"])}"',
        f'message_id: "{quote_meta(metadata["message_id"])}"',
        f'thread_key: "{quote_meta(metadata["thread_key"])}"',
        f'gmail_message_id: "{quote_meta(record.get("gmail_message_id", ""))}"',
        f'gmail_thread_id: "{quote_meta(record.get("gmail_thread_id", ""))}"',
        f'source_kind: "{quote_meta(record.get("source_kind", ""))}"',
        f'from_email: "{quote_meta(metadata["from_email"])}"',
        f'subject: "{quote_meta(metadata["subject"])}"',
        f'received_at: "{quote_meta(metadata["received_at"])}"',
        f'classification: "{quote_meta(metadata["classification"])}"',
        f"requires_response: {str(metadata['requires_response']).lower()}",
        f'triaged_at: "{quote_meta(metadata["triaged_at"])}"',
        "---",
        "",
        "## Raw Body",
        "",
        body if body else "_No body content parsed._",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return True


def normalized_task_filename(record: dict) -> str:
    uid = record.get("uid", "unknown")
    subject_slug = sanitize_filename(str(record.get("subject", "")), fallback=f"uid-{uid}")
    return f"task__uid-{uid}__{subject_slug}.md"


def write_task_record(path: Path, record: dict) -> bool:
    if path.exists():
        return False

    body = str(record.get("body_text", "")).strip()
    task_title = compact_whitespace(str(record.get("subject", ""))) or f"Inbound task from uid {record.get('uid', 'unknown')}"
    body_summary = summarize_body(body)
    thread_key = str(record.get("thread_key", ""))
    task_id = next_task_id(str(record.get("uid", "")), thread_key)
    now = utc_now_iso()
    lines = [
        "---",
        f'task_id: "{quote_meta(task_id)}"',
        'status: "queued"',
        'priority: "normal"',
        f'source_message_id: "{quote_meta(record.get("message_id", ""))}"',
        f'source_uid: "{quote_meta(record.get("uid", ""))}"',
        f'source_from: "{quote_meta(record.get("from_email", ""))}"',
        f'source_subject: "{quote_meta(task_title)}"',
        f'thread_key: "{quote_meta(thread_key)}"',
        f'gmail_message_id: "{quote_meta(record.get("gmail_message_id", ""))}"',
        f'gmail_thread_id: "{quote_meta(record.get("gmail_thread_id", ""))}"',
        f'rfc_message_id: "{quote_meta(record.get("message_id", ""))}"',
        f'source_kind: "{quote_meta(record.get("source_kind", ""))}"',
        f'reply_style: "{quote_meta(record.get("reply_style", ""))}"',
        f'queued_at: "{quote_meta(now)}"',
        f'updated_at: "{quote_meta(now)}"',
        "attempts: 0",
        'claimed_at: ""',
        'run_id: ""',
        'completed_at: ""',
        'snagged_at: ""',
        'last_error: ""',
        'result_path: ""',
        "---",
        "",
        f"# {task_title}",
        "",
        "## Requested Work",
        "",
        body if body else "_No body content parsed._",
        "",
        "## Intake Notes",
        "",
        f"- Task ID: {task_id}",
        f"- Summary: {body_summary if body_summary else 'No summary available.'}",
        f"- Thread key: {thread_key}",
        "- Suggested next step: review and convert to active project task.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return True


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"Fetch output not found: {input_path}")

    data = read_json(input_path, default={})
    messages = data.get("messages", [])
    if not isinstance(messages, list):
        raise ValueError("Invalid fetch input: messages must be a list.")

    email_dir = Path(args.email_dir)
    task_dir = Path(args.task_dir)
    ensure_dir(email_dir)
    ensure_dir(task_dir)

    normalized_count = 0
    tasks_created = 0
    skipped_ledger = 0
    classifications: dict[str, int] = {
        "question": 0,
        "answer": 0,
        "task": 0,
        "update": 0,
        "document_shared": 0,
        "photo_batch": 0,
    }
    ledger = load_ledger(args.ledger)

    for item in messages:
        if not isinstance(item, dict):
            continue
        gmail_message_id = str(item.get("gmail_message_id", ""))
        gmail_thread_id = str(item.get("gmail_thread_id", ""))
        rfc_message_id = str(item.get("message_id", ""))
        if is_terminal_message(ledger, gmail_message_id):
            skipped_ledger += 1
            continue
        subject = str(item.get("subject", ""))
        body = str(item.get("body_text", ""))
        classification = classify_record(item)
        classifications[classification] = classifications.get(classification, 0) + 1
        needs_response = requires_response(classification, subject, body)

        email_filename = normalized_email_filename(item)
        email_path = email_dir / email_filename
        if write_email_record(email_path, item, classification, needs_response):
            normalized_count += 1

        should_queue_task = classification == "task" or bool(item.get("trusted_share_notification"))
        if should_queue_task:
            task_filename = normalized_task_filename(item)
            task_path = task_dir / task_filename
            if write_task_record(task_path, item):
                tasks_created += 1
                ledger = upsert_message(
                    ledger,
                    gmail_message_id=gmail_message_id,
                    gmail_thread_id=gmail_thread_id,
                    rfc_message_id=rfc_message_id,
                    status="queued",
                    task_id=next_task_id(str(item.get("uid", "")), str(item.get("thread_key", ""))),
                )
        elif classification == "document_shared":
            ledger = upsert_message(
                ledger,
                gmail_message_id=gmail_message_id,
                gmail_thread_id=gmail_thread_id,
                rfc_message_id=rfc_message_id,
                status="source_only",
                note="Forward-only or source-material email.",
            )

    summary = {
        "triaged_at": utc_now_iso(),
        "source_file": str(input_path),
        "messages_in_payload": len(messages),
        "normalized_count": normalized_count,
        "tasks_created": tasks_created,
        "skipped_ledger": skipped_ledger,
        "classifications": classifications,
    }
    write_json(Path(args.summary_output), summary)
    save_ledger(ledger, args.ledger)

    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
