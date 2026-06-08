#!/usr/bin/env python3
"""Write deterministic knowledge updates and optional summary email replies."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
EMAIL_DIR = SCRIPT_DIR.parent / "email"
if str(EMAIL_DIR) not in sys.path:
    sys.path.insert(0, str(EMAIL_DIR))

import gmail_api  # noqa: E402
from common import get_env, load_env_file, resolve_email_address  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish ingestion ledger updates and summary email.")
    parser.add_argument("--summary", default=".agentcore/state/ingestion-summary.json", help="Combined summary JSON path.")
    parser.add_argument("--drive-summary", default=".agentcore/state/drive-ingest-summary.json", help="Drive summary JSON path.")
    parser.add_argument(
        "--ledger",
        default="agentcore/knowledge/communications/ingestion-ledger.md",
        help="Knowledge ledger markdown path.",
    )
    parser.add_argument(
        "--send-policy",
        default="changes",
        choices=("always", "changes", "never"),
        help="When to send summary email to trusted client.",
    )
    parser.add_argument("--project", default="Ingestion", help="Project label used in subject line.")
    return parser.parse_args()


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _should_send(summary: dict, send_policy: str) -> bool:
    if send_policy == "never":
        return False
    if send_policy == "always":
        return True
    drive = summary.get("drive", {})
    documents = int((drive or {}).get("documents_created", 0) or 0)
    photos = int((drive or {}).get("photos_created", 0) or 0)
    # Direct email intake has its own natural reply path; do not send a
    # second operational "ingestion update" just because an email task queued.
    return bool(documents > 0 or photos > 0)


def _format_ledger_entry(summary: dict, drive_summary: dict) -> str:
    generated = str(summary.get("generated_at", "")) or _now_iso()
    reason_codes = summary.get("reason_codes", [])
    totals = summary.get("totals", {})
    email = summary.get("email", {})
    chat = summary.get("chat", {})
    drive = summary.get("drive", {})
    errors = summary.get("errors", [])
    created_items = drive_summary.get("created_items", []) if isinstance(drive_summary.get("created_items"), list) else []

    lines = [
        f"## {generated} | {', '.join(reason_codes) if reason_codes else 'NO_REASON'}",
        "",
        f"- Records created: {int((totals or {}).get('records_created', 0) or 0)}",
        f"- Tasks created: {int((totals or {}).get('tasks_created', 0) or 0)}",
        f"- Email normalized records: {int((email or {}).get('normalized_count', 0) or 0)}",
        f"- Chat normalized records: {int((chat or {}).get('normalized_count', 0) or 0)}",
        f"- Drive documents: {int((drive or {}).get('documents_created', 0) or 0)}",
        f"- Photo records: {int((drive or {}).get('photos_created', 0) or 0)}",
    ]
    if errors:
        lines.append(f"- Errors: {errors}")
    if created_items:
        lines.append("- New items:")
        for item in created_items[:5]:
            lines.append(
                f"  - [{item.get('classification', 'item')}] {item.get('title', '')} ({item.get('drive_file_id', '')})"
            )
    lines.append("")
    return "\n".join(lines)


def _write_ledger(ledger_path: Path, entry: str) -> None:
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    if not ledger_path.exists():
        header = [
            "# Ingestion Ledger",
            "",
            "Deterministic ingestion run history across email, Drive documents, and photo uploads.",
            "",
        ]
        ledger_path.write_text("\n".join(header), encoding="utf-8")
    with ledger_path.open("a", encoding="utf-8") as handle:
        if not entry.startswith("\n"):
            handle.write("\n")
        handle.write(entry.rstrip("\n"))
        handle.write("\n")


def _build_email_body(summary: dict) -> str:
    reasons = summary.get("reason_codes", [])
    totals = summary.get("totals", {})
    drive = summary.get("drive", {})
    email = summary.get("email", {})
    chat = summary.get("chat", {})
    lines = [
        "Ingestion update:",
        "",
        f"- Reason codes: {reasons}",
        f"- Records created: {int((totals or {}).get('records_created', 0) or 0)}",
        f"- Tasks created: {int((totals or {}).get('tasks_created', 0) or 0)}",
        f"- Email normalized: {int((email or {}).get('normalized_count', 0) or 0)}",
        f"- Chat normalized: {int((chat or {}).get('normalized_count', 0) or 0)}",
        f"- Drive documents: {int((drive or {}).get('documents_created', 0) or 0)}",
        f"- Photo records: {int((drive or {}).get('photos_created', 0) or 0)}",
    ]
    lines.extend(["", f"Generated at: {summary.get('generated_at', _now_iso())}"])
    return "\n".join(lines) + "\n"


def _send_email(summary: dict, args: argparse.Namespace, env_map: dict[str, str]) -> dict:
    trusted_client_email = get_env(
        "AGENTCORE_CLIENT_EMAIL",
        fallback_keys=("CLIENT_EMAIL",),
        default="briandherbert@gmail.com",
        env_map=env_map,
    )
    sender = resolve_email_address(env_map=env_map)
    reason_codes = summary.get("reason_codes", [])
    primary_reason = reason_codes[0] if reason_codes else "NO_NEW_ITEMS"

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = trusted_client_email
    msg["Subject"] = f"[AgentCore][Update][{args.project}] {primary_reason}"
    msg.set_content(_build_email_body(summary))
    result = gmail_api.send_message(msg, env_map=env_map)
    return {"to": trusted_client_email, "gmail_message_id": result.get("id", "")}


def main() -> int:
    args = parse_args()
    summary = _read_json(Path(args.summary))
    drive_summary = _read_json(Path(args.drive_summary))
    ledger_path = Path(args.ledger)
    ledger_entry = _format_ledger_entry(summary=summary, drive_summary=drive_summary)
    _write_ledger(ledger_path, ledger_entry)

    output = {
        "published_at": _now_iso(),
        "ledger_path": str(ledger_path),
        "email_sent": False,
        "send_policy": args.send_policy,
        "reason_codes": summary.get("reason_codes", []),
    }
    env_map = load_env_file(".env")
    if _should_send(summary, args.send_policy):
        try:
            email_result = _send_email(summary=summary, args=args, env_map=env_map)
            output["email_sent"] = True
            output.update(email_result)
        except Exception as exc:  # pragma: no cover - network/env dependent
            output["email_error"] = str(exc)

    print(json.dumps(output, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
