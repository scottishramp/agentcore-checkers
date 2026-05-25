#!/usr/bin/env python3
"""Run one claimed task using a CI-safe command adapter."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from common import compact_whitespace, utc_now_iso
from task_queue import TASK_STATUS_DONE, TASK_STATUS_SNAG, load_task, write_json

DEFAULT_OUTPUT_PATH = ".agentcore/state/task-run-result.json"
DEFAULT_LOG_DIR = ".agentcore/state/task-runs"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Execute one claimed task.")
    parser.add_argument("--task-file", required=True, help="Path to claimed task markdown file.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH, help="Output JSON path.")
    parser.add_argument("--log-dir", default=DEFAULT_LOG_DIR, help="Directory for run logs.")
    parser.add_argument(
        "--command-template",
        default="",
        help="Command template. Defaults to AGENTCORE_TASK_RUN_COMMAND env var.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=int(os.getenv("AGENTCORE_TASK_RUN_TIMEOUT_SECONDS", "900")),
        help="Subprocess timeout in seconds.",
    )
    return parser.parse_args()


def _run_id() -> str:
    github_run = os.getenv("GITHUB_RUN_ID", "").strip()
    if github_run:
        return github_run
    return f"local-{utc_now_iso()}"


def _substitute_template(template: str, task_file: str, task_id: str, thread_key: str) -> str:
    out = template
    out = out.replace("{{TASK_FILE}}", task_file)
    out = out.replace("{{TASK_ID}}", task_id)
    out = out.replace("{{THREAD_KEY}}", thread_key)
    return out


def _build_result_base(task_file: Path, task_id: str, run_id: str, command: str) -> dict:
    return {
        "task_file": str(task_file),
        "task_id": task_id,
        "run_id": run_id,
        "command": command,
        "started_at": utc_now_iso(),
        "ended_at": "",
        "duration_seconds": 0.0,
        "exit_code": None,
        "status": TASK_STATUS_SNAG,
        "summary": "",
        "error": "",
        "result_path": "",
        "log_path": "",
    }


def main() -> int:
    args = parse_args()
    task_file = Path(args.task_file)
    task = load_task(task_file)
    task_id = str(task.meta.get("task_id", ""))
    run_id = _run_id()

    command_template = args.command_template.strip() or os.getenv("AGENTCORE_TASK_RUN_COMMAND", "").strip()
    command = _substitute_template(
        command_template,
        task_file=str(task_file),
        task_id=task_id,
        thread_key=str(task.meta.get("thread_key", "")),
    )
    result = _build_result_base(task_file=task_file, task_id=task_id, run_id=run_id, command=command)

    output_path = Path(args.output)
    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    safe_task_id = compact_whitespace(task_id).replace(" ", "-") or "task"
    log_path = log_dir / f"{safe_task_id}__{run_id}.log"
    result["log_path"] = str(log_path)
    result["result_path"] = str(output_path)

    started_at = datetime.now(timezone.utc)
    if not command:
        result["status"] = TASK_STATUS_SNAG
        result["summary"] = "Missing AGENTCORE_TASK_RUN_COMMAND adapter. No task command was executed."
        result["error"] = "Set AGENTCORE_TASK_RUN_COMMAND with {{TASK_FILE}} placeholder."
        result["started_at"] = started_at.isoformat()
        result["ended_at"] = datetime.now(timezone.utc).isoformat()
        write_json(output_path, result)
        print(json.dumps(result, ensure_ascii=True))
        return 0

    try:
        proc = subprocess.run(
            command,
            shell=True,
            text=True,
            capture_output=True,
            timeout=max(1, args.timeout_seconds),
            check=False,
        )
        ended_at = datetime.now(timezone.utc)
        stdout_text = proc.stdout or ""
        stderr_text = proc.stderr or ""
        combined = compact_whitespace(f"{stdout_text}\n{stderr_text}")

        result["started_at"] = started_at.isoformat()
        result["ended_at"] = ended_at.isoformat()
        result["duration_seconds"] = round((ended_at - started_at).total_seconds(), 3)
        result["exit_code"] = proc.returncode
        result["status"] = TASK_STATUS_DONE if proc.returncode == 0 else TASK_STATUS_SNAG
        result["summary"] = combined[:600] if combined else "Task command completed without output."
        if proc.returncode != 0:
            result["error"] = compact_whitespace(stderr_text)[:600] or f"Task command exited with {proc.returncode}."

        log_text = (
            f"command: {command}\n"
            f"task_file: {task_file}\n"
            f"task_id: {task_id}\n"
            f"run_id: {run_id}\n"
            f"exit_code: {proc.returncode}\n\n"
            "===== STDOUT =====\n"
            f"{stdout_text}\n\n"
            "===== STDERR =====\n"
            f"{stderr_text}\n"
        )
        log_path.write_text(log_text, encoding="utf-8")
    except subprocess.TimeoutExpired as exc:
        ended_at = datetime.now(timezone.utc)
        partial_out = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        partial_err = (exc.stderr or "") if isinstance(exc.stderr, str) else ""
        result["started_at"] = started_at.isoformat()
        result["ended_at"] = ended_at.isoformat()
        result["duration_seconds"] = round((ended_at - started_at).total_seconds(), 3)
        result["status"] = TASK_STATUS_SNAG
        result["exit_code"] = None
        result["summary"] = "Task command timed out."
        result["error"] = f"Timed out after {args.timeout_seconds}s."
        log_path.write_text(
            f"command: {command}\nstatus: timeout\ntimeout_seconds: {args.timeout_seconds}\n\n"
            "===== PARTIAL STDOUT =====\n"
            f"{partial_out}\n\n"
            "===== PARTIAL STDERR =====\n"
            f"{partial_err}\n",
            encoding="utf-8",
        )

    write_json(output_path, result)
    print(json.dumps(result, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
