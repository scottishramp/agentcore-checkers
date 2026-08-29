"""Durable per-sender handling policy for Brian's personal mailbox.

The policy ledger is the memory that makes the nightly mailbox sweep cheaper and
smarter over time: each sender is decided once, and every later message from that
sender is handled without another LLM call or another question to Brian.

Policies:
- ``learn``  : messages carry durable facts about Brian; extract knowledge.
- ``info``   : legitimate but transient (receipts, notifications); note the sender, skip extraction.
- ``ignore`` : marketing, spam, automated noise; skip entirely.

Metadata only. Sender addresses, display names, and sample subjects are stored;
message bodies never are.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

POLICY_PATH = Path("agentcore/knowledge/email/sender-policy.json")

POLICY_LEARN = "learn"
POLICY_INFO = "info"
POLICY_IGNORE = "ignore"
VALID_POLICIES = {POLICY_LEARN, POLICY_INFO, POLICY_IGNORE}

SOURCE_BRIAN = "brian"
SOURCE_LLM = "llm"
SOURCE_SEED = "seed"

# Brian's answers outrank the model's guesses and are never silently overwritten.
SOURCE_RANK = {SOURCE_SEED: 0, SOURCE_LLM: 1, SOURCE_BRIAN: 2}

MAX_SAMPLE_SUBJECTS = 3


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_policy(value: str) -> str:
    policy = str(value or "").strip().lower()
    return policy if policy in VALID_POLICIES else ""


def sender_key(address: str) -> str:
    return str(address or "").strip().lower()


def domain_of(address: str) -> str:
    key = sender_key(address)
    return key.rsplit("@", 1)[-1] if "@" in key else ""


def load(path: Path = POLICY_PATH) -> dict:
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("senders"), dict):
                data.setdefault("domains", {})
                return data
        except json.JSONDecodeError:
            pass
    return {"version": 1, "senders": {}, "domains": {}}


def save(ledger: dict, path: Path = POLICY_PATH) -> None:
    payload = {
        "version": 1,
        "updated_at": now_iso(),
        "senders": ledger.get("senders") or {},
        "domains": ledger.get("domains") or {},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def lookup(ledger: dict, address: str) -> dict:
    """Resolve a sender to its policy entry, falling back to a domain-wide rule."""
    key = sender_key(address)
    entry = (ledger.get("senders") or {}).get(key)
    if isinstance(entry, dict) and normalize_policy(entry.get("policy", "")):
        return entry
    domain_entry = (ledger.get("domains") or {}).get(domain_of(key))
    if isinstance(domain_entry, dict) and normalize_policy(domain_entry.get("policy", "")):
        resolved = dict(domain_entry)
        resolved["matched_by"] = "domain"
        return resolved
    return {}


def record(
    ledger: dict,
    address: str,
    policy: str,
    source: str,
    display_name: str = "",
    rationale: str = "",
    subject: str = "",
    confidence: float | None = None,
    seen_count: int = 0,
) -> bool:
    """Record a sender policy. Returns False when an authoritative entry was preserved."""
    key = sender_key(address)
    normalized = normalize_policy(policy)
    if not key or not normalized:
        return False

    senders = ledger.setdefault("senders", {})
    existing = senders.get(key) if isinstance(senders.get(key), dict) else {}
    if existing:
        incoming_rank = SOURCE_RANK.get(source, 0)
        existing_rank = SOURCE_RANK.get(str(existing.get("source", "")), 0)
        if incoming_rank < existing_rank:
            return False

    subjects = [str(item) for item in (existing.get("sample_subjects") or []) if str(item).strip()]
    trimmed_subject = str(subject or "").strip()[:160]
    if trimmed_subject and trimmed_subject not in subjects:
        subjects.append(trimmed_subject)

    entry = {
        "policy": normalized,
        "source": source,
        "display_name": str(display_name or existing.get("display_name", ""))[:120],
        "rationale": str(rationale or existing.get("rationale", ""))[:300],
        "sample_subjects": subjects[-MAX_SAMPLE_SUBJECTS:],
        "message_count": int(existing.get("message_count", 0) or 0) + max(0, seen_count),
        "first_seen": str(existing.get("first_seen") or now_iso()),
        "updated_at": now_iso(),
    }
    if confidence is not None:
        entry["confidence"] = round(float(confidence), 2)
    elif existing.get("confidence") is not None and source != SOURCE_BRIAN:
        entry["confidence"] = existing["confidence"]
    senders[key] = entry
    return True


def note_message(ledger: dict, address: str, subject: str = "") -> None:
    """Count a message against an existing sender entry without changing its policy."""
    key = sender_key(address)
    entry = (ledger.get("senders") or {}).get(key)
    if not isinstance(entry, dict):
        return
    entry["message_count"] = int(entry.get("message_count", 0) or 0) + 1
    entry["last_seen"] = now_iso()
    trimmed = str(subject or "").strip()[:160]
    if trimmed:
        subjects = [str(item) for item in (entry.get("sample_subjects") or [])]
        if trimmed not in subjects:
            subjects.append(trimmed)
        entry["sample_subjects"] = subjects[-MAX_SAMPLE_SUBJECTS:]


def counts(ledger: dict) -> dict[str, int]:
    tally = {POLICY_LEARN: 0, POLICY_INFO: 0, POLICY_IGNORE: 0}
    for entry in (ledger.get("senders") or {}).values():
        policy = normalize_policy((entry or {}).get("policy", ""))
        if policy:
            tally[policy] += 1
    return tally
