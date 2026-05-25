#!/usr/bin/env python3
"""Combine channel-level ingestion outputs into one deterministic summary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from datetime import datetime, timezone


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build combined ingestion summary.")
    parser.add_argument("--email-summary", default=".agentcore/state/email-sync-summary.json", help="Email summary JSON path.")
    parser.add_argument("--drive-summary", default=".agentcore/state/drive-ingest-summary.json", help="Drive summary JSON path.")
    parser.add_argument(
        "--output",
        default=".agentcore/state/ingestion-summary.json",
        help="Combined ingestion summary output path.",
    )
    return parser.parse_args()


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    args = parse_args()
    email_summary = _read_json(Path(args.email_summary))
    drive_summary = _read_json(Path(args.drive_summary))

    email_tasks = int(email_summary.get("tasks_created", 0) or 0)
    drive_tasks = int(drive_summary.get("tasks_created", 0) or 0)
    email_records = int(email_summary.get("normalized_count", 0) or 0)
    drive_records = int(drive_summary.get("records_created", 0) or 0)

    errors: list[str] = []
    for item in email_summary.get("errors", []) if isinstance(email_summary.get("errors"), list) else []:
        errors.append(f"email:{item}")
    for item in drive_summary.get("errors", []) if isinstance(drive_summary.get("errors"), list) else []:
        errors.append(f"drive:{item}")

    reason_codes: list[str] = []
    if email_tasks > 0:
        reason_codes.append("NEW_EMAIL_TASKS")
    if int(drive_summary.get("documents_created", 0) or 0) > 0:
        reason_codes.append("NEW_DOCUMENTS")
    if int(drive_summary.get("photos_created", 0) or 0) > 0:
        reason_codes.append("NEW_PHOTOS")
    if not reason_codes:
        reason_codes.append("NO_NEW_ITEMS")
    if errors:
        reason_codes.append("RUNNER_SNAG")

    combined = {
        "generated_at": _now_iso(),
        "email": {
            "normalized_count": email_records,
            "tasks_created": email_tasks,
            "classifications": email_summary.get("classifications", {}),
        },
        "drive": {
            "records_created": drive_records,
            "documents_created": int(drive_summary.get("documents_created", 0) or 0),
            "photos_created": int(drive_summary.get("photos_created", 0) or 0),
            "tasks_created": drive_tasks,
        },
        "totals": {
            "records_created": email_records + drive_records,
            "tasks_created": email_tasks + drive_tasks,
        },
        "reason_codes": reason_codes,
        "errors": errors,
    }
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(combined, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(json.dumps(combined, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
