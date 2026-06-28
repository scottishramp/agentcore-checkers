#!/usr/bin/env python3
"""Telegram Bot API helpers for runner-side media materialization."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request


def bot_token() -> str:
    return (
        os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        or os.getenv("AGENTCORE_TELEGRAM_BOT_TOKEN", "").strip()
    )


def download_file(file_id: str, max_bytes: int | None = None) -> tuple[bytes, str]:
    token = bot_token()
    if not token:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN.")
    limit = max_bytes or int(os.getenv("AGENTCORE_TELEGRAM_MAX_DOWNLOAD_BYTES", str(20 * 1024 * 1024)))

    meta_url = f"https://api.telegram.org/bot{token}/getFile?{urllib.parse.urlencode({'file_id': file_id})}"
    meta_request = urllib.request.Request(meta_url, method="GET")
    try:
        with urllib.request.urlopen(meta_request, timeout=60) as response:
            meta_payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Telegram getFile failed: {exc.code} {exc.read().decode('utf-8', errors='replace')}") from exc

    if not meta_payload.get("ok") or not isinstance(meta_payload.get("result"), dict):
        raise RuntimeError(f"Telegram getFile returned invalid payload: {meta_payload}")

    file_path = str(meta_payload["result"].get("file_path", "")).strip()
    if not file_path:
        raise RuntimeError("Telegram getFile did not return file_path.")

    file_size = int(meta_payload["result"].get("file_size") or 0)
    if file_size and file_size > limit:
        raise RuntimeError(f"Telegram file exceeds download limit ({file_size} > {limit}).")

    file_url = f"https://api.telegram.org/file/bot{token}/{file_path}"
    file_request = urllib.request.Request(file_url, method="GET")
    try:
        with urllib.request.urlopen(file_request, timeout=120) as response:
            content = response.read()
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Telegram file download failed: {exc.code}") from exc

    if len(content) > limit:
        raise RuntimeError(f"Telegram file exceeds download limit ({len(content)} > {limit}).")

    mime_type = "image/jpeg"
    lower = file_path.lower()
    if lower.endswith(".png"):
        mime_type = "image/png"
    elif lower.endswith(".webp"):
        mime_type = "image/webp"
    elif lower.endswith(".gif"):
        mime_type = "image/gif"
    return content, mime_type
