#!/usr/bin/env python3
"""Fetch inbound messages from Gmail API or IMAP with checkpointing."""

from __future__ import annotations

import argparse
import email
import imaplib
import json
from datetime import datetime, timedelta, timezone
from email.message import Message
from pathlib import Path

import gmail_api
from common import (
    compact_whitespace,
    decode_mime_header,
    get_env,
    load_env_file,
    make_thread_key,
    message_body_text,
    normalize_email_address,
    normalize_subject,
    read_json,
    resolve_email_credentials,
    utc_now_iso,
    write_json,
)


DEFAULT_STATE_PATH = ".agentcore/state/email-last-uid.json"
DEFAULT_OUTPUT_PATH = ".agentcore/state/email-fetch/latest.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch new inbox emails from IMAP.")
    parser.add_argument("--mailbox", default="INBOX", help="Mailbox/folder to query.")
    parser.add_argument("--limit", type=int, default=50, help="Maximum accepted messages to output.")
    parser.add_argument("--state-file", default=DEFAULT_STATE_PATH, help="Path for UID checkpoint JSON.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH, help="Path for fetched message JSON.")
    parser.add_argument(
        "--bootstrap-window",
        type=int,
        default=250,
        help="On first run with no checkpoint, scan only the most recent N UIDs.",
    )
    parser.add_argument(
        "--transport",
        default="",
        help="Email transport: auto, gmail-api, or imap. Defaults to AGENTCORE_EMAIL_TRANSPORT/auto.",
    )
    return parser.parse_args()


def parse_message(uid: int | str, msg: Message) -> dict[str, str | int]:
    from_value = decode_mime_header(msg.get("From", ""))
    to_value = decode_mime_header(msg.get("To", ""))
    subject = normalize_subject(msg.get("Subject", ""))
    message_id = compact_whitespace(msg.get("Message-Id", "")).strip("<>")
    body = message_body_text(msg)

    return {
        "uid": uid,
        "message_id": message_id,
        "from": from_value,
        "from_email": normalize_email_address(from_value),
        "to": to_value,
        "subject": subject,
        "date_header": compact_whitespace(msg.get("Date", "")),
        "received_at": utc_now_iso(),
        "thread_key": make_thread_key(message_id, subject),
        "body_text": body,
        "body_preview": compact_whitespace(body)[:240],
    }


def _gmail_after_query(last_internal_ms: int) -> str:
    if last_internal_ms <= 0:
        return ""
    dt = datetime.fromtimestamp(last_internal_ms / 1000, tz=timezone.utc) - timedelta(days=2)
    return f" after:{dt.strftime('%Y/%m/%d')}"


def fetch_gmail_api(args: argparse.Namespace, env_map: dict[str, str], allowed_senders: set[str]) -> dict:
    state_path = Path(args.state_file)
    output_path = Path(args.output)
    state = read_json(state_path, default={"last_internal_date_ms": 0, "seen_message_ids": []})
    last_internal_ms = int(state.get("last_internal_date_ms", 0) or 0)
    seen_at_last = {str(item) for item in state.get("seen_message_ids", [])}
    sender_terms = [f"from:{sender}" for sender in sorted(allowed_senders)]
    sender_query = sender_terms[0] if len(sender_terms) == 1 else "{" + " ".join(sender_terms) + "}"
    query = f"in:inbox {sender_query}{_gmail_after_query(last_internal_ms)}"
    token = gmail_api.access_token(env_map=env_map)
    max_results = min(max(args.limit, args.bootstrap_window, 1), 500)

    messages: list[dict] = []
    page_token = ""
    while True:
        params: dict[str, str | int] = {"q": query, "maxResults": max_results}
        if page_token:
            params["pageToken"] = page_token
        page = gmail_api.gmail_request("GET", "/users/me/messages", token=token, query=params)
        messages.extend(page.get("messages", []))
        page_token = str(page.get("nextPageToken", ""))
        if not page_token or len(messages) >= max_results:
            break

    accepted_messages: list[dict[str, str | int]] = []
    seen_message_ids: list[str] = []
    for item in messages[:max_results]:
        gmail_id = str(item.get("id", ""))
        if not gmail_id:
            continue
        detail = gmail_api.gmail_request(
            "GET",
            f"/users/me/messages/{gmail_id}",
            token=token,
            query={"format": "raw"},
        )
        internal_ms = int(detail.get("internalDate", 0) or 0)
        seen_message_ids.append(gmail_id)
        if last_internal_ms and internal_ms < last_internal_ms:
            continue
        if last_internal_ms and internal_ms == last_internal_ms and gmail_id in seen_at_last:
            continue
        raw = str(detail.get("raw", ""))
        if not raw:
            continue
        parsed = email.message_from_bytes(gmail_api.decode_raw_message(raw))
        payload = parse_message(f"gmail-{gmail_id}", parsed)
        payload["gmail_message_id"] = gmail_id
        payload["gmail_thread_id"] = str(detail.get("threadId", ""))
        payload["internal_date_ms"] = internal_ms
        if allowed_senders and payload["from_email"] not in allowed_senders:
            continue
        accepted_messages.append(payload)

    accepted_messages.sort(key=lambda item: int(item.get("internal_date_ms", 0)))
    if args.limit > 0:
        accepted_messages = accepted_messages[-args.limit :]

    max_internal_ms = max([int(item.get("internal_date_ms", 0)) for item in accepted_messages], default=last_internal_ms)
    seen_at_max = [
        str(item.get("gmail_message_id", ""))
        for item in accepted_messages
        if int(item.get("internal_date_ms", 0)) == max_internal_ms and item.get("gmail_message_id")
    ]
    checkpoint = {
        "transport": "gmail-api",
        "last_internal_date_ms": max_internal_ms,
        "seen_message_ids": seen_at_max if seen_at_max else sorted(seen_at_last),
        "updated_at": utc_now_iso(),
        "mailbox": args.mailbox,
        "allowed_senders": sorted(allowed_senders),
    }
    write_json(state_path, checkpoint)

    output = {
        "fetched_at": utc_now_iso(),
        "transport": "gmail-api",
        "mailbox": args.mailbox,
        "start_uid": last_internal_ms,
        "end_uid": max_internal_ms,
        "total_seen": len(seen_message_ids),
        "accepted_count": len(accepted_messages),
        "allowed_senders": sorted(allowed_senders),
        "messages": accepted_messages,
    }
    write_json(output_path, output)
    print(json.dumps({k: output[k] for k in ("total_seen", "accepted_count", "start_uid", "end_uid")}))
    return output


def parse_uidnext(status_payload: bytes) -> int:
    text = status_payload.decode("utf-8", errors="replace")
    marker = "UIDNEXT "
    if marker not in text:
        return 0
    tail = text.split(marker, 1)[1]
    digits = []
    for char in tail:
        if char.isdigit():
            digits.append(char)
        elif digits:
            break
    return int("".join(digits)) if digits else 0


def main() -> int:
    args = parse_args()
    env_map = load_env_file(".env")

    default_sender = get_env(
        "AGENTCORE_CLIENT_EMAIL",
        fallback_keys=("CLIENT_EMAIL",),
        default="briandherbert@gmail.com",
        env_map=env_map,
    )
    allowed_senders: set[str] = {default_sender.strip().lower()}
    transport = gmail_api.resolve_transport(args.transport, "gmail-api", "imap", env_map=env_map)

    if transport == "gmail-api":
        fetch_gmail_api(args, env_map, allowed_senders)
        return 0

    username, password = resolve_email_credentials(env_map=env_map)

    state_path = Path(args.state_file)
    output_path = Path(args.output)
    state = read_json(state_path, default={"last_uid": 0})
    last_uid = int(state.get("last_uid", 0))
    start_uid = last_uid + 1

    imap_host = get_env(
        "AGENTCORE_IMAP_HOST",
        fallback_keys=("IMAP_HOST",),
        default="imap.gmail.com",
        env_map=env_map,
    )
    imap_port = int(
        get_env(
            "AGENTCORE_IMAP_PORT",
            fallback_keys=("IMAP_PORT",),
            default="993",
            env_map=env_map,
        )
    )

    accepted_messages: list[dict[str, str | int]] = []
    seen_uids: list[int] = []

    with imaplib.IMAP4_SSL(imap_host, imap_port) as imap:
        imap.login(username, password)
        status, _ = imap.select(args.mailbox, readonly=True)
        if status != "OK":
            raise RuntimeError(f"Unable to select mailbox: {args.mailbox}")

        uidnext = 0
        status, status_data = imap.status(args.mailbox, "(UIDNEXT)")
        if status == "OK" and status_data and status_data[0]:
            uidnext = parse_uidnext(status_data[0])

        if last_uid == 0 and uidnext > 0 and args.bootstrap_window > 0:
            start_uid = max(1, uidnext - args.bootstrap_window)

        status, data = imap.uid("SEARCH", None, f"UID {start_uid}:*")
        if status != "OK":
            raise RuntimeError("IMAP UID search failed")

        uid_tokens = [token for token in data[0].split() if token]
        for token in uid_tokens:
            uid = int(token.decode("utf-8"))
            if uid < start_uid:
                continue
            seen_uids.append(uid)
            status, msg_data = imap.uid("FETCH", str(uid), "(BODY.PEEK[])")
            if status != "OK" or not msg_data or msg_data[0] is None:
                continue
            raw_bytes = msg_data[0][1]
            if not raw_bytes:
                continue
            parsed = email.message_from_bytes(raw_bytes)
            payload = parse_message(uid, parsed)
            if allowed_senders and payload["from_email"] not in allowed_senders:
                continue
            accepted_messages.append(payload)

    accepted_messages.sort(key=lambda item: int(item["uid"]))
    if args.limit > 0:
        accepted_messages = accepted_messages[-args.limit :]

    end_uid = max(seen_uids) if seen_uids else last_uid
    checkpoint = {
        "last_uid": end_uid,
        "updated_at": utc_now_iso(),
        "mailbox": args.mailbox,
        "allowed_senders": sorted(allowed_senders),
    }
    write_json(state_path, checkpoint)

    output = {
        "fetched_at": utc_now_iso(),
        "mailbox": args.mailbox,
        "start_uid": start_uid,
        "end_uid": end_uid,
        "total_seen": len(seen_uids),
        "accepted_count": len(accepted_messages),
        "allowed_senders": sorted(allowed_senders),
        "messages": accepted_messages,
    }
    write_json(output_path, output)
    print(json.dumps({k: output[k] for k in ("total_seen", "accepted_count", "start_uid", "end_uid")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
