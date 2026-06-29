#!/usr/bin/env python3
"""Orchestrate periodic knowledge content ingest from Gmail, Telegram, and shared Drive docs."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
DEFAULT_STATE_PATH = ".agentcore/state/knowledge-content-ingest-state.json"
DEFAULT_SUMMARY_PATH = ".agentcore/state/knowledge-content-ingest-summary.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run knowledge content ingest across intake channels.")
    parser.add_argument("--state-file", default=DEFAULT_STATE_PATH, help="Checkpoint JSON path.")
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_PATH, help="Summary JSON path.")
    parser.add_argument("--email-limit", type=int, default=50, help="Max emails to fetch.")
    parser.add_argument("--email-bootstrap-window", type=int, default=168, help="Email lookback hours.")
    parser.add_argument("--skip-email", action="store_true", help="Skip Gmail fetch/triage.")
    parser.add_argument("--skip-telegram", action="store_true", help="Skip Telegram fetch/triage.")
    parser.add_argument("--skip-drive-metadata", action="store_true", help="Skip shared Drive metadata ingest.")
    parser.add_argument("--force-export", action="store_true", help="Re-export allowlisted Drive docs.")
    parser.add_argument("--dispatch-runner", action="store_true", help="Dispatch async runner when tasks activate.")
    return parser.parse_args()


def _run_step(label: str, command: list[str]) -> dict:
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    payload = {
        "step": label,
        "command": command,
        "returncode": result.returncode,
        "stdout_tail": result.stdout.strip()[-2000:],
        "stderr_tail": result.stderr.strip()[-2000:],
    }
    if result.returncode != 0:
        payload["error"] = f"{label} failed with exit code {result.returncode}"
    return payload


def _count_records(directory: Path, pattern: str) -> int:
    if not directory.exists():
        return 0
    return len(list(directory.glob(pattern)))


def main() -> int:
    args = parse_args()
    state_path = Path(args.state_file)
    summary_path = Path(args.summary_path if hasattr(args, "summary_path") else args.summary_output)

    from datetime import datetime, timezone

    started_at = datetime.now(timezone.utc).isoformat()
    steps: list[dict] = []

    if not args.skip_email:
        steps.append(
            _run_step(
                "fetch_email",
                [
                    "python3",
                    "scripts/email/fetch_inbox.py",
                    "--limit",
                    str(args.email_limit),
                    "--bootstrap-window",
                    str(args.email_bootstrap_window),
                ],
            )
        )
        steps.append(_run_step("triage_email", ["python3", "scripts/email/triage_messages.py"]))

    if not args.skip_telegram:
        steps.append(_run_step("fetch_telegram", ["python3", "scripts/telegram/fetch_pending.py"]))
        steps.append(_run_step("triage_telegram", ["python3", "scripts/telegram/triage_messages.py"]))

    if not args.skip_drive_metadata:
        steps.append(
            _run_step(
                "ingest_drive_metadata",
                ["python3", "scripts/ingest/ingest_drive_updates.py", "--include-shared-with-me"],
            )
        )

    export_cmd = ["python3", "scripts/ingest/export_flagged_docs.py"]
    if args.force_export:
        export_cmd.append("--force")
    steps.append(_run_step("export_flagged_docs", export_cmd))
    steps.append(_run_step("activate_content_tasks", ["python3", "scripts/ingest/activate_content_tasks.py"]))

    dispatch_result = None
    activation = {}
    activation_path = Path(".agentcore/state/content-task-activation-summary.json")
    if activation_path.exists():
        activation = json.loads(activation_path.read_text(encoding="utf-8"))
    telegram_sync = {}
    telegram_sync_path = Path(".agentcore/state/telegram-sync-summary.json")
    if telegram_sync_path.exists():
        telegram_sync = json.loads(telegram_sync_path.read_text(encoding="utf-8"))

    should_dispatch = bool(activation.get("activated")) or int(telegram_sync.get("created_tasks", 0) or 0) > 0
    if args.dispatch_runner and should_dispatch:
        dispatch_result = _run_step("dispatch_runner", ["python3", "scripts/ingest/dispatch_runner_trigger.py"])
        steps.append(dispatch_result)

    email_dir = Path("agentcore/inbox/email")
    telegram_dir = Path("agentcore/inbox/telegram")
    drive_dir = Path("agentcore/inbox/drive")
    drive_content_dir = Path(".agentcore/state/drive-content")

    summary = {
        "started_at": started_at,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "channels": {
            "gmail_records": _count_records(email_dir, "email__*.md"),
            "telegram_records": _count_records(telegram_dir, "telegram__*.md"),
            "drive_records": _count_records(drive_dir, "drive__*.md"),
            "exported_drive_docs": _count_records(drive_content_dir, "*.txt"),
        },
        "activation": activation,
        "telegram_sync": telegram_sync,
        "steps": steps,
        "errors": [step["error"] for step in steps if step.get("error")],
    }

    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps({"last_run_at": summary["completed_at"]}, indent=2) + "\n", encoding="utf-8")
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=True))

    return 1 if summary["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
