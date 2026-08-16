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
from html import unescape
from pathlib import Path
from zoneinfo import ZoneInfo

import gmail_api
from common import load_env_file

ROSTER_PATH = Path("agentcore/knowledge/school/2026-27-roster.json")
DOC_REGISTRY_PATH = Path("agentcore/knowledge/school/digest-doc.json")
OUTPUT_PATH = Path(".agentcore/state/school-digest/latest.md")
LABEL_NAME = "26-27 School"
DOC_TITLE = "2026-27 School Digest"
DOC_FOLDER = "School"
SHARE_EMAIL = "briandherbert@gmail.com"
CHILD_ORDER = ["Daniel", "Nathan", "Ezra", "Silver", "Levi"]
TZ = ZoneInfo("America/Chicago")
ACCOUNT = gmail_api.ACCOUNT_BRIAN

ACTION_RE = re.compile(
    r"\b(due|deadline|sign up|signup|permission|waiver|fee|supply|supplies|form|conference|"
    r"detention|behavior|missing homework|bring|tomorrow|today|this week|schedule change|"
    r"cancelled|canceled|no school|early release|assembly|picture day|registration|rank one|"
    r"physical|walkabout)\b",
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
    parser.add_argument("--update-doc", action="store_true", help="Create or replace the Google Doc digest.")
    parser.add_argument("--send-telegram", action="store_true", help="Send Important items plus the Doc link on Telegram.")
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
    if "north high" in blob or "enhs" in blob or "english i" in blob:
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
    if re.search(r"picture day|psat|rank one", row["subject"], re.I):
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


def when_label(row: dict) -> str:
    parsed = parse_date(row.get("date", ""))
    email_day = ""
    if parsed:
        local = parsed.astimezone(TZ)
        email_day = f"{local.strftime('%a')} {local.month}/{local.day}"
    blob = f"{row.get('subject', '')} {row.get('snippet', '')}"
    match = re.search(
        r"\b((?:mon|tues|wednes|thurs|fri|satur|sun)day|\d{1,2}/\d{1,2}(?:/\d{2,4})?|this week|tomorrow|today|tonight)\b",
        blob,
        re.I,
    )
    extra = match.group(1) if match else ""
    if extra and extra.lower() not in email_day.lower():
        return f"{email_day} · {extra}" if email_day else extra
    return email_day or "undated"


def annotate(rows: list[dict], roster: dict) -> list[dict]:
    annotated = []
    for row in rows:
        kind = classify(row)
        kids = children_for(row, roster)
        row = dict(row)
        row["kind"] = kind
        row["kids"] = kids
        row["importance"] = importance(kind)
        row["when"] = when_label(row)
        annotated.append(row)
    return annotated


def kid_line(row: dict) -> str:
    kids = ", ".join(row["kids"]) or "family"
    return f"• {row['when']} · {kids} — {summarize_row(row)}"


def section_items(rows: list[dict], roster: dict) -> dict[str, list[dict]]:
    important = []
    stale_actions = []
    for row in rows:
        if row["importance"] == "high" and row["kind"] == "action":
            if is_stale_action(row):
                stale_actions.append(row)
            else:
                important.append(row)
    teacher_or_class = [row for row in rows if row["kind"] in {"teacher", "classroom_app"} or (row["importance"] == "high" and row["kind"] != "action")]
    general = [row for row in rows if row["kind"] == "fyi"] + stale_actions
    per_kid: dict[str, list[dict]] = {name: [] for name in CHILD_ORDER}
    unassigned: list[dict] = []
    for row in teacher_or_class:
        if row in important:
            continue
        names = [name for name in row["kids"] if name in per_kid]
        if not names:
            unassigned.append(row)
            continue
        for name in names:
            per_kid[name].append(row)
    if unassigned:
        general = unassigned + general
    return {"important": important, "per_kid": per_kid, "general": general, "roster": roster}


def school_for(name: str, roster: dict) -> str:
    for child in roster.get("children") or []:
        if child.get("name") == name:
            grade = child.get("grade", "")
            school = child.get("school_short") or child.get("school", "")
            return f"{school}, grade {grade}".strip(", ")
    return ""


def render_doc_text(rows: list[dict], roster: dict) -> tuple[str, list[str], str]:
    now_local = datetime.now(TZ)
    title = DOC_TITLE
    sections = section_items(rows, roster)
    headings = ["Important", "General"]
    lines = [
        title,
        f"Updated {now_local.strftime('%A, %B')} {now_local.day}, {now_local.year}, {now_local.strftime('%I:%M %p').lstrip('0')} CT",
        "",
        "Important",
        "Action items we need to handle. Each line has a date and a child.",
        "",
    ]
    if sections["important"]:
        lines.extend(kid_line(row) for row in sections["important"])
    else:
        lines.append("• None right now.")
    lines.append("")
    for name in CHILD_ORDER:
        heading = f"{name} — {school_for(name, roster)}"
        headings.append(heading)
        lines.extend([heading, ""])
        items = sections["per_kid"].get(name) or []
        if items:
            lines.extend(kid_line(row) for row in items)
        else:
            lines.append("• Nothing extra this window.")
        lines.append("")
    lines.extend(
        [
            "General",
            "School announcements that are not urgent.",
            "",
        ]
    )
    if sections["general"]:
        lines.extend(kid_line(row) for row in sections["general"])
    else:
        lines.append("• None this window.")
    lines.append("")
    return "\n".join(lines), headings, title


def render_telegram(rows: list[dict], roster: dict, doc_link: str) -> str:
    sections = section_items(rows, roster)
    lines = ["School digest"]
    if sections["important"]:
        lines.append("Important")
        lines.extend(kid_line(row) for row in sections["important"][:8])
    else:
        lines.append("No action items in this window.")
    if doc_link:
        lines.append(f"Full digest: {doc_link}")
    return "\n".join(lines) + "\n"


def is_stale_action(row: dict) -> bool:
    parsed = parse_date(row.get("date", ""))
    if not parsed:
        return False
    age = datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)
    when = str(row.get("when", "")).lower()
    if age > timedelta(days=2) and re.search(r"\b(tomorrow|today|tonight)\b", when):
        return True
    if age > timedelta(days=6) and "this week" in when:
        return True
    return False


def summarize_row(row: dict) -> str:
    subject = unescape(row["subject"].strip() or "(no subject)")
    snippet = unescape(re.sub(r"\s+", " ", row["snippet"]).strip())
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
    text, _headings, _title = render_doc_text(rows, roster)
    header = f"Window: last {hours}h\n"
    return header + text


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


def load_doc_registry() -> dict:
    if DOC_REGISTRY_PATH.exists():
        return json.loads(DOC_REGISTRY_PATH.read_text(encoding="utf-8"))
    return {}


def save_doc_registry(payload: dict) -> None:
    DOC_REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOC_REGISTRY_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def update_google_doc(env_map: dict[str, str], rows: list[dict], roster: dict) -> dict:
    docs_dir = Path(__file__).resolve().parent.parent / "docs"
    if str(docs_dir) not in sys.path:
        sys.path.insert(0, str(docs_dir))
    import google_docs  # noqa: WPS433

    registry = load_doc_registry()
    folder = google_docs.ensure_folder(DOC_FOLDER, env_map=env_map)
    folder_id = str(folder.get("id") or registry.get("folder_id") or "")
    document = {}
    file_id = str(registry.get("file_id") or "")
    if file_id:
        document = {"id": file_id, "webViewLink": registry.get("web_view_link", "")}
    else:
        document = google_docs.ensure_document(DOC_TITLE, env_map=env_map, folder_id=folder_id)
        file_id = str(document.get("id", ""))
    if not file_id:
        raise google_docs.GoogleDocsError("Google Doc create did not return a file id.")
    text, headings, title = render_doc_text(rows, roster)
    google_docs.replace_document_text(file_id, text, heading_lines=headings, title_line=title, env_map=env_map)
    shared_with = list(registry.get("shared_with") or [])
    if SHARE_EMAIL not in shared_with:
        google_docs.share_file(file_id, SHARE_EMAIL, env_map=env_map, role="writer", notify=True)
        shared_with.append(SHARE_EMAIL)
    link = str(document.get("webViewLink") or registry.get("web_view_link") or "")
    if not link:
        looked_up = google_docs.find_app_file(DOC_TITLE, google_docs.GOOGLE_DOC_MIME, env_map=env_map, parent_id=folder_id)
        link = str(looked_up.get("webViewLink") or f"https://docs.google.com/document/d/{file_id}/edit")
        document = {**document, **looked_up}
    registry = {
        "title": DOC_TITLE,
        "file_id": file_id,
        "folder_id": folder_id,
        "web_view_link": link,
        "shared_with": shared_with,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    save_doc_registry(registry)
    return registry


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
    rows = annotate(rows, roster)
    digest = render(rows, roster, args.hours)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(digest, encoding="utf-8")
    print(digest)
    labeled = 0
    registry = {}
    if args.apply_label and not args.dry_run:
        labeled = apply_label(env_map, rows)
        print(f"labeled {labeled} message(s) with {LABEL_NAME}", file=sys.stderr)
    if args.update_doc and not args.dry_run:
        registry = update_google_doc(env_map, rows, roster)
        print(f"updated doc {registry.get('web_view_link', '')}", file=sys.stderr)
    if args.send_telegram and not args.dry_run:
        link = str(registry.get("web_view_link") or load_doc_registry().get("web_view_link") or "")
        telegram_text = render_telegram(rows, roster, link)
        send_telegram(telegram_text)
        print("sent telegram digest", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
