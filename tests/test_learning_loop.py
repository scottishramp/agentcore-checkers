#!/usr/bin/env python3
"""Tests for the mailbox learning loop: answer parsing, policy precedence, fact writing.

Run with `npm run test:learn` or `python3 tests/test_learning_loop.py`. No network,
no Gmail, no model calls: everything here is pure logic over temp files.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
for extra_path in (REPO_ROOT / "scripts/learn", REPO_ROOT / "scripts/email"):
    if str(extra_path) not in sys.path:
        sys.path.insert(0, str(extra_path))

import facts  # noqa: E402
import questions  # noqa: E402
import resolve_answers  # noqa: E402
import sender_policy  # noqa: E402

FAILURES: list[str] = []


def check(label: str, actual, expected) -> None:
    if actual == expected:
        print(f"  pass: {label}")
    else:
        FAILURES.append(f"{label}\n    expected: {expected!r}\n    actual:   {actual!r}")
        print(f"  FAIL: {label}")


def test_answer_parsing() -> None:
    print("answer parsing")
    parse = resolve_answers.parse_answer_text

    check("comma separated", parse("1 learn, 2 ignore", 3), {1: "learn", 2: "ignore"})
    check("no separators", parse("1 learn 2 info 3 spam", 3), {1: "learn", 2: "info", 3: "ignore"})
    check("single letters", parse("1l 2i 3s", 3), {1: "learn", 2: "info", 3: "ignore"})
    check("punctuated", parse("1) learn. 2) ignore.", 2), {1: "learn", 2: "ignore"})
    check("reversed order", parse("learn 1, spam 2", 2), {1: "learn", 2: "ignore"})
    check("all shorthand", parse("all ignore", 3), {1: "ignore", 2: "ignore", 3: "ignore"})
    check("synonyms", parse("1 keep, 2 junk, 3 fyi", 3), {1: "learn", 2: "ignore", 3: "info"})
    check("mixed case", parse("1 LEARN, 2 Ignore", 2), {1: "learn", 2: "ignore"})
    check("partial answer", parse("2 learn", 3), {2: "learn"})
    check("bare word single question", parse("ignore", 1), {1: "ignore"})
    check("bare word multi question is ambiguous", parse("ignore", 3), {})

    # Numbers outside the batch must never be applied to the wrong sender.
    check("out of range dropped", parse("1 learn, 9 ignore", 2), {1: "learn"})
    check("prose reply defers", parse("the barber one is mine, drop the rest", 3), {})
    check("empty reply", parse("", 3), {})


def test_policy_precedence() -> None:
    print("sender policy precedence")
    ledger = sender_policy.load(Path("/nonexistent/policy.json"))

    sender_policy.record(ledger, "A@Example.com", "ignore", sender_policy.SOURCE_LLM, confidence=0.9)
    check("address lowercased", "a@example.com" in ledger["senders"], True)

    sender_policy.record(ledger, "a@example.com", "learn", sender_policy.SOURCE_BRIAN)
    check("brian overrides llm", ledger["senders"]["a@example.com"]["policy"], "learn")

    sender_policy.record(ledger, "a@example.com", "ignore", sender_policy.SOURCE_LLM, confidence=0.99)
    check("llm cannot override brian", ledger["senders"]["a@example.com"]["policy"], "learn")
    check("source stays brian", ledger["senders"]["a@example.com"]["source"], sender_policy.SOURCE_BRIAN)

    sender_policy.record(ledger, "b@example.com", "bogus", sender_policy.SOURCE_LLM)
    check("invalid policy rejected", "b@example.com" in ledger["senders"], False)

    sender_policy.record(ledger, "c@example.com", "info", sender_policy.SOURCE_LLM, seen_count=4)
    sender_policy.note_message(ledger, "c@example.com", "Another subject")
    check("message count accumulates", ledger["senders"]["c@example.com"]["message_count"], 5)

    ledger.setdefault("domains", {})["spam-farm.test"] = {"policy": "ignore", "source": "brian"}
    check("domain rule applies", sender_policy.lookup(ledger, "any@spam-farm.test")["policy"], "ignore")
    check("unknown sender empty", sender_policy.lookup(ledger, "who@nowhere.test"), {})
    check("counts", sender_policy.counts(ledger), {"learn": 1, "info": 1, "ignore": 0})


def test_question_lifecycle() -> None:
    print("question lifecycle")
    ledger = questions.load(Path("/nonexistent/questions.json"))

    created = questions.enqueue(ledger, questions.KIND_SENDER_POLICY, "x@example.com", "X?", ["learn"])
    check("question created", bool(created), True)

    duplicate = questions.enqueue(ledger, questions.KIND_SENDER_POLICY, "x@example.com", "X?", ["learn"])
    check("duplicate suppressed", duplicate, "")
    check("one open question", len(questions.open_questions(ledger)), 1)

    entry = questions.open_questions(ledger)[0]
    questions.mark_asked(entry, "ask-1", 1)
    check("no longer open", len(questions.open_questions(ledger)), 0)
    check("now asked", len(questions.asked_questions(ledger)), 1)

    questions.mark_answered(entry, "learn", "telegram", "1 learn")
    check("answered recorded", entry["answer"], "learn")
    check("answered clears asked", len(questions.asked_questions(ledger)), 0)

    # An answered subject should not be re-asked on the next sweep.
    check(
        "answered blocks re-enqueue",
        questions.enqueue(ledger, questions.KIND_SENDER_POLICY, "x@example.com", "X?", ["learn"]),
        "",
    )


def test_fact_page() -> None:
    print("fact page")
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "brian-learned-facts.md"

        added = facts.append([{"text": "Brian banks with Capital One.", "category": "finance"}], path)
        check("first fact added", added, ["Brian banks with Capital One."])

        again = facts.append([{"text": "Brian banks with Capital One.", "category": "finance"}], path)
        check("exact duplicate skipped", again, [])

        superset = facts.append(
            [{"text": "Brian banks with Capital One and has a VentureOne card.", "category": "finance"}],
            path,
        )
        check("restated fact skipped", superset, [])

        other = facts.append([{"text": "Brian sees Dr. Corbin in Edmond.", "category": "health"}], path)
        check("distinct fact added", other, ["Brian sees Dr. Corbin in Edmond."])

        unknown = facts.append([{"text": "Brian likes trains.", "category": "not-a-category"}], path)
        check("unknown category accepted", unknown, ["Brian likes trains."])

        text = path.read_text(encoding="utf-8")
        check("filed under Other", "## Other\n\n- " in text, True)
        check("blank line after heading", "## Finance\n\n- " in text, True)
        check("no double blank lines", "\n\n\n" in text, False)
        check("health fact present", "Dr. Corbin" in text, True)


def main() -> int:
    for suite in (test_answer_parsing, test_policy_precedence, test_question_lifecycle, test_fact_page):
        suite()
    print()
    if FAILURES:
        print(f"{len(FAILURES)} failure(s):")
        for failure in FAILURES:
            print(f"  - {failure}")
        return 1
    print("All learning-loop tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
