#!/usr/bin/env python3
"""Send a Google Chat direct message using gcloud Application Default Credentials."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

CHAT_API_ROOT = "https://chat.googleapis.com/v1"
SCOPE_HINT_COMMAND = (
    "gcloud auth application-default login "
    '--scopes="openid,https://www.googleapis.com/auth/userinfo.email,'
    'https://www.googleapis.com/auth/cloud-platform,'
    'https://www.googleapis.com/auth/chat.spaces,'
    'https://www.googleapis.com/auth/chat.messages.create"'
)


def load_env_file(path: str = ".env") -> dict[str, str]:
    env_map: dict[str, str] = {}
    env_path = Path(path)
    if not env_path.exists():
        return env_map

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env_map[key.strip()] = value.strip()
    return env_map


def get_env(
    key: str,
    fallback_keys: tuple[str, ...] = (),
    default: str = "",
    env_map: dict[str, str] | None = None,
) -> str:
    for candidate in (key, *fallback_keys):
        value = os.getenv(candidate)
        if value:
            return value
        if env_map and env_map.get(candidate):
            return env_map[candidate]
    return default


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ChatApiError(Exception):
    status_code: int
    payload: dict

    def __str__(self) -> str:
        return json.dumps({"status_code": self.status_code, "payload": self.payload}, ensure_ascii=True)


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


def run_json_request(method: str, path: str, token: str, payload: dict | None = None) -> dict:
    url = f"{CHAT_API_ROOT}/{path.lstrip('/')}"
    body = None
    headers = {"Authorization": f"Bearer {token}"}
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"

    request = urllib.request.Request(url=url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw_error = exc.read().decode("utf-8", errors="replace")
        try:
            payload_error = json.loads(raw_error)
        except json.JSONDecodeError:
            payload_error = {"error": {"message": raw_error or exc.reason}}
        raise ChatApiError(status_code=exc.code, payload=payload_error) from exc


def get_access_token() -> str:
    cmd = ["gcloud", "auth", "application-default", "print-access-token"]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        raise RuntimeError(
            "Unable to fetch ADC token. Run `gcloud auth application-default login` first. "
            f"Details: {stderr}"
        )
    token = result.stdout.strip()
    if not token:
        raise RuntimeError("gcloud returned an empty access token.")
    return token


def find_dm_space(token: str, recipient_email: str) -> dict:
    name_param = urllib.parse.quote(f"users/{recipient_email}", safe="")
    return run_json_request("GET", f"spaces:findDirectMessage?name={name_param}", token=token)


def create_dm_space(token: str, recipient_email: str) -> dict:
    return run_json_request(
        "POST",
        "spaces:setup",
        token=token,
        payload={
            "space": {"spaceType": "DIRECT_MESSAGE"},
            "memberships": [{"member": {"name": f"users/{recipient_email}", "type": "HUMAN"}}],
        },
    )


def send_message(token: str, space_name: str, text: str) -> dict:
    return run_json_request("POST", f"{space_name}/messages", token=token, payload={"text": text})


def error_has_scope_issue(error_payload: dict) -> bool:
    text = json.dumps(error_payload, ensure_ascii=True)
    return "ACCESS_TOKEN_SCOPE_INSUFFICIENT" in text


def default_message(project: str) -> str:
    return f"[AgentCore][{project}] Test Google Chat message at {utc_now_iso()}"


def main() -> int:
    args = parse_args()
    env_map = load_env_file(".env")

    trusted_client_email = get_env(
        "AGENTCORE_CLIENT_EMAIL",
        fallback_keys=("CLIENT_EMAIL",),
        default="briandherbert@gmail.com",
        env_map=env_map,
    ).strip()
    recipient = (args.to or trusted_client_email).strip().lower()
    if not args.allow_non_client and recipient != trusted_client_email.lower():
        raise ValueError(
            "Refusing to send to non-client recipient. "
            f"Trusted client email is: {trusted_client_email}. "
            "Use --allow-non-client to override."
        )

    message_text = (args.text or default_message(args.project)).strip()
    token = get_access_token()
    summary = {
        "recipient": recipient,
        "create_dm_if_missing": not args.no_create_dm,
        "message_preview": message_text,
    }

    if args.dry_run:
        print(json.dumps({**summary, "status": "dry_run"}, indent=2, ensure_ascii=True))
        return 0

    try:
        try:
            space = find_dm_space(token=token, recipient_email=recipient)
            dm_status = "found_existing_dm"
        except ChatApiError as err:
            if err.status_code == 404 and not args.no_create_dm:
                space = create_dm_space(token=token, recipient_email=recipient)
                dm_status = "created_dm"
            else:
                raise

        space_name = (space.get("name") or "").strip()
        if not space_name:
            raise RuntimeError(f"Chat API response missing space name: {json.dumps(space, ensure_ascii=True)}")

        sent = send_message(token=token, space_name=space_name, text=message_text)
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
    except ChatApiError as err:
        if error_has_scope_issue(err.payload):
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
