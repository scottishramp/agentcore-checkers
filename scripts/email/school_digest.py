#!/usr/bin/env python3
"""Build a compact daily digest of kids' school email."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from pathlib import Path
from zoneinfo import ZoneInfo

import email_evaluator as evaluator
import gmail_api
from common import load_env_file

ROSTER_PATH = Path("agentcore/knowledge/school/2026-27-roster.json")
DOC_REGISTRY_PATH = Path("agentcore/knowledge/school/digest-doc.json")
CHILDREN_PAGE_PATH = Path("agentcore/knowledge/people/herbert-children.md")
FAMILY_FACTS_PATH = Path("agentcore/knowledge/people/family-facts.md")
OUTPUT_PATH = Path(".agentcore/state/school-digest/latest.md")
LABEL_NAME = "26-27 School"
DOC_TITLE = "2026-27 School Digest"
DOC_FOLDER = "School"
SHARE_EMAIL = "briandherbert@gmail.com"
CHILD_ORDER = ["Daniel", "Nathan", "Ezra", "Silver", "Levi"]
TZ = ZoneInfo("America/Chicago")
ACCOUNT = gmail_api.ACCOUNT_BRIAN

ACTION_RE = re.compile(
    r"\b(due|deadline|sign up|signup|permission|waiver|fee|supply|supplies|form|conference|"
    r"detention|behavior|missing homework|bring|tomorrow|today|this week|schedule change|"
    r"cancelled|canceled|no school|early release|assembly|picture day|registration|rank one|"
    r"physical|walkabout)\b",
    re.I,
)
BLAST_FROM_RE = re.compile(
    r"(donotreply@edmondschools\.net|edmond public schools|mustang round-up|husky pride|falcon news)",
    re.I,
)
LOW_SUBJECT_RE = re.compile(
    r"(pto|candy gram|staff appreciation|baked potato|newsletter|news flash|round-up|"
    r"husky pride|utility verification|before & after care|bird.?s nest)",
    re.I,
)
SPORT_RE = re.compile(
    r"\b(basketball|track|football|soccer|volleyball|baseball|softball|cross country|"
    r"cheer|wrestling|golf|tennis|swim|husky basketball)\b",
    re.I,
)
URL_RE = re.compile(r"https?://[^\s<>\"']+", re.I)
SKIP_URL_RE = re.compile(
    r"(unsubscribe|safelink|sendgrid\.net|googleusercontent|public\.govdelivery|"
    r"facebook\.com/tr|doubleclick|list-manage|cmsv2-assets|/logo/|"
    r"\.(?:png|jpe?g|gif|svg|webp)(?:\?|$))",
    re.I,
)
PREFERRED_URL_RE = re.compile(
    r"(smore\.com|rankone|docs\.google|forms\.gle|signupgenius|seesaw|edmondschools\.net)",
    re.I,
)
GREETING_RE = re.compile(
    r"\b(hello|hi |hey |greetings|welcome to|hope you had|we are so excited|"
    r"i(?:['’]m| am) excited|thrilled|can['’]?t wait|so glad|looking forward to "
    r"(?:a |the )?(?:great |wonderful |new )?year|dear (?:families|parents|students|class))\b",
    re.I,
)
NEED_RE = re.compile(
    r"\b(bring|wear|dress|pack|turn in|turned in|complete|register|registration|"
    r"sign up|signup|permission|waiver|pay|fee|\$|supply list|supplies|form|"
    r"physical|rank one|picture day|due|deadline|must|need to|required|"
    r"please (?:make sure|send|return|complete|sign|bring|wear|review)|"
    r"carline|conference|no school|early release|virtual student)\b",
    re.I,
)
NEGATED_NEED_RE = re.compile(
    r"\b(?:do not|don't|does not|doesn't|no need to|not need to)\s+(?:bring|worry|pack|send|wear)",
    re.I,
)
FACT_RE = re.compile(
    r"\b(meet(?:s|ing)? (?:in|at|on)|report to|arrive|dismiss|pick(?: )?up|drop off|"
    r"\d{1,2}:\d{2}\s*(?:a\.?m\.?|p\.?m\.?)?|[1-7](?:st|nd|rd|th)? hour|gym|"
    r"auditorium|room \d+|english classes|off season|siberian|"
    r"wednesday|thursday|friday|monday|tuesday|saturday|sunday|"
    r"aug(?:ust)?|sept(?:ember)?|october|november|december|"
    r"schedule|homeroom|advisory)\b",
    re.I,
)
TEACHER_INTRO_RE = re.compile(
    r"(?:i am|i'm)\s+(?:so\s+)?(?:excited to (?:be|let you know that i am)\s+)?(?:your (?:child|student)['’]s\s+)?(?:the\s+)?(.{2,60}?)teacher",
    re.I,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize recent school mail for Brian.")
    parser.add_argument("--hours", type=int, default=24, help="Lookback window in hours.")
    parser.add_argument("--apply-label", action="store_true", help="Apply the 26-27 School label to matching mail.")
    parser.add_argument("--update-doc", action="store_true", help="Create or replace the Google Doc digest.")
    parser.add_argument("--send-telegram", action="store_true", help="Send Important items plus the Doc link on Telegram.")
    parser.add_argument("--dry-run", action="store_true", help="Print without labeling or sending.")
    parser.add_argument("--roster", default=str(ROSTER_PATH), help="Roster JSON path.")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM evaluation; use the keyword classifier only.")
    parser.add_argument("--reeval", action="store_true", help="Re-evaluate emails already in the eval ledger.")
    return parser.parse_args()


def load_roster(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def after_unix(hours: int) -> int:
    return int((datetime.now(timezone.utc) - timedelta(hours=max(1, hours))).timestamp())


def collect_ids(env_map: dict[str, str], hours: int) -> list[str]:
    query = (
        f"after:{after_unix(hours)} "
        "(edmondschools.net OR from:remind.com OR from:seesaw.me OR "
        'label:"26-27 School" OR "Frontier Elementary" OR "Cheyenne Middle" OR "Edmond North" OR '
        '"husky basketball" OR "rank one" OR rankone OR from:corbin.byford OR from:kelly.beck)'
    )
    ids: list[str] = []
    page = ""
    while True:
        payload = gmail_api.list_messages(
            query=query,
            max_results=100,
            env_map=env_map,
            account=ACCOUNT,
            page_token=page,
        )
        ids.extend(str(item.get("id", "")) for item in payload.get("messages") or [] if item.get("id"))
        page = str(payload.get("nextPageToken") or "")
        if not page:
            break
    return list(dict.fromkeys(ids))


def parse_date(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def children_for(row: dict, roster: dict) -> list[str]:
    blob = f"{row['from']} {row['subject']} {row.get('snippet','')} {row.get('body_text','')}".lower()
    if re.search(r"\b(8th graders?|8th grade|eighth grade)\b", blob) and "cheyenne" in blob:
        return ["Nathan"]
    if re.search(r"\b(6th graders?|6th grade|sixth grade)\b", blob) and "cheyenne" in blob:
        return ["Ezra"]
    hits = []
    for child in roster.get("children") or []:
        name = str(child.get("name", ""))
        if name and name.lower() in blob:
            hits.append(name)
            continue
        if any(needle.lower() in blob for needle in child.get("sender_needles") or []):
            hits.append(name)
    if hits:
        return list(dict.fromkeys(hits))
    if re.search(r"\b(8th graders?|8th grade|eighth grade)\b", blob) and "cheyenne" in blob:
        return ["Nathan"]
    if re.search(r"\b(6th graders?|6th grade|sixth grade)\b", blob) and "cheyenne" in blob:
        return ["Ezra"]
    if re.search(r"\b4th grade\b", blob) or "trofemuk" in blob:
        return ["Silver"]
    if "levi" in blob or re.search(r"\b1st grade\b", blob):
        return ["Levi"]
    if re.search(r"siberian gym|off season track|kelly\.beck|corbin\.byford|husky basketball", blob):
        return ["Daniel"]
    if "north high" in blob or "enhs" in blob or "english i" in blob:
        return ["Daniel"]
    if "cheyenne" in blob:
        return ["Nathan", "Ezra"]
    if "frontier" in blob or "seesaw" in blob:
        return ["Silver", "Levi"] if "levi" not in blob else ["Levi"]
    if SPORT_RE.search(blob) and ("north" in blob or "byford" in blob or "beck" in blob):
        return ["Daniel"]
    return []


def classify(row: dict) -> str:
    blob = f"{row['from']} {row['subject']} {row.get('snippet','')} {row.get('body_text','')}"
    if "seesaw" in row["from"].lower():
        return "classroom_app"
    if SPORT_RE.search(blob) and ACTION_RE.search(blob):
        return "action"
    if SPORT_RE.search(blob) and not LOW_SUBJECT_RE.search(row["subject"]):
        return "sports"
    if ACTION_RE.search(blob) and not LOW_SUBJECT_RE.search(row["subject"]):
        return "action"
    if re.search(r"picture day|psat|rank one", row["subject"], re.I):
        return "action"
    if LOW_SUBJECT_RE.search(blob) or BLAST_FROM_RE.search(blob):
        return "fyi"
    if any(name in row["from"].lower() for name in ("byford", "trofemuk", "wildman", "copenhaver", "jackson", "beck")):
        return "teacher"
    if "@edmondschools.net" in row["from"].lower() and "donotreply" not in row["from"].lower() and "messenger@" not in row["from"].lower():
        return "teacher"
    return "fyi"


def importance(kind: str) -> str:
    if kind in {"action", "teacher", "sports"}:
        return "high"
    if kind == "classroom_app":
        return "medium"
    return "low"


SKIP_SENDER_RE = re.compile(
    r"(donotreply|no-reply|noreply|messenger@|edmond public schools|govdelivery)",
    re.I,
)
ACTIVITY_RE = re.compile(r"\b(band|orchestra|choir|drama|fcccla|fccla)\b", re.I)
SPORT_NAME_MAP = {
    "husky basketball": "Basketball",
    "cross country": "Cross Country",
}


def html_to_text(html: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</(p|div|h[1-6]|li|tr)>", "\n", text)
    text = re.sub(r"<[^>]+>", " ", text)
    return unescape(re.sub(r"[ \t]+", " ", text))


JUNK_SENTENCE_RE = re.compile(
    r"(privacy policy|how we process data|you are receiving this email|"
    r"unsubscribe|powered by|get real-time updates with the seesaw app|"
    r"view all updates|once you enable push notifications|"
    r"notification preferences|download the app|help seesaw learning|"
    r"forwarded message|opted in to receive messages)",
    re.I,
)


def clean_body(text: str) -> str:
    text = unescape(str(text or "")).replace("\u200e", "").replace("\u200f", "")
    text = re.sub(
        r"-{5,}\s*Forwarded message\s*-{5,}.*?(?:To:.*?)(?:\n|$)",
        " ",
        text,
        flags=re.I | re.S,
    )
    text = re.sub(r"^[\s\-]*From:\s.*?(?:\n|$)", " ", text, flags=re.I | re.M)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"[<>]", " ", text)
    text = re.sub(r"\(\s*\)", "", text)
    text = re.sub(r"\s\(\s", " ", text)
    text = re.sub(r"\s+([.,;:])", r"\1", text)
    text = re.sub(r"\s+", " ", text).strip()
    parts = re.split(r"(?<=[.!?])\s+", text)
    kept = [part.strip() for part in parts if part.strip() and not JUNK_SENTENCE_RE.search(part)]
    return " ".join(kept)


def parse_from(value: str) -> tuple[str, str]:
    value = unescape(value or "").strip()
    match = re.match(r'^(?:"?([^"<]+?)"?\s+)?<([^>]+)>$', value)
    if match:
        return (match.group(1) or "").strip(), (match.group(2) or "").strip()
    if "@" in value and " " not in value:
        return "", value
    return value, ""


def normalize_sport(raw: str) -> str:
    key = re.sub(r"\s+", " ", (raw or "").strip().lower())
    return SPORT_NAME_MAP.get(key, key.title())


def walk_payload_text(payload: dict | None) -> tuple[str, str]:
    if not payload:
        return "", ""
    mime = str(payload.get("mimeType", ""))
    data = str((payload.get("body") or {}).get("data") or "")
    plain = ""
    html = ""
    if data:
        decoded = gmail_api.decode_body_data(data)
        if mime.startswith("text/html"):
            html = decoded
        elif mime.startswith("text/plain"):
            plain = decoded
    for part in payload.get("parts") or []:
        child_plain, child_html = walk_payload_text(part)
        plain = plain or child_plain
        html = html or child_html
    return plain, html


def extract_urls(html: str, plain: str) -> list[str]:
    found: list[str] = []
    for raw in re.findall(r"""href=["'](https?://[^"']+)["']""", html, flags=re.I) + URL_RE.findall(html + " " + plain):
        url = unescape(raw).rstrip(").,;")
        if SKIP_URL_RE.search(url):
            continue
        if url not in found:
            found.append(url)
    preferred = [url for url in found if PREFERRED_URL_RE.search(url)]
    return preferred or found


def gmail_link(message_id: str) -> str:
    return f"https://mail.google.com/mail/u/0/#all/{message_id}"


def best_link(row: dict) -> str:
    urls = row.get("urls") or []
    return str(urls[0] if urls else gmail_link(str(row.get("id", ""))))


ABBREV_RE = re.compile(
    r"\b(Mr|Mrs|Ms|Miss|Dr|Prof|Sr|Jr|vs|etc|"
    r"Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.",
    re.I,
)


def split_sentences(text: str) -> list[str]:
    cleaned = unescape(re.sub(r"\s+", " ", text or "")).strip()
    if not cleaned:
        return []
    placeholders: list[str] = []

    def protect(match: re.Match[str]) -> str:
        placeholders.append(match.group(0))
        return f"@@ABBREV{len(placeholders) - 1}@@"

    protected = ABBREV_RE.sub(protect, cleaned)
    parts = []
    for part in re.split(r"(?<=[.!?])\s+", protected):
        restored = part
        for index, original in enumerate(placeholders):
            restored = restored.replace(f"@@ABBREV{index}@@", original)
        restored = restored.strip()
        if restored:
            parts.append(restored)
    return parts


def is_greeting_sentence(sentence: str) -> bool:
    if NEED_RE.search(sentence):
        return False
    return bool(GREETING_RE.search(sentence)) and not FACT_RE.search(sentence)


def distill_sentence(sentence: str) -> str:
    if GREETING_RE.search(sentence) and (FACT_RE.search(sentence) or NEED_RE.search(sentence)):
        paren = re.search(r"\(([^)]+)\)", sentence)
        if paren and (FACT_RE.search(paren.group(1)) or NEED_RE.search(paren.group(1))):
            return paren.group(1).strip()
        rest = GREETING_RE.sub("", sentence, count=1).strip(" ,.-")
        rest = re.sub(r"^(?:but|and|so)\s+", "", rest, flags=re.I)
        return rest or sentence
    return sentence


def content_sentences(text: str, max_n: int = 3, max_len: int = 320) -> list[str]:
    kept: list[str] = []
    greetings: list[str] = []
    for sentence in split_sentences(text):
        if re.search(r"unsubscribe|powered by|you.?re receiving this email", sentence, re.I):
            continue
        if JUNK_SENTENCE_RE.search(sentence):
            continue
        if len(sentence) < 12:
            continue
        if is_greeting_sentence(sentence):
            greetings.append(sentence.rstrip())
            continue
        kept.append(distill_sentence(sentence).rstrip())
        if len(" ".join(kept)) >= 90 or len(kept) >= max_n:
            break
    chosen = kept or greetings[:1]
    joined = " ".join(chosen)
    if len(joined) <= max_len:
        return chosen
    cut = []
    total = 0
    for sentence in chosen:
        if total and total + len(sentence) > max_len:
            break
        cut.append(sentence)
        total += len(sentence) + 1
    return cut or chosen[:1]


def complete_sentences(text: str, max_len: int = 320) -> str:
    chosen = content_sentences(text, max_n=3, max_len=max_len)
    joined = " ".join(chosen)
    if joined and joined[-1] not in ".!?":
        joined += "."
    return joined


def finish_sentence(text: str) -> str:
    text = unescape(re.sub(r"\s+", " ", text or "")).strip()
    if text and text[-1] not in ".!?":
        text += "."
    return text


def topic_label(subject: str) -> str:
    label = re.sub(r"^\s*(?:fwd|fw|re):\s*", "", subject or "", flags=re.I).strip()
    label = re.sub(r"\s+", " ", label).rstrip(".!?")
    return label or "School update"


def analyze_item(row: dict) -> tuple[str, bool]:
    """Distill one display line from the full cleaned body: the need, the key fact, or 'no action'."""
    body = clean_body(row.get("body_text") or row.get("snippet") or "")
    subject = unescape(str(row.get("subject") or "").strip())
    useful = [distill_sentence(sentence) for sentence in content_sentences(body, max_n=4, max_len=420)]
    useful = [sentence for sentence in useful if sentence]
    need_bits = [sentence for sentence in useful if NEED_RE.search(sentence) and not NEGATED_NEED_RE.search(sentence)]
    fact_bits = [sentence for sentence in useful if sentence not in need_bits and (FACT_RE.search(sentence) or NEGATED_NEED_RE.search(sentence))]
    if not need_bits and NEED_RE.search(subject) and not NEGATED_NEED_RE.search(subject):
        need_bits = [subject]

    if need_bits:
        need_text = finish_sentence(" ".join(need_bits[:2]))
        if re.search(r"\bcarline\b", need_text, re.I):
            need_text = "Learn the carline routine for the first weeks of school."
        return f"Need: {need_text}", True

    if fact_bits:
        fact_text = finish_sentence(" ".join(fact_bits[:2]))
        return f"FYI: {fact_text}", False

    return f"No action ({topic_label(subject)}).", False


def paraphrase(row: dict) -> str:
    subject = unescape(str(row.get("subject") or "").strip())
    if subject.lower() in {"", "(no subject)"}:
        subject = ""
    body = complete_sentences(clean_body(row.get("body_text") or row.get("snippet") or ""))
    if body and JUNK_SENTENCE_RE.search(body) and len(body) < 160:
        body = ""
    if body and len(body) >= 80:
        return body
    if subject and body:
        if body.lower().startswith(subject.lower()[:20].lower()):
            return body
        return f"{subject}. {body}"
    return body or subject or "School update."


def extract_event_dates(row: dict, now_local: datetime) -> list[datetime]:
    blob = f"{row.get('subject','')} {row.get('body_text','')} {row.get('snippet','')}"
    found: list[datetime] = []
    month_map = {
        "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3, "apr": 4, "april": 4,
        "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7, "aug": 8, "august": 8,
        "sep": 9, "sept": 9, "september": 9, "oct": 10, "october": 10, "nov": 11, "november": 11,
        "dec": 12, "december": 12,
    }
    for match in re.finditer(
        r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|"
        r"aug(?:ust)?|sept?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?\s+(\d{1,2})(?:st|nd|rd|th)?\b",
        blob,
        re.I,
    ):
        month = month_map[match.group(1).lower().rstrip(".")]
        day = int(match.group(2))
        year = now_local.year
        try:
            found.append(now_local.replace(month=month, day=day, hour=12, minute=0, second=0, microsecond=0))
        except ValueError:
            continue
    for match in re.finditer(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", blob):
        month = int(match.group(1))
        day = int(match.group(2))
        year = int(match.group(3) or now_local.year)
        if year < 100:
            year += 2000
        try:
            found.append(now_local.replace(year=year, month=month, day=day, hour=12, minute=0, second=0, microsecond=0))
        except ValueError:
            continue
    return found


def due_this_week(row: dict) -> bool:
    now_local = datetime.now(TZ)
    window_end = now_local + timedelta(days=6)
    events = extract_event_dates(row, now_local)
    in_window = [event for event in events if now_local.date() <= event.date() <= window_end.date()]
    if in_window:
        return True
    if events:
        return False
    blob = f"{row.get('subject', '')} {row.get('body_text', '')}"
    if row.get("kind") != "action":
        return False
    if re.search(r"\b(this week|picture day)\b", blob, re.I):
        parsed = parse_date(row.get("date", ""))
        if parsed and datetime.now(timezone.utc) - parsed.astimezone(timezone.utc) <= timedelta(days=7):
            return True
    return False


def when_label(row: dict) -> str:
    parsed = parse_date(row.get("date", ""))
    email_day = ""
    if parsed:
        local = parsed.astimezone(TZ)
        email_day = f"{local.strftime('%a')} {local.month}/{local.day}"
    blob = f"{row.get('subject', '')} {row.get('snippet', '')} {row.get('body_text', '')}"
    match = re.search(
        r"\b((?:mon|tues|wednes|thurs|fri|satur|sun)day|\d{1,2}/\d{1,2}(?:/\d{2,4})?|this week|tomorrow|today|tonight)\b",
        blob,
        re.I,
    )
    extra = match.group(1) if match else ""
    if extra and extra.lower() not in email_day.lower():
        return f"{email_day} · {extra}" if email_day else extra
    return email_day or "undated"


def demote_kind(row: dict) -> str:
    blob = f"{row['from']} {row['subject']} {row.get('snippet','')} {row.get('body_text','')}"
    if "seesaw" in row["from"].lower():
        return "classroom_app"
    if SPORT_RE.search(blob) and not LOW_SUBJECT_RE.search(row["subject"]):
        return "sports"
    if LOW_SUBJECT_RE.search(blob) or BLAST_FROM_RE.search(blob):
        return "fyi"
    if any(name in row["from"].lower() for name in ("byford", "trofemuk", "wildman", "copenhaver", "jackson", "beck")):
        return "teacher"
    if "@edmondschools.net" in row["from"].lower() and "donotreply" not in row["from"].lower() and "messenger@" not in row["from"].lower():
        return "teacher"
    return "fyi"


def llm_context(roster: dict) -> str:
    lines = ["Herbert children, school year 2026-27 (Edmond Public Schools, Oklahoma):"]
    for child in roster.get("children") or []:
        name = child.get("name", "")
        lines.append(f"- {name}: grade {child.get('grade', '?')}, {child.get('school', '')}.")
        teachers = ", ".join(
            f"{teacher.get('name')} ({teacher.get('role')})" for teacher in (child.get("teachers") or [])[:12]
        )
        if teachers:
            lines.append(f"  Teachers: {teachers}.")
        sports = ", ".join(
            f"{item.get('sport')} (coach {item.get('coach')})" if item.get("coach") else str(item.get("sport"))
            for item in child.get("sports") or []
        )
        if sports:
            lines.append(f"  Sports: {sports}.")
        activities = ", ".join(str(item.get("name")) for item in child.get("activities") or [])
        if activities:
            lines.append(f"  Activities: {activities}.")
    lines.append("Parents: Brian and Kristin Herbert. Brian's mailbox is the source of these emails.")
    return "\n".join(lines)


VERDICT_KIND_MAP = {"teacher_info": "teacher", "sports": "sports", "classroom_app": "classroom_app"}


def parse_due_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").replace(tzinfo=TZ, hour=12)
    except ValueError:
        return None


def apply_verdict(row: dict, verdict: dict, roster: dict) -> dict:
    row = dict(row)
    row["verdict"] = verdict
    if verdict.get("done") or not verdict.get("relevant", True):
        row["skip"] = True
        row["kids"] = []
        row["kind"] = "fyi"
        row["importance"] = importance("fyi")
        row["has_action"] = False
        row["display"] = ""
        row["when"] = when_label(row)
        row["link"] = best_link(row)
        row["due_this_week"] = False
        return row
    kids = [name for name in verdict.get("children") or [] if name in CHILD_ORDER]
    row["kids"] = kids or children_for(row, roster)
    need = verdict.get("need")
    row["has_action"] = bool(need)
    row["display"] = str(verdict.get("line") or "").strip() or (f"Need: {need}" if need else "FYI: see the linked email.")
    row["kind"] = "action" if need else VERDICT_KIND_MAP.get(str(verdict.get("category")), "fyi")
    row["importance"] = importance(row["kind"])
    row["when"] = when_label(row)
    row["link"] = best_link(row)
    row["unsubscribe"] = bool(verdict.get("unsubscribe"))
    due = parse_due_date(verdict.get("due_date"))
    row["due_parsed"] = due
    now_local = datetime.now(TZ)
    if due:
        row["due_this_week"] = now_local.date() <= due.date() <= (now_local + timedelta(days=6)).date()
    else:
        row["due_this_week"] = due_this_week(row)
    return row


def annotate(rows: list[dict], roster: dict, verdicts: dict[str, dict] | None = None) -> list[dict]:
    annotated = []
    for row in rows:
        verdict = (verdicts or {}).get(str(row.get("id") or ""))
        if verdict is not None:
            annotated.append(apply_verdict(row, verdict, roster))
            continue
        kids = children_for(row, roster)
        row = dict(row)
        row["kids"] = kids
        display, has_action = analyze_item(row)
        kind = classify(row)
        if kind == "action" and not has_action:
            kind = demote_kind(row)
        row["kind"] = kind
        row["importance"] = importance(kind)
        row["when"] = when_label(row)
        row["display"] = display
        row["has_action"] = has_action
        row["link"] = best_link(row)
        row["due_this_week"] = due_this_week(row)
        annotated.append(row)
    return annotated


def kid_line(row: dict, markdown: bool = False) -> str:
    kids = ", ".join(row["kids"]) or "family"
    display = str(row.get("display") or "").strip() or paraphrase(row)
    prefix = f"• {row['when']} · {kids} — {display}"
    link = str(row.get("link") or "")
    if markdown and link:
        return f"{prefix} [Link]({link})"
    return f"{prefix} Link"


def item_paragraphs(row: dict, checklist: bool = False) -> list[dict]:
    text = kid_line(row, markdown=False)
    if checklist and text.startswith("• "):
        text = text[2:]  # the checkbox glyph replaces the bullet
    paragraph: dict = {"text": text, "bold": bool(row.get("due_this_week")) and bool(row.get("has_action"))}
    if checklist:
        paragraph["checklist"] = True
    link = str(row.get("link") or "")
    offset = text.rfind("Link")
    if link and offset >= 0:
        paragraph["links"] = [{"offset": offset, "length": 4, "url": link}]
    return [paragraph]


def normalize_doc_line(text: str) -> str:
    text = unescape(str(text or "")).replace("\u00a0", " ").replace("\u200b", "")
    text = re.sub(r"^[•\s]+", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _import_google_docs():
    docs_dir = Path(__file__).resolve().parent.parent / "docs"
    if str(docs_dir) not in sys.path:
        sys.path.insert(0, str(docs_dir))
    import google_docs  # noqa: WPS433

    return google_docs


def detect_done_items(env_map: dict[str, str], ledger: dict) -> list[str]:
    """Mark ledger verdicts done when their checkbox is checked in the Doc.

    The Docs API hides checked state, so this reads the Drive HTML export where
    checked checklist items carry text-decoration:line-through.
    """
    registry = load_doc_registry()
    file_id = str(registry.get("file_id") or "")
    if not file_id:
        return []
    google_docs = _import_google_docs()
    try:
        html = google_docs.export_document_html(file_id, env_map=env_map)
    except Exception as exc:  # noqa: BLE001 - read-back is best effort
        print(f"doc read-back failed ({exc}); skipping done detection.", file=sys.stderr)
        return []
    done_texts = []
    for match in re.finditer(r"<li[^>]*>(.*?)</li>", html, re.S | re.I):
        if "line-through" not in match.group(0):
            continue
        text = normalize_doc_line(re.sub(r"<[^>]+>", "", match.group(1)))
        if text:
            done_texts.append(text)
    if not done_texts:
        return []
    marked = []
    now = datetime.now(timezone.utc).isoformat()
    for entry in (ledger.get("evaluated") or {}).values():
        verdict = entry.get("verdict") or {}
        doc_line = normalize_doc_line(entry.get("doc_line") or "")
        if not doc_line or verdict.get("done"):
            continue
        if any(doc_line == text or doc_line in text or text in doc_line for text in done_texts):
            verdict["done"] = True
            verdict["done_at"] = now
            marked.append(str(entry.get("subject") or doc_line)[:80])
    return marked


def section_items(rows: list[dict], roster: dict) -> dict[str, list[dict]]:
    rows = [row for row in rows if not row.get("skip")]

    def dedup_priority(row: dict) -> int:
        if row["has_action"] and not is_stale_action(row):
            return 0
        if row["has_action"]:
            return 1
        return 2

    best: dict[tuple[str, tuple[str, ...]], dict] = {}
    order: list[tuple[str, tuple[str, ...]]] = []
    for row in rows:
        key = (str(row.get("display") or ""), tuple(row.get("kids") or []))
        if key not in best:
            best[key] = row
            order.append(key)
        elif dedup_priority(row) < dedup_priority(best[key]):
            best[key] = row
    rows = [best[key] for key in order]
    important = []
    stale_actions = []
    for row in rows:
        if row["has_action"]:
            if is_stale_action(row):
                stale_actions.append(row)
            else:
                important.append(row)
    non_action = [row for row in rows if not row["has_action"]]
    kid_worthy = [row for row in non_action if row["kind"] in {"teacher", "classroom_app", "sports"}]
    general = [row for row in non_action if row not in kid_worthy]
    per_kid: dict[str, list[dict]] = {name: [] for name in CHILD_ORDER}
    unassigned: list[dict] = []
    for row in kid_worthy:
        names = [name for name in row["kids"] if name in per_kid]
        if not names:
            unassigned.append(row)
            continue
        for name in names:
            per_kid[name].append(row)
    leftover_stale = []
    for row in stale_actions:
        row = dict(row)
        row["display"] = re.sub(r"^Need:", "Past need (likely done):", str(row.get("display") or ""))
        row["due_this_week"] = False
        names = [name for name in row["kids"] if name in per_kid]
        if names:
            for name in names:
                per_kid[name].append(row)
        else:
            leftover_stale.append(row)
    if unassigned or leftover_stale:
        general = unassigned + leftover_stale + general
    suggestions: list[str] = []
    seen_senders: set[str] = set()
    for row in rows:
        if not row.get("unsubscribe"):
            continue
        sender_name, sender_email = parse_from(row.get("from", ""))
        key = (sender_email or sender_name).lower()
        if key and key not in seen_senders:
            seen_senders.add(key)
            label = sender_name or sender_email
            suggestions.append(f"Consider unsubscribing from {label} — recurring low-value mail.")
    return {
        "important": important,
        "per_kid": per_kid,
        "general": general,
        "suggestions": suggestions,
        "roster": roster,
    }


def school_for(name: str, roster: dict) -> str:
    for child in roster.get("children") or []:
        if child.get("name") == name:
            grade = child.get("grade", "")
            school = child.get("school_short") or child.get("school", "")
            return f"{school}, grade {grade}".strip(", ")
    return ""


def child_record(name: str, roster: dict) -> dict:
    for child in roster.get("children") or []:
        if child.get("name") == name:
            return child
    return {}


def seed_teams(roster: dict) -> dict:
    roster = json.loads(json.dumps(roster))
    for child in roster.get("children") or []:
        sports = child.setdefault("sports", [])
        activities = child.setdefault("activities", [])
        known_sports = {(item.get("sport") or "").strip().lower() for item in sports}
        known_activities = {(item.get("name") or "").strip().lower() for item in activities}
        for teacher in child.get("teachers") or []:
            role = str(teacher.get("role") or "")
            sport_match = SPORT_RE.search(role)
            activity_match = ACTIVITY_RE.search(role)
            if sport_match:
                sport = normalize_sport(sport_match.group(1))
                if sport.lower() not in known_sports:
                    sports.append(
                        {
                            "sport": sport,
                            "team": role,
                            "coach": teacher.get("name", ""),
                            "confidence": teacher.get("confidence", "schedule"),
                        }
                    )
                    known_sports.add(sport.lower())
            elif activity_match:
                name = role.strip() or activity_match.group(1).title()
                if name.lower() not in known_activities:
                    activities.append(
                        {
                            "name": name,
                            "advisor": teacher.get("name", ""),
                            "confidence": teacher.get("confidence", "schedule"),
                        }
                    )
                    known_activities.add(name.lower())
    return roster


def standing_team_lines(name: str, roster: dict) -> list[str]:
    child = child_record(name, roster)
    lines = []
    sports = child.get("sports") or []
    if sports:
        parts = []
        for item in sports:
            sport = str(item.get("sport") or "").strip()
            team = str(item.get("team") or "").strip()
            coach = str(item.get("coach") or "").strip()
            bit = team or sport
            if coach:
                bit = f"{bit} — {coach}" if bit else coach
            if bit:
                parts.append(bit)
        if parts:
            lines.append("Sports: " + "; ".join(parts) + ".")
    else:
        lines.append("Sports: none on file.")
    activities = child.get("activities") or []
    if activities:
        parts = []
        for item in activities:
            label = str(item.get("name") or "").strip()
            advisor = str(item.get("advisor") or item.get("coach") or "").strip()
            if advisor:
                label = f"{label} — {advisor}"
            if label:
                parts.append(label)
        if parts:
            lines.append("Activities: " + "; ".join(parts) + ".")
    return lines


def render_doc_paragraphs(rows: list[dict], roster: dict) -> tuple[list[dict], str]:
    now_local = datetime.now(TZ)
    title = DOC_TITLE
    sections = section_items(rows, roster)
    paragraphs: list[dict] = [
        {"text": title, "style": "TITLE"},
        {
            "text": (
                f"Updated {now_local.strftime('%A, %B')} {now_local.day}, {now_local.year}, "
                f"{now_local.strftime('%I:%M %p').lstrip('0')} CT"
            )
        },
        {"text": ""},
        {"text": "Important", "style": "HEADING_1"},
        {"text": "Only items with a real to-do. Items due this week are bold. Check off what you've handled — checked items drop off on the next update."},
        {"text": ""},
    ]
    if sections["important"]:
        for row in sections["important"]:
            paragraphs.extend(item_paragraphs(row, checklist=True))
    else:
        paragraphs.append({"text": "• None right now."})
    paragraphs.append({"text": ""})
    for name in CHILD_ORDER:
        heading = f"{name} — {school_for(name, roster)}"
        paragraphs.extend([{"text": heading, "style": "HEADING_1"}, {"text": ""}])
        for line in standing_team_lines(name, roster):
            paragraphs.append({"text": line})
        items = sections["per_kid"].get(name) or []
        if items:
            for row in items:
                paragraphs.extend(item_paragraphs(row))
        else:
            paragraphs.append({"text": "• No extra classroom notes this window."})
        paragraphs.append({"text": ""})
    paragraphs.extend(
        [
            {"text": "General", "style": "HEADING_1"},
            {"text": "School announcements that are not urgent."},
            {"text": ""},
        ]
    )
    if sections["general"]:
        for row in sections["general"]:
            paragraphs.extend(item_paragraphs(row))
    else:
        paragraphs.append({"text": "• None this window."})
    paragraphs.append({"text": ""})
    if sections.get("suggestions"):
        paragraphs.extend(
            [
                {"text": "Suggestions", "style": "HEADING_1"},
                {"text": "Mailbox hygiene ideas from the evaluator."},
                {"text": ""},
            ]
        )
        for suggestion in sections["suggestions"]:
            paragraphs.append({"text": f"• {suggestion}"})
        paragraphs.append({"text": ""})
    return paragraphs, title


def render_doc_text(rows: list[dict], roster: dict) -> tuple[str, list[str], str]:
    paragraphs, title = render_doc_paragraphs(rows, roster)
    headings = [str(item.get("text", "")) for item in paragraphs if item.get("style") == "HEADING_1"]
    text = "\n".join(str(item.get("text", "")) for item in paragraphs)
    return text, headings, title


def render_telegram(rows: list[dict], roster: dict, doc_link: str) -> str:
    sections = section_items(rows, roster)
    lines = ["School digest"]
    if sections["important"]:
        lines.append("Important")
        lines.extend(kid_line(row, markdown=True) for row in sections["important"][:8])
    else:
        lines.append("No action items in this window.")
    if doc_link:
        lines.append(f"Full digest: {doc_link}")
    return "\n".join(lines) + "\n"


def is_stale_action(row: dict) -> bool:
    now_local = datetime.now(TZ)
    due = row.get("due_parsed")
    if due is not None:
        return due.date() < now_local.date()
    events = extract_event_dates(row, now_local)
    if events and all(event.date() < now_local.date() for event in events):
        return True
    parsed = parse_date(row.get("date", ""))
    if not parsed:
        return False
    age = datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)
    when = str(row.get("when", "")).lower()
    blob = f"{row.get('subject', '')} {row.get('body_text', '')}"
    if age > timedelta(days=2) and re.search(r"\b(tomorrow|today|tonight)\b", when):
        return True
    if age > timedelta(days=6) and "this week" in when:
        return True
    if age > timedelta(days=2) and re.search(r"\b(walkabout|meet the teacher|new to north)\b", blob, re.I):
        return True
    return False


def summarize_row(row: dict) -> str:
    return str(row.get("summary") or paraphrase(row))


def fetch_rows(env_map: dict[str, str], ids: list[str]) -> list[dict]:
    rows = []
    for message_id in ids:
        message = gmail_api.get_message(message_id, env_map=env_map, account=ACCOUNT, fmt="full")
        headers = gmail_api.header_map(message)
        payload = message.get("payload") or {}
        plain, html = walk_payload_text(payload)
        body_text = clean_body(plain.strip() or html_to_text(html))[:4000]
        rows.append(
            {
                "id": message_id,
                "from": headers.get("from", ""),
                "subject": headers.get("subject", ""),
                "date": headers.get("date", ""),
                "snippet": message.get("snippet", ""),
                "body_text": body_text,
                "urls": extract_urls(html, plain),
                "label_ids": message.get("labelIds") or [],
            }
        )
    return rows


def teacher_already_known(child: dict, name: str, email: str) -> bool:
    needles = {name.lower(), email.lower()}
    for teacher in child.get("teachers") or []:
        if str(teacher.get("name") or "").lower() in needles:
            return True
        if email and str(teacher.get("email") or "").lower() == email.lower():
            return True
    return False


def append_family_facts(facts: list[str]) -> list[str]:
    """Append new general facts to the family facts page. Returns facts actually added."""
    if not facts:
        return []
    today = datetime.now(TZ).date().isoformat()
    if FAMILY_FACTS_PATH.exists():
        existing = FAMILY_FACTS_PATH.read_text(encoding="utf-8")
    else:
        existing = (
            "# Family Facts (Email-Learned)\n\n"
            "Durable facts about the Herbert household learned by the email evaluator. "
            "Appended automatically; prune or correct freely.\n"
        )
    existing_lower = existing.lower()
    added = []
    for fact in facts:
        fact = fact.strip().rstrip(".") + "."
        if fact.lower().rstrip(".") in existing_lower:
            continue
        existing += f"\n- {today}: {fact}"
        existing_lower += "\n" + fact.lower()
        added.append(fact)
    if added:
        FAMILY_FACTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        FAMILY_FACTS_PATH.write_text(existing.rstrip() + "\n", encoding="utf-8")
    return added


def apply_llm_learn(rows: list[dict], roster: dict) -> tuple[dict, list[str]]:
    """Apply LLM 'learn' entries to the roster and family facts page."""
    roster = seed_teams(roster)
    children = {str(child.get("name")): child for child in roster.get("children") or []}
    notes: list[str] = []
    facts: list[str] = []
    today = datetime.now(TZ).date().isoformat()
    for row in rows:
        verdict = row.get("verdict")
        if not verdict:
            continue
        sender_name, sender_email = parse_from(row.get("from", ""))
        for entry in verdict.get("learn") or []:
            kind = entry.get("type")
            value = str(entry.get("value") or "").strip()
            person = str(entry.get("person") or "").strip()
            role = str(entry.get("role") or "").strip()
            child = children.get(entry.get("child") or "")
            if kind == "teacher" and child:
                name = person or value
                if name and not teacher_already_known(child, name, sender_email if name == sender_name else ""):
                    child.setdefault("teachers", []).append(
                        {
                            "role": role or "Teacher",
                            "name": name,
                            "email": sender_email if name == sender_name else "",
                            "confidence": "llm-ingest",
                            "notes": f"Learned {today} by email evaluator.",
                        }
                    )
                    notes.append(f"{child.get('name')}: teacher {name}")
            elif kind == "sport" and child:
                sport = normalize_sport(role or value)
                known = {(item.get("sport") or "").strip().lower() for item in child.get("sports") or []}
                if sport and sport.lower() not in known:
                    child.setdefault("sports", []).append(
                        {
                            "sport": sport,
                            "coach": person or sender_name,
                            "confidence": "llm-ingest",
                            "notes": f"Learned {today} by email evaluator.",
                        }
                    )
                    notes.append(f"{child.get('name')}: sport {sport}")
            elif kind == "activity" and child:
                activity = (role or value).title()
                known = {(item.get("name") or "").strip().lower() for item in child.get("activities") or []}
                if activity and activity.lower() not in known:
                    child.setdefault("activities", []).append(
                        {
                            "name": activity,
                            "advisor": person or sender_name,
                            "confidence": "llm-ingest",
                            "notes": f"Learned {today} by email evaluator.",
                        }
                    )
                    notes.append(f"{child.get('name')}: activity {activity}")
            elif value:
                facts.append(value if not entry.get("child") else f"{entry['child']}: {value}")
    added_facts = append_family_facts(facts)
    notes.extend(f"fact: {fact}" for fact in added_facts)
    return roster, notes


def ingest_knowledge(rows: list[dict], roster: dict) -> tuple[dict, list[str]]:
    roster = seed_teams(roster)
    children = {str(child.get("name")): child for child in roster.get("children") or []}
    notes: list[str] = []
    today = datetime.now(TZ).date().isoformat()
    for row in rows:
        if row.get("verdict") is not None:
            continue
        sender_name, sender_email = parse_from(row.get("from", ""))
        blob = f"{row.get('subject', '')} {row.get('body_text', '')}"
        school_sender = "edmondschools.net" in sender_email.lower() or "edmondschools.net" in str(row.get("from", "")).lower()
        if SKIP_SENDER_RE.search(row.get("from", "")):
            school_sender = False
        for kid_name in row.get("kids") or []:
            child = children.get(kid_name)
            if not child:
                continue
            if school_sender and sender_name and re.search(r"\b(welcome|homeroom|i am|i'm your|advisory)\b", blob, re.I):
                if not teacher_already_known(child, sender_name, sender_email):
                    role = "Teacher"
                    intro = TEACHER_INTRO_RE.search(blob)
                    if intro:
                        guessed = re.sub(r"\s+", " ", intro.group(1)).strip(" ,")
                        if 2 < len(guessed) < 40:
                            role = guessed.title()
                    child.setdefault("teachers", []).append(
                        {
                            "role": role,
                            "name": sender_name,
                            "email": sender_email,
                            "confidence": "email-ingest",
                            "notes": f"Ingested {today} from school mail.",
                        }
                    )
                    local = sender_email.split("@")[0] if sender_email else sender_name.lower()
                    needles = child.setdefault("sender_needles", [])
                    if local and local not in needles:
                        needles.append(local)
                    notes.append(f"{kid_name}: teacher {sender_name}")
            sport_match = SPORT_RE.search(blob)
            named_kid = kid_name.lower() in blob.lower()
            single_kid = len(row.get("kids") or []) == 1
            if sport_match and school_sender and (named_kid or single_kid):
                sport = normalize_sport(sport_match.group(1))
                known = {(item.get("sport") or "").strip().lower() for item in child.get("sports") or []}
                if sport.lower() not in known:
                    child.setdefault("sports", []).append(
                        {
                            "sport": sport,
                            "coach": sender_name,
                            "confidence": "email-ingest",
                            "notes": f"Ingested {today} from school mail.",
                        }
                    )
                    notes.append(f"{kid_name}: sport {sport}")
            activity_match = ACTIVITY_RE.search(blob)
            if activity_match and school_sender and (named_kid or single_kid):
                activity = str(activity_match.group(1)).title()
                known = {(item.get("name") or "").strip().lower() for item in child.get("activities") or []}
                if activity.lower() not in known and not any(activity.lower() in name for name in known):
                    child.setdefault("activities", []).append(
                        {
                            "name": activity,
                            "advisor": sender_name,
                            "confidence": "email-ingest",
                            "notes": f"Ingested {today} from school mail.",
                        }
                    )
                    notes.append(f"{kid_name}: activity {activity}")
    return roster, notes


def homeroom_label(child: dict) -> str:
    for teacher in child.get("teachers") or []:
        role = str(teacher.get("role") or "").lower()
        if "homeroom" in role or "advisory" in role:
            room = f" (Rm {teacher['room']})" if teacher.get("room") else ""
            team = f", {teacher['team']}" if teacher.get("team") else ""
            return f"{teacher.get('name', '')}{room}{team}".strip()
    if child.get("name") == "Daniel":
        return "n/a (high school)"
    return "n/a"


def child_notes_line(child: dict) -> str:
    bits = []
    sports = child.get("sports") or []
    if sports:
        bits.append(
            "Sports: "
            + "; ".join(
                f"{item.get('sport')} ({item.get('coach')})" if item.get("coach") else str(item.get("sport"))
                for item in sports
            )
            + "."
        )
    activities = child.get("activities") or []
    if activities:
        bits.append(
            "Activities: "
            + "; ".join(
                f"{item.get('name')} ({item.get('advisor')})" if item.get("advisor") else str(item.get("name"))
                for item in activities
            )
            + "."
        )
    extras = []
    for teacher in child.get("teachers") or []:
        role = str(teacher.get("role") or "")
        if any(token in role.lower() for token in ("homeroom", "advisory", "basketball", "track", "band")):
            continue
        if teacher.get("confidence") in {"confirmed", "welcome-email", "email-ingest"} or "english" in role.lower():
            extras.append(f"{role}: {teacher.get('name')}".strip(": "))
        if len(extras) >= 2:
            break
    bits.extend(extras)
    if child.get("name") == "Levi" and not extras:
        bits.append("Seesaw posts to Levi's journal.")
    return " ".join(bit.rstrip(".") + "." for bit in bits if bit) or "See roster JSON."


def sync_children_page(roster: dict) -> bool:
    if not CHILDREN_PAGE_PATH.exists():
        return False
    original = CHILDREN_PAGE_PATH.read_text(encoding="utf-8")
    table_lines = [
        "| Child | Grade | School | Homeroom / advisory | Notes |",
        "|-------|-------|--------|---------------------|-------|",
    ]
    for child in roster.get("children") or []:
        table_lines.append(
            f"| {child.get('name')} | {child.get('grade', '')} | {child.get('school', '')} | "
            f"{homeroom_label(child)} | {child_notes_line(child)} |"
        )
    table = "\n".join(table_lines)
    updated = re.sub(
        r"\| Child \| Grade \| School \| Homeroom / advisory \| Notes \|.*?(?=\n## )",
        table + "\n\n",
        original,
        count=1,
        flags=re.S,
    )
    if updated == original:
        return False
    CHILDREN_PAGE_PATH.write_text(updated, encoding="utf-8")
    return True


def save_roster(path: Path, roster: dict) -> None:
    path.write_text(json.dumps(roster, indent=2) + "\n", encoding="utf-8")


def render(rows: list[dict], roster: dict, hours: int) -> str:
    text, _headings, _title = render_doc_text(rows, roster)
    header = f"Window: last {hours}h\n"
    return header + text


def apply_label(env_map: dict[str, str], rows: list[dict]) -> int:
    label = gmail_api.ensure_label(LABEL_NAME, env_map=env_map, account=ACCOUNT)
    label_id = str(label.get("id", ""))
    pending = [row["id"] for row in rows if label_id not in (row.get("label_ids") or [])]
    if not pending:
        return 0
    for offset in range(0, len(pending), 1000):
        gmail_api.batch_modify_messages(
            pending[offset : offset + 1000],
            add_label_ids=[label_id],
            env_map=env_map,
            account=ACCOUNT,
        )
    return len(pending)


def load_doc_registry() -> dict:
    if DOC_REGISTRY_PATH.exists():
        return json.loads(DOC_REGISTRY_PATH.read_text(encoding="utf-8"))
    return {}


def save_doc_registry(payload: dict) -> None:
    DOC_REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOC_REGISTRY_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def update_google_doc(env_map: dict[str, str], rows: list[dict], roster: dict) -> dict:
    docs_dir = Path(__file__).resolve().parent.parent / "docs"
    if str(docs_dir) not in sys.path:
        sys.path.insert(0, str(docs_dir))
    import google_docs  # noqa: WPS433

    registry = load_doc_registry()
    folder = google_docs.ensure_folder(DOC_FOLDER, env_map=env_map)
    folder_id = str(folder.get("id") or registry.get("folder_id") or "")
    document = {}
    file_id = str(registry.get("file_id") or "")
    if file_id:
        document = {"id": file_id, "webViewLink": registry.get("web_view_link", "")}
    else:
        document = google_docs.ensure_document(DOC_TITLE, env_map=env_map, folder_id=folder_id)
        file_id = str(document.get("id", ""))
    if not file_id:
        raise google_docs.GoogleDocsError("Google Doc create did not return a file id.")
    google_docs.replace_document_content(file_id, render_doc_paragraphs(rows, roster)[0], env_map=env_map)
    shared_with = list(registry.get("shared_with") or [])
    if SHARE_EMAIL not in shared_with:
        google_docs.share_file(file_id, SHARE_EMAIL, env_map=env_map, role="writer", notify=True)
        shared_with.append(SHARE_EMAIL)
    link = str(document.get("webViewLink") or registry.get("web_view_link") or "")
    if not link:
        looked_up = google_docs.find_app_file(DOC_TITLE, google_docs.GOOGLE_DOC_MIME, env_map=env_map, parent_id=folder_id)
        link = str(looked_up.get("webViewLink") or f"https://docs.google.com/document/d/{file_id}/edit")
        document = {**document, **looked_up}
    registry = {
        "title": DOC_TITLE,
        "file_id": file_id,
        "folder_id": folder_id,
        "web_view_link": link,
        "shared_with": shared_with,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    save_doc_registry(registry)
    return registry


def send_telegram(text: str) -> None:
    sys.path.insert(0, str(Path("scripts/telegram").resolve()))
    from send_task_response import send_message  # noqa: WPS433

    raw = (
        os.getenv("AGENTCORE_TELEGRAM_NOTIFY_CHAT_IDS", "").strip()
        or os.getenv("AGENTCORE_TELEGRAM_ALLOWED_USER_IDS", "").strip()
    )
    chat_ids = [part.strip() for part in raw.split(",") if part.strip()]
    if not chat_ids:
        raise RuntimeError("Missing AGENTCORE_TELEGRAM_NOTIFY_CHAT_IDS / ALLOWED_USER_IDS.")
    for chat_id in chat_ids:
        send_message(chat_id, text)


def main() -> int:
    args = parse_args()
    env_map = load_env_file(".env")
    roster = load_roster(Path(args.roster))
    ids = collect_ids(env_map, args.hours)
    rows = fetch_rows(env_map, ids)
    rows.sort(key=lambda row: parse_date(row["date"]) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

    ledger = evaluator.load_ledger()
    done_marks = detect_done_items(env_map, ledger)
    if done_marks:
        print("checked off in Doc: " + "; ".join(done_marks), file=sys.stderr)
    evaluated = ledger.get("evaluated") or {}
    verdicts: dict[str, dict] = {}
    pending: list[dict] = []
    for row in rows:
        row_id = str(row.get("id") or "")
        entry = evaluated.get(row_id)
        if entry and isinstance(entry.get("verdict"), dict) and not args.reeval:
            verdicts[row_id] = {**entry["verdict"], "id": row_id}
            continue
        skip_verdict = evaluator.prefilter_verdict(row)
        if skip_verdict:
            verdicts[row_id] = skip_verdict
            evaluator.record_verdict(ledger, row, skip_verdict, "prefilter", link=best_link(row))
            continue
        pending.append(row)
    if pending and not args.no_llm:
        try:
            new_verdicts, backend = evaluator.evaluate_rows(pending, llm_context(roster), CHILD_ORDER)
            for row in pending:
                verdict = new_verdicts.get(str(row.get("id") or ""))
                if verdict:
                    verdicts[verdict["id"]] = verdict
                    evaluator.record_verdict(ledger, row, verdict, backend, link=best_link(row))
            print(f"llm evaluated {len(new_verdicts)}/{len(pending)} new email(s) via {backend}", file=sys.stderr)
        except Exception as exc:  # noqa: BLE001 - digest must still render on any LLM failure
            print(f"LLM evaluation unavailable ({exc}); keyword fallback for {len(pending)} email(s).", file=sys.stderr)
    elif pending:
        print(f"--no-llm: keyword fallback for {len(pending)} email(s).", file=sys.stderr)

    rows = annotate(rows, roster, verdicts)
    # Remember the exact rendered line for each Important checkbox so the next
    # run can match checked (struck-through) items in the Doc export back to
    # their ledger entries.
    for row in section_items(rows, roster)["important"]:
        entry = (ledger.get("evaluated") or {}).get(str(row.get("id") or ""))
        if entry is not None:
            entry["doc_line"] = normalize_doc_line(kid_line(row, markdown=False))
    if not args.dry_run:
        evaluator.save_ledger(ledger)
    roster, learn_notes = apply_llm_learn(rows, roster)
    roster, keyword_notes = ingest_knowledge(rows, roster)
    ingest_notes = learn_notes + keyword_notes
    if ingest_notes and not args.dry_run:
        save_roster(Path(args.roster), roster)
        print("ingested: " + "; ".join(ingest_notes), file=sys.stderr)
        if sync_children_page(roster):
            print(f"updated {CHILDREN_PAGE_PATH}", file=sys.stderr)
    elif ingest_notes:
        print("ingest dry-run: " + "; ".join(ingest_notes), file=sys.stderr)
    digest = render(rows, roster, args.hours)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(digest, encoding="utf-8")
    print(digest)
    labeled = 0
    registry = {}
    if args.apply_label and not args.dry_run:
        labeled = apply_label(env_map, rows)
        print(f"labeled {labeled} message(s) with {LABEL_NAME}", file=sys.stderr)
    if args.update_doc and not args.dry_run:
        registry = update_google_doc(env_map, rows, roster)
        print(f"updated doc {registry.get('web_view_link', '')}", file=sys.stderr)
    if args.send_telegram and not args.dry_run:
        link = str(registry.get("web_view_link") or load_doc_registry().get("web_view_link") or "")
        telegram_text = render_telegram(rows, roster, link)
        send_telegram(telegram_text)
        print("sent telegram digest", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
