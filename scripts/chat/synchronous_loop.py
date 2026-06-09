#!/usr/bin/env python3
"""Run a bounded pseudo-synchronous Google Chat conversation loop."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

SCRIPT_DIR = Path(__file__).resolve().parent
EMAIL_DIR = SCRIPT_DIR.parent / "email"
if str(EMAIL_DIR) not in sys.path:
    sys.path.insert(0, str(EMAIL_DIR))

from common import compact_whitespace, read_json, write_json  # noqa: E402
from task_queue import load_task  # noqa: E402

DEFAULT_SUMMARY_PATH = ".agentcore/state/chat-sync-loop-summary.json"
DEFAULT_FETCH_OUTPUT = ".agentcore/state/chat-fetch/sync-loop.json"
DEFAULT_TRIAGE_OUTPUT = ".agentcore/state/chat-sync-loop-triage.json"
DEFAULT_CLAIM_OUTPUT = ".agentcore/state/chat-sync-loop-claim.json"
DEFAULT_RESULT_OUTPUT = ".agentcore/state/chat-sync-loop-result.json"
DEFAULT_NOTIFY_OUTPUT = ".agentcore/state/chat-sync-loop-notify.json"
DEFAULT_MAX_MINUTES = 15
DEFAULT_POLL_SECONDS = 20
DEFAULT_START_HOUR = 9
DEFAULT_END_HOUR = 20
DEFAULT_TIMEZONE = "America/Chicago"

CONVERSATIONAL_HINTS = {
    "hi",
    "hello",
    "hey",
    "ok",
    "okay",
    "yes",
    "no",
    "yep",
    "nope",
    "sure",
    "thanks",
    "thank you",
    "try again",
    "go on",
    "continue",
    "what about",
    "why",
    "how",
    "can you",
    "could you",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Maintain a bounded Google Chat conversation in one runner.")
    parser.add_argument("--seed-task-file", required=True, help="Initial Chat task file that just completed.")
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_PATH, help="Loop summary JSON path.")
    parser.add_argument("--max-minutes", type=int, default=int(os.getenv("AGENTCORE_CHAT_SYNC_MAX_MINUTES", DEFAULT_MAX_MINUTES)))
    parser.add_argument("--poll-seconds", type=int, default=int(os.getenv("AGENTCORE_CHAT_SYNC_POLL_SECONDS", DEFAULT_POLL_SECONDS)))
    parser.add_argument("--start-hour", type=int, default=int(os.getenv("AGENTCORE_CHAT_SYNC_START_HOUR", DEFAULT_START_HOUR)))
    parser.add_argument("--end-hour", type=int, default=int(os.getenv("AGENTCORE_CHAT_SYNC_END_HOUR", DEFAULT_END_HOUR)))
    parser.add_argument("--timezone", default=os.getenv("AGENTCORE_CHAT_SYNC_TIMEZONE", DEFAULT_TIMEZONE))
    parser.add_argument(
        "--enabled",
        default=os.getenv("AGENTCORE_CHAT_SYNC_WINDOW_ENABLED", "true"),
        help="Set false to disable the sync loop.",
    )
    return parser.parse_args()


def truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_cmd(command: list[str], *, output_path: Path | None = None, env: dict[str, str] | None = None) -> dict:
    proc = subprocess.run(command, text=True, capture_output=True, check=False, env=env)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(proc.stdout, encoding="utf-8")
    return {
        "command": " ".join(shlex.quote(part) for part in command),
        "exit_code": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def commit_if_needed(message: str) -> dict:
    status = run_cmd(["git", "status", "--short"])
    if not compact_whitespace(status["stdout"]):
        return {"committed": False, "reason": "No changes to commit."}
    add = run_cmd(["git", "add", "-A"])
    reset_state = run_cmd(["git", "reset", "--", ".agentcore/state"])
    diff = run_cmd(["git", "diff", "--cached", "--quiet"])
    if diff["exit_code"] == 0:
        return {"committed": False, "reason": "No staged changes after excluding .agentcore/state."}
    commit = run_cmd(["git", "-c", "user.name=AgentCore Bot", "-c", "user.email=scottishramp@gmail.com", "commit", "-m", message])
    if commit["exit_code"] != 0:
        return {"committed": False, "reason": "Commit failed.", "stderr": commit["stderr"]}
    pull = run_cmd(["git", "pull", "--rebase", "origin", "main"])
    push = run_cmd(["git", "push"])
    return {
        "committed": push["exit_code"] == 0,
        "commit_stdout": commit["stdout"],
        "pull_exit_code": pull["exit_code"],
        "push_exit_code": push["exit_code"],
        "stderr": compact_whitespace(f"{commit['stderr']} {pull['stderr']} {push['stderr']}"),
    }


def is_central_daytime(tz_name: str, start_hour: int, end_hour: int) -> tuple[bool, str]:
    local_now = datetime.now(ZoneInfo(tz_name))
    return start_hour <= local_now.hour < end_hour, local_now.isoformat()


def seed_is_conversational(task_file: Path) -> tuple[bool, str]:
    task = load_task(task_file)
    if str(task.meta.get("source_kind", "")).strip().lower() != "google_chat":
        return False, "not_google_chat"
    text = compact_whitespace(task.body).lower()
    if not text:
        return False, "empty"
    word_count = len(re.findall(r"\b[\w']+\b", text))
    if word_count > 80:
        return False, "too_long"
    if "## requested work" in text:
        text = text.split("## requested work", 1)[-1]
    if any(hint in text for hint in CONVERSATIONAL_HINTS):
        return True, "hint_match"
    if word_count <= 20 and ("?" in text or not re.search(r"\b(implement|deploy|build|research|summarize|organize)\b", text)):
        return True, "short_conversational"
    return False, "task_like"


def claim_source_kind(claim: dict) -> str:
    task_file = str(claim.get("task_file", ""))
    if not task_file:
        return ""
    try:
        task = load_task(Path(task_file))
    except FileNotFoundError:
        return ""
    return str(task.meta.get("source_kind", "")).strip().lower()


def process_claimed_chat_task(claim: dict, env: dict[str, str], iteration: int) -> dict:
    task_file = str(claim.get("task_file", ""))
    result_path = Path(f".agentcore/state/chat-sync-loop-result-{iteration}.json")
    notify_path = Path(f".agentcore/state/chat-sync-loop-notify-{iteration}.json")
    run_result = run_cmd(
        [
            "python3",
            "scripts/email/run_task_adapter.py",
            "--task-file",
            task_file,
            "--output",
            str(result_path),
        ],
        env=env,
    )
    finalize = run_cmd(
        [
            "python3",
            "scripts/email/finalize_task.py",
            "--task-file",
            task_file,
            "--result-json",
            str(result_path),
        ],
        env=env,
    )
    result = read_json(result_path, default={})
    status = str(result.get("status", "snag")).lower() or "snag"
    commit_workspace = commit_if_needed("Apply async chat session changes") if status == "done" else {"committed": False}
    notify = run_cmd(
        [
            "python3",
            "scripts/chat/send_task_response.py",
            "--task-file",
            task_file,
            "--status",
            "done" if status == "done" else "snag",
            "--result-json",
            str(result_path),
        ],
        output_path=notify_path,
        env=env,
    )
    record = run_cmd(
        [
            "python3",
            "scripts/chat/record_chat_response.py",
            "--task-file",
            task_file,
            "--result-json",
            str(result_path),
            "--notification-json",
            str(notify_path),
        ],
        env=env,
    )
    commit_ledger = commit_if_needed("Record async chat session result")
    return {
        "task_file": task_file,
        "task_id": claim.get("task_id", ""),
        "run_exit_code": run_result["exit_code"],
        "finalize_exit_code": finalize["exit_code"],
        "status": status,
        "notify_exit_code": notify["exit_code"],
        "record_exit_code": record["exit_code"],
        "commit_workspace": commit_workspace,
        "commit_ledger": commit_ledger,
    }


def main() -> int:
    args = parse_args()
    summary_path = Path(args.summary_output)
    summary = {
        "started_at": now_iso(),
        "ended_at": "",
        "enabled": truthy(str(args.enabled)),
        "entered_loop": False,
        "reason": "",
        "seed_task_file": args.seed_task_file,
        "max_minutes": args.max_minutes,
        "poll_seconds": args.poll_seconds,
        "processed_tasks": [],
        "polls": 0,
    }

    if not summary["enabled"]:
        summary["reason"] = "disabled"
        write_json(summary_path, summary)
        print(json.dumps(summary, ensure_ascii=True))
        return 0
    in_window, local_now = is_central_daytime(args.timezone, args.start_hour, args.end_hour)
    summary["local_time"] = local_now
    if not in_window:
        summary["reason"] = "outside_time_window"
        write_json(summary_path, summary)
        print(json.dumps(summary, ensure_ascii=True))
        return 0
    conversational, reason = seed_is_conversational(Path(args.seed_task_file))
    if not conversational:
        summary["reason"] = f"seed_not_conversational:{reason}"
        write_json(summary_path, summary)
        print(json.dumps(summary, ensure_ascii=True))
        return 0

    summary["entered_loop"] = True
    env = os.environ.copy()
    deadline = time.monotonic() + max(1, args.max_minutes) * 60
    iteration = 0
    while time.monotonic() < deadline:
        sleep_for = min(max(1, args.poll_seconds), max(0.0, deadline - time.monotonic()))
        if sleep_for > 0:
            time.sleep(sleep_for)
        iteration += 1
        summary["polls"] = iteration
        fetch = run_cmd(
            [
                "python3",
                "scripts/chat/fetch_messages.py",
                "--limit",
                "20",
                "--bootstrap-window",
                "0",
                "--output",
                DEFAULT_FETCH_OUTPUT,
            ],
            env=env,
        )
        triage = run_cmd(
            [
                "python3",
                "scripts/chat/triage_messages.py",
                "--input",
                DEFAULT_FETCH_OUTPUT,
                "--summary-output",
                DEFAULT_TRIAGE_OUTPUT,
            ],
            env=env,
        )
        claim = run_cmd(
            [
                "python3",
                "scripts/email/claim_next_task.py",
                "--output",
                DEFAULT_CLAIM_OUTPUT,
                "--runner-id",
                os.getenv("GITHUB_RUN_ID", f"sync-loop-{iteration}"),
                "--source-kind",
                "google_chat",
            ],
            env=env,
        )
        claim_payload = read_json(Path(DEFAULT_CLAIM_OUTPUT), default={})
        if not claim_payload.get("claimed"):
            continue
        if claim_source_kind(claim_payload) != "google_chat":
            summary["reason"] = "non_chat_task_claimed_during_loop"
            break
        processed = process_claimed_chat_task(claim_payload, env=env, iteration=iteration)
        processed["fetch_exit_code"] = fetch["exit_code"]
        processed["triage_exit_code"] = triage["exit_code"]
        processed["claim_exit_code"] = claim["exit_code"]
        summary["processed_tasks"].append(processed)

    summary["ended_at"] = now_iso()
    if not summary["reason"]:
        summary["reason"] = "deadline_reached"
    write_json(summary_path, summary)
    print(json.dumps(summary, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
