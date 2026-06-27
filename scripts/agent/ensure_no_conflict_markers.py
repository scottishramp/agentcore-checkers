#!/usr/bin/env python3
"""Fail CI if unresolved merge-conflict markers are present."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

MARKERS = ("<<<<<<< ", "=======", ">>>>>>> ")


def tracked_paths() -> list[Path]:
    proc = subprocess.run(
        ["git", "ls-files"],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        print(proc.stderr.strip() or "git ls-files failed", file=sys.stderr)
        return []
    return [Path(line) for line in proc.stdout.splitlines() if line.strip()]


def marker_locations(path: Path) -> list[tuple[int, str]]:
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []

    locations: list[tuple[int, str]] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if any(stripped.startswith(marker) for marker in MARKERS):
            locations.append((line_no, stripped))
    return locations


def main() -> int:
    failures: list[str] = []
    for path in tracked_paths():
        if not path.exists() or path.is_dir():
            continue
        for line_no, marker in marker_locations(path):
            failures.append(f"{path}:{line_no}: {marker}")

    if failures:
        print("Unresolved merge-conflict markers found; refusing to commit:", file=sys.stderr)
        for item in failures:
            print(f"  {item}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
