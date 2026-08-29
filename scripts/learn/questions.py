"""Pending-question ledger for things AgentCore needs Brian to decide.

The nightly jobs enqueue a question whenever they cannot confidently classify
something on their own. Questions are asked in small numbered Telegram batches so
Brian can answer with a short reply like ``1 spam, 2 learn``. Answers are folded
back into durable policy, which is what makes the next sweep smarter.

Lifecycle: ``open`` -> ``asked`` -> ``answered``. Questions that go unanswered for
too long expire so the batch never fills up with stale items.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

QUESTIONS_PATH = Path("agentcore/knowledge/communications/pending-questions.json")

STATUS_OPEN = "open"
STATUS_ASKED = "asked"
STATUS_ANSWERED = "answered"
STATUS_EXPIRED = "expired"

KIND_SENDER_POLICY = "sender_policy"

DEFAULT_EXPIRY_DAYS = 21
ANSWERED_RETENTION_DAYS = 120


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(stamp: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(stamp))
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def load(path: Path = QUESTIONS_PATH) -> dict:
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("questions"), dict):
                return data
        except json.JSONDecodeError:
            pass
    return {"version": 1, "questions": {}}


def save(ledger: dict, path: Path = QUESTIONS_PATH) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=ANSWERED_RETENTION_DAYS)
    kept: dict[str, dict] = {}
    for question_id, entry in (ledger.get("questions") or {}).items():
        if not isinstance(entry, dict):
            continue
        if entry.get("status") == STATUS_ANSWERED:
            answered_at = _parse_iso(entry.get("answered_at", ""))
            if answered_at and answered_at < cutoff:
                continue
        kept[question_id] = entry
    payload = {"version": 1, "updated_at": now_iso(), "questions": kept}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def question_id(kind: str, subject_key: str) -> str:
    return f"{kind}:{str(subject_key).strip().lower()}"


def find_by_subject(ledger: dict, kind: str, subject_key: str) -> dict:
    return (ledger.get("questions") or {}).get(question_id(kind, subject_key)) or {}


def is_pending_or_answered(ledger: dict, kind: str, subject_key: str) -> bool:
    """True when this subject already has a live or settled question."""
    entry = find_by_subject(ledger, kind, subject_key)
    return bool(entry) and entry.get("status") in {STATUS_OPEN, STATUS_ASKED, STATUS_ANSWERED}


def enqueue(
    ledger: dict,
    kind: str,
    subject_key: str,
    prompt: str,
    options: list[str],
    context: dict | None = None,
) -> str:
    """Add an open question unless this subject is already pending or settled."""
    key = question_id(kind, subject_key)
    existing = (ledger.get("questions") or {}).get(key)
    if isinstance(existing, dict) and existing.get("status") in {STATUS_OPEN, STATUS_ASKED, STATUS_ANSWERED}:
        return ""
    ledger.setdefault("questions", {})[key] = {
        "id": key,
        "kind": kind,
        "subject_key": subject_key,
        "prompt": prompt,
        "options": list(options),
        "context": context or {},
        "status": STATUS_OPEN,
        "created_at": now_iso(),
    }
    return key


def open_questions(ledger: dict) -> list[dict]:
    items = [
        entry
        for entry in (ledger.get("questions") or {}).values()
        if isinstance(entry, dict) and entry.get("status") == STATUS_OPEN
    ]
    return sorted(items, key=lambda entry: str(entry.get("created_at", "")))


def asked_questions(ledger: dict) -> list[dict]:
    items = [
        entry
        for entry in (ledger.get("questions") or {}).values()
        if isinstance(entry, dict) and entry.get("status") == STATUS_ASKED
    ]
    return sorted(items, key=lambda entry: str(entry.get("asked_at", "")))


def mark_asked(entry: dict, batch_id: str, number: int) -> None:
    entry["status"] = STATUS_ASKED
    entry["asked_at"] = now_iso()
    entry["asked_batch"] = batch_id
    entry["asked_number"] = number
    entry["ask_count"] = int(entry.get("ask_count", 0) or 0) + 1


def mark_answered(entry: dict, answer: str, source: str, raw: str = "") -> None:
    entry["status"] = STATUS_ANSWERED
    entry["answer"] = answer
    entry["answer_source"] = source
    entry["answer_raw"] = str(raw)[:300]
    entry["answered_at"] = now_iso()


def expire_stale(ledger: dict, days: int = DEFAULT_EXPIRY_DAYS) -> int:
    """Expire questions asked long ago with no answer so batches stay current."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    expired = 0
    for entry in (ledger.get("questions") or {}).values():
        if not isinstance(entry, dict) or entry.get("status") != STATUS_ASKED:
            continue
        asked_at = _parse_iso(entry.get("asked_at", ""))
        if asked_at and asked_at < cutoff:
            entry["status"] = STATUS_EXPIRED
            entry["expired_at"] = now_iso()
            expired += 1
    return expired
