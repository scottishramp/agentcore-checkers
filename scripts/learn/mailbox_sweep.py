#!/usr/bin/env python3
"""Nightly sweep of Brian's whole personal mailbox to learn durable facts about him.

This is broader than the school digest, which only queries school senders. The sweep
looks at everything that arrived since the last run and decides what to do with it
one *sender* at a time:

1. Senders with a recorded policy are handled immediately, no model call.
2. Unknown senders are classified by the LLM into learn / info / ignore.
3. Low-confidence senders become a question for Brian instead of a guess.
4. Messages from ``learn`` senders get a fact-extraction pass into knowledge.

Read-only against Gmail: nothing is labelled, archived, or trashed. Message bodies
are read for extraction but never written to the repo; only distilled facts,
senders, and subjects are persisted.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
EMAIL_DIR = SCRIPT_DIR.parent / "email"
for extra_path in (str(EMAIL_DIR), str(SCRIPT_DIR)):
    if extra_path not in sys.path:
        sys.path.insert(0, extra_path)

import email_evaluator  # noqa: E402
import facts as facts_page  # noqa: E402
import gmail_api  # noqa: E402
import questions  # noqa: E402
import sender_policy  # noqa: E402
from common import (  # noqa: E402
    compact_whitespace,
    load_env_file,
    normalize_email_address,
    normalize_subject,
    write_json,
)

ACCOUNT = gmail_api.ACCOUNT_BRIAN
STATE_PATH = Path("agentcore/knowledge/email/mailbox-sweep-state.json")
DEFAULT_SUMMARY_PATH = ".agentcore/state/mailbox-sweep-summary.json"

SENDER_BATCH_SIZE = 15
FACT_BATCH_SIZE = 8
FACT_BODY_CHARS = 1200
RECENT_ID_MEMORY = 500
AUTO_POLICY_CONFIDENCE = 0.8

FACT_CATEGORIES = facts_page.CATEGORIES

# Senders whose mail is pure machine noise; never worth a model call or a question.
NEVER_ASK_RE = re.compile(
    r"(mailer-daemon|postmaster@|no-?reply@accounts\.google\.com|"
    r"calendar-notification@google\.com|forwarding-noreply@google\.com)",
    re.I,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sweep Brian's mailbox and learn durable facts.")
    parser.add_argument("--hours", type=int, default=26, help="Lookback window when no watermark exists.")
    parser.add_argument("--backfill-days", type=int, default=0, help="One-time historical backfill window in days.")
    parser.add_argument("--max-messages", type=int, default=250, help="Max messages to inspect per run.")
    parser.add_argument("--ask-limit", type=int, default=5, help="Max new sender questions to enqueue per run.")
    parser.add_argument("--extract-limit", type=int, default=30, help="Max messages to run fact extraction on.")
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_PATH, help="Summary JSON path.")
    parser.add_argument("--dry-run", action="store_true", help="Classify and report without writing ledgers.")
    parser.add_argument("--no-llm", action="store_true", help="Apply known policies only; skip model calls.")
    return parser.parse_args()


def load_state() -> dict:
    if STATE_PATH.exists():
        try:
            data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("recent_ids", [])
                return data
        except json.JSONDecodeError:
            pass
    return {"version": 1, "last_internal_date_ms": 0, "recent_ids": []}


def save_state(state: dict) -> None:
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    state["recent_ids"] = list(state.get("recent_ids", []))[-RECENT_ID_MEMORY:]
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_query(state: dict, args: argparse.Namespace) -> str:
    if args.backfill_days > 0:
        start = datetime.now(timezone.utc) - timedelta(days=args.backfill_days)
    else:
        watermark_ms = int(state.get("last_internal_date_ms", 0) or 0)
        if watermark_ms:
            start = datetime.fromtimestamp(watermark_ms / 1000, tz=timezone.utc)
        else:
            start = datetime.now(timezone.utc) - timedelta(hours=max(1, args.hours))
    return f"after:{int(start.timestamp())} -in:chats"


def collect_message_ids(query: str, limit: int, env_map: dict[str, str]) -> list[str]:
    ids: list[str] = []
    page_token = ""
    while len(ids) < limit:
        payload = gmail_api.list_messages(
            query=query,
            max_results=min(100, limit - len(ids)),
            env_map=env_map,
            account=ACCOUNT,
            page_token=page_token,
        )
        for item in payload.get("messages") or []:
            message_id = str(item.get("id") or "")
            if message_id:
                ids.append(message_id)
        page_token = str(payload.get("nextPageToken") or "")
        if not page_token:
            break
    return ids[:limit]


def fetch_metadata(message_id: str, env_map: dict[str, str]) -> dict:
    message = gmail_api.get_message(
        message_id,
        env_map=env_map,
        account=ACCOUNT,
        fmt="metadata",
        metadata_headers=["From", "To", "Subject", "Date", "List-Unsubscribe"],
    )
    headers = gmail_api.header_map(message)
    raw_from = headers.get("from", "")
    return {
        "id": message_id,
        "thread_id": str(message.get("threadId") or ""),
        "internal_date_ms": int(str(message.get("internalDate") or "0") or 0),
        "from_raw": raw_from,
        "from": normalize_email_address(raw_from),
        "display_name": compact_whitespace(re.sub(r"<[^>]*>", "", raw_from)).strip('" '),
        "subject": normalize_subject(headers.get("subject", "")),
        "date": headers.get("date", ""),
        "snippet": compact_whitespace(str(message.get("snippet") or "")),
        "bulk": bool(headers.get("list-unsubscribe")),
    }


def fetch_body_excerpt(message_id: str, env_map: dict[str, str]) -> str:
    message = gmail_api.get_message(message_id, env_map=env_map, account=ACCOUNT, fmt="full")
    text = gmail_api.extract_text_body(message.get("payload"))
    if "<" in text and ">" in text:
        text = re.sub(r"<[^>]+>", " ", text)
    return compact_whitespace(text)[:FACT_BODY_CHARS]


def build_sender_prompt(senders: list[dict], today: str) -> str:
    payload = json.dumps(senders, ensure_ascii=False, indent=1)
    return f"""You are AgentCore, the private administrative assistant for Brian Herbert. Today is {today}.

You are triaging Brian's personal Gmail one SENDER at a time so AgentCore knows how to
treat that sender's mail from now on. For each sender below decide a lasting policy.

Policies:
- "learn": mail from this sender regularly contains durable facts worth remembering about Brian
  or his family: doctors, schools, financial accounts, insurance, bills, travel bookings,
  government/legal mail, real people who know him, accounts and services he actually uses.
- "info": legitimate but transient. Worth knowing the sender exists, but individual messages
  carry no lasting facts: routine receipts, shipping notices, security alerts, app notifications.
- "ignore": marketing, promotions, cold outreach, newsletters he does not act on, spam.

For each sender return one JSON object:
- "sender": copy the input sender address exactly.
- "policy": "learn", "info", or "ignore".
- "confidence": 0.0-1.0. Be honest. Use below 0.8 whenever a reasonable person would need to
  ask Brian, for example an unfamiliar personal name, a service you cannot tell he uses, a
  small business that might be his employer, doctor, or contractor.
- "rationale": one short sentence explaining the call, written for Brian to read.
- "description": a few words naming what this sender is, e.g. "auto insurance carrier".

Rules:
- A real human writing to Brian personally is "learn" with high confidence.
- A well-known retailer, airline, or bank sending marketing is "ignore"; the same bank sending
  statements or account notices is "learn".
- Do not guess when the sender is an unrecognizable personal or small-business address. Lower
  the confidence and let Brian decide.
- Answer with ONLY the JSON array, no prose, no code fences.

Senders:
{payload}
"""


def build_fact_prompt(items: list[dict], today: str) -> str:
    payload = json.dumps(items, ensure_ascii=False, indent=1)
    categories = ", ".join(f'"{name}"' for name in FACT_CATEGORIES)
    return f"""You are AgentCore, the private administrative assistant for Brian Herbert. Today is {today}.

Below are emails from senders already known to carry durable information about Brian. Extract
only facts worth remembering months from now.

For each email return one JSON object:
- "id": copy the input id exactly.
- "facts": a list of durable facts. Each fact is {{"text": one complete sentence, "category": one of {categories}, "confidence": 0.0-1.0}}.

What counts as durable: providers and account relationships, policy or member numbers' existence
(do NOT copy full account numbers, passwords, or one-time codes), recurring bills and their rough
amounts, subscriptions, appointments and commitments with dates, travel bookings, home and vehicle
service history, employer and work context, named people and their relationship to Brian.

What does not count: marketing copy, one-time verification codes, delivery status updates, anything
already obvious from the sender's identity alone, and speculation.

Rules:
- Write each fact as a standalone sentence that makes sense with no other context, naming Brian or
  the family member it concerns.
- Never include passwords, full account or card numbers, or authentication codes.
- Return an empty "facts" list when the email holds nothing durable. That is a normal outcome.
- Answer with ONLY the JSON array, no prose, no code fences.

Emails:
{payload}
"""


def classify_senders(candidates: list[dict], today: str) -> tuple[dict[str, dict], str]:
    verdicts: dict[str, dict] = {}
    backend = ""
    for offset in range(0, len(candidates), SENDER_BATCH_SIZE):
        batch = candidates[offset : offset + SENDER_BATCH_SIZE]
        items = [
            {
                "sender": entry["from"],
                "display_name": entry.get("display_name", "")[:120],
                "message_count": entry.get("message_count", 1),
                "bulk_mail": entry.get("bulk", False),
                "recent_subjects": entry.get("subjects", [])[:3],
            }
            for entry in batch
        ]
        raw_out, backend = email_evaluator.call_model(build_sender_prompt(items, today))
        for raw in email_evaluator.parse_json_array(raw_out):
            address = sender_policy.sender_key(raw.get("sender", ""))
            policy = sender_policy.normalize_policy(raw.get("policy", ""))
            if not address or not policy:
                continue
            try:
                confidence = float(raw.get("confidence", 0))
            except (TypeError, ValueError):
                confidence = 0.0
            verdicts[address] = {
                "policy": policy,
                "confidence": max(0.0, min(1.0, confidence)),
                "rationale": compact_whitespace(str(raw.get("rationale") or ""))[:300],
                "description": compact_whitespace(str(raw.get("description") or ""))[:120],
            }
    return verdicts, backend


def extract_facts(rows: list[dict], today: str) -> tuple[list[dict], str]:
    facts: list[dict] = []
    backend = ""
    for offset in range(0, len(rows), FACT_BATCH_SIZE):
        batch = rows[offset : offset + FACT_BATCH_SIZE]
        items = [
            {
                "id": row["id"],
                "from": row.get("from_raw", "")[:120],
                "subject": row.get("subject", "")[:200],
                "date": row.get("date", "")[:60],
                "body": row.get("body", ""),
            }
            for row in batch
        ]
        raw_out, backend = email_evaluator.call_model(build_fact_prompt(items, today))
        for raw in email_evaluator.parse_json_array(raw_out):
            source_id = str(raw.get("id") or "")
            for fact in raw.get("facts") or []:
                if not isinstance(fact, dict):
                    continue
                text = compact_whitespace(str(fact.get("text") or ""))
                if not text:
                    continue
                category = facts_page.normalize_category(fact.get("category", ""))
                try:
                    confidence = float(fact.get("confidence", 0.5))
                except (TypeError, ValueError):
                    confidence = 0.5
                facts.append(
                    {
                        "text": text[:400],
                        "category": category,
                        "confidence": max(0.0, min(1.0, confidence)),
                        "source_id": source_id,
                    }
                )
    return facts, backend


def question_prompt(entry: dict, verdict: dict) -> str:
    name = entry.get("display_name") or entry["from"]
    description = verdict.get("description") or "unclear what this is"
    count = entry.get("message_count", 1)
    plural = "message" if count == 1 else "messages"
    subject = (entry.get("subjects") or [""])[0]
    prompt = f"{name} <{entry['from']}> - {count} {plural}, {description}"
    if subject:
        prompt += f'\n   Latest: "{subject[:90]}"'
    return prompt


def main() -> int:
    args = parse_args()
    env_map = load_env_file()
    state = load_state()
    policy_ledger = sender_policy.load()
    question_ledger = questions.load()
    today = datetime.now(timezone.utc).astimezone().strftime("%A %Y-%m-%d")

    query = build_query(state, args)
    message_ids = collect_message_ids(query, args.max_messages, env_map)
    already_seen = set(state.get("recent_ids", []))
    watermark = int(state.get("last_internal_date_ms", 0) or 0)

    rows: list[dict] = []
    for message_id in message_ids:
        if message_id in already_seen:
            continue
        row = fetch_metadata(message_id, env_map)
        if row["internal_date_ms"] and row["internal_date_ms"] <= watermark and args.backfill_days == 0:
            continue
        rows.append(row)

    # Group by sender so each sender is decided once, however many messages arrived.
    by_sender: dict[str, dict] = {}
    for row in rows:
        address = row["from"]
        if not address:
            continue
        entry = by_sender.setdefault(
            address,
            {
                "from": address,
                "display_name": row.get("display_name", ""),
                "bulk": row.get("bulk", False),
                "message_count": 0,
                "subjects": [],
                "message_ids": [],
            },
        )
        entry["message_count"] += 1
        entry["message_ids"].append(row["id"])
        if row["subject"] and row["subject"] not in entry["subjects"]:
            entry["subjects"].append(row["subject"])

    known: dict[str, str] = {}
    unknown: list[dict] = []
    for address, entry in by_sender.items():
        existing = sender_policy.lookup(policy_ledger, address)
        if existing:
            known[address] = sender_policy.normalize_policy(existing.get("policy", ""))
            sender_policy.note_message(policy_ledger, address, (entry["subjects"] or [""])[0])
        elif NEVER_ASK_RE.search(address):
            sender_policy.record(
                policy_ledger,
                address,
                sender_policy.POLICY_IGNORE,
                sender_policy.SOURCE_SEED,
                display_name=entry.get("display_name", ""),
                rationale="Automated system notification address.",
                seen_count=entry.get("message_count", 0),
            )
            known[address] = sender_policy.POLICY_IGNORE
        else:
            unknown.append(entry)

    already_known = len(known)
    verdicts: dict[str, dict] = {}
    backend = ""
    errors: list[str] = []
    if unknown and not args.no_llm:
        try:
            verdicts, backend = classify_senders(unknown, today)
        except Exception as exc:  # noqa: BLE001 - a model failure must not lose the sweep
            errors.append(f"sender classification failed: {exc}")

    auto_recorded = 0
    asked_candidates: list[tuple[dict, dict]] = []
    for entry in unknown:
        verdict = verdicts.get(entry["from"])
        if not verdict:
            continue
        if verdict["confidence"] >= AUTO_POLICY_CONFIDENCE:
            recorded = sender_policy.record(
                policy_ledger,
                entry["from"],
                verdict["policy"],
                sender_policy.SOURCE_LLM,
                display_name=entry.get("display_name", ""),
                rationale=verdict["rationale"],
                subject=(entry["subjects"] or [""])[0],
                confidence=verdict["confidence"],
                seen_count=entry.get("message_count", 0),
            )
            if recorded:
                auto_recorded += 1
                known[entry["from"]] = verdict["policy"]
                pending = questions.find_by_subject(
                    question_ledger, questions.KIND_SENDER_POLICY, entry["from"]
                )
                if pending.get("status") in {questions.STATUS_OPEN, questions.STATUS_ASKED}:
                    questions.mark_answered(
                        pending,
                        verdict["policy"],
                        "llm-auto",
                        "Later mail from this sender was classified with high confidence.",
                    )
        else:
            asked_candidates.append((entry, verdict))

    # Ask about the senders Brian hears from most first; those matter most to get right.
    asked_candidates.sort(key=lambda pair: pair[0].get("message_count", 0), reverse=True)
    enqueued = 0
    for entry, verdict in asked_candidates:
        if enqueued >= max(0, args.ask_limit):
            break
        if questions.is_pending_or_answered(question_ledger, questions.KIND_SENDER_POLICY, entry["from"]):
            continue
        created = questions.enqueue(
            question_ledger,
            questions.KIND_SENDER_POLICY,
            entry["from"],
            question_prompt(entry, verdict),
            ["learn", "info", "ignore"],
            context={
                "display_name": entry.get("display_name", ""),
                "message_count": entry.get("message_count", 0),
                "subjects": entry.get("subjects", [])[:3],
                "model_guess": verdict["policy"],
                "model_confidence": verdict["confidence"],
                "model_rationale": verdict["rationale"],
            },
        )
        if created:
            enqueued += 1

    learn_rows: list[dict] = []
    if not args.no_llm:
        for row in rows:
            if len(learn_rows) >= max(0, args.extract_limit):
                break
            if known.get(row["from"]) != sender_policy.POLICY_LEARN:
                continue
            try:
                row["body"] = fetch_body_excerpt(row["id"], env_map)
            except gmail_api.GmailApiError as exc:
                errors.append(f"body fetch failed for {row['id']}: {exc}")
                continue
            learn_rows.append(row)

    facts: list[dict] = []
    if learn_rows:
        try:
            facts, fact_backend = extract_facts(learn_rows, today)
            backend = backend or fact_backend
        except Exception as exc:  # noqa: BLE001 - keep policy learning even if extraction fails
            errors.append(f"fact extraction failed: {exc}")

    facts_added = 0
    if not args.dry_run:
        facts_added = len(facts_page.append(facts))
        for row in rows:
            state.setdefault("recent_ids", []).append(row["id"])
            watermark = max(watermark, row["internal_date_ms"])
        state["last_internal_date_ms"] = watermark
        questions.expire_stale(question_ledger)
        sender_policy.save(policy_ledger)
        questions.save(question_ledger)
        save_state(state)

    summary = {
        "status": "ok" if not errors else "partial",
        "query": query,
        "messages_seen": len(rows),
        "senders_seen": len(by_sender),
        "senders_already_known": already_known,
        "senders_new": len(unknown),
        "policies_auto_recorded": auto_recorded,
        "questions_enqueued": enqueued,
        "messages_extracted": len(learn_rows),
        "facts_found": len(facts),
        "facts_added": facts_added,
        "policy_totals": sender_policy.counts(policy_ledger),
        "backend": backend,
        "dry_run": args.dry_run,
        "errors": errors,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(Path(args.summary_output), summary)
    print(json.dumps(summary, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
