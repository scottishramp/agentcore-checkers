#!/usr/bin/env python3
"""Minimal Upstash Redis REST client for Telegram inbox scripts."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


def redis_config() -> tuple[str, str]:
    url = (
        os.getenv("UPSTASH_REDIS_REST_URL", "").strip()
        or os.getenv("KV_REST_API_URL", "").strip()
    ).rstrip("/")
    token = (
        os.getenv("UPSTASH_REDIS_REST_TOKEN", "").strip()
        or os.getenv("KV_REST_API_TOKEN", "").strip()
    )
    return url, token


def redis_command(command: list) -> dict:
    url, token = redis_config()
    if not url or not token:
        return {"configured": False, "result": None}
    payload = json.dumps(command, ensure_ascii=True).encode("utf-8")
    request = urllib.request.Request(
        url=url,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
            parsed = json.loads(raw) if raw else {}
            if response.status >= 400:
                raise RuntimeError(f"Upstash error {response.status}: {parsed}")
            return {"configured": True, "result": parsed.get("result")}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Upstash HTTP {exc.code}: {raw}") from exc


TELEGRAM_INBOX_KEY = "agentcore:telegram:inbox"
