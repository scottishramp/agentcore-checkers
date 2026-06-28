#!/usr/bin/env python3
"""Download Telegram photos from inbox records and upload them to Google Drive."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
EMAIL_DIR = SCRIPT_DIR.parent / "email"
if str(EMAIL_DIR) not in sys.path:
    sys.path.insert(0, str(EMAIL_DIR))
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import ensure_dir, sanitize_filename, utc_now_iso, write_json  # noqa: E402
from drive_upload import target_folder_id, upload_bytes  # noqa: E402
from photo_registry import DEFAULT_REGISTRY_PATH, upsert_photo  # noqa: E402
from telegram_api import download_file  # noqa: E402

DEFAULT_SUMMARY = ".agentcore/state/telegram-media-summary.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Materialize Telegram inbox photos to Drive + photo inbox records.")
    parser.add_argument("--telegram-dir", default="agentcore/inbox/telegram", help="Telegram inbox markdown dir.")
    parser.add_argument("--photo-dir", default="agentcore/inbox/photos", help="Photo metadata dir.")
    parser.add_argument("--task-dir", default="agentcore/inbox/tasks", help="Task queue dir.")
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY, help="Summary JSON path.")
    return parser.parse_args()


def parse_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    block = text[3:end].strip()
    values: dict[str, str] = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, raw = line.split(":", 1)
        values[key.strip()] = raw.strip().strip('"')
    return values


def rewrite_frontmatter_value(path: Path, key: str, value: str) -> None:
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(rf'^{re.escape(key)}: ".*"$', re.MULTILINE)
    replacement = f'{key}: "{quote_meta(value)}"'
    if pattern.search(text):
        text = pattern.sub(replacement, text, count=1)
    else:
        text = text.replace("---\n", f'---\n{key}: "{quote_meta(value)}"\n', 1)
    path.write_text(text, encoding="utf-8")


def patch_task_drive_link(task_dir: Path, message_id: str, drive_link: str, photo_label: str = "") -> None:
    safe = sanitize_filename(message_id, fallback="telegram-message")
    task_path = task_dir / f"task__telegram__{safe}.md"
    if not task_path.exists():
        return
    text = task_path.read_text(encoding="utf-8")
    if drive_link:
        text = text.replace("- Drive link: pending materialization", f"- Drive link: {drive_link}")
    if photo_label and "- Photo label:" not in text:
        text = text.replace(
            f"- Message id: {message_id}",
            f"- Message id: {message_id}\n- Photo label: {photo_label}",
        )
    task_path.write_text(text, encoding="utf-8")


def quote_meta(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def write_photo_record(path: Path, meta: dict, drive: dict, caption: str, photo_description: str) -> None:
    if path.exists():
        return
    photo_label = str(meta.get("photo_label", "")).strip()
    lines = [
        "---",
        f'photo_label: "{quote_meta(photo_label)}"',
        f'drive_file_id: "{quote_meta(str(drive.get("id", "")))}"',
        f'title: "{quote_meta(str(drive.get("name", "")))}"',
        f'mime_type: "{quote_meta(str(drive.get("mimeType", "")))}"',
        f'modified_time: "{quote_meta(str(drive.get("modifiedTime", "")))}"',
        f'created_time: "{quote_meta(str(drive.get("createdTime", "")))}"',
        f'web_view_link: "{quote_meta(str(drive.get("webViewLink", "")))}"',
        f'source_message_id: "{quote_meta(str(meta.get("message_id", "")))}"',
        f'telegram_file_id: "{quote_meta(str(meta.get("telegram_file_id", "")))}"',
        f'recorded_at: "{quote_meta(utc_now_iso())}"',
        "requires_review: true",
        'classification: "telegram_photo"',
        "---",
        "",
        "## Caption",
        "",
        caption or "_No caption._",
        "",
        "## Fast-agent description",
        "",
        photo_description or "_No fast-agent description recorded._",
        "",
        "## Source",
        "",
        f"- Telegram message: {meta.get('message_id', '')}",
        f"- Sender: {meta.get('sender_display_name', '')}",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def extract_caption(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    marker = "## Raw Telegram Message"
    idx = text.find(marker)
    if idx < 0:
        return ""
    body = text[idx + len(marker) :].split("## Fast Router Reply", 1)[0].strip()
    return body if body and body != "_No message text parsed._" else ""


def extract_photo_description(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    meta = parse_frontmatter(path)
    if meta.get("photo_description"):
        return meta["photo_description"]
    marker = "## Fast-agent Photo Description"
    idx = text.find(marker)
    if idx < 0:
        return ""
    return text[idx + len(marker) :].split("##", 1)[0].strip()


def main() -> int:
    args = parse_args()
    telegram_dir = Path(args.telegram_dir)
    photo_dir = Path(args.photo_dir)
    task_dir = Path(args.task_dir)
    ensure_dir(photo_dir)
    folder_id = target_folder_id()

    processed = 0
    skipped = 0
    errors: list[dict] = []

    for record_path in sorted(telegram_dir.glob("telegram__*.md")):
        meta = parse_frontmatter(record_path)
        file_id = str(meta.get("telegram_file_id", "")).strip()
        if not file_id:
            continue
        if str(meta.get("drive_file_id", "")).strip():
            skipped += 1
            continue
        try:
            content, mime_type = download_file(file_id)
            caption = extract_caption(record_path)
            photo_description = extract_photo_description(record_path)
            photo_label = str(meta.get("photo_label", "")).strip()
            safe_name = sanitize_filename(meta.get("message_id", "telegram-photo"), fallback="telegram-photo")
            ext = mime_type.split("/")[-1] or "jpg"
            filename = f"{sanitize_filename(photo_label, fallback=safe_name)}.{ext}" if photo_label else f"{safe_name}.{ext}"
            drive = upload_bytes(content, filename, mime_type, folder_id=folder_id)
            photo_path = photo_dir / (
                f"photo__{sanitize_filename(photo_label, fallback=f'telegram__{safe_name}')}.md"
                if photo_label
                else f"photo__telegram__{safe_name}.md"
            )
            write_photo_record(photo_path, meta, drive, caption, photo_description)
            rewrite_frontmatter_value(record_path, "drive_file_id", str(drive.get("id", "")))
            rewrite_frontmatter_value(record_path, "drive_web_view_link", str(drive.get("webViewLink", "")))
            patch_task_drive_link(
                task_dir,
                str(meta.get("message_id", "")),
                str(drive.get("webViewLink", "")),
                photo_label,
            )
            if photo_label:
                upsert_photo(
                    DEFAULT_REGISTRY_PATH,
                    photo_label,
                    {
                        "photo_description": photo_description,
                        "caption": caption,
                        "message_id": str(meta.get("message_id", "")),
                        "telegram_file_id": file_id,
                        "drive_file_id": str(drive.get("id", "")),
                        "drive_web_view_link": str(drive.get("webViewLink", "")),
                        "photo_record_path": str(photo_path),
                        "materialized_at": utc_now_iso(),
                        "status": "materialized",
                    },
                )
            processed += 1
        except Exception as exc:  # noqa: BLE001
            errors.append({"record": str(record_path), "error": str(exc)})

    summary = {
        "status": "ok",
        "processed": processed,
        "skipped_already_materialized": skipped,
        "errors": errors,
        "folder_id": folder_id,
    }
    write_json(Path(args.summary_output), summary)
    print(json.dumps(summary, ensure_ascii=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
