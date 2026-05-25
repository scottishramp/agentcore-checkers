#!/usr/bin/env python3
"""Write terminal queue state (`done` or `snag`) to a task file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import compact_whitespace, read_json, utc_now_iso
from task_queue import TASK_STATUS_DONE, TASK_STATUS_SNAG, load_task, save_task

DEFAULT_RESULT_PATH = ".agentcore/state/task-run-result.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Finalize a claimed queue task.")
    parser.add_argument("--task-file", required=True, help="Path to task markdown file.")
    parser.add_argument("--result-json", default=DEFAULT_RESULT_PATH, help="Result JSON path from runner.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    task = load_task(Path(args.task_file))
    result = read_json(Path(args.result_json), default={})

    status = str(result.get("status", "")).strip().lower()
    if status not in {TASK_STATUS_DONE, TASK_STATUS_SNAG}:
        status = TASK_STATUS_SNAG

    now = utc_now_iso()
    task.meta["status"] = status
    task.meta["updated_at"] = now
    if result.get("run_id"):
        task.meta["run_id"] = str(result.get("run_id"))
    if result.get("result_path"):
        task.meta["result_path"] = str(result.get("result_path"))
    elif args.result_json:
        task.meta["result_path"] = args.result_json

    if status == TASK_STATUS_DONE:
        task.meta["completed_at"] = now
        task.meta["snagged_at"] = ""
        task.meta["last_error"] = ""
    else:
        task.meta["snagged_at"] = now
        summary = compact_whitespace(str(result.get("summary", "")))
        error_text = compact_whitespace(str(result.get("error", "")))
        task.meta["last_error"] = summary or error_text or "Task run ended in snag state."

    save_task(task)
    payload = {
        "task_file": args.task_file,
        "task_id": str(task.meta.get("task_id", "")),
        "status": status,
        "updated_at": now,
    }
    print(json.dumps(payload, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
