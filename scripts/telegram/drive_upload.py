#!/usr/bin/env python3
"""Upload bytes to AgentCore Google Drive."""

from __future__ import annotations

import json
import os
import uuid
import urllib.error
import urllib.request

SCRIPT_DIR = __file__
EMAIL_DIR = os.path.join(os.path.dirname(__file__), "..", "email")
import sys

if EMAIL_DIR not in sys.path:
    sys.path.insert(0, EMAIL_DIR)

import gmail_api  # noqa: E402


def upload_bytes(
    content: bytes,
    filename: str,
    mime_type: str,
    folder_id: str = "",
) -> dict:
    token = gmail_api.access_token()
    metadata = {"name": filename}
    if folder_id:
        metadata["parents"] = [folder_id]

    boundary = f"agentcore-{uuid.uuid4().hex}"
    meta_part = json.dumps(metadata, ensure_ascii=True).encode("utf-8")
    body = (
        f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n".encode("utf-8")
        + meta_part
        + f"\r\n--{boundary}\r\nContent-Type: {mime_type}\r\n\r\n".encode("utf-8")
        + content
        + f"\r\n--{boundary}--\r\n".encode("utf-8")
    )
    request = urllib.request.Request(
        "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,name,mimeType,webViewLink,createdTime,modifiedTime",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/related; boundary={boundary}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Drive upload failed: {exc.code} {detail}") from exc
    return payload


def target_folder_id() -> str:
    return (
        os.getenv("AGENTCORE_TELEGRAM_DRIVE_FOLDER_ID", "").strip()
        or os.getenv("AGENTCORE_DRIVE_PHOTOS_FOLDER_ID", "").strip()
    )
