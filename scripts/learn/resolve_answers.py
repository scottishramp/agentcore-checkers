#!/usr/bin/env python3
"""Turn Brian's Telegram replies into durable sender policy.

Reads the normalized Telegram inbox records written by ``telegram/triage_messages.py``,
matches short replies like ``1 learn, 2 ignore`` against the most recent question batch
that was asked before the reply arrived, and records his answers as authoritative policy.

Replies that cannot be parsed are left alone: the questions stay in the ``asked`` state
and the message still reaches Cursor through the normal Telegram review task, so nothing
is lost when Brian answers in prose.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
EMAIL_DIR = SCRIPT_DIR.parent / "email"
for extra_path in (str(EMAIL_DIR), str(SCRIPT_DIR)):
    if extra_path not in sys.path:
        sys.path.insert(0, extra_path)

import questions  # noqa: E402
import sender_policy  # noqa: E402
from common import write_json  # noqa: E402

TELEGRAM_INBOX_DIR = Path("agentcore/inbox/telegram")
DEFAULT_SUMMARY_PATH = ".agentcore/state/resolve-answers-summary.json"

ANSWER_WORDS = {
    "learn": sender_policy.POLICY_LEARN,
    "l": sender_policy.POLICY_LEARN,
    "keep": sender_policy.POLICY_LEARN,
    "important": sender_policy.POLICY_LEARN,
    "remember": sender_policy.POLICY_LEARN,
    "info": sender_policy.POLICY_INFO,
    "i": sender_policy.POLICY_INFO,
    "fyi": sender_policy.POLICY_INFO,
    "ignore": sender_policy.POLICY_IGNORE,
    "spam": sender_policy.POLICY_IGNORE,
    "junk": sender_policy.POLICY_IGNORE,
    "skip": sender_policy.POLICY_IGNORE,
    "s": sender_policy.POLICY_IGNORE,
    "x": sender_policy.POLICY_IGNORE,
}
ANSWER_ALTERNATION = "|".join(sorted(ANSWER_WORDS, key=len, reverse=True))
NUMBERED_RE = re.compile(rf"\b(\d{{1,2}})\s*[\).:=-]?\s*({ANSWER_ALTERNATION})\b", re.I)
REVERSED_RE = re.compile(rf"\b({ANSWER_ALTERNATION})\s*[\).:=-]?\s*(\d{{1,2}})\b", re.I)
ALL_RE = re.compile(rf"\ball\s+({ANSWER_ALTERNATION})\b", re.I)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply Brian's Telegram answers to sender policy.")
    parser.add_argument("--telegram-dir", default=str(TELEGRAM_INBOX_DIR), help="Telegram inbox record dir.")
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_PATH, help="Summary JSON path.")
    parser.add_argument("--dry-run", action="store_true", help="Report matches without writing ledgers.")
    return parser.parse_args()


def _parse_iso(stamp: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def read_telegram_record(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    meta: dict[str, str] = {}
    body_lines: list[str] = []
    in_front_matter = False
    in_body = False
    for line in text.splitlines():
        if line.strip() == "---":
            in_front_matter = not in_front_matter
            continue
        if in_front_matter:
            match = re.match(r'^([a-z_]+):\s*"?(.*?)"?\s*$', line)
            if match:
                meta[match.group(1)] = match.group(2)
            continue
        if line.startswith("## Raw Telegram Message"):
            in_body = True
            continue
        if in_body and line.startswith("## "):
            in_body = False
            continue
        if in_body:
            body_lines.append(line)
    return {
        "path": str(path),
        "message_id": meta.get("message_id", ""),
        "received_at": meta.get("received_at", ""),
        "text": "\n".join(body_lines).strip(),
    }


def parse_answer_text(text: str, batch_size: int) -> dict[int, str]:
    """Map question numbers to policies from a short reply. Empty when unparseable."""
    lowered = text.strip().lower()
    if not lowered:
        return {}

    all_match = ALL_RE.search(lowered)
    if all_match:
        policy = ANSWER_WORDS[all_match.group(1)]
        return {number: policy for number in range(1, batch_size + 1)}

    answers: dict[int, str] = {}
    for match in NUMBERED_RE.finditer(lowered):
        number = int(match.group(1))
        if 1 <= number <= batch_size:
            answers[number] = ANSWER_WORDS[match.group(2)]
    for match in REVERSED_RE.finditer(lowered):
        number = int(match.group(2))
        if 1 <= number <= batch_size and number not in answers:
            answers[number] = ANSWER_WORDS[match.group(1)]

    if not answers and batch_size == 1:
        bare = re.fullmatch(rf"({ANSWER_ALTERNATION})[.!]?", lowered)
        if bare:
            answers[1] = ANSWER_WORDS[bare.group(1)]
    return answers


def batches_by_id(asked: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for entry in asked:
        batch_id = str(entry.get("asked_batch", ""))
        if batch_id:
            grouped.setdefault(batch_id, []).append(entry)
    for entries in grouped.values():
        entries.sort(key=lambda item: int(item.get("asked_number", 0) or 0))
    return grouped


def main() -> int:
    args = parse_args()
    question_ledger = questions.load()
    asked = questions.asked_questions(question_ledger)
    grouped = batches_by_id(asked)

    if not grouped:
        summary = {"status": "ok", "resolved": 0, "reason": "no_asked_questions"}
        write_json(Path(args.summary_output), summary)
        print(json.dumps(summary, ensure_ascii=True))
        return 0

    telegram_dir = Path(args.telegram_dir)
    records = []
    if telegram_dir.exists():
        for path in sorted(telegram_dir.glob("telegram__*.md")):
            record = read_telegram_record(path)
            if record["text"]:
                records.append(record)
    records.sort(key=lambda item: str(item.get("received_at", "")))

    policy_ledger = sender_policy.load()
    resolved: list[dict] = []
    unmatched: list[str] = []

    for record in records:
        received_at = _parse_iso(record.get("received_at", ""))
        # Answers apply to the newest batch that was already outstanding when Brian replied.
        candidate_batches = []
        for batch_id, entries in grouped.items():
            if not entries:
                continue
            asked_at = _parse_iso(entries[0].get("asked_at", ""))
            if asked_at and received_at and received_at < asked_at:
                continue
            candidate_batches.append((asked_at or datetime.min.replace(tzinfo=timezone.utc), batch_id, entries))
        if not candidate_batches:
            continue
        candidate_batches.sort(key=lambda item: item[0], reverse=True)
        _, batch_id, entries = candidate_batches[0]

        answers = parse_answer_text(record["text"], len(entries))
        if not answers:
            unmatched.append(record["message_id"])
            continue

        by_number = {int(entry.get("asked_number", 0) or 0): entry for entry in entries}
        for number, policy in sorted(answers.items()):
            entry = by_number.get(number)
            if not entry or entry.get("status") != questions.STATUS_ASKED:
                continue
            questions.mark_answered(entry, policy, "telegram", record["text"])
            if entry.get("kind") == questions.KIND_SENDER_POLICY:
                context = entry.get("context") or {}
                sample_subjects = context.get("subjects") or []
                sender_policy.record(
                    policy_ledger,
                    entry.get("subject_key", ""),
                    policy,
                    sender_policy.SOURCE_BRIAN,
                    display_name=str(context.get("display_name", "")),
                    rationale="Brian answered this directly on Telegram.",
                    subject=str(sample_subjects[0]) if sample_subjects else "",
                    seen_count=int(context.get("message_count", 0) or 0),
                )
            resolved.append(
                {
                    "question_id": entry.get("id", ""),
                    "subject_key": entry.get("subject_key", ""),
                    "answer": policy,
                    "batch_id": batch_id,
                    "telegram_message_id": record["message_id"],
                }
            )
        grouped[batch_id] = [item for item in entries if item.get("status") == questions.STATUS_ASKED]

    if not args.dry_run and resolved:
        sender_policy.save(policy_ledger)
        questions.save(question_ledger)

    summary = {
        "status": "ok",
        "resolved": len(resolved),
        "answers": resolved,
        "unparsed_replies": len(unmatched),
        "outstanding_questions": len(questions.asked_questions(question_ledger)),
        "policy_totals": sender_policy.counts(policy_ledger),
        "dry_run": args.dry_run,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(Path(args.summary_output), summary)
    print(json.dumps(summary, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
