"""Helpers for reading and writing task queue markdown records."""

from __future__ import annotations

import fcntl
import json
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from common import compact_whitespace, sanitize_filename, utc_now_iso

TASK_STATUS_QUEUED = "queued"
TASK_STATUS_IN_PROGRESS = "in_progress"
TASK_STATUS_DONE = "done"
TASK_STATUS_SNAG = "snag"

KNOWN_TASK_KEYS = [
    "task_id",
    "status",
    "priority",
    "source_message_id",
    "source_uid",
    "source_from",
    "source_subject",
    "thread_key",
    "queued_at",
    "updated_at",
    "attempts",
    "claimed_at",
    "run_id",
    "completed_at",
    "snagged_at",
    "last_error",
    "result_path",
]


@dataclass
class TaskRecord:
    path: Path
    meta: dict[str, str | int | bool]
    body: str

    @property
    def task_id(self) -> str:
        return str(self.meta.get("task_id", ""))

    @property
    def status(self) -> str:
        return str(self.meta.get("status", TASK_STATUS_QUEUED))


def _parse_scalar(raw: str):
    value = raw.strip()
    if value.startswith('"') and value.endswith('"') and len(value) >= 2:
        return value[1:-1].replace('\\"', '"')
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    if value.isdigit():
        return int(value)
    return value


def _serialize_scalar(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    text = str(value)
    escaped = text.replace('"', '\\"')
    return f'"{escaped}"'


def split_frontmatter(text: str) -> tuple[dict[str, object], str]:
    if not text.startswith("---\n"):
        return {}, text

    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text

    end_idx = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end_idx = idx
            break
    if end_idx is None:
        return {}, text

    meta: dict[str, object] = {}
    for line in lines[1:end_idx]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = _parse_scalar(value)

    remainder = "\n".join(lines[end_idx + 1 :]).lstrip("\n")
    if remainder and not remainder.endswith("\n"):
        remainder += "\n"
    return meta, remainder


def dump_frontmatter(meta: dict[str, object], body: str) -> str:
    ordered_keys = [key for key in KNOWN_TASK_KEYS if key in meta]
    ordered_keys.extend(sorted([key for key in meta.keys() if key not in KNOWN_TASK_KEYS]))
    lines = ["---"]
    for key in ordered_keys:
        lines.append(f"{key}: {_serialize_scalar(meta[key])}")
    lines.append("---")
    lines.append("")
    normalized_body = body if body.endswith("\n") else f"{body}\n"
    lines.append(normalized_body.rstrip("\n"))
    return "\n".join(lines).rstrip("\n") + "\n"


def load_task(path: Path) -> TaskRecord:
    raw = path.read_text(encoding="utf-8")
    meta, body = split_frontmatter(raw)
    return TaskRecord(path=path, meta=dict(meta), body=body)


def save_task(record: TaskRecord) -> None:
    record.path.write_text(dump_frontmatter(record.meta, record.body), encoding="utf-8")


def parse_iso(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def is_stale_claimed(task: TaskRecord, stale_after_minutes: int) -> bool:
    if task.status != TASK_STATUS_IN_PROGRESS:
        return False
    claimed_at = parse_iso(str(task.meta.get("claimed_at", "")))
    if claimed_at is None:
        return True
    now = datetime.now(timezone.utc)
    age_seconds = (now - claimed_at).total_seconds()
    return age_seconds > (stale_after_minutes * 60)


def next_task_id(source_uid: str, thread_key: str) -> str:
    uid_part = sanitize_filename(str(source_uid), fallback="uid")
    thread_part = sanitize_filename(str(thread_key), fallback="thread")
    short_thread = thread_part[:36] if thread_part else "thread"
    return f"task-{uid_part}-{short_thread}"


def summarize_requested_work(task: TaskRecord, limit: int = 280) -> str:
    compact = compact_whitespace(task.body)
    return compact[:limit] + ("..." if len(compact) > limit else "")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def list_task_files(task_dir: Path) -> list[Path]:
    return sorted(task_dir.glob("task__*.md"))


def sort_key_for_queue(task: TaskRecord) -> tuple[str, int]:
    queued_at = str(task.meta.get("queued_at", ""))
    raw_uid = str(task.meta.get("source_uid", "0") or "0")
    digits = "".join(ch for ch in raw_uid if ch.isdigit())
    source_uid = int(digits) if digits else 0
    return queued_at, source_uid


@contextmanager
def queue_lock(lock_path: Path) -> Iterator[None]:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("w", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        handle.write(utc_now_iso())
        handle.flush()
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
