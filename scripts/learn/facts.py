"""Durable fact page shared by the nightly mailbox sweep and calendar ingest.

Facts are short standalone sentences filed under a category heading and dated. Both
writers go through :func:`append` so the page keeps one shape and one dedupe rule no
matter which job learned the fact.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

FACTS_PATH = Path("agentcore/knowledge/people/brian-learned-facts.md")

CATEGORIES = [
    "finance",
    "health",
    "home",
    "work",
    "family",
    "travel",
    "subscriptions",
    "commitments",
    "other",
]

# Two facts are "the same" when one phrasing contains the other, which catches the common
# case of a later email restating a fact with a few extra words.
CONTAINMENT_MIN_LENGTH = 25


def normalize_category(value: str) -> str:
    category = str(value or "other").strip().lower()
    return category if category in CATEGORIES else "other"


def fingerprint(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(text).lower()).strip()


def _header_lines() -> list[str]:
    lines = [
        "# Brian Learned Facts",
        "",
        "Durable facts about Brian and the household, learned automatically by the nightly",
        "mailbox sweep and calendar ingest. Each bullet is dated. Source messages stay in Gmail",
        "and Google Calendar; only distilled facts live here.",
        "",
    ]
    for category in CATEGORIES:
        lines.extend([f"## {category.title()}", ""])
    return lines


def ensure_page(path: Path = FACTS_PATH) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(_header_lines()), encoding="utf-8")


BULLET_DATE_RE = re.compile(r"^-\s*\d{4}-\d{2}-\d{2}:\s*")


def existing_fingerprints(lines: list[str]) -> set[str]:
    """Fingerprint recorded facts without their date prefix so restatements still match."""
    return {fingerprint(BULLET_DATE_RE.sub("", line)) for line in lines if line.startswith("- ")}


def is_duplicate(candidate: str, seen: set[str]) -> bool:
    if not candidate or candidate in seen:
        return True
    return any(
        candidate in known or known in candidate
        for known in seen
        if len(known) >= CONTAINMENT_MIN_LENGTH and len(candidate) >= CONTAINMENT_MIN_LENGTH
    )


def append(items: list[dict], path: Path = FACTS_PATH) -> list[str]:
    """Append new facts under their category heading. Returns the texts actually added."""
    if not items:
        return []
    ensure_page(path)
    lines = path.read_text(encoding="utf-8").splitlines()
    seen = existing_fingerprints(lines)
    today = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")
    added: list[str] = []

    for item in items:
        text = str(item.get("text") or "").strip()
        candidate = fingerprint(text)
        if not text or is_duplicate(candidate, seen):
            continue
        heading = f"## {normalize_category(item.get('category', '')).title()}"
        if heading not in lines:
            lines.extend(["", heading, ""])
        # Rewrite the whole category block so spacing stays uniform however it was left.
        start = lines.index(heading) + 1
        end = start
        while end < len(lines) and not lines[end].startswith("## "):
            end += 1
        bullets = [line for line in lines[start:end] if line.strip()]
        bullets.append(f"- {today}: {text}")
        lines[start:end] = ["", *bullets, ""]
        seen.add(candidate)
        added.append(text)

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return added
