#!/usr/bin/env python3
"""Dispatch async runner workflow for event-driven pickup when work arrives."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dispatch runner workflow when tasks were created.")
    parser.add_argument("--summary", default=".agentcore/state/ingestion-summary.json", help="Combined summary JSON path.")
    parser.add_argument(
        "--workflow-id",
        default="agent-runner.yml",
        help="Workflow file name or workflow id to dispatch.",
    )
    parser.add_argument("--ref", default="", help="Git ref to dispatch on. Defaults to current branch/ref.")
    parser.add_argument("--force", action="store_true", help="Dispatch even when no tasks were created.")
    return parser.parse_args()


def _read_summary(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _resolve_ref(user_ref: str) -> str:
    if user_ref.strip():
        return user_ref.strip()
    github_head = os.getenv("GITHUB_REF_NAME", "").strip()
    if github_head:
        return github_head
    full_ref = os.getenv("GITHUB_REF", "").strip()
    if full_ref.startswith("refs/heads/"):
        return full_ref.split("/", 2)[-1]
    return "main"


def main() -> int:
    args = parse_args()
    summary = _read_summary(Path(args.summary))
    tasks_created = int((summary.get("totals") or {}).get("tasks_created", 0) or 0)
    should_dispatch = args.force or tasks_created > 0
    repository = os.getenv("GITHUB_REPOSITORY", "").strip()
    token = os.getenv("GITHUB_TOKEN", "").strip()
    ref_name = _resolve_ref(args.ref)

    payload = {
        "dispatched": False,
        "reason": "",
        "tasks_created": tasks_created,
        "workflow_id": args.workflow_id,
        "ref": ref_name,
    }

    if not should_dispatch:
        payload["reason"] = "No new tasks created."
        print(json.dumps(payload, ensure_ascii=True))
        return 0
    if not repository or not token:
        payload["reason"] = "Missing GITHUB_REPOSITORY or GITHUB_TOKEN."
        print(json.dumps(payload, ensure_ascii=True))
        return 0

    url = f"https://api.github.com/repos/{repository}/actions/workflows/{args.workflow_id}/dispatches"
    body = json.dumps({"ref": ref_name}).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30):
            pass
        payload["dispatched"] = True
        payload["reason"] = "Dispatched runner workflow."
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        payload["reason"] = f"Dispatch failed: HTTP {exc.code} {detail}"
    except Exception as exc:  # pragma: no cover - environment dependent
        payload["reason"] = f"Dispatch failed: {exc}"

    print(json.dumps(payload, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
