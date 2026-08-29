#!/usr/bin/env python3
"""Ingest Brian's shared Google Calendar into durable knowledge.

Brian shared his calendar with AgentCore as a reader, and AgentCore's OAuth token
already carries ``calendar.readonly``. This script turns that access into two things:

1. ``agentcore/knowledge/calendar/upcoming.md`` - a regenerated view of the near-term
   schedule, so the fast Telegram layer can answer "what do I have this week" from repo
   context instead of deferring.
2. Recurring-commitment facts appended to ``brian-learned-facts.md`` once a series has
   appeared often enough to count as a routine rather than a one-off.

Read-only. Nothing is written back to Google Calendar.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
EMAIL_DIR = SCRIPT_DIR.parent / "email"
LEARN_DIR = SCRIPT_DIR.parent / "learn"
for extra_path in (str(EMAIL_DIR), str(LEARN_DIR)):
    if extra_path not in sys.path:
        sys.path.insert(0, extra_path)

import facts as facts_page  # noqa: E402
import gmail_api  # noqa: E402
from common import compact_whitespace, get_env, load_env_file, write_json  # noqa: E402

CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3"
SCHEDULE_PATH = Path("agentcore/knowledge/calendar/upcoming.md")
STATE_PATH = Path("agentcore/knowledge/calendar/calendar-state.json")
DEFAULT_SUMMARY_PATH = ".agentcore/state/calendar-ingest-summary.json"

# A series has to show up this many times in the window before it counts as a routine.
RECURRING_THRESHOLD = 3
MAX_EVENTS_PER_CALENDAR = 250


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest shared Google Calendar events into knowledge.")
    parser.add_argument("--past-days", type=int, default=7, help="How far back to include events.")
    parser.add_argument("--future-days", type=int, default=60, help="How far forward to include events.")
    parser.add_argument("--calendar-id", action="append", default=[], help="Explicit calendar id (repeatable).")
    parser.add_argument("--include-agentcore-calendar", action="store_true", help="Also include AgentCore's own calendar.")
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_PATH, help="Summary JSON path.")
    parser.add_argument("--dry-run", action="store_true", help="Report without writing knowledge files.")
    return parser.parse_args()


def _calendar_request(token: str, path: str, query: dict[str, str] | None = None) -> dict:
    url = f"{CALENDAR_API_BASE}{path}"
    if query:
        url = f"{url}?{urllib.parse.urlencode(query)}"
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"}, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Calendar API request failed: GET {path}: {exc.code} {detail}") from exc
    return json.loads(body) if body else {}


def list_calendars(token: str) -> list[dict]:
    payload = _calendar_request(token, "/users/me/calendarList", {"maxResults": "250"})
    return [item for item in (payload.get("items") or []) if isinstance(item, dict)]


def select_calendars(calendars: list[dict], args: argparse.Namespace, agentcore_email: str) -> list[dict]:
    if args.calendar_id:
        wanted = {item.strip().lower() for item in args.calendar_id}
        return [cal for cal in calendars if str(cal.get("id", "")).lower() in wanted]

    selected = []
    for calendar in calendars:
        calendar_id = str(calendar.get("id", "")).lower()
        if calendar_id.endswith("#contacts@group.v.calendar.google.com"):
            continue
        if calendar_id.endswith("holiday@group.v.calendar.google.com"):
            continue
        is_agentcore_own = calendar_id == agentcore_email.lower()
        if is_agentcore_own and not args.include_agentcore_calendar:
            continue
        selected.append(calendar)
    return selected


def list_events(token: str, calendar_id: str, time_min: str, time_max: str) -> list[dict]:
    events: list[dict] = []
    page_token = ""
    while len(events) < MAX_EVENTS_PER_CALENDAR:
        query = {
            "timeMin": time_min,
            "timeMax": time_max,
            "singleEvents": "true",
            "orderBy": "startTime",
            "maxResults": "250",
            "showDeleted": "false",
        }
        if page_token:
            query["pageToken"] = page_token
        payload = _calendar_request(token, f"/calendars/{urllib.parse.quote(calendar_id)}/events", query)
        events.extend(item for item in (payload.get("items") or []) if isinstance(item, dict))
        page_token = str(payload.get("nextPageToken") or "")
        if not page_token:
            break
    return events[:MAX_EVENTS_PER_CALENDAR]


def event_start(event: dict) -> tuple[str, bool]:
    """Return (ISO-ish start string, all_day)."""
    start = event.get("start") or {}
    if start.get("date"):
        return str(start["date"]), True
    return str(start.get("dateTime") or ""), False


def format_when(event: dict) -> tuple[str, str, str]:
    """Return (date key YYYY-MM-DD, 24h sort key, human time label)."""
    raw, all_day = event_start(event)
    if not raw:
        return "", "", ""
    if all_day:
        return raw, "00:00", "all day"
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return raw[:10], "00:00", ""
    local = parsed.astimezone()
    return local.strftime("%Y-%m-%d"), local.strftime("%H:%M"), local.strftime("%-I:%M %p").lower()


def series_key(event: dict) -> str:
    summary = compact_whitespace(str(event.get("summary") or "")).lower()
    return re.sub(r"[^a-z0-9 ]+", "", summary).strip()


def load_state() -> dict:
    if STATE_PATH.exists():
        try:
            data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("known_routines", [])
                return data
        except json.JSONDecodeError:
            pass
    return {"version": 1, "known_routines": []}


def save_state(state: dict) -> None:
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def render_schedule(events: list[dict], past_days: int, future_days: int) -> str:
    today = datetime.now().astimezone().strftime("%Y-%m-%d")
    lines = [
        "# Upcoming Schedule",
        "",
        f"Regenerated by the nightly calendar ingest on {today}. Covers {past_days} days back "
        f"through {future_days} days ahead of that run, from calendars Brian shares with AgentCore.",
        "",
        "This page is rebuilt each run. Do not hand-edit it; durable facts belong in the people and",
        "project pages instead.",
        "",
    ]

    by_date: dict[str, list[tuple[str, str, str, str]]] = {}
    for event in events:
        date_key, sort_key, time_label = format_when(event)
        summary = compact_whitespace(str(event.get("summary") or "(no title)"))
        location = compact_whitespace(str(event.get("location") or ""))
        if not date_key:
            continue
        by_date.setdefault(date_key, []).append((sort_key, time_label, summary, location))

    if not by_date:
        lines.extend(["_No events in the current window._", ""])
        return "\n".join(lines)

    for date_key in sorted(by_date):
        try:
            heading = datetime.strptime(date_key, "%Y-%m-%d").strftime("%A, %B %-d, %Y")
        except ValueError:
            heading = date_key
        marker = " (today)" if date_key == today else ""
        lines.extend([f"## {heading}{marker}", ""])
        for _, time_label, summary, location in sorted(by_date[date_key]):
            bullet = f"- {time_label} — {summary}" if time_label else f"- {summary}"
            if location:
                bullet += f" @ {location}"
            lines.append(bullet)
        lines.append("")
    return "\n".join(lines)


def detect_routines(events: list[dict]) -> list[str]:
    """Summaries that recur often enough in the window to count as a standing commitment."""
    counter: Counter[str] = Counter()
    labels: dict[str, str] = {}
    for event in events:
        key = series_key(event)
        if not key or len(key) < 3:
            continue
        counter[key] += 1
        labels.setdefault(key, compact_whitespace(str(event.get("summary") or "")))
    return [labels[key] for key, count in counter.items() if count >= RECURRING_THRESHOLD]


def append_routine_facts(routines: list[str], state: dict) -> list[str]:
    known = {str(item).lower() for item in state.get("known_routines", [])}
    fresh = [name for name in routines if name.lower() not in known]
    if not fresh:
        return []
    facts_page.append(
        [
            {
                "text": f'Brian has a recurring calendar commitment named "{name}".',
                "category": "commitments",
            }
            for name in fresh
        ]
    )
    state.setdefault("known_routines", []).extend(fresh)
    return fresh


def main() -> int:
    args = parse_args()
    env_map = load_env_file()
    agentcore_email = get_env("AGENTCORE_EMAIL", default="scottishramp@gmail.com", env_map=env_map)

    token = gmail_api.access_token(env_map=env_map, account=gmail_api.ACCOUNT_AGENTCORE)
    calendars = select_calendars(list_calendars(token), args, agentcore_email)

    now = datetime.now(timezone.utc)
    time_min = (now - timedelta(days=max(0, args.past_days))).isoformat()
    time_max = (now + timedelta(days=max(1, args.future_days))).isoformat()

    all_events: list[dict] = []
    per_calendar: list[dict] = []
    errors: list[str] = []
    for calendar in calendars:
        calendar_id = str(calendar.get("id", ""))
        try:
            events = list_events(token, calendar_id, time_min, time_max)
        except RuntimeError as exc:
            errors.append(str(exc)[:300])
            continue
        all_events.extend(events)
        per_calendar.append(
            {
                "id": calendar_id,
                "summary": str(calendar.get("summary", "")),
                "access_role": str(calendar.get("accessRole", "")),
                "event_count": len(events),
            }
        )

    routines = detect_routines(all_events)
    state = load_state()
    new_routines: list[str] = []
    if not args.dry_run:
        SCHEDULE_PATH.parent.mkdir(parents=True, exist_ok=True)
        SCHEDULE_PATH.write_text(render_schedule(all_events, args.past_days, args.future_days), encoding="utf-8")
        new_routines = append_routine_facts(routines, state)
        state["last_event_count"] = len(all_events)
        save_state(state)

    summary = {
        "status": "ok" if not errors else "partial",
        "calendars": per_calendar,
        "calendar_count": len(per_calendar),
        "event_count": len(all_events),
        "recurring_detected": len(routines),
        "new_routine_facts": new_routines,
        "window": {"time_min": time_min, "time_max": time_max},
        "dry_run": args.dry_run,
        "errors": errors,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(Path(args.summary_output), summary)
    print(json.dumps(summary, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
