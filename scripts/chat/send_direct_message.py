#!/usr/bin/env python3
"""Send a Google Chat direct message."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

import chat_api

SCOPE_HINT_COMMAND = (
    "gcloud auth application-default login "
    '--scopes="openid,https://www.googleapis.com/auth/userinfo.email,'
    'https://www.googleapis.com/auth/cloud-platform,'
    'https://www.googleapis.com/auth/chat.spaces.create,'
    'https://www.googleapis.com/auth/chat.messages.create,'
    'https://www.googleapis.com/auth/chat.messages.readonly"'
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send a direct message in Google Chat.")
    parser.add_argument("--to", default="", help="Recipient email for the DM.")
    parser.add_argument("--text", default="", help="Message body text.")
    parser.add_argument(
        "--project",
        default="General",
        help="Project label embedded in default message text.",
    )
    parser.add_argument(
        "--no-create-dm",
        action="store_true",
        help="Do not auto-create the DM if it does not already exist.",
    )
    parser.add_argument(
        "--allow-non-client",
        action="store_true",
        help="Permit non-trusted recipients. Disabled by default for safety.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve auth + recipient and print payload without sending.",
    )
    return parser.parse_args()




def default_message(project: str) -> str:
    return f"[AgentCore][{project}] Test Google Chat message at {utc_now_iso()}"


def main() -> int:
    args = parse_args()
    env_map = chat_api.load_env_file(".env")

    trusted_client_email = chat_api.trusted_client_email(env_map=env_map)
    recipient = (args.to or trusted_client_email).strip().lower()
    if not args.allow_non_client and recipient != trusted_client_email.lower():
        raise ValueError(
            "Refusing to send to non-client recipient. "
            f"Trusted client email is: {trusted_client_email}. "
            "Use --allow-non-client to override."
        )

    message_text = (args.text or default_message(args.project)).strip()
    token = chat_api.access_token(env_map=env_map)
    summary = {
        "recipient": recipient,
        "create_dm_if_missing": not args.no_create_dm,
        "message_preview": message_text,
    }

    if args.dry_run:
        print(json.dumps({**summary, "status": "dry_run"}, indent=2, ensure_ascii=True))
        return 0

    try:
        if args.no_create_dm:
            space = chat_api.find_dm_space(token=token, recipient_email=recipient)
            dm_status = "found_existing_dm"
        else:
            # spaces.setup returns an existing direct-message space when one
            # already exists, avoiding an extra spaces.readonly scope.
            space = chat_api.create_or_get_dm_space(token=token, recipient_email=recipient)
            dm_status = "created_or_found_dm"

        space_name = (space.get("name") or "").strip()
        if not space_name:
            raise RuntimeError(f"Chat API response missing space name: {json.dumps(space, ensure_ascii=True)}")

        sent = chat_api.send_message(token=token, space_name=space_name, text=message_text)
        print(
            json.dumps(
                {
                    **summary,
                    "status": "sent",
                    "dm_status": dm_status,
                    "space": space_name,
                    "message_name": sent.get("name", ""),
                },
                indent=2,
                ensure_ascii=True,
            )
        )
        return 0
    except chat_api.ChatApiError as err:
        if chat_api.error_has_scope_issue(err.payload):
            print(
                json.dumps(
                    {
                        **summary,
                        "status": "auth_scope_error",
                        "details": err.payload,
                        "next_step": "Authorize ADC with Chat scopes, then rerun this command.",
                        "command": SCOPE_HINT_COMMAND,
                    },
                    indent=2,
                    ensure_ascii=True,
                ),
                file=sys.stderr,
            )
            return 2
        print(
            json.dumps(
                {**summary, "status": "chat_api_error", "status_code": err.status_code, "details": err.payload},
                indent=2,
                ensure_ascii=True,
            ),
            file=sys.stderr,
        )
        return 3
    except Exception as err:  # noqa: BLE001
        print(
            json.dumps(
                {**summary, "status": "error", "details": str(err)},
                indent=2,
                ensure_ascii=True,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
