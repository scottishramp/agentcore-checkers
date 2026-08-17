#!/usr/bin/env python3
"""Create and update AgentCore-owned Google Docs."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

EMAIL_DIR = Path(__file__).resolve().parent.parent / "email"
if str(EMAIL_DIR) not in sys.path:
    sys.path.insert(0, str(EMAIL_DIR))

import gmail_api  # noqa: E402

DOCS_API_BASE = "https://docs.googleapis.com/v1"
DRIVE_API_BASE = "https://www.googleapis.com/drive/v3"
GOOGLE_DOC_MIME = "application/vnd.google-apps.document"
GOOGLE_FOLDER_MIME = "application/vnd.google-apps.folder"


class GoogleDocsError(RuntimeError):
    """Raised when Docs or Drive requests fail."""


def _token(env_map: dict[str, str] | None = None) -> str:
    return gmail_api.access_token(env_map=env_map, account=gmail_api.ACCOUNT_AGENTCORE)


def _request(
    method: str,
    url: str,
    token: str,
    payload: dict | None = None,
    timeout: int = 60,
) -> dict:
    data = None
    headers = {"Authorization": f"Bearer {token}"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise GoogleDocsError(f"{method} {url} failed: {exc.code} {detail}") from exc
    return json.loads(body) if body else {}


def drive_create_file(
    name: str,
    mime_type: str,
    env_map: dict[str, str] | None = None,
    parent_id: str = "",
) -> dict:
    token = _token(env_map=env_map)
    metadata: dict[str, str | list[str]] = {"name": name, "mimeType": mime_type}
    if parent_id:
        metadata["parents"] = [parent_id]
    query = urllib.parse.urlencode({"fields": "id,name,mimeType,webViewLink,parents"})
    return _request("POST", f"{DRIVE_API_BASE}/files?{query}", token, payload=metadata)


def find_app_file(
    name: str,
    mime_type: str,
    env_map: dict[str, str] | None = None,
    parent_id: str = "",
) -> dict:
    token = _token(env_map=env_map)
    clauses = [f"name = '{name.replace(chr(39), chr(92) + chr(39))}'", f"mimeType = '{mime_type}'", "trashed = false"]
    if parent_id:
        clauses.append(f"'{parent_id}' in parents")
    query = urllib.parse.urlencode(
        {
            "q": " and ".join(clauses),
            "pageSize": 1,
            "fields": "files(id,name,mimeType,webViewLink,parents)",
        }
    )
    payload = _request("GET", f"{DRIVE_API_BASE}/files?{query}", token)
    files = payload.get("files") or []
    return files[0] if files else {}


def ensure_folder(name: str, env_map: dict[str, str] | None = None) -> dict:
    existing = find_app_file(name, GOOGLE_FOLDER_MIME, env_map=env_map)
    if existing:
        return existing
    return drive_create_file(name, GOOGLE_FOLDER_MIME, env_map=env_map)


def ensure_document(title: str, env_map: dict[str, str] | None = None, folder_id: str = "") -> dict:
    existing = find_app_file(title, GOOGLE_DOC_MIME, env_map=env_map, parent_id=folder_id)
    if existing:
        return existing
    return drive_create_file(title, GOOGLE_DOC_MIME, env_map=env_map, parent_id=folder_id)


def share_file(
    file_id: str,
    email: str,
    env_map: dict[str, str] | None = None,
    role: str = "writer",
    notify: bool = True,
) -> dict:
    token = _token(env_map=env_map)
    query = urllib.parse.urlencode(
        {
            "sendNotificationEmail": "true" if notify else "false",
            "fields": "id,role,type,emailAddress",
        }
    )
    return _request(
        "POST",
        f"{DRIVE_API_BASE}/files/{urllib.parse.quote(file_id)}/permissions?{query}",
        token,
        payload={"type": "user", "role": role, "emailAddress": email},
    )


def get_document(document_id: str, env_map: dict[str, str] | None = None) -> dict:
    token = _token(env_map=env_map)
    return _request("GET", f"{DOCS_API_BASE}/documents/{urllib.parse.quote(document_id)}", token)


def export_document_html(document_id: str, env_map: dict[str, str] | None = None) -> str:
    """Export a Google Doc as HTML via Drive.

    The Docs API does not expose checklist checked state, but the HTML export
    renders checked items with text-decoration:line-through, so callers can
    detect what the user has checked off.
    """
    token = _token(env_map=env_map)
    query = urllib.parse.urlencode({"mimeType": "text/html"})
    url = f"{DRIVE_API_BASE}/files/{urllib.parse.quote(document_id)}/export?{query}"
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise GoogleDocsError(f"GET {url} failed: {exc.code} {detail}") from exc


def replace_document_content(
    document_id: str,
    paragraphs: list[dict],
    env_map: dict[str, str] | None = None,
) -> dict:
    """Replace the document with styled paragraphs.

    Each paragraph is a dict with:
      text: str
      style: TITLE | HEADING_1 | NORMAL (optional)
      bold: bool
      checklist: bool (render as a clickable checkbox list item)
      links: list[{offset, length, url}] relative to paragraph text
    """
    token = _token(env_map=env_map)
    lines = [str(item.get("text", "")) for item in paragraphs]
    text = "\n".join(lines) + "\n"
    document = get_document(document_id, env_map=env_map)
    body = document.get("body") or {}
    content = body.get("content") or []
    end_index = int((content[-1] or {}).get("endIndex", 2)) if content else 2
    requests: list[dict] = []
    if end_index > 2:
        requests.append(
            {
                "deleteContentRange": {
                    "range": {"startIndex": 1, "endIndex": end_index - 1},
                }
            }
        )
    requests.append({"insertText": {"location": {"index": 1}, "text": text}})

    index = 1
    checklist_requests: list[dict] = []
    for item in paragraphs:
        paragraph_text = str(item.get("text", ""))
        start = index
        text_end = start + len(paragraph_text)
        newline_end = text_end + 1
        if item.get("checklist") and text_end > start:
            checklist_requests.append(
                {
                    "createParagraphBullets": {
                        "range": {"startIndex": start, "endIndex": text_end},
                        "bulletPreset": "BULLET_CHECKBOX",
                    }
                }
            )
        style = str(item.get("style") or "")
        if style in {"TITLE", "HEADING_1", "HEADING_2"} and newline_end > start:
            requests.append(
                {
                    "updateParagraphStyle": {
                        "range": {"startIndex": start, "endIndex": newline_end},
                        "paragraphStyle": {"namedStyleType": style},
                        "fields": "namedStyleType",
                    }
                }
            )
        if item.get("italic") and text_end > start:
            requests.append(
                {
                    "updateTextStyle": {
                        "range": {"startIndex": start, "endIndex": text_end},
                        "textStyle": {"italic": True},
                        "fields": "italic",
                    }
                }
            )
        if item.get("bold") and text_end > start:
            requests.append(
                {
                    "updateTextStyle": {
                        "range": {"startIndex": start, "endIndex": text_end},
                        "textStyle": {"bold": True},
                        "fields": "bold",
                    }
                }
            )
        for link in item.get("links") or []:
            offset = int(link.get("offset", 0))
            length = int(link.get("length", 0))
            url = str(link.get("url", "")).strip()
            if not url or length <= 0:
                continue
            link_start = start + offset
            link_end = link_start + length
            textStyle = {"link": {"url": url}, "underline": True}
            fields = "link,underline"
            if item.get("bold"):
                textStyle["bold"] = True
                fields = "link,underline,bold"
            requests.append(
                {
                    "updateTextStyle": {
                        "range": {"startIndex": link_start, "endIndex": link_end},
                        "textStyle": textStyle,
                        "fields": fields,
                    }
                }
            )
        index = newline_end

    # Bullet creation goes last: our paragraphs have no leading tabs, so these
    # requests do not shift the indices used by the styling requests above.
    requests.extend(checklist_requests)

    return _request(
        "POST",
        f"{DOCS_API_BASE}/documents/{urllib.parse.quote(document_id)}:batchUpdate",
        token,
        payload={"requests": requests},
        timeout=90,
    )


def replace_document_text(
    document_id: str,
    text: str,
    heading_lines: list[str] | None = None,
    title_line: str = "",
    env_map: dict[str, str] | None = None,
) -> dict:
    paragraphs = []
    heading_set = {line.strip() for line in (heading_lines or []) if line.strip()}
    for line in text.split("\n"):
        style = ""
        stripped = line.strip()
        if title_line and stripped == title_line.strip():
            style = "TITLE"
        elif stripped in heading_set:
            style = "HEADING_1"
        paragraphs.append({"text": line, "style": style})
    return replace_document_content(document_id, paragraphs, env_map=env_map)
