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

ACCOUNT_AGENTCORE = "agentcore"
ACCOUNT_BRIAN = "brian"
ACCOUNTS = {ACCOUNT_AGENTCORE, ACCOUNT_BRIAN}
BRIAN_DEFAULT_AUTHORIZED_USER_FILE = ".secrets/brian-gmail-authorized-user.json"
GMAIL_MODIFY_SCOPE = "https://www.googleapis.com/auth/gmail.modify"
SYSTEM_LABELS = {
    "INBOX",
    "SPAM",
    "TRASH",
    "UNREAD",
    "STARRED",
    "IMPORTANT",
    "SENT",
    "DRAFT",
    "CATEGORY_PERSONAL",
    "CATEGORY_SOCIAL",
    "CATEGORY_PROMOTIONS",
    "CATEGORY_UPDATES",
    "CATEGORY_FORUMS",
}


class GmailApiError(RuntimeError):
    """Raised when Gmail API auth or requests fail."""


def _normalize_account(account: str | None) -> str:
    normalized = (account or ACCOUNT_AGENTCORE).strip().lower()
    if normalized not in ACCOUNTS:
        raise ValueError(f"Unsupported Gmail account profile: {account}")
    return normalized


def has_oauth_credentials(env_map: dict[str, str] | None = None, account: str = ACCOUNT_AGENTCORE) -> bool:
    return bool(_oauth_credentials(env_map=env_map, account=account))


def _authorized_user_payload(env_map: dict[str, str] | None = None, account: str = ACCOUNT_AGENTCORE) -> dict[str, str]:
    account = _normalize_account(account)
    if account == ACCOUNT_BRIAN:
        inline_json = get_env("AGENTCORE_BRIAN_GMAIL_AUTHORIZED_USER_JSON", env_map=env_map)
        if inline_json:
            return json.loads(inline_json)
        json_file = get_env("AGENTCORE_BRIAN_GMAIL_AUTHORIZED_USER_FILE", env_map=env_map)
        if not json_file and Path(BRIAN_DEFAULT_AUTHORIZED_USER_FILE).exists():
            json_file = BRIAN_DEFAULT_AUTHORIZED_USER_FILE
        if json_file:
            return json.loads(Path(json_file).read_text(encoding="utf-8"))
        return {}

    inline_json = get_env("AGENTCORE_GMAIL_AUTHORIZED_USER_JSON", env_map=env_map)
    if inline_json:
        return json.loads(inline_json)

    json_file = get_env("AGENTCORE_GMAIL_AUTHORIZED_USER_FILE", env_map=env_map)
    if json_file:
        return json.loads(Path(json_file).read_text(encoding="utf-8"))
    return {}


def _oauth_credentials(env_map: dict[str, str] | None = None, account: str = ACCOUNT_AGENTCORE) -> dict[str, str]:
    account = _normalize_account(account)
    if account == ACCOUNT_BRIAN:
        authorized_user = _authorized_user_payload(env_map=env_map, account=account)
        from_json = {
            "client_id": str(authorized_user.get("client_id", "")),
            "client_secret": str(authorized_user.get("client_secret", "")),
            "refresh_token": str(authorized_user.get("refresh_token", "")),
        }
        if all(from_json.values()):
            return from_json
        mixed = {
            "client_id": get_env(
                "AGENTCORE_GMAIL_CLIENT_ID",
                fallback_keys=("GOOGLE_OAUTH_CLIENT_ID",),
                env_map=env_map,
            )
            or from_json["client_id"],
            "client_secret": get_env(
                "AGENTCORE_GMAIL_CLIENT_SECRET",
                fallback_keys=("GOOGLE_OAUTH_CLIENT_SECRET",),
                env_map=env_map,
            )
            or from_json["client_secret"],
            "refresh_token": get_env("AGENTCORE_BRIAN_GMAIL_REFRESH_TOKEN", env_map=env_map)
            or from_json["refresh_token"],
        }
        return mixed if all(mixed.values()) else {}

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

    authorized_user = _authorized_user_payload(env_map=env_map, account=account)
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


def refresh_access_token(env_map: dict[str, str] | None = None, account: str = ACCOUNT_AGENTCORE) -> str:
    credentials = _oauth_credentials(env_map=env_map, account=account)
    if not credentials:
        if _normalize_account(account) == ACCOUNT_BRIAN:
            raise GmailApiError(
                "Missing Brian Gmail OAuth credentials. Set "
                "AGENTCORE_BRIAN_GMAIL_AUTHORIZED_USER_JSON/FILE or run "
                "`npm run email:oauth:brian`."
            )
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


def access_token(env_map: dict[str, str] | None = None, account: str = ACCOUNT_AGENTCORE) -> str:
    account = _normalize_account(account)
    token_key = "AGENTCORE_BRIAN_GMAIL_ACCESS_TOKEN" if account == ACCOUNT_BRIAN else "AGENTCORE_GMAIL_ACCESS_TOKEN"
    configured_token = get_env(token_key, env_map=env_map)
    return configured_token or refresh_access_token(env_map=env_map, account=account)


def gmail_request(
    method: str,
    path: str,
    token: str,
    query: dict[str, str | int | list[str]] | None = None,
    payload: dict | None = None,
) -> dict:
    url = f"{GMAIL_API_BASE}{path}"
    if query:
        pairs: list[tuple[str, str | int]] = []
        for key, value in query.items():
            if isinstance(value, list):
                pairs.extend((key, item) for item in value)
            else:
                pairs.append((key, value))
        url = f"{url}?{urllib.parse.urlencode(pairs)}"
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


def decode_body_data(data: str) -> str:
    return decode_raw_message(data).decode("utf-8", errors="replace")


def get_profile(env_map: dict[str, str] | None = None, account: str = ACCOUNT_AGENTCORE) -> dict:
    token = access_token(env_map=env_map, account=account)
    return gmail_request("GET", "/users/me/profile", token=token)


def list_labels(env_map: dict[str, str] | None = None, account: str = ACCOUNT_AGENTCORE) -> list[dict]:
    token = access_token(env_map=env_map, account=account)
    payload = gmail_request("GET", "/users/me/labels", token=token)
    return list(payload.get("labels") or [])


def create_label(
    name: str,
    env_map: dict[str, str] | None = None,
    account: str = ACCOUNT_AGENTCORE,
    label_list_visibility: str = "labelShow",
    message_list_visibility: str = "show",
) -> dict:
    token = access_token(env_map=env_map, account=account)
    return gmail_request(
        "POST",
        "/users/me/labels",
        token=token,
        payload={
            "name": name,
            "labelListVisibility": label_list_visibility,
            "messageListVisibility": message_list_visibility,
        },
    )


def ensure_label(
    name: str,
    env_map: dict[str, str] | None = None,
    account: str = ACCOUNT_AGENTCORE,
) -> dict:
    existing = find_label(name, env_map=env_map, account=account)
    if existing:
        return existing
    return create_label(name, env_map=env_map, account=account)


def find_label(
    name_or_id: str,
    env_map: dict[str, str] | None = None,
    account: str = ACCOUNT_AGENTCORE,
    labels: list[dict] | None = None,
) -> dict:
    needle = name_or_id.strip()
    if not needle:
        raise GmailApiError("Label name or id is required.")
    catalog = labels if labels is not None else list_labels(env_map=env_map, account=account)
    for label in catalog:
        if str(label.get("id", "")) == needle or str(label.get("name", "")) == needle:
            return label
    if needle.upper() in SYSTEM_LABELS:
        system_id = needle.upper()
        for label in catalog:
            if str(label.get("id", "")) == system_id:
                return label
    return {}


def resolve_label_id(
    name_or_id: str,
    env_map: dict[str, str] | None = None,
    account: str = ACCOUNT_AGENTCORE,
    labels: list[dict] | None = None,
) -> str:
    label = find_label(name_or_id, env_map=env_map, account=account, labels=labels)
    if label:
        return str(label["id"])
    raise GmailApiError(f"Unknown Gmail label: {name_or_id}")


def list_messages(
    query: str = "",
    max_results: int = 20,
    env_map: dict[str, str] | None = None,
    account: str = ACCOUNT_AGENTCORE,
    page_token: str = "",
) -> dict:
    token = access_token(env_map=env_map, account=account)
    params: dict[str, str | int] = {"maxResults": max(1, min(int(max_results), 100))}
    if query:
        params["q"] = query
    if page_token:
        params["pageToken"] = page_token
    return gmail_request("GET", "/users/me/messages", token=token, query=params)


def get_message(
    message_id: str,
    env_map: dict[str, str] | None = None,
    account: str = ACCOUNT_AGENTCORE,
    fmt: str = "metadata",
    metadata_headers: list[str] | None = None,
) -> dict:
    token = access_token(env_map=env_map, account=account)
    query: dict[str, str | int | list[str]] = {"format": fmt}
    if fmt == "metadata":
        query["metadataHeaders"] = metadata_headers or ["From", "To", "Subject", "Date"]
    return gmail_request(
        "GET",
        f"/users/me/messages/{urllib.parse.quote(message_id)}",
        token=token,
        query=query,
    )


def header_map(message: dict) -> dict[str, str]:
    headers = (((message.get("payload") or {}).get("headers")) or [])
    return {str(item.get("name", "")).lower(): str(item.get("value", "")) for item in headers}


def extract_text_body(payload: dict | None) -> str:
    if not payload:
        return ""
    mime = str(payload.get("mimeType", ""))
    data = str((payload.get("body") or {}).get("data") or "")
    if mime.startswith("text/") and data:
        return decode_body_data(data)
    for part in payload.get("parts") or []:
        text = extract_text_body(part)
        if text:
            return text
    return ""


def modify_message(
    message_id: str,
    add_label_ids: list[str] | None = None,
    remove_label_ids: list[str] | None = None,
    env_map: dict[str, str] | None = None,
    account: str = ACCOUNT_AGENTCORE,
) -> dict:
    token = access_token(env_map=env_map, account=account)
    payload = {
        "addLabelIds": add_label_ids or [],
        "removeLabelIds": remove_label_ids or [],
    }
    return gmail_request(
        "POST",
        f"/users/me/messages/{urllib.parse.quote(message_id)}/modify",
        token=token,
        payload=payload,
    )


def archive_message(
    message_id: str,
    env_map: dict[str, str] | None = None,
    account: str = ACCOUNT_AGENTCORE,
) -> dict:
    return modify_message(
        message_id,
        remove_label_ids=["INBOX"],
        env_map=env_map,
        account=account,
    )


def trash_message(
    message_id: str,
    env_map: dict[str, str] | None = None,
    account: str = ACCOUNT_AGENTCORE,
) -> dict:
    token = access_token(env_map=env_map, account=account)
    return gmail_request(
        "POST",
        f"/users/me/messages/{urllib.parse.quote(message_id)}/trash",
        token=token,
    )
