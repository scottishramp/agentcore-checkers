#!/usr/bin/env python3
"""Registry mapping fast-agent photo labels to Drive URLs and filing status."""

from __future__ import annotations

import json
from pathlib import Path

DEFAULT_REGISTRY_PATH = Path("agentcore/knowledge/communications/telegram-photo-registry.json")


def load_registry(path: Path = DEFAULT_REGISTRY_PATH) -> dict:
    if not path.exists():
        return {"version": 1, "photos": {}}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {"version": 1, "photos": {}}
    payload.setdefault("version", 1)
    payload.setdefault("photos", {})
    return payload


def save_registry(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def upsert_photo(path: Path, label: str, entry: dict) -> None:
    if not label:
        return
    payload = load_registry(path)
    photos = payload.setdefault("photos", {})
    existing = photos.get(label, {}) if isinstance(photos.get(label), dict) else {}
    merged = {**existing, **entry, "label": label}
    photos[label] = merged
    save_registry(path, payload)
