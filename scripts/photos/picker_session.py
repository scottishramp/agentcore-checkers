#!/usr/bin/env python3
"""Create and inspect Google Photos Picker sessions."""

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
from common import load_env_file  # noqa: E402

PICKER_API_ROOT = "https://photospicker.googleapis.com/v1"


class PhotosPickerError(RuntimeError):
    """Raised when the Google Photos Picker API returns an error."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manage Google Photos Picker sessions.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create", help="Create a Picker session.")
    create.add_argument("--max-items", type=int, default=50, help="Maximum items Brian can select.")

    get = subparsers.add_parser("get", help="Get Picker session status.")
    get.add_argument("session_id", help="Picker session id.")

    list_items = subparsers.add_parser("list", help="List media items selected for a session.")
    list_items.add_argument("session_id", help="Picker session id.")
    list_items.add_argument("--page-size", type=int, default=50, help="Maximum items per API page.")

    delete = subparsers.add_parser("delete", help="Delete a Picker session.")
    delete.add_argument("session_id", help="Picker session id.")

    return parser.parse_args()


def picker_request(token: str, method: str, path: str, payload: dict | None = None) -> dict:
    url = f"{PICKER_API_ROOT}/{path.lstrip('/')}"
    data = None
    headers = {"Authorization": f"Bearer {token}"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise PhotosPickerError(f"Picker API request failed: {method} {path}: {exc.code} {detail}") from exc
    return json.loads(raw) if raw else {}


def create_session(token: str, max_items: int) -> dict:
    payload: dict[str, dict[str, str]] = {}
    if max_items > 0:
        payload["pickingConfig"] = {"maxItemCount": str(max_items)}
    return picker_request(token, "POST", "sessions", payload=payload)


def list_media_items(token: str, session_id: str, page_size: int) -> dict:
    items = []
    page_token = ""
    while True:
        query = {
            "sessionId": session_id,
            "pageSize": str(max(1, min(page_size, 100))),
        }
        if page_token:
            query["pageToken"] = page_token
        payload = picker_request(token, "GET", f"mediaItems?{urllib.parse.urlencode(query)}")
        batch = payload.get("mediaItems", [])
        if isinstance(batch, list):
            items.extend(batch)
        page_token = str(payload.get("nextPageToken", ""))
        if not page_token:
            break
    return {"mediaItems": items}


def main() -> int:
    args = parse_args()
    env_map = load_env_file(".env")
    token = gmail_api.access_token(env_map=env_map)

    if args.command == "create":
        result = create_session(token, args.max_items)
    elif args.command == "get":
        result = picker_request(token, "GET", f"sessions/{urllib.parse.quote(args.session_id, safe='')}")
    elif args.command == "list":
        result = list_media_items(token, args.session_id, args.page_size)
    elif args.command == "delete":
        result = picker_request(token, "DELETE", f"sessions/{urllib.parse.quote(args.session_id, safe='')}")
    else:
        raise ValueError(f"Unsupported command: {args.command}")

    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
