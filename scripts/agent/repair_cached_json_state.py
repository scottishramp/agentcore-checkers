#!/usr/bin/env python3
"""Repair invalid JSON files restored from GitHub Actions cache."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

DEFAULT_PATHS = (
    "agentcore/knowledge/communications/email-thread-ledger.json",
    "agentcore/knowledge/communications/chat-thread-ledger.json",
    "agentcore/knowledge/communications/scheduled-messages-state.json",
)
CONFLICT_MARKERS = ("<<<<<<< ", "=======", ">>>>>>> ")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Repair invalid cached JSON state from HEAD.")
    parser.add_argument("paths", nargs="*", default=list(DEFAULT_PATHS), help="JSON files to validate and repair.")
    return parser.parse_args()


def has_conflict_markers(text: str) -> bool:
    return any(line.strip().startswith(CONFLICT_MARKERS) for line in text.splitlines())


def is_valid_json(path: Path) -> bool:
    if not path.exists():
        return True
    try:
        text = path.read_text(encoding="utf-8")
        if has_conflict_markers(text):
            return False
        json.loads(text)
        return True
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return False


def committed_content(path: Path) -> str | None:
    proc = subprocess.run(
        ["git", "show", f"HEAD:{path.as_posix()}"],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        return None
    return proc.stdout


def repair(path: Path) -> bool:
    text = committed_content(path)
    if text is None:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return is_valid_json(path)


def main() -> int:
    args = parse_args()
    repaired: list[str] = []
    failed: list[str] = []

    for raw_path in args.paths:
        path = Path(raw_path)
        if is_valid_json(path):
            continue
        if repair(path):
            repaired.append(raw_path)
        else:
            failed.append(raw_path)

    if repaired:
        print(json.dumps({"status": "repaired", "paths": repaired}, ensure_ascii=True))
    else:
        print(json.dumps({"status": "ok", "paths_checked": args.paths}, ensure_ascii=True))

    if failed:
        print(f"Failed to repair invalid cached JSON state: {', '.join(failed)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
