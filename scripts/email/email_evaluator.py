#!/usr/bin/env python3
"""LLM evaluation of school/family email with a durable evaluation ledger.

Backends, in preference order:
1. Gemini REST (GEMINI_API_KEY / GOOGLE_AI_STUDIO_API_KEY / GOOGLE_API_KEY)
2. Cursor Agent CLI (cursor-agent / agent), authenticated locally or via CURSOR_API_KEY in CI

The ledger stores one verdict per Gmail message id so each email is evaluated once.
Metadata only — no full bodies persisted.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

LEDGER_PATH = Path("agentcore/knowledge/email/eval-ledger.json")
LEDGER_RETENTION_DAYS = 60
BATCH_SIZE = 12
BODY_CHARS = 900

VALID_CATEGORIES = {"action", "teacher_info", "sports", "classroom_app", "fyi", "irrelevant"}

# Cheap pre-filter: mail that is never worth an LLM call.
OBVIOUS_SKIP_FROM_RE = re.compile(
    r"(mailer-daemon|postmaster@|calendar-notification@google\.com|"
    r"drive-shares-noreply@google\.com|no-reply@accounts\.google\.com)",
    re.I,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_ledger(path: Path = LEDGER_PATH) -> dict:
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("evaluated"), dict):
                return data
        except json.JSONDecodeError:
            pass
    return {"version": 1, "evaluated": {}}


def save_ledger(ledger: dict, path: Path = LEDGER_PATH) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=LEDGER_RETENTION_DAYS)
    kept = {}
    for message_id, entry in (ledger.get("evaluated") or {}).items():
        stamp = str(entry.get("evaluated_at") or "")
        try:
            when = datetime.fromisoformat(stamp)
        except ValueError:
            when = datetime.now(timezone.utc)
        if when >= cutoff:
            kept[message_id] = entry
    payload = {"version": 1, "evaluated": kept}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def prefilter_verdict(row: dict) -> dict | None:
    """Return a skip verdict for obviously irrelevant mail, else None (send to LLM)."""
    sender = str(row.get("from") or "")
    if OBVIOUS_SKIP_FROM_RE.search(sender):
        return {
            "id": str(row.get("id") or ""),
            "relevant": False,
            "category": "irrelevant",
            "children": [],
            "line": "",
            "need": None,
            "due_date": None,
            "learn": [],
            "unsubscribe": False,
            "reason": "prefilter: automated notification sender",
        }
    return None


def backend_name() -> str:
    if gemini_api_key():
        return "gemini"
    if find_cursor_cli():
        return "cursor"
    return ""


def gemini_api_key() -> str:
    for name in ("GEMINI_API_KEY", "GOOGLE_AI_STUDIO_API_KEY", "GOOGLE_API_KEY"):
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""


def find_cursor_cli() -> str:
    for name in ("cursor-agent", "agent"):
        found = shutil.which(name)
        if found:
            return found
        for base in (Path.home() / ".local/bin", Path.home() / ".cursor/bin"):
            candidate = base / name
            if candidate.exists():
                return str(candidate)
    return ""


def build_prompt(items: list[dict], context_text: str, today: str) -> str:
    payload = json.dumps(items, ensure_ascii=False, indent=1)
    return f"""You are AgentCore, the private administrative assistant for Brian Herbert's family. Today is {today}.

Household context (authoritative; do not contradict it):
{context_text}

Below is a JSON array of emails from Brian's mailbox (id, from, subject, date, body excerpt). Evaluate each one for the family school digest.

For every email return one JSON object:
- "id": copy the input id exactly.
- "relevant": false if this email has no value to the family digest (pure marketing, duplicates of school blasts, tracking noise). Otherwise true.
- "category": one of "action" (a parent must do something), "teacher_info" (from a teacher/coach, informational), "sports" (team/athletics info), "classroom_app" (Seesaw or similar), "fyi" (school announcement worth a glance), "irrelevant".
- "children": which of Daniel, Nathan, Ezra, Silver, Levi this concerns (empty list = whole family).
- "line": ONE distilled sentence for the digest. Start with "Need:" if a parent must act (state the specific to-do and any date), otherwise "FYI:" with the single key fact. Do not copy greetings or excerpts. Empty string if irrelevant.
- "need": the to-do as a short imperative sentence, or null.
- "due_date": "YYYY-MM-DD" if the item has a real date/deadline, else null.
- "learn": durable facts worth remembering, as a list of {{"child": name-or-null, "type": "teacher"|"sport"|"activity"|"fact", "value": short fact, "role": optional role/team, "person": optional teacher/coach name}}. Only include NEW facts not already in the household context. Examples: a newly named teacher, a kid joining a team, a family subscription. Empty list if nothing new.
- "unsubscribe": true if this sender is recurring noise Brian should consider unsubscribing from.

Rules:
- A welcome message or excitement note with no parent to-do is NOT an action.
- "Bring/wear/pay/sign/register/fill out/turn in" style requests ARE actions; quote the concrete ask in "line".
- Do not invent facts, children, or dates that are not in the email.
- Answer with ONLY the JSON array, no prose, no code fences.

Emails:
{payload}
"""


def _parse_json_array(text: str) -> list[dict]:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start < 0 or end <= start:
        raise ValueError("No JSON array in model output.")
    parsed = json.loads(cleaned[start : end + 1])
    if not isinstance(parsed, list):
        raise ValueError("Model output is not a JSON array.")
    return [item for item in parsed if isinstance(item, dict)]


def _call_gemini(prompt: str) -> str:
    model = os.getenv("AGENTCORE_EMAIL_EVAL_GEMINI_MODEL", "gemini-2.5-flash")
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{urllib.parse.quote(model)}:generateContent?key={urllib.parse.quote(gemini_api_key())}"
    )
    body = json.dumps(
        {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
        }
    ).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = json.loads(response.read().decode("utf-8"))
    candidates = payload.get("candidates") or []
    parts = ((candidates[0].get("content") or {}).get("parts") or []) if candidates else []
    return "\n".join(str(part.get("text") or "") for part in parts)


def _call_cursor(prompt: str) -> str:
    cli = find_cursor_cli()
    if not cli:
        raise FileNotFoundError("Cursor Agent CLI not found.")
    model = os.getenv("AGENTCORE_EMAIL_EVAL_MODEL") or os.getenv("AGENTCORE_CURSOR_MODEL") or "grok-4.6"
    command = [cli, "-p", "--output-format", "text", "--trust", "--model", model, prompt]
    proc = subprocess.run(
        command,
        text=True,
        capture_output=True,
        timeout=int(os.getenv("AGENTCORE_EMAIL_EVAL_TIMEOUT_SECONDS", "600")),
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Cursor CLI eval failed ({proc.returncode}): {proc.stderr.strip()[:400]}")
    return proc.stdout


def normalize_verdict(raw: dict, valid_children: list[str]) -> dict:
    children = [name for name in (raw.get("children") or []) if name in valid_children]
    category = str(raw.get("category") or "").strip().lower()
    if category not in VALID_CATEGORIES:
        category = "fyi"
    need = raw.get("need")
    need = str(need).strip() if need else None
    line = str(raw.get("line") or "").strip()
    relevant = bool(raw.get("relevant", True)) and category != "irrelevant"
    if relevant and not line:
        line = f"Need: {need}" if need else "FYI: see the linked email."
    due_date = raw.get("due_date")
    if due_date:
        due_date = str(due_date).strip()
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", due_date):
            due_date = None
    learn = []
    for item in raw.get("learn") or []:
        if not isinstance(item, dict):
            continue
        value = str(item.get("value") or "").strip()
        kind = str(item.get("type") or "fact").strip().lower()
        if not value or kind not in {"teacher", "sport", "activity", "fact"}:
            continue
        child = item.get("child")
        learn.append(
            {
                "child": child if child in valid_children else None,
                "type": kind,
                "value": value,
                "role": str(item.get("role") or "").strip(),
                "person": str(item.get("person") or "").strip(),
            }
        )
    return {
        "id": str(raw.get("id") or ""),
        "relevant": relevant,
        "category": category if relevant else "irrelevant",
        "children": children,
        "line": line if relevant else "",
        "need": need if relevant else None,
        "due_date": due_date,
        "learn": learn,
        "unsubscribe": bool(raw.get("unsubscribe", False)),
    }


def evaluate_rows(rows: list[dict], context_text: str, valid_children: list[str]) -> tuple[dict[str, dict], str]:
    """Evaluate rows with the LLM. Returns ({message_id: verdict}, backend). Raises on total failure."""
    backend = backend_name()
    if not backend:
        raise RuntimeError("No LLM backend: set GEMINI_API_KEY or install Cursor Agent CLI.")
    call = _call_gemini if backend == "gemini" else _call_cursor
    today = datetime.now(timezone.utc).astimezone().strftime("%A %Y-%m-%d")
    verdicts: dict[str, dict] = {}
    for offset in range(0, len(rows), BATCH_SIZE):
        batch = rows[offset : offset + BATCH_SIZE]
        items = [
            {
                "id": str(row.get("id") or ""),
                "from": str(row.get("from") or "")[:120],
                "subject": str(row.get("subject") or "")[:200],
                "date": str(row.get("date") or "")[:60],
                "body": str(row.get("body_text") or row.get("snippet") or "")[:BODY_CHARS],
            }
            for row in batch
        ]
        prompt = build_prompt(items, context_text, today)
        raw_out = ""
        for attempt in (1, 2):
            try:
                raw_out = call(prompt)
                parsed = _parse_json_array(raw_out)
                break
            except (ValueError, json.JSONDecodeError):
                if attempt == 2:
                    raise
        for raw in parsed:
            verdict = normalize_verdict(raw, valid_children)
            if verdict["id"]:
                verdicts[verdict["id"]] = verdict
    return verdicts, backend


def record_verdict(ledger: dict, row: dict, verdict: dict, backend: str, link: str = "") -> None:
    ledger.setdefault("evaluated", {})[str(row.get("id") or "")] = {
        "from": str(row.get("from") or "")[:160],
        "subject": str(row.get("subject") or "")[:200],
        "date": str(row.get("date") or "")[:60],
        "link": link,
        "verdict": {key: value for key, value in verdict.items() if key != "id"},
        "backend": backend,
        "evaluated_at": _now_iso(),
    }
