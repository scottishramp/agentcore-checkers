#!/usr/bin/env python3
"""Send outbound AgentCore emails through Gmail API or SMTP."""

from __future__ import annotations

import argparse
import json
import smtplib
from email.message import EmailMessage
from pathlib import Path

import gmail_api
from common import get_env, load_env_file, resolve_email_address, resolve_email_credentials, utc_now_iso


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send an email from the AgentCore mailbox.")
    parser.add_argument("--to", dest="to_email", default="", help="Recipient email address.")
    parser.add_argument("--subject", default="", help="Email subject line.")
    parser.add_argument(
        "--kind",
        default="question",
        choices=("question", "update", "ack"),
        help="Message category used in default subject prefixes.",
    )
    parser.add_argument(
        "--project",
        default="General",
        help="Project name used in the default subject format.",
    )
    parser.add_argument("--body", default="", help="Inline email body text.")
    parser.add_argument("--body-file", default="", help="Path to a text file for the email body.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print payload details without sending.",
    )
    parser.add_argument(
        "--transport",
        default="",
        help="Email transport: auto, gmail-api, or smtp. Defaults to AGENTCORE_EMAIL_TRANSPORT/auto.",
    )
    return parser.parse_args()


def read_body(args: argparse.Namespace) -> str:
    if args.body_file:
        return Path(args.body_file).read_text(encoding="utf-8")
    if args.body:
        return args.body
    return "No body provided."


def build_subject(args: argparse.Namespace) -> str:
    if args.subject.strip():
        return args.subject.strip()
    label = args.kind.capitalize()
    return f"[AgentCore][{label}][{args.project}]"


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
    recipient = args.to_email.strip() or trusted_client_email
    if recipient.strip().lower() != trusted_client_email.strip().lower():
        raise ValueError(
            "Refusing to send to non-client recipient. "
            f"Trusted client email is: {trusted_client_email}"
        )
    subject = build_subject(args)
    body = read_body(args)

    payload = {
        "from": username,
        "to": recipient,
        "subject": subject,
        "kind": args.kind,
        "project": args.project,
        "created_at": utc_now_iso(),
        "transport": gmail_api.resolve_transport(args.transport, "gmail-api", "smtp", env_map=env_map),
    }

    if args.dry_run:
        print(json.dumps(payload, indent=2))
        return 0

    msg = EmailMessage()
    msg["From"] = username
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.set_content(body)

    if payload["transport"] == "gmail-api":
        result = gmail_api.send_message(msg, env_map=env_map)
        print(json.dumps({**payload, "status": "sent", "gmail_message_id": result.get("id", "")}))
        return 0

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

    print(json.dumps({**payload, "status": "sent"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
