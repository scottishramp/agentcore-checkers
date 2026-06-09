#!/usr/bin/env python3
"""Claim the next queued task for async runner execution."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from common import utc_now_iso
from task_queue import (
    TASK_STATUS_IN_PROGRESS,
    TASK_STATUS_QUEUED,
    TaskRecord,
    is_stale_claimed,
    list_task_files,
    load_task,
    queue_lock,
    save_task,
    sort_key_for_queue,
    write_json,
)

DEFAULT_TASK_DIR = "agentcore/inbox/tasks"
DEFAULT_OUTPUT_PATH = ".agentcore/state/task-claim.json"
DEFAULT_LOCK_PATH = ".agentcore/state/task-queue.lock"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Claim oldest queued task record.")
    parser.add_argument("--task-dir", default=DEFAULT_TASK_DIR, help="Task queue directory.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH, help="Output JSON summary path.")
    parser.add_argument("--lock-file", default=DEFAULT_LOCK_PATH, help="Lock file for queue claim operations.")
    parser.add_argument(
        "--stale-minutes",
        type=int,
        default=120,
        help="Requeue tasks stuck in progress beyond this age.",
    )
    parser.add_argument(
        "--runner-id",
        default="",
        help="Runner/run identifier. Defaults to GITHUB_RUN_ID or timestamp.",
    )
    parser.add_argument(
        "--source-kind",
        default="",
        help="Optional task source_kind filter, such as google_chat.",
    )
    return parser.parse_args()


def _runner_id(args: argparse.Namespace) -> str:
    if args.runner_id.strip():
        return args.runner_id.strip()
    run_id = os.getenv("GITHUB_RUN_ID", "").strip()
    if run_id:
        return run_id
    return f"local-{utc_now_iso()}"


def _requeue_stale(task: TaskRecord, reason: str) -> None:
    task.meta["status"] = TASK_STATUS_QUEUED
    task.meta["updated_at"] = utc_now_iso()
    task.meta["claimed_at"] = ""
    task.meta["run_id"] = ""
    task.meta["last_error"] = reason
    save_task(task)


def main() -> int:
    args = parse_args()
    task_dir = Path(args.task_dir)
    output_path = Path(args.output)
    lock_path = Path(args.lock_file)
    runner_id = _runner_id(args)

    task_dir.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    stale_requeued = 0
    queued_candidates: list[TaskRecord] = []
    claimed_payload = {
        "claimed": False,
        "runner_id": runner_id,
        "task_file": "",
        "task_id": "",
        "thread_key": "",
        "status": "",
        "stale_requeued": 0,
    }

    with queue_lock(lock_path):
        for task_path in list_task_files(task_dir):
            task = load_task(task_path)
            if is_stale_claimed(task, stale_after_minutes=args.stale_minutes):
                stale_requeued += 1
                _requeue_stale(task, reason="Requeued after stale in_progress lock timeout.")
                task = load_task(task_path)
            if str(task.meta.get("status", "")) == TASK_STATUS_QUEUED:
                if args.source_kind and str(task.meta.get("source_kind", "")).strip().lower() != args.source_kind:
                    continue
                queued_candidates.append(task)

        if queued_candidates:
            queued_candidates.sort(key=sort_key_for_queue)
            target = queued_candidates[0]
            target.meta["status"] = TASK_STATUS_IN_PROGRESS
            target.meta["claimed_at"] = utc_now_iso()
            target.meta["updated_at"] = utc_now_iso()
            target.meta["run_id"] = runner_id
            attempts = int(target.meta.get("attempts", 0) or 0)
            target.meta["attempts"] = attempts + 1
            save_task(target)

            claimed_payload.update(
                {
                    "claimed": True,
                    "task_file": str(target.path),
                    "task_id": str(target.meta.get("task_id", "")),
                    "thread_key": str(target.meta.get("thread_key", "")),
                    "status": TASK_STATUS_IN_PROGRESS,
                }
            )

    claimed_payload["stale_requeued"] = stale_requeued
    write_json(output_path, claimed_payload)
    print(json.dumps(claimed_payload, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
