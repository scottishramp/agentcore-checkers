#!/usr/bin/env python3
"""Activate deferred content-ingest tasks once exported source material is available."""

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

from common import utc_now_iso, write_json  # noqa: E402
from task_queue import TASK_STATUS_QUEUED, list_task_files, load_task, save_task  # noqa: E402

DEFAULT_TASK_DIR = "agentcore/inbox/tasks"
DEFAULT_ALLOWLIST = "agentcore/knowledge/documents/content-ingest-allowlist.json"
DEFAULT_DRIVE_CONTENT_DIR = ".agentcore/state/drive-content"
DEFAULT_SUMMARY_PATH = ".agentcore/state/content-task-activation-summary.json"
DRIVE_CONTENT_RE = re.compile(r"\.agentcore/state/drive-content/([A-Za-z0-9_-]+)\.txt")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Flip deferred content-ingest tasks to queued.")
    parser.add_argument("--task-dir", default=DEFAULT_TASK_DIR, help="Task queue directory.")
    parser.add_argument("--allowlist", default=DEFAULT_ALLOWLIST, help="Content ingest allowlist JSON.")
    parser.add_argument("--drive-content-dir", default=DEFAULT_DRIVE_CONTENT_DIR, help="Exported Drive text dir.")
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_PATH, help="Summary JSON path.")
    return parser.parse_args()


def _load_allowlist_task_map(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    mapping: dict[str, str] = {}
    for entry in payload.get("drive_files", []):
        if not isinstance(entry, dict):
            continue
        task_id = str(entry.get("deferred_task_id", "")).strip()
        file_id = str(entry.get("drive_file_id", "")).strip()
        if task_id and file_id:
            mapping[task_id] = file_id
    return mapping


def _drive_content_ready(drive_content_dir: Path, file_id: str) -> bool:
    path = drive_content_dir / f"{file_id}.txt"
    if not path.exists():
        return False
    return bool(path.read_text(encoding="utf-8", errors="replace").strip())


def _referenced_drive_ids(body: str) -> list[str]:
    return DRIVE_CONTENT_RE.findall(body)


def _activate_task(
    task,
    drive_content_dir: Path,
    allowlist_map: dict[str, str],
) -> tuple[bool, str]:
    status = str(task.meta.get("status", "")).strip().lower()
    if status != "deferred":
        return False, "not_deferred"

    task_id = str(task.meta.get("task_id", "")).strip()
    allowlisted_file_id = allowlist_map.get(task_id, "")
    if allowlisted_file_id and _drive_content_ready(drive_content_dir, allowlisted_file_id):
        task.meta["status"] = TASK_STATUS_QUEUED
        task.meta["updated_at"] = utc_now_iso()
        task.meta["activation_note"] = f"Activated after Drive export for {allowlisted_file_id}"
        save_task(task)
        return True, f"allowlist:{allowlisted_file_id}"

    for file_id in _referenced_drive_ids(task.body):
        if _drive_content_ready(drive_content_dir, file_id):
            task.meta["status"] = TASK_STATUS_QUEUED
            task.meta["updated_at"] = utc_now_iso()
            task.meta["activation_note"] = f"Activated after Drive export for {file_id}"
            save_task(task)
            return True, f"body_ref:{file_id}"

    return False, "content_not_ready"


def main() -> int:
    args = parse_args()
    task_dir = Path(args.task_dir)
    drive_content_dir = Path(args.drive_content_dir)
    allowlist_map = _load_allowlist_task_map(Path(args.allowlist))

    summary = {
        "activated_at": utc_now_iso(),
        "activated": [],
        "still_deferred": [],
        "skipped": [],
    }

    for task_path in list_task_files(task_dir):
        task = load_task(task_path)
        activated, reason = _activate_task(task, drive_content_dir, allowlist_map)
        entry = {
            "task_file": str(task_path),
            "task_id": str(task.meta.get("task_id", "")),
            "reason": reason,
        }
        if activated:
            summary["activated"].append(entry)
        elif str(task.meta.get("status", "")).strip().lower() == "deferred":
            summary["still_deferred"].append(entry)
        else:
            summary["skipped"].append(entry)

    write_json(Path(args.summary_output), summary)
    print(json.dumps(summary, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
