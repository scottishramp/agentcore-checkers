"""Shared Google Chat API helpers for AgentCore automation."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
EMAIL_DIR = SCRIPT_DIR.parent / "email"
if str(EMAIL_DIR) not in sys.path:
    sys.path.insert(0, str(EMAIL_DIR))

import gmail_api  # noqa: E402

CHAT_API_ROOT = "https://chat.googleapis.com/v1"
DEFAULT_CLIENT_EMAIL = "briandherbert@gmail.com"
DEFAULT_DM_SPACE = "spaces/6RZ69yAAAAE"


@dataclass
class ChatApiError(Exception):
    status_code: int
    payload: dict

    def __str__(self) -> str:
        return json.dumps({"status_code": self.status_code, "payload": self.payload}, ensure_ascii=True)


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


def trusted_client_email(env_map: dict[str, str] | None = None) -> str:
    return get_env(
        "AGENTCORE_CLIENT_EMAIL",
        fallback_keys=("CLIENT_EMAIL",),
        default=DEFAULT_CLIENT_EMAIL,
        env_map=env_map,
    ).strip()


def default_space_name(env_map: dict[str, str] | None = None) -> str:
    return get_env("AGENTCORE_CHAT_DM_SPACE", default=DEFAULT_DM_SPACE, env_map=env_map).strip()


def self_user_name(env_map: dict[str, str] | None = None) -> str:
    return get_env("AGENTCORE_CHAT_SELF_USER_NAME", default="users/112143982168307832773", env_map=env_map).strip()


def access_token(env_map: dict[str, str]) -> str:
    if gmail_api.has_oauth_credentials(env_map=env_map):
        return gmail_api.access_token(env_map=env_map)

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


def error_has_scope_issue(error_payload: dict) -> bool:
    text = json.dumps(error_payload, ensure_ascii=True)
    return "ACCESS_TOKEN_SCOPE_INSUFFICIENT" in text


def create_or_get_dm_space(token: str, recipient_email: str) -> dict:
    return run_json_request(
        "POST",
        "spaces:setup",
        token=token,
        payload={
            "space": {"spaceType": "DIRECT_MESSAGE"},
            "memberships": [{"member": {"name": f"users/{recipient_email}", "type": "HUMAN"}}],
        },
    )


def find_dm_space(token: str, recipient_email: str) -> dict:
    name_param = urllib.parse.quote(f"users/{recipient_email}", safe="")
    return run_json_request("GET", f"spaces:findDirectMessage?name={name_param}", token=token)


def list_messages(
    token: str,
    space_name: str,
    page_size: int = 50,
    page_token: str = "",
    order_by: str = "",
) -> dict:
    params = {"pageSize": str(page_size)}
    if page_token:
        params["pageToken"] = page_token
    if order_by:
        # e.g. "createTime desc" so the newest messages are always on page 1.
        params["orderBy"] = order_by
    query = urllib.parse.urlencode(params)
    return run_json_request("GET", f"{space_name}/messages?{query}", token=token)


def send_message(token: str, space_name: str, text: str) -> dict:
    return run_json_request("POST", f"{space_name}/messages", token=token, payload={"text": text})
