#!/usr/bin/env python3
"""Process all remaining queued tasks in one runner invocation.

This script loops through the task queue, processing each task until
the queue is empty or the time budget is exhausted. It handles the
full lifecycle: claim → execute → finalize → respond → ledger.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
EMAIL_DIR = SCRIPT_DIR.parent / "email"
TELEGRAM_DIR = SCRIPT_DIR.parent / "telegram"

for p in (str(EMAIL_DIR), str(TELEGRAM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from common import read_json, utc_now_iso, write_json  # noqa: E402
from task_queue import (  # noqa: E402
    TASK_STATUS_DONE,
    TASK_STATUS_IN_PROGRESS,
    TASK_STATUS_QUEUED,
    TASK_STATUS_SNAG,
    list_task_files,
    load_task,
    save_task,
    sort_key_for_queue,
)

TASK_DIR = REPO_ROOT / "agentcore" / "inbox" / "tasks"
MAX_MINUTES = int(os.getenv("AGENTCORE_DRAIN_MAX_MINUTES", "30"))
TASK_TIMEOUT = int(os.getenv("AGENTCORE_CURSOR_TIMEOUT_SECONDS", "1200"))
MAX_CLIENT_REPLY_CHARS = 4096


def _runner_id() -> str:
    run_id = os.getenv("GITHUB_RUN_ID", "").strip()
    return run_id or f"local-drain-{utc_now_iso()}"


def claim_next() -> Path | None:
    """Claim the oldest queued task. Returns task path or None."""
    candidates = []
    for task_path in list_task_files(TASK_DIR):
        task = load_task(task_path)
        if str(task.meta.get("status", "")) == TASK_STATUS_QUEUED:
            candidates.append(task)

    if not candidates:
        return None

    candidates.sort(key=sort_key_for_queue)
    target = candidates[0]
    target.meta["status"] = TASK_STATUS_IN_PROGRESS
    target.meta["claimed_at"] = utc_now_iso()
    target.meta["updated_at"] = utc_now_iso()
    target.meta["run_id"] = _runner_id()
    target.meta["attempts"] = int(target.meta.get("attempts", 0) or 0) + 1
    save_task(target)
    return target.path


def run_cursor_task(task_file: Path) -> dict:
    """Execute the Cursor agent on a task file."""
    command = os.getenv(
        "AGENTCORE_TASK_RUN_COMMAND",
        f"python3 scripts/agent/run_cursor_task.py --task-file {{{{TASK_FILE}}}} --workspace .",
    ).replace("{{TASK_FILE}}", str(task_file))

    try:
        proc = subprocess.run(
            command,
            shell=True,
            text=True,
            capture_output=True,
            timeout=max(60, TASK_TIMEOUT),
            check=False,
            cwd=str(REPO_ROOT),
        )
        summary = proc.stdout.strip()
        if proc.returncode == 0:
            if len(summary) > MAX_CLIENT_REPLY_CHARS:
                summary = summary[: MAX_CLIENT_REPLY_CHARS - 1] + "…"
            return {"status": TASK_STATUS_DONE, "summary": summary or "Done.", "exit_code": proc.returncode}
        else:
            error = proc.stderr.strip()[:600] or f"Exit code {proc.returncode}"
            return {"status": TASK_STATUS_SNAG, "summary": summary[:600] or error, "error": error, "exit_code": proc.returncode}
    except subprocess.TimeoutExpired:
        return {"status": TASK_STATUS_SNAG, "summary": "Task timed out.", "error": f"Timeout after {TASK_TIMEOUT}s"}


def finalize_task(task_file: Path, result: dict) -> None:
    """Update task status to done or snag."""
    task = load_task(task_file)
    status = result.get("status", TASK_STATUS_SNAG)
    now = utc_now_iso()
    task.meta["status"] = status
    task.meta["updated_at"] = now
    if status == TASK_STATUS_DONE:
        task.meta["completed_at"] = now
        task.meta["last_error"] = ""
    else:
        task.meta["snagged_at"] = now
        task.meta["last_error"] = result.get("error", "Unknown error")
    save_task(task)


def send_response(task_file: Path, result: dict) -> dict:
    """Send Chat or email response for the completed task."""
    task = load_task(task_file)
    source_kind = str(task.meta.get("source_kind", "")).strip().lower()
    status = result.get("status", TASK_STATUS_SNAG)

    tmp_result = REPO_ROOT / ".agentcore" / "state" / "drain-task-result.json"
    tmp_result.parent.mkdir(parents=True, exist_ok=True)
    write_json(tmp_result, {"status": status, "summary": result.get("summary", ""), "error": result.get("error", "")})

    if source_kind == "telegram":
        cmd = [
            sys.executable, str(TELEGRAM_DIR / "send_task_response.py"),
            "--task-file", str(task_file),
            "--status", "done" if status == TASK_STATUS_DONE else "snag",
            "--result-json", str(tmp_result),
        ]
    else:
        cmd = [
            sys.executable, str(EMAIL_DIR / "send_task_status.py"),
            "--task-file", str(task_file),
            "--status", "done" if status == TASK_STATUS_DONE else "snag",
            "--result-json", "/dev/null",
            "--project", "AsyncLoop",
        ]
        tmp_result = REPO_ROOT / ".agentcore" / "state" / "drain-task-result.json"
        tmp_result.parent.mkdir(parents=True, exist_ok=True)
        write_json(tmp_result, {"status": status, "summary": result.get("summary", ""), "error": result.get("error", "")})
        cmd[cmd.index("/dev/null")] = str(tmp_result)

    proc = subprocess.run(cmd, text=True, capture_output=True, check=False, cwd=str(REPO_ROOT))
    try:
        return json.loads(proc.stdout.strip()) if proc.stdout.strip() else {}
    except json.JSONDecodeError:
        return {"raw_output": proc.stdout[:200]}


def record_ledger(task_file: Path, result: dict, notification: dict) -> None:
    """Record the response in the appropriate ledger."""
    task = load_task(task_file)
    source_kind = str(task.meta.get("source_kind", "")).strip().lower()

    tmp_result = REPO_ROOT / ".agentcore" / "state" / "drain-task-result.json"
    tmp_notify = REPO_ROOT / ".agentcore" / "state" / "drain-notify-result.json"
    write_json(tmp_result, {"status": result.get("status", ""), "summary": result.get("summary", "")})
    write_json(tmp_notify, notification)

    if source_kind == "telegram":
        return
    else:
        cmd = [
            sys.executable, str(EMAIL_DIR / "record_email_response.py"),
            "--task-file", str(task_file),
            "--result-json", str(tmp_result),
            "--notification-json", str(tmp_notify),
        ]

    subprocess.run(cmd, text=True, capture_output=True, check=False, cwd=str(REPO_ROOT))


def main() -> int:
    start = time.time()
    deadline = start + (MAX_MINUTES * 60)
    processed = []

    while time.time() < deadline:
        task_path = claim_next()
        if task_path is None:
            break

        task = load_task(task_path)
        task_id = str(task.meta.get("task_id", ""))
        print(f"[drain] Processing: {task_id}", file=sys.stderr)

        result = run_cursor_task(task_path)
        finalize_task(task_path, result)
        notification = send_response(task_path, result)
        record_ledger(task_path, result, notification)

        processed.append({
            "task_id": task_id,
            "status": result.get("status", ""),
            "task_file": str(task_path),
        })

    summary = {
        "drain_completed": True,
        "tasks_processed": len(processed),
        "elapsed_seconds": round(time.time() - start, 1),
        "tasks": processed,
    }
    print(json.dumps(summary, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
