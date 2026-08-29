#!/usr/bin/env python3
"""Ask Brian the open questions from the nightly jobs as one small numbered Telegram batch.

Questions are numbered so Brian can answer tersely ("1 learn, 2 ignore"). The batch id
and each question's number are recorded on the ledger so ``resolve_answers.py`` can map
his reply back to the right sender.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
EMAIL_DIR = SCRIPT_DIR.parent / "email"
TELEGRAM_DIR = SCRIPT_DIR.parent / "telegram"
for extra_path in (str(EMAIL_DIR), str(TELEGRAM_DIR), str(SCRIPT_DIR)):
    if extra_path not in sys.path:
        sys.path.insert(0, extra_path)

import questions  # noqa: E402
from common import write_json  # noqa: E402
from send_task_response import send_message  # noqa: E402

DEFAULT_SUMMARY_PATH = ".agentcore/state/ask-questions-summary.json"

INTRO = (
    "A few senders in your mail I'm not sure how to treat. "
    "Reply with the number and one word each, like \"1 learn, 2 ignore\"."
)
LEGEND = (
    "learn = remember facts from them | "
    "info = legit but nothing to remember | "
    "ignore = marketing or spam"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send open questions to Brian on Telegram.")
    parser.add_argument("--limit", type=int, default=5, help="Max questions per batch.")
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_PATH, help="Summary JSON path.")
    parser.add_argument("--dry-run", action="store_true", help="Print the message without sending.")
    return parser.parse_args()


def chat_ids() -> list[str]:
    raw = (
        os.getenv("AGENTCORE_TELEGRAM_NOTIFY_CHAT_IDS", "").strip()
        or os.getenv("AGENTCORE_TELEGRAM_ALLOWED_USER_IDS", "").strip()
    )
    return [item.strip() for item in raw.replace(";", ",").split(",") if item.strip()]


def build_batch_id() -> str:
    return "ask-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def compose(batch: list[dict]) -> str:
    lines = [INTRO, ""]
    for number, entry in enumerate(batch, start=1):
        lines.append(f"{number}. {entry.get('prompt', entry.get('subject_key', ''))}")
    lines.extend(["", LEGEND])
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    ledger = questions.load()
    questions.expire_stale(ledger)

    pending = questions.open_questions(ledger)[: max(0, args.limit)]
    if not pending:
        questions.save(ledger)
        summary = {"status": "ok", "sent": 0, "reason": "no_open_questions"}
        write_json(Path(args.summary_output), summary)
        print(json.dumps(summary, ensure_ascii=True))
        return 0

    text = compose(pending)
    targets = chat_ids()
    if args.dry_run or not targets:
        summary = {
            "status": "ok" if args.dry_run else "skipped",
            "sent": 0,
            "reason": "dry_run" if args.dry_run else "no_chat_ids",
            "question_count": len(pending),
            "message": text,
        }
        write_json(Path(args.summary_output), summary)
        print(json.dumps(summary, ensure_ascii=True))
        return 0

    batch_id = build_batch_id()
    delivered = 0
    errors: list[str] = []
    for chat_id in targets:
        try:
            send_message(chat_id, text)
            delivered += 1
        except RuntimeError as exc:
            errors.append(f"{chat_id}: {exc}")

    if delivered:
        for number, entry in enumerate(pending, start=1):
            questions.mark_asked(entry, batch_id, number)
    questions.save(ledger)

    summary = {
        "status": "ok" if delivered and not errors else "partial",
        "batch_id": batch_id,
        "sent": delivered,
        "question_count": len(pending),
        "subjects": [entry.get("subject_key", "") for entry in pending],
        "errors": errors,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(Path(args.summary_output), summary)
    print(json.dumps(summary, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
