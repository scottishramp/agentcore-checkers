"""Gmail API helpers for dependency-free email automation."""

from __future__ import annotations

import base64
import json
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request
from email.message import EmailMessage

from common import get_env

TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1"


class GmailApiError(RuntimeError):
    """Raised when Gmail API auth or requests fail."""


def has_oauth_credentials(env_map: dict[str, str] | None = None) -> bool:
    return bool(_oauth_credentials(env_map=env_map))


def _authorized_user_payload(env_map: dict[str, str] | None = None) -> dict[str, str]:
    inline_json = get_env("AGENTCORE_GMAIL_AUTHORIZED_USER_JSON", env_map=env_map)
    if inline_json:
        return json.loads(inline_json)

    json_file = get_env("AGENTCORE_GMAIL_AUTHORIZED_USER_FILE", env_map=env_map)
    if json_file:
        return json.loads(Path(json_file).read_text(encoding="utf-8"))
    return {}


def _oauth_credentials(env_map: dict[str, str] | None = None) -> dict[str, str]:
    direct = {
        "client_id": get_env("AGENTCORE_GMAIL_CLIENT_ID", fallback_keys=("GOOGLE_OAUTH_CLIENT_ID",), env_map=env_map),
        "client_secret": get_env(
            "AGENTCORE_GMAIL_CLIENT_SECRET",
            fallback_keys=("GOOGLE_OAUTH_CLIENT_SECRET",),
            env_map=env_map,
        ),
        "refresh_token": get_env(
            "AGENTCORE_GMAIL_REFRESH_TOKEN",
            fallback_keys=("GOOGLE_OAUTH_REFRESH_TOKEN",),
            env_map=env_map,
        ),
    }
    if all(direct.values()):
        return direct

    authorized_user = _authorized_user_payload(env_map=env_map)
    from_json = {
        "client_id": str(authorized_user.get("client_id", "")),
        "client_secret": str(authorized_user.get("client_secret", "")),
        "refresh_token": str(authorized_user.get("refresh_token", "")),
    }
    return from_json if all(from_json.values()) else {}


def resolve_transport(
    requested: str,
    api_name: str,
    fallback_name: str,
    env_map: dict[str, str] | None = None,
) -> str:
    configured = requested or get_env("AGENTCORE_EMAIL_TRANSPORT", default="auto", env_map=env_map)
    normalized = configured.strip().lower().replace("_", "-")
    if normalized == "gmail":
        normalized = "gmail-api"
    if normalized == "auto":
        return api_name if has_oauth_credentials(env_map=env_map) else fallback_name
    if normalized not in {api_name, fallback_name}:
        raise ValueError(f"Unsupported email transport: {configured}")
    return normalized


def refresh_access_token(env_map: dict[str, str] | None = None) -> str:
    credentials = _oauth_credentials(env_map=env_map)
    if not credentials:
        raise GmailApiError(
            "Missing Gmail OAuth credentials. Set AGENTCORE_GMAIL_CLIENT_ID, "
            "AGENTCORE_GMAIL_CLIENT_SECRET, and AGENTCORE_GMAIL_REFRESH_TOKEN, "
            "or provide AGENTCORE_GMAIL_AUTHORIZED_USER_JSON/FILE."
        )
    client_id = credentials["client_id"]
    client_secret = credentials["client_secret"]
    refresh_token = credentials["refresh_token"]

    payload = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        TOKEN_URL,
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            token_payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise GmailApiError(f"Gmail OAuth token refresh failed: {exc.code} {detail}") from exc

    access_token = str(token_payload.get("access_token", ""))
    if not access_token:
        raise GmailApiError("Gmail OAuth token refresh did not return an access token.")
    return access_token


def access_token(env_map: dict[str, str] | None = None) -> str:
    configured_token = get_env("AGENTCORE_GMAIL_ACCESS_TOKEN", env_map=env_map)
    return configured_token or refresh_access_token(env_map=env_map)


def gmail_request(
    method: str,
    path: str,
    token: str,
    query: dict[str, str | int] | None = None,
    payload: dict | None = None,
) -> dict:
    url = f"{GMAIL_API_BASE}{path}"
    if query:
        url = f"{url}?{urllib.parse.urlencode(query)}"
    data = None
    headers = {"Authorization": f"Bearer {token}"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise GmailApiError(f"Gmail API request failed: {method} {path}: {exc.code} {detail}") from exc
    if not body:
        return {}
    return json.loads(body)


def encode_raw_message(msg: EmailMessage) -> str:
    return base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")


def send_message(msg: EmailMessage, env_map: dict[str, str] | None = None, thread_id: str = "") -> dict:
    token = access_token(env_map=env_map)
    payload = {"raw": encode_raw_message(msg)}
    if thread_id:
        payload["threadId"] = thread_id
    return gmail_request(
        "POST",
        "/users/me/messages/send",
        token=token,
        payload=payload,
    )


def decode_raw_message(raw: str) -> bytes:
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode((raw + padding).encode("ascii"))
