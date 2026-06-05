#!/usr/bin/env python3
"""Send standardized task status notifications to the trusted client email."""

from __future__ import annotations

import argparse
import json
import smtplib
from email.message import EmailMessage
from pathlib import Path

import gmail_api
from common import (
    compact_whitespace,
    get_env,
    load_env_file,
    read_json,
    resolve_email_address,
    resolve_email_credentials,
    utc_now_iso,
)
from task_queue import load_task, summarize_requested_work

DEFAULT_RESULT_PATH = ".agentcore/state/task-run-result.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send queue task status email.")
    parser.add_argument("--task-file", required=True, help="Task file path.")
    parser.add_argument(
        "--status",
        required=True,
        choices=("running", "done", "snag"),
        help="Status template type.",
    )
    parser.add_argument("--result-json", default=DEFAULT_RESULT_PATH, help="Runner result JSON for done/snag templates.")
    parser.add_argument("--project", default="AsyncLoop", help="Project tag for subject line.")
    parser.add_argument(
        "--transport",
        default="",
        help="Email transport: auto, gmail-api, or smtp. Defaults to AGENTCORE_EMAIL_TRANSPORT/auto.",
    )
    return parser.parse_args()


def _run_url() -> str:
    server = get_env("GITHUB_SERVER_URL", default="")
    repo = get_env("GITHUB_REPOSITORY", default="")
    run_id = get_env("GITHUB_RUN_ID", default="")
    if server and repo and run_id:
        return f"{server}/{repo}/actions/runs/{run_id}"
    return ""


def _subject(status: str, project: str, task_id: str) -> str:
    label = "Update" if status == "running" else ("Ack" if status == "done" else "Question")
    return f"[AgentCore][{label}][{project}][{task_id}] {status.upper()}"


def _reply_subject(source_subject: str, fallback: str) -> str:
    subject = compact_whitespace(source_subject) or fallback
    if subject.lower().startswith("re:"):
        return subject
    return f"Re: {subject}"


def _uses_natural_reply(task_meta: dict, trusted_client_email: str) -> bool:
    if str(task_meta.get("reply_style", "")).strip().lower() == "natural":
        return True
    if str(task_meta.get("source_kind", "")).strip().lower() == "trusted_share_notification":
        return True
    return str(task_meta.get("source_from", "")).strip().lower() == trusted_client_email.strip().lower()


def _body_running(task_id: str, thread_key: str, run_id: str, source_subject: str, requested: str, run_url: str) -> str:
    lines = [
        "Task status: RUNNING",
        "",
        f"- Task ID: {task_id}",
        f"- Thread key: {thread_key}",
        f"- Run ID: {run_id}",
        f"- Source subject: {source_subject}",
        f"- Requested work summary: {requested}",
        "",
        "The async runner has claimed this task and started execution.",
    ]
    if run_url:
        lines.extend(["", f"Run URL: {run_url}"])
    lines.extend(["", f"Timestamp: {utc_now_iso()}"])
    return "\n".join(lines) + "\n"


def _body_direct_done(summary: str) -> str:
    body = summary.strip()
    return (body or "Done.") + "\n"


def _body_done(task_id: str, thread_key: str, run_id: str, source_subject: str, summary: str, run_url: str) -> str:
    lines = [
        "Task status: COMPLETED",
        "",
        f"- Task ID: {task_id}",
        f"- Thread key: {thread_key}",
        f"- Run ID: {run_id}",
        f"- Source subject: {source_subject}",
        "",
        "Completion summary:",
        summary or "No summary output was captured.",
    ]
    if run_url:
        lines.extend(["", f"Run URL: {run_url}"])
    lines.extend(["", f"Timestamp: {utc_now_iso()}"])
    return "\n".join(lines) + "\n"


def _body_direct_snag(summary: str, error: str) -> str:
    detail = summary or error or "The async task did not complete cleanly."
    return (
        "I hit a snag while trying to handle that email.\n\n"
        f"{detail}\n\n"
        "Reply with any extra context and I will try again.\n"
    )


def _body_snag(
    task_id: str,
    thread_key: str,
    run_id: str,
    source_subject: str,
    summary: str,
    error: str,
    run_url: str,
) -> str:
    lines = [
        "Task status: SNAG",
        "",
        f"- Task ID: {task_id}",
        f"- Thread key: {thread_key}",
        f"- Run ID: {run_id}",
        f"- Source subject: {source_subject}",
        "",
        "Snag summary:",
        summary or "No summary output was captured.",
        "",
        "Error details:",
        error or "No explicit error details were captured.",
        "",
        "Please reply with clarification or next instruction and the runner will pick it up.",
    ]
    if run_url:
        lines.extend(["", f"Run URL: {run_url}"])
    lines.extend(["", f"Timestamp: {utc_now_iso()}"])
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    env_map = load_env_file(".env")
    username = resolve_email_address(env_map=env_map)
    trusted_client_email = get_env(
        "AGENTCORE_CLIENT_EMAIL",
        fallback_keys=("CLIENT_EMAIL",),
        default="briandherbert@gmail.com",
        env_map=env_map,
    )
    transport = gmail_api.resolve_transport(args.transport, "gmail-api", "smtp", env_map=env_map)

    task = load_task(Path(args.task_file))
    task_id = str(task.meta.get("task_id", ""))
    thread_key = str(task.meta.get("thread_key", ""))
    run_id = str(task.meta.get("run_id", ""))
    source_subject = str(task.meta.get("source_subject", ""))
    gmail_thread_id = str(task.meta.get("gmail_thread_id", ""))
    rfc_message_id = str(task.meta.get("rfc_message_id", "")) or str(task.meta.get("source_message_id", ""))
    requested_summary = summarize_requested_work(task)
    run_url = _run_url()
    natural_reply = _uses_natural_reply(task.meta, trusted_client_email)

    result = {}
    if args.status in {"done", "snag"} and args.result_json:
        result = read_json(Path(args.result_json), default={})
        run_id = str(result.get("run_id", "")) or run_id

    if args.status == "running":
        body = _body_running(task_id, thread_key, run_id, source_subject, requested_summary, run_url)
    elif args.status == "done":
        summary = str(result.get("summary", "")).strip()
        if natural_reply:
            body = _body_direct_done(summary)
        else:
            body = _body_done(
                task_id=task_id,
                thread_key=thread_key,
                run_id=run_id,
                source_subject=source_subject,
                summary=compact_whitespace(summary),
                run_url=run_url,
            )
    else:
        summary = compact_whitespace(str(result.get("summary", "")))
        error = compact_whitespace(str(result.get("error", "")))
        if natural_reply:
            body = _body_direct_snag(summary, error)
        else:
            body = _body_snag(
                task_id=task_id,
                thread_key=thread_key,
                run_id=run_id,
                source_subject=source_subject,
                summary=summary,
                error=error,
                run_url=run_url,
            )

    msg = EmailMessage()
    msg["From"] = username
    msg["To"] = trusted_client_email
    msg["Subject"] = (
        _reply_subject(source_subject, fallback=_subject(status=args.status, project=args.project, task_id=task_id))
        if natural_reply and args.status in {"done", "snag"}
        else _subject(status=args.status, project=args.project, task_id=task_id)
    )
    if rfc_message_id and "@" in rfc_message_id:
        msg["In-Reply-To"] = f"<{rfc_message_id.strip('<>')}>"
        msg["References"] = f"<{rfc_message_id.strip('<>')}>"
    msg.set_content(body)

    gmail_message_id = ""
    if transport == "gmail-api":
        result = gmail_api.send_message(msg, env_map=env_map, thread_id=gmail_thread_id)
        gmail_message_id = str(result.get("id", ""))
    else:
        _, password = resolve_email_credentials(env_map=env_map)
        smtp_host = get_env(
            "AGENTCORE_SMTP_HOST",
            fallback_keys=("SMTP_HOST",),
            default="smtp.gmail.com",
            env_map=env_map,
        )
        smtp_port = int(
            get_env(
                "AGENTCORE_SMTP_PORT",
                fallback_keys=("SMTP_PORT",),
                default="465",
                env_map=env_map,
            )
        )
        with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30) as smtp:
            smtp.login(username, password)
            smtp.send_message(msg)

    payload = {
        "status": "sent",
        "task_file": args.task_file,
        "task_id": task_id,
        "notify_status": args.status,
        "to": trusted_client_email,
        "transport": transport,
        "gmail_message_id": gmail_message_id,
        "gmail_thread_id": gmail_thread_id,
        "source_gmail_message_id": str(task.meta.get("gmail_message_id", "")),
        "source_rfc_message_id": rfc_message_id,
    }
    print(json.dumps(payload, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
