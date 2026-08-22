"""Date language → ISO dates, using regex and calendar arithmetic only.

Handles exact forms ("Oct 12", "2026-10-12", "10/12") and the vague forms travellers
actually type ("early March", "next Friday", "in three weeks", "this weekend").
Vague forms are marked ``approximate`` so Roma can say out loud what it assumed.
"""

from __future__ import annotations

import calendar
import datetime as dt
import re
from dataclasses import dataclass

MONTHS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}
MONTH_RE = "|".join(sorted(MONTHS, key=len, reverse=True))

WEEKDAYS = {
    "monday": 0, "mon": 0, "tuesday": 1, "tue": 1, "tues": 1, "wednesday": 2, "wed": 2,
    "thursday": 3, "thu": 3, "thur": 3, "thurs": 3, "friday": 4, "fri": 4,
    "saturday": 5, "sat": 5, "sunday": 6, "sun": 6,
}
WEEKDAY_RE = "|".join(sorted(WEEKDAYS, key=len, reverse=True))

NUMBER_WORDS = {
    "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "couple": 2, "few": 3,
}

PART_OF_MONTH = {"early": 5, "beginning": 3, "start": 3, "mid": 15, "middle": 15, "late": 25, "end": 27}


@dataclass
class DateHit:
    start: int
    end: int
    date: dt.date
    precision: str  # "exact" | "approximate"
    text: str
    note: str = ""
    kind: str = "calendar"  # "calendar" | "relative"


def _int(token: str) -> int | None:
    token = token.strip().lower()
    if token.isdigit():
        return int(token)
    return NUMBER_WORDS.get(token)


def _month_date(month: int, day: int, ref: dt.date) -> dt.date:
    """Pick the next occurrence of month/day at or after `ref`."""
    year = ref.year
    day = min(day, calendar.monthrange(year, month)[1])
    candidate = dt.date(year, month, day)
    if candidate < ref:
        year += 1
        day = min(day, calendar.monthrange(year, month)[1])
        candidate = dt.date(year, month, day)
    return candidate


def _add_months(ref: dt.date, months: int) -> dt.date:
    month_index = ref.month - 1 + months
    year = ref.year + month_index // 12
    month = month_index % 12 + 1
    return dt.date(year, month, min(ref.day, calendar.monthrange(year, month)[1]))


def _weekday_date(weekday: int, ref: dt.date, next_week: bool) -> dt.date:
    """"friday" = the coming Friday; "next friday" = Friday of the following week."""
    if next_week:
        monday_next = ref + dt.timedelta(days=7 - ref.weekday())
        return monday_next + dt.timedelta(days=weekday)
    delta = (weekday - ref.weekday()) % 7
    return ref + dt.timedelta(days=delta or 7)


def find_dates(text: str, ref: dt.date | None = None) -> list[DateHit]:
    """Return date mentions in the order they appear, de-overlapped."""
    ref = ref or dt.date.today()
    lowered = " " + str(text or "").lower() + " "
    hits: list[DateHit] = []

    def add(match: re.Match, date: dt.date, precision: str, note: str = "", kind: str = "calendar") -> None:
        hits.append(DateHit(match.start(), match.end(), date, precision, match.group(0).strip(), note, kind))

    for m in re.finditer(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", lowered):
        year, month, day = (int(g) for g in m.groups())
        try:
            add(m, dt.date(year, month, day), "exact")
        except ValueError:
            pass

    # "early/mid/late March", "end of March"
    for m in re.finditer(
        rf"\b(early|beginning|start|mid|middle|late|end)\s*(?:-|\s)?(?:of\s+)?({MONTH_RE})\b", lowered
    ):
        part, month_name = m.group(1), m.group(2)
        date = _month_date(MONTHS[month_name], PART_OF_MONTH[part], ref)
        add(m, date, "approximate", f"read “{m.group(0).strip()}” as {date.isoformat()}")

    # "Oct 12", "October 12th", "Oct 12 2026"
    for m in re.finditer(
        rf"\b({MONTH_RE})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:,?\s+(\d{{4}}))?\b", lowered
    ):
        month = MONTHS[m.group(1)]
        day = int(m.group(2))
        if day > 31:
            continue
        if m.group(3):
            try:
                add(m, dt.date(int(m.group(3)), month, min(day, calendar.monthrange(int(m.group(3)), month)[1])), "exact")
            except ValueError:
                pass
        else:
            add(m, _month_date(month, day, ref), "exact")

    # "12 October", "12th of October"
    for m in re.finditer(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?({MONTH_RE})\b", lowered):
        day = int(m.group(1))
        if day > 31:
            continue
        add(m, _month_date(MONTHS[m.group(2)], day, ref), "exact")

    # "10/12" or "10/12/2026" (US month/day ordering)
    for m in re.finditer(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", lowered):
        month, day = int(m.group(1)), int(m.group(2))
        if not (1 <= month <= 12 and 1 <= day <= 31):
            continue
        if m.group(3):
            year = int(m.group(3))
            year += 2000 if year < 100 else 0
            try:
                add(m, dt.date(year, month, day), "exact")
            except ValueError:
                pass
        else:
            add(m, _month_date(month, day, ref), "exact")

    for m in re.finditer(r"\b(today|tonight|tomorrow|day after tomorrow)\b", lowered):
        offset = {"today": 0, "tonight": 0, "tomorrow": 1, "day after tomorrow": 2}[m.group(1)]
        add(m, ref + dt.timedelta(days=offset), "exact")

    for m in re.finditer(r"\b(this|next|coming)\s+weekend\b", lowered):
        saturday = _weekday_date(5, ref, m.group(1) == "next")
        add(m, saturday, "approximate", f"read “{m.group(0).strip()}” as {saturday.isoformat()}", "relative")

    for m in re.finditer(rf"\b(this|next|coming)?\s*({WEEKDAY_RE})\b", lowered):
        qualifier = (m.group(1) or "").strip()
        date = _weekday_date(WEEKDAYS[m.group(2)], ref, qualifier == "next")
        note = f"read “{m.group(0).strip()}” as {date.isoformat()}"
        add(m, date, "approximate", note, "relative")

    for m in re.finditer(r"\bnext\s+(week|month|year)\b", lowered):
        unit = m.group(1)
        if unit == "week":
            date = _weekday_date(0, ref, True) + dt.timedelta(days=2)
        elif unit == "month":
            first = _add_months(ref.replace(day=1), 1)
            date = first + dt.timedelta(days=14)
        else:
            date = _add_months(ref, 12)
        add(m, date, "approximate", f"read “{m.group(0).strip()}” as {date.isoformat()}", "relative")

    for m in re.finditer(
        r"\bin\s+(a|an|one|two|three|four|five|six|seven|eight|nine|ten|couple|few|\d+)\s*"
        r"(?:of\s+)?(day|days|week|weeks|month|months)\b",
        lowered,
    ):
        count = _int(m.group(1)) or 1
        unit = m.group(2)
        if unit.startswith("day"):
            date = ref + dt.timedelta(days=count)
        elif unit.startswith("week"):
            date = ref + dt.timedelta(days=7 * count)
        else:
            date = _add_months(ref, count)
        add(m, date, "approximate", f"read “{m.group(0).strip()}” as {date.isoformat()}", "relative")

    # Bare month: "in March", "sometime in March", "for March"
    for m in re.finditer(rf"\b(?:in|during|around|for|sometime in)\s+({MONTH_RE})\b", lowered):
        date = _month_date(MONTHS[m.group(1)], 15, ref)
        add(m, date, "approximate", f"read “{m.group(0).strip()}” as mid-{m.group(1).title()} ({date.isoformat()})")

    # An explicit calendar date beats a relative phrase elsewhere in the sentence
    # ("Friday Oct 12" is one date, not two).
    if any(h.kind == "calendar" for h in hits):
        hits = [h for h in hits if h.kind == "calendar"]

    hits.sort(key=lambda h: (h.start, -(h.end - h.start)))
    deduped: list[DateHit] = []
    for hit in hits:
        if any(hit.start < kept.end and hit.end > kept.start for kept in deduped):
            continue
        deduped.append(hit)
    return deduped


def find_duration_days(text: str) -> int | None:
    """"for a week", "for 10 days", "5 night trip" → number of days."""
    lowered = str(text or "").lower()
    m = re.search(
        r"\bfor\s+(a|an|one|two|three|four|five|six|seven|eight|nine|ten|couple|few|\d+)\s*"
        r"(?:of\s+)?(day|days|night|nights|week|weeks|month|months)\b",
        lowered,
    )
    if not m:
        m = re.search(
            r"\b(a|an|one|two|three|four|five|six|seven|eight|nine|ten|couple|few|\d+)[\s-]*"
            r"(day|days|night|nights|week|weeks)\s+(?:trip|stay|holiday|vacation)\b",
            lowered,
        )
    if not m:
        return None
    count = _int(m.group(1)) or 1
    unit = m.group(2)
    if unit.startswith("week"):
        return 7 * count
    if unit.startswith("month"):
        return 30 * count
    return count


def resolve_trip_dates(text: str, ref: dt.date | None = None) -> dict:
    """Extract depart/return dates plus precision and human-readable notes."""
    ref = ref or dt.date.today()
    hits = find_dates(text, ref)
    lowered = str(text or "").lower()
    # find_dates matches against a space-padded copy; keep the same offsets here.
    padded = f" {lowered} "
    notes = []
    depart = ret = None
    precision = "exact"

    # "Oct 12 to 20" / "Oct 12-20": second day belongs to the first month.
    if hits:
        tail = padded[hits[0].end:hits[0].end + 14]
        m = re.match(r"\s*(?:to|through|thru|until|till|-|–|—)\s*(\d{1,2})(?:st|nd|rd|th)?\b", tail)
        if m and len(hits) == 1:
            day = int(m.group(1))
            base = hits[0].date
            if 1 <= day <= calendar.monthrange(base.year, base.month)[1]:
                candidate = dt.date(base.year, base.month, day)
                if candidate < base:
                    candidate = _add_months(candidate, 1)
                ret = candidate

    if hits:
        depart = hits[0].date
        precision = hits[0].precision
        if hits[0].note:
            notes.append(hits[0].note)
        if ret is None and len(hits) > 1:
            for hit in hits[1:]:
                if hit.date >= depart:
                    ret = hit.date
                    if hit.note:
                        notes.append(hit.note)
                    break

    if depart and ret is None:
        days = find_duration_days(text)
        if days:
            ret = depart + dt.timedelta(days=days)
            notes.append(f"return set to {ret.isoformat()} for a {days}-day trip")

    if depart and re.search(r"\b(one[\s-]?way|single|no return)\b", lowered):
        ret = None

    return {
        "depart_date": depart.isoformat() if depart else None,
        "return_date": ret.isoformat() if ret else None,
        "date_precision": precision,
        "notes": notes,
    }
