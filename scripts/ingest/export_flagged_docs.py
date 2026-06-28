#!/usr/bin/env python3
"""Export allowlisted Google Drive documents to local text for knowledge content ingest."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
EMAIL_DIR = SCRIPT_DIR.parent / "email"
if str(EMAIL_DIR) not in sys.path:
    sys.path.insert(0, str(EMAIL_DIR))

import gmail_api  # noqa: E402
from common import get_env, load_env_file, utc_now_iso, write_json  # noqa: E402

DRIVE_API_BASE = "https://www.googleapis.com/drive/v3"
DEFAULT_ALLOWLIST = "agentcore/knowledge/documents/content-ingest-allowlist.json"
DEFAULT_OUTPUT_DIR = ".agentcore/state/drive-content"
DEFAULT_SUMMARY_PATH = ".agentcore/state/drive-content-export-summary.json"

GOOGLE_EXPORT_MIMES = {
    "application/vnd.google-apps.document": "text/plain",
    "application/vnd.google-apps.spreadsheet": "text/csv",
    "application/vnd.google-apps.presentation": "text/plain",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export allowlisted Drive docs to local text files.")
    parser.add_argument("--allowlist", default=DEFAULT_ALLOWLIST, help="Content ingest allowlist JSON.")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Directory for exported text files.")
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_PATH, help="Summary JSON path.")
    parser.add_argument("--force", action="store_true", help="Re-export even when export file already exists.")
    return parser.parse_args()


def _drive_get(token: str, file_id: str, fields: str = "id,name,mimeType,modifiedTime") -> dict:
    query = urllib.parse.urlencode({"fields": fields, "supportsAllDrives": "true"})
    url = f"{DRIVE_API_BASE}/files/{file_id}?{query}"
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"}, method="GET")
    with urllib.request.urlopen(request, timeout=60) as response:
        body = response.read().decode("utf-8")
    return json.loads(body) if body else {}


def _drive_export(token: str, file_id: str, mime_type: str) -> bytes:
    query = urllib.parse.urlencode({"mimeType": mime_type})
    url = f"{DRIVE_API_BASE}/files/{file_id}/export?{query}"
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"}, method="GET")
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def _drive_download(token: str, file_id: str) -> bytes:
    query = urllib.parse.urlencode({"alt": "media", "supportsAllDrives": "true"})
    url = f"{DRIVE_API_BASE}/files/{file_id}?{query}"
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"}, method="GET")
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def load_allowlist(path: Path) -> list[dict]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    files = payload.get("drive_files", [])
    return files if isinstance(files, list) else []


def export_entry(
    token: str,
    entry: dict,
    output_dir: Path,
    force: bool,
) -> dict:
    file_id = str(entry.get("drive_file_id", "")).strip()
    title = str(entry.get("title", "")).strip() or file_id
    preferred_mime = str(entry.get("export_mime", "")).strip()
    output_path = output_dir / f"{file_id}.txt"

    result = {
        "drive_file_id": file_id,
        "title": title,
        "output_path": str(output_path),
        "exported": False,
        "skipped": False,
        "bytes": 0,
        "error": "",
    }

    if not file_id:
        result["error"] = "Missing drive_file_id"
        return result

    if output_path.exists() and not force:
        text = output_path.read_text(encoding="utf-8", errors="replace")
        if text.strip():
            result["skipped"] = True
            result["bytes"] = len(text.encode("utf-8"))
            return result

    try:
        meta = _drive_get(token, file_id)
        mime_type = str(meta.get("mimeType", ""))
        if mime_type in GOOGLE_EXPORT_MIMES:
            export_mime = preferred_mime or GOOGLE_EXPORT_MIMES[mime_type]
            content = _drive_export(token, file_id, export_mime)
        elif mime_type.startswith("text/") or mime_type in {"application/json", "application/pdf"}:
            content = _drive_download(token, file_id)
        else:
            result["error"] = f"Unsupported mime type for export: {mime_type}"
            return result

        text = content.decode("utf-8", errors="replace")
        if not text.strip():
            result["error"] = "Export returned empty content"
            return result

        output_dir.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text, encoding="utf-8")
        result["exported"] = True
        result["bytes"] = len(content)
        result["modified_time"] = str(meta.get("modifiedTime", ""))
        result["mime_type"] = mime_type
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        result["error"] = f"HTTP {exc.code}: {detail[:500]}"
    except Exception as exc:  # pragma: no cover - runtime environment dependent
        result["error"] = str(exc)

    return result


def main() -> int:
    args = parse_args()
    env_map = load_env_file(".env")
    allowlist_path = Path(args.allowlist)
    output_dir = Path(args.output_dir)
    summary_path = Path(args.summary_output)

    summary = {
        "exported_at": utc_now_iso(),
        "allowlist": str(allowlist_path),
        "output_dir": str(output_dir),
        "entries": [],
        "exported_count": 0,
        "skipped_count": 0,
        "error_count": 0,
        "errors": [],
    }

    entries = load_allowlist(allowlist_path)
    if not entries:
        summary["errors"].append(f"No allowlist entries found at {allowlist_path}")
        write_json(summary_path, summary)
        print(json.dumps(summary, ensure_ascii=True))
        return 0

    try:
        token = gmail_api.access_token(env_map=env_map)
    except Exception as exc:  # pragma: no cover - runtime environment dependent
        summary["errors"].append(f"OAuth token unavailable: {exc}")
        write_json(summary_path, summary)
        print(json.dumps(summary, ensure_ascii=True))
        return 1

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        result = export_entry(token=token, entry=entry, output_dir=output_dir, force=args.force)
        summary["entries"].append(result)
        if result.get("exported"):
            summary["exported_count"] += 1
        elif result.get("skipped"):
            summary["skipped_count"] += 1
        elif result.get("error"):
            summary["error_count"] += 1
            summary["errors"].append(f"{result.get('title', '')}: {result['error']}")

    write_json(summary_path, summary)
    print(json.dumps(summary, ensure_ascii=True))
    return 0 if summary["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
