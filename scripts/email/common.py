"""Shared helpers for AgentCore email automation scripts."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from email.header import decode_header, make_header
from email.message import Message
from email.utils import parseaddr
from pathlib import Path
from typing import Iterable


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_env_file(path: str = ".env") -> dict[str, str]:
    env_map: dict[str, str] = {}
    env_path = Path(path)
    if not env_path.exists():
        return env_map

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env_map[key.strip()] = value.strip()
    return env_map


def get_env(
    key: str,
    fallback_keys: Iterable[str] | None = None,
    default: str | None = None,
    required: bool = False,
    env_map: dict[str, str] | None = None,
) -> str:
    lookup = [key]
    if fallback_keys:
        lookup.extend(list(fallback_keys))

    for candidate in lookup:
        value = os.getenv(candidate)
        if value:
            return value
        if env_map and env_map.get(candidate):
            return env_map[candidate]

    if default is not None:
        return default
    if required:
        joined = ", ".join(lookup)
        raise ValueError(f"Missing required environment variable: one of [{joined}]")
    return ""


def resolve_email_credentials(env_map: dict[str, str] | None = None) -> tuple[str, str]:
    username = get_env(
        "AGENTCORE_EMAIL",
        fallback_keys=("GOOGLE_EMAIL",),
        required=True,
        env_map=env_map,
    )
    password = get_env(
        "AGENTCORE_EMAIL_APP_PASSWORD",
        fallback_keys=("GOOGLE_PASSWORD",),
        required=True,
        env_map=env_map,
    )
    return username, password


def resolve_email_address(env_map: dict[str, str] | None = None) -> str:
    return get_env(
        "AGENTCORE_EMAIL",
        fallback_keys=("GOOGLE_EMAIL",),
        required=True,
        env_map=env_map,
    )


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def read_json(path: Path, default: dict | list | None = None):
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict | list) -> None:
    ensure_parent_dir(path)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def decode_mime_header(value: str | None) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value


def compact_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def sanitize_filename(text: str, fallback: str = "item") -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", text).strip("-._")
    return cleaned or fallback


def normalize_email_address(raw: str | None) -> str:
    if not raw:
        return ""
    _, addr = parseaddr(raw)
    return (addr or "").strip().lower()


def normalize_subject(raw_subject: str | None) -> str:
    subject = decode_mime_header(raw_subject)
    return compact_whitespace(subject)


def make_thread_key(message_id: str, subject: str) -> str:
    if message_id:
        return sanitize_filename(message_id.lower(), fallback="thread")
    normalized = re.sub(r"^(re:|fwd:|fw:)\s*", "", subject.lower())
    return sanitize_filename(normalized, fallback="thread")


def _decode_part(part: Message) -> str:
    payload = part.get_payload(decode=True)
    if payload is None:
        return ""
    charset = part.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset, errors="replace")
    except LookupError:
        return payload.decode("utf-8", errors="replace")


def message_body_text(msg: Message) -> str:
    if msg.is_multipart():
        plain_parts: list[str] = []
        html_parts: list[str] = []
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = (part.get("Content-Disposition") or "").lower()
            if "attachment" in content_disposition:
                continue
            if content_type == "text/plain":
                plain_parts.append(_decode_part(part))
            elif content_type == "text/html":
                html_parts.append(_decode_part(part))
        if plain_parts:
            return "\n\n".join([p.strip() for p in plain_parts if p.strip()]).strip()
        if html_parts:
            no_tags = re.sub(r"<[^>]+>", " ", "\n\n".join(html_parts))
            return compact_whitespace(no_tags)
        return ""

    return _decode_part(msg).strip()
