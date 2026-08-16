#!/usr/bin/env python3
"""Build a compact daily digest of kids' school email."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import gmail_api
from common import load_env_file

ROSTER_PATH = Path("agentcore/knowledge/school/2026-27-roster.json")
OUTPUT_PATH = Path(".agentcore/state/school-digest/latest.md")
LABEL_NAME = "26-27 School"
TZ = ZoneInfo("America/Chicago")
ACCOUNT = gmail_api.ACCOUNT_BRIAN

ACTION_RE = re.compile(
    r"\b(due|deadline|sign up|signup|permission|waiver|fee|supply|supplies|form|conference|"
    r"detention|behavior|missing homework|bring|tomorrow|today|this week|schedule change|"
    r"cancelled|canceled|no school|early release|assembly)\b",
    re.I,
)
BLAST_FROM_RE = re.compile(
    r"(donotreply@edmondschools\.net|edmond public schools|mustang round-up|husky pride|falcon news)",
    re.I,
)
LOW_SUBJECT_RE = re.compile(
    r"(pto|candy gram|staff appreciation|baked potato|newsletter|news flash|round-up|"
    r"husky pride|utility verification|before & after care|bird.?s nest)",
    re.I,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize recent school mail for Brian.")
    parser.add_argument("--hours", type=int, default=24, help="Lookback window in hours.")
    parser.add_argument("--apply-label", action="store_true", help="Apply the 26-27 School label to matching mail.")
    parser.add_argument("--send-telegram", action="store_true", help="Send the digest to Brian on Telegram.")
    parser.add_argument("--dry-run", action="store_true", help="Print without labeling or sending.")
    parser.add_argument("--roster", default=str(ROSTER_PATH), help="Roster JSON path.")
    return parser.parse_args()


def load_roster(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def after_unix(hours: int) -> int:
    return int((datetime.now(timezone.utc) - timedelta(hours=max(1, hours))).timestamp())


def collect_ids(env_map: dict[str, str], hours: int) -> list[str]:
    query = (
        f"after:{after_unix(hours)} "
        "(edmondschools.net OR from:remind.com OR from:seesaw.me OR "
        'label:"26-27 School" OR "Frontier Elementary" OR "Cheyenne Middle" OR "Edmond North")'
    )
    ids: list[str] = []
    page = ""
    while True:
        payload = gmail_api.list_messages(
            query=query,
            max_results=100,
            env_map=env_map,
            account=ACCOUNT,
            page_token=page,
        )
        ids.extend(str(item.get("id", "")) for item in payload.get("messages") or [] if item.get("id"))
        page = str(payload.get("nextPageToken") or "")
        if not page:
            break
    return list(dict.fromkeys(ids))


def parse_date(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def children_for(row: dict, roster: dict) -> list[str]:
    blob = f"{row['from']} {row['subject']} {row['snippet']}".lower()
    hits = []
    for child in roster.get("children") or []:
        name = str(child.get("name", ""))
        if name and name.lower() in blob:
            hits.append(name)
            continue
        if any(needle.lower() in blob for needle in child.get("sender_needles") or []):
            hits.append(name)
    if hits:
        return list(dict.fromkeys(hits))
    if "north high" in blob or "enhs" in blob:
        return ["Daniel"]
    if "cheyenne" in blob:
        return ["Nathan", "Ezra"]
    if "frontier" in blob or "seesaw" in blob:
        return ["Silver", "Levi"] if "levi" not in blob else ["Levi"]
    return []


def classify(row: dict) -> str:
    blob = f"{row['from']} {row['subject']} {row['snippet']}"
    if "seesaw" in row["from"].lower():
        return "classroom_app"
    if ACTION_RE.search(blob) and not LOW_SUBJECT_RE.search(row["subject"]):
        return "action"
    if LOW_SUBJECT_RE.search(blob) or BLAST_FROM_RE.search(blob):
        return "fyi"
    if any(name in row["from"].lower() for name in ("byford", "trofemuk", "wildman", "copenhaver", "jackson")):
        return "teacher"
    if "@edmondschools.net" in row["from"].lower() and "donotreply" not in row["from"].lower() and "messenger@" not in row["from"].lower():
        return "teacher"
    return "fyi"


def importance(kind: str) -> str:
    if kind in {"action", "teacher"}:
        return "high"
    if kind == "classroom_app":
        return "medium"
    return "low"


def summarize_row(row: dict) -> str:
    subject = row["subject"].strip() or "(no subject)"
    snippet = re.sub(r"\s+", " ", row["snippet"]).strip()
    if snippet and snippet.lower() not in subject.lower():
        return f"{subject} — {snippet[:140]}"
    return subject


def fetch_rows(env_map: dict[str, str], ids: list[str]) -> list[dict]:
    rows = []
    for message_id in ids:
        message = gmail_api.get_message(message_id, env_map=env_map, account=ACCOUNT, fmt="metadata")
        headers = gmail_api.header_map(message)
        rows.append(
            {
                "id": message_id,
                "from": headers.get("from", ""),
                "subject": headers.get("subject", ""),
                "date": headers.get("date", ""),
                "snippet": message.get("snippet", ""),
                "label_ids": message.get("labelIds") or [],
            }
        )
    return rows


def render(rows: list[dict], roster: dict, hours: int) -> str:
    now_local = datetime.now(TZ)
    header = f"School digest · {now_local.strftime('%a %b')} {now_local.day} · last {hours}h"
    if not rows:
        return f"{header}\n\nNo new school mail."

    grouped = {"high": [], "medium": [], "low": []}
    for row in rows:
        kind = classify(row)
        row["kind"] = kind
        row["kids"] = children_for(row, roster)
        row["importance"] = importance(kind)
        grouped[row["importance"]].append(row)

    lines = [header, ""]
    if grouped["high"]:
        lines.append("Action / teacher")
        for row in grouped["high"]:
            kids = ", ".join(row["kids"]) or "family"
            lines.append(f"• {kids} — {summarize_row(row)}")
        lines.append("")
    if grouped["medium"]:
        lines.append("Classroom")
        for row in grouped["medium"]:
            kids = ", ".join(row["kids"]) or "family"
            lines.append(f"• {kids} — {summarize_row(row)}")
        lines.append("")
    skipped = len(grouped["low"])
    if skipped:
        lines.append(f"Skipped {skipped} school-wide/PTO/newsletter item{'s' if skipped != 1 else ''}.")
    return "\n".join(lines).strip() + "\n"


def apply_label(env_map: dict[str, str], rows: list[dict]) -> int:
    label = gmail_api.ensure_label(LABEL_NAME, env_map=env_map, account=ACCOUNT)
    label_id = str(label.get("id", ""))
    pending = [row["id"] for row in rows if label_id not in (row.get("label_ids") or [])]
    if not pending:
        return 0
    for offset in range(0, len(pending), 1000):
        gmail_api.batch_modify_messages(
            pending[offset : offset + 1000],
            add_label_ids=[label_id],
            env_map=env_map,
            account=ACCOUNT,
        )
    return len(pending)


def send_telegram(text: str) -> None:
    sys.path.insert(0, str(Path("scripts/telegram").resolve()))
    from send_task_response import send_message  # noqa: WPS433

    raw = (
        os.getenv("AGENTCORE_TELEGRAM_NOTIFY_CHAT_IDS", "").strip()
        or os.getenv("AGENTCORE_TELEGRAM_ALLOWED_USER_IDS", "").strip()
    )
    chat_ids = [part.strip() for part in raw.split(",") if part.strip()]
    if not chat_ids:
        raise RuntimeError("Missing AGENTCORE_TELEGRAM_NOTIFY_CHAT_IDS / ALLOWED_USER_IDS.")
    for chat_id in chat_ids:
        send_message(chat_id, text)


def main() -> int:
    args = parse_args()
    env_map = load_env_file(".env")
    roster = load_roster(Path(args.roster))
    ids = collect_ids(env_map, args.hours)
    rows = fetch_rows(env_map, ids)
    rows.sort(key=lambda row: parse_date(row["date"]) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    digest = render(rows, roster, args.hours)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(digest, encoding="utf-8")
    print(digest)
    labeled = 0
    if args.apply_label and not args.dry_run:
        labeled = apply_label(env_map, rows)
        print(f"labeled {labeled} message(s) with {LABEL_NAME}", file=sys.stderr)
    if args.send_telegram and not args.dry_run:
        if "No new school mail" in digest:
            print("skip telegram: empty digest", file=sys.stderr)
        else:
            send_telegram(digest)
            print("sent telegram digest", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
