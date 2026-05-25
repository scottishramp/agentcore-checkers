#!/usr/bin/env python3
"""Ingest new Drive documents/photos into inbox records and task queue."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
EMAIL_DIR = SCRIPT_DIR.parent / "email"
if str(EMAIL_DIR) not in sys.path:
    sys.path.insert(0, str(EMAIL_DIR))

import gmail_api  # noqa: E402
from common import compact_whitespace, get_env, load_env_file, sanitize_filename, utc_now_iso, write_json  # noqa: E402
from task_queue import next_task_id  # noqa: E402

DRIVE_API_BASE = "https://www.googleapis.com/drive/v3"
DEFAULT_STATE_PATH = ".agentcore/state/drive-ingest-state.json"
DEFAULT_SUMMARY_PATH = ".agentcore/state/drive-ingest-summary.json"


@dataclass
class SourceSpec:
    name: str
    folder_id: str
    classification: str
    output_dir: Path
    task_prefix: str
    file_query_suffix: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest new Drive documents and photos.")
    parser.add_argument("--state-file", default=DEFAULT_STATE_PATH, help="State JSON path.")
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_PATH, help="Summary JSON output path.")
    parser.add_argument("--drive-record-dir", default="agentcore/inbox/drive", help="Drive document metadata dir.")
    parser.add_argument("--photo-record-dir", default="agentcore/inbox/photos", help="Photo metadata dir.")
    parser.add_argument("--task-dir", default="agentcore/inbox/tasks", help="Task queue dir.")
    parser.add_argument("--docs-folder-id", default="", help="Drive folder id for document ingestion.")
    parser.add_argument("--photos-folder-id", default="", help="Drive folder id for photo ingestion.")
    parser.add_argument("--include-shared-with-me", action="store_true", help="Also ingest shared-with-me docs.")
    parser.add_argument("--limit", type=int, default=100, help="Max files per source per run.")
    return parser.parse_args()


def _drive_request(token: str, query: dict[str, str | int]) -> dict:
    url = f"{DRIVE_API_BASE}/files?{urllib.parse.urlencode(query)}"
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"}, method="GET")
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read().decode("utf-8")
    return json.loads(body) if body else {}


def _list_files(token: str, source: SourceSpec, modified_after: str, limit: int) -> list[dict]:
    query_chunks = ["trashed = false", source.file_query_suffix]
    if source.folder_id:
        query_chunks.append(f"'{source.folder_id}' in parents")
    if modified_after:
        query_chunks.append(f"modifiedTime > '{modified_after}'")
    q = " and ".join([chunk for chunk in query_chunks if chunk])

    files: list[dict] = []
    page_token = ""
    remaining = max(1, limit)
    while remaining > 0:
        payload = _drive_request(
            token=token,
            query={
                "q": q,
                "spaces": "drive",
                "fields": "nextPageToken,files(id,name,mimeType,modifiedTime,createdTime,webViewLink,owners(emailAddress),parents,size)",
                "pageSize": min(remaining, 100),
                "orderBy": "modifiedTime asc",
                "supportsAllDrives": "true",
                "includeItemsFromAllDrives": "true",
                "pageToken": page_token,
            },
        )
        batch = payload.get("files", [])
        if isinstance(batch, list):
            files.extend(batch)
            remaining -= len(batch)
        page_token = str(payload.get("nextPageToken", ""))
        if not page_token:
            break
    return files[:limit]


def _markdown_frontmatter(meta: dict[str, str | bool]) -> str:
    ordered = [
        "drive_file_id",
        "title",
        "mime_type",
        "modified_time",
        "created_time",
        "owner_email",
        "web_view_link",
        "source_folder_id",
        "recorded_at",
        "requires_review",
    ]
    lines = ["---"]
    for key in ordered:
        value = meta.get(key, "")
        if isinstance(value, bool):
            lines.append(f"{key}: {'true' if value else 'false'}")
        else:
            escaped = str(value).replace('"', '\\"')
            lines.append(f'{key}: "{escaped}"')
    lines.append("---")
    return "\n".join(lines) + "\n"


def _record_path(source: SourceSpec, file_id: str) -> Path:
    safe = sanitize_filename(file_id, fallback="unknown")
    prefix = "photo" if source.classification == "photo_batch" else "drive"
    return source.output_dir / f"{prefix}__id-{safe}.md"


def _write_record(source: SourceSpec, file_obj: dict) -> tuple[bool, Path]:
    file_id = str(file_obj.get("id", ""))
    path = _record_path(source, file_id)
    if path.exists():
        return False, path

    owners = file_obj.get("owners", [])
    owner_email = ""
    if isinstance(owners, list) and owners:
        owner_email = str((owners[0] or {}).get("emailAddress", ""))
    meta = {
        "drive_file_id": file_id,
        "title": str(file_obj.get("name", "")),
        "mime_type": str(file_obj.get("mimeType", "")),
        "modified_time": str(file_obj.get("modifiedTime", "")),
        "created_time": str(file_obj.get("createdTime", "")),
        "owner_email": owner_email,
        "web_view_link": str(file_obj.get("webViewLink", "")),
        "source_folder_id": source.folder_id,
        "recorded_at": utc_now_iso(),
        "requires_review": True,
    }
    notes = [
        "## Intake Notes",
        "",
        f"- Classification: {source.classification}",
        f"- Title: {meta['title']}",
        f"- Mime type: {meta['mime_type']}",
        "- Suggested action: Review, classify, and file in Drive taxonomy.",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_markdown_frontmatter(meta) + "\n".join(notes), encoding="utf-8")
    return True, path


def _write_task(task_dir: Path, source: SourceSpec, file_obj: dict) -> bool:
    file_id = str(file_obj.get("id", ""))
    title = compact_whitespace(str(file_obj.get("name", ""))) or file_id
    thread_key = sanitize_filename(f"{source.task_prefix}-{file_id}", fallback="thread")
    task_id = next_task_id(source_uid=f"{source.task_prefix}-{file_id}", thread_key=thread_key)
    safe_title = sanitize_filename(title, fallback=thread_key)
    path = task_dir / f"task__uid-{source.task_prefix}-{sanitize_filename(file_id)}__{safe_title}.md"
    if path.exists():
        return False

    now = utc_now_iso()
    web_link = str(file_obj.get("webViewLink", ""))
    lines = [
        "---",
        f'task_id: "{task_id}"',
        'status: "queued"',
        'priority: "normal"',
        f'source_message_id: "drive:{file_id}"',
        f'source_uid: "{source.task_prefix}-{file_id}"',
        'source_from: "google-drive"',
        f'source_subject: "{title.replace("\"", "\\\"")}"',
        f'thread_key: "{thread_key}"',
        f'queued_at: "{now}"',
        f'updated_at: "{now}"',
        "attempts: 0",
        'claimed_at: ""',
        'run_id: ""',
        'completed_at: ""',
        'snagged_at: ""',
        'last_error: ""',
        'result_path: ""',
        "---",
        "",
        f"# {title}",
        "",
        "## Requested Work",
        "",
        f"- Source: {source.classification}",
        f"- Drive file id: {file_id}",
        f"- Link: {web_link}",
        "- Action: classify metadata and file in canonical Drive folder.",
        "",
        "## Intake Notes",
        "",
        f"- Thread key: {thread_key}",
        "- Suggested next step: extract metadata and determine action required.",
        "",
    ]
    task_dir.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return True


def main() -> int:
    args = parse_args()
    env_map = load_env_file(".env")
    docs_folder = args.docs_folder_id.strip() or get_env("AGENTCORE_DRIVE_DOCS_FOLDER_ID", env_map=env_map)
    photos_folder = args.photos_folder_id.strip() or get_env("AGENTCORE_DRIVE_PHOTOS_FOLDER_ID", env_map=env_map)
    include_shared = args.include_shared_with_me or get_env(
        "AGENTCORE_DRIVE_INCLUDE_SHARED_WITH_ME", default="", env_map=env_map
    ).strip().lower() in {"1", "true", "yes", "on"}

    sources: list[SourceSpec] = []
    if docs_folder:
        sources.append(
            SourceSpec(
                name="docs_folder",
                folder_id=docs_folder,
                classification="document_shared",
                output_dir=Path(args.drive_record_dir),
                task_prefix="drive",
                file_query_suffix="",
            )
        )
    if photos_folder:
        sources.append(
            SourceSpec(
                name="photos_folder",
                folder_id=photos_folder,
                classification="photo_batch",
                output_dir=Path(args.photo_record_dir),
                task_prefix="photo",
                file_query_suffix="(mimeType contains 'image/' or mimeType = 'application/pdf')",
            )
        )
    if include_shared:
        sources.append(
            SourceSpec(
                name="shared_with_me_docs",
                folder_id="",
                classification="document_shared",
                output_dir=Path(args.drive_record_dir),
                task_prefix="shared",
                file_query_suffix="sharedWithMe = true",
            )
        )

    state_path = Path(args.state_file)
    summary_path = Path(args.summary_output)
    prior_state = {"last_modified_time": "", "seen_ids_at_last_modified_time": []}
    if state_path.exists():
        try:
            prior_state = json.loads(state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            prior_state = {"last_modified_time": "", "seen_ids_at_last_modified_time": []}

    summary = {
        "ingested_at": utc_now_iso(),
        "transport": "google-drive-api",
        "configured_sources": [source.name for source in sources],
        "records_created": 0,
        "tasks_created": 0,
        "documents_created": 0,
        "photos_created": 0,
        "errors": [],
        "created_items": [],
    }

    if not sources:
        summary["errors"].append("No Drive source configured. Set AGENTCORE_DRIVE_DOCS_FOLDER_ID and/or AGENTCORE_DRIVE_PHOTOS_FOLDER_ID.")
        write_json(summary_path, summary)
        print(json.dumps(summary, ensure_ascii=True))
        return 0

    token = ""
    try:
        token = gmail_api.access_token(env_map=env_map)
    except Exception as exc:  # pragma: no cover - runtime environment dependent
        summary["errors"].append(f"OAuth token unavailable: {exc}")
        write_json(summary_path, summary)
        print(json.dumps(summary, ensure_ascii=True))
        return 0

    task_dir = Path(args.task_dir)
    seen_current_max_ids: list[str] = []
    max_modified_time = str(prior_state.get("last_modified_time", ""))

    for source in sources:
        try:
            items = _list_files(
                token=token,
                source=source,
                modified_after=str(prior_state.get("last_modified_time", "")),
                limit=max(1, args.limit),
            )
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            summary["errors"].append(f"{source.name}: {exc.code} {detail}")
            continue
        except Exception as exc:  # pragma: no cover - runtime environment dependent
            summary["errors"].append(f"{source.name}: {exc}")
            continue

        for file_obj in items:
            modified_time = str(file_obj.get("modifiedTime", ""))
            file_id = str(file_obj.get("id", ""))
            if not file_id:
                continue
            if max_modified_time and modified_time < max_modified_time:
                continue
            if modified_time == str(prior_state.get("last_modified_time", "")) and file_id in prior_state.get(
                "seen_ids_at_last_modified_time", []
            ):
                continue

            created, record_path = _write_record(source, file_obj)
            if not created:
                continue
            summary["records_created"] += 1
            if source.classification == "photo_batch":
                summary["photos_created"] += 1
            else:
                summary["documents_created"] += 1

            if _write_task(task_dir=task_dir, source=source, file_obj=file_obj):
                summary["tasks_created"] += 1

            summary["created_items"].append(
                {
                    "source": source.name,
                    "classification": source.classification,
                    "drive_file_id": file_id,
                    "title": str(file_obj.get("name", "")),
                    "modified_time": modified_time,
                    "record_path": str(record_path),
                    "web_view_link": str(file_obj.get("webViewLink", "")),
                }
            )

            if not max_modified_time or modified_time > max_modified_time:
                max_modified_time = modified_time
                seen_current_max_ids = [file_id]
            elif modified_time == max_modified_time and file_id not in seen_current_max_ids:
                seen_current_max_ids.append(file_id)

    next_state = {
        "last_modified_time": max_modified_time,
        "seen_ids_at_last_modified_time": sorted(seen_current_max_ids),
        "updated_at": utc_now_iso(),
    }
    write_json(state_path, next_state)
    write_json(summary_path, summary)
    print(json.dumps(summary, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
