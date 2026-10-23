"""Turning a sentence into search slots.

This is a rule-based parser, not a model. It extracts places, dates, airline,
cabin and party size, and reports honestly when it found nothing. Whatever it
extracts is handed to the same engine the form uses.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, timedelta

from . import airlines, airports

_MONTHS = {
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

_WEEKDAYS = {
    "monday": 0, "mon": 0,
    "tuesday": 1, "tue": 1, "tues": 1,
    "wednesday": 2, "wed": 2,
    "thursday": 3, "thu": 3, "thurs": 3,
    "friday": 4, "fri": 4,
    "saturday": 5, "sat": 5,
    "sunday": 6, "sun": 6,
}

_ORIGIN_CUES = (
    "from", "out of", "outof", "leaving", "leave", "departing", "depart",
    "starting in", "based in", "i am in", "im in",
)
_DESTINATION_CUES = (
    "to", "into", "toward", "towards", "for", "visit", "visiting", "see",
    "go to", "going to", "fly to", "flying to", "head to", "heading to",
    "destination",
)
_RETURN_CUES = (
    "returning", "return", "back on", "back", "coming back", "come back",
    "through", "until", "til", "till", "then home", "home on",
)
_DEPART_CUES = ("leaving", "leave", "departing", "depart", "outbound", "flying out", "on")

_ONE_WAY_RE = re.compile(r"\b(one[\s-]?way|single|no return|not coming back)\b")
_ROUND_TRIP_RE = re.compile(r"\b(round[\s-]?trip|return trip|there and back)\b")
_RESET_RE = re.compile(r"\b(start over|reset|new search|forget (that|it)|clear)\b")
_HELP_RE = re.compile(r"\b(help|what can you do|how does this work|who are you)\b")
_GREETING_RE = re.compile(r"^\s*(hi|hey|hello|yo|good (morning|afternoon|evening)|thanks|thank you)\b")

_CABINS = (
    (re.compile(r"\bpremium\s+economy\b"), "premium_economy"),
    (re.compile(r"\b(business|business\s+class)\b"), "business"),
    (re.compile(r"\bfirst\s+class\b"), "first"),
    (re.compile(r"\b(economy|coach)\b"), "economy"),
)

_ADULTS_RE = re.compile(r"\b(\d{1,2})\s*(adults?|people|passengers?|of us|travellers?|travelers?|pax)\b")
_NIGHTS_RE = re.compile(r"\bfor\s+(\d{1,2})\s*(nights?|days?|weeks?)\b")

_CITY_PHRASE_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(p) for p in airports.CITY_PHRASES) + r")\b"
)
_CODE_AFTER_CUE_RE = re.compile(
    r"\b(?:from|to|into|via|for|leaving|departing|depart|out of)\s+([a-z]{3})\b"
)


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    lowered = stripped.lower()
    cleaned = re.sub(r"[^a-z0-9/\-,: ]+", " ", lowered)
    return re.sub(r"[ ]+", " ", cleaned)


@dataclass
class DateHit:
    value: date
    start: int
    end: int
    role: str = "unknown"  # "depart" | "return" | "unknown"


@dataclass
class PlaceHit:
    code: str
    start: int
    end: int
    role: str = "unknown"  # "origin" | "destination" | "unknown"
    text: str = ""


@dataclass
class Parsed:
    """Everything one message contributed. Absent fields stay ``None``."""

    origin: str | None = None
    destination: str | None = None
    depart_date: date | None = None
    return_date: date | None = None
    nights: int | None = None
    airline: str | None = None
    airline_label: str | None = None
    cabin: str | None = None
    adults: int | None = None
    one_way: bool | None = None
    intent: str = "search"
    places: list[PlaceHit] = field(default_factory=list)
    dates: list[DateHit] = field(default_factory=list)

    @property
    def found_anything(self) -> bool:
        return any(
            value is not None
            for value in (
                self.origin,
                self.destination,
                self.depart_date,
                self.return_date,
                self.nights,
                self.airline,
                self.cabin,
                self.adults,
                self.one_way,
            )
        )


# --------------------------------------------------------------------------- #
# dates
# --------------------------------------------------------------------------- #
def _resolve_year(month: int, day: int, today: date, year: int | None) -> date | None:
    if year is not None:
        if year < 100:
            year += 2000
        try:
            return date(year, month, day)
        except ValueError:
            return None
    for candidate_year in (today.year, today.year + 1, today.year + 2):
        try:
            candidate = date(candidate_year, month, day)
        except ValueError:
            continue
        if candidate >= today:
            return candidate
    return None


def _find_dates(text: str, today: date) -> list[DateHit]:
    hits: list[DateHit] = []
    taken: list[tuple[int, int]] = []

    def claim(start: int, end: int) -> bool:
        for s, e in taken:
            if start < e and end > s:
                return False
        taken.append((start, end))
        return True

    for match in re.finditer(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", text):
        try:
            value = date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            continue
        if claim(*match.span()):
            hits.append(DateHit(value, *match.span()))

    month_names = "|".join(sorted(_MONTHS, key=len, reverse=True))
    pattern_md = re.compile(
        rf"\b({month_names})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:,?\s*(\d{{4}}))?\b"
    )
    for match in pattern_md.finditer(text):
        value = _resolve_year(
            _MONTHS[match.group(1)],
            int(match.group(2)),
            today,
            int(match.group(3)) if match.group(3) else None,
        )
        if value and claim(*match.span()):
            hits.append(DateHit(value, *match.span()))

    pattern_dm = re.compile(
        rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?({month_names})\.?(?:,?\s*(\d{{4}}))?\b"
    )
    for match in pattern_dm.finditer(text):
        value = _resolve_year(
            _MONTHS[match.group(2)],
            int(match.group(1)),
            today,
            int(match.group(3)) if match.group(3) else None,
        )
        if value and claim(*match.span()):
            hits.append(DateHit(value, *match.span()))

    for match in re.finditer(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", text):
        value = _resolve_year(
            int(match.group(1)),
            int(match.group(2)),
            today,
            int(match.group(3)) if match.group(3) else None,
        )
        if value and claim(*match.span()):
            hits.append(DateHit(value, *match.span()))

    for match in re.finditer(r"\b(today|tonight|tomorrow|day after tomorrow)\b", text):
        offset = {"today": 0, "tonight": 0, "tomorrow": 1, "day after tomorrow": 2}[match.group(1)]
        if claim(*match.span()):
            hits.append(DateHit(today + timedelta(days=offset), *match.span()))

    for match in re.finditer(r"\bin\s+(\d{1,3})\s*(day|days|week|weeks|month|months)\b", text):
        count = int(match.group(1))
        unit = match.group(2)
        days = count if unit.startswith("day") else count * 7 if unit.startswith("week") else count * 30
        if claim(*match.span()):
            hits.append(DateHit(today + timedelta(days=days), *match.span()))

    for match in re.finditer(r"\bnext\s+(week|month|year)\b", text):
        unit = match.group(1)
        days = {"week": 7, "month": 30, "year": 365}[unit]
        if claim(*match.span()):
            hits.append(DateHit(today + timedelta(days=days), *match.span()))

    weekday_names = "|".join(sorted(_WEEKDAYS, key=len, reverse=True))
    for match in re.finditer(rf"\b(next|this|coming)?\s*({weekday_names})\b", text):
        target = _WEEKDAYS[match.group(2)]
        ahead = (target - today.weekday()) % 7
        if ahead == 0:
            ahead = 7
        if match.group(1) == "next" and ahead < 7:
            ahead += 7
        if claim(*match.span()):
            hits.append(DateHit(today + timedelta(days=ahead), *match.span()))

    hits.sort(key=lambda hit: hit.start)
    return hits


def _label_dates(text: str, hits: list[DateHit]) -> None:
    for index, hit in enumerate(hits):
        window = text[max(0, hit.start - 24) : hit.start]
        if any(cue in window for cue in _RETURN_CUES):
            hit.role = "return"
        elif any(re.search(rf"\b{re.escape(cue)}\b", window) for cue in _DEPART_CUES):
            hit.role = "depart"
        elif index == 0:
            hit.role = "depart"
        elif index == 1:
            hit.role = "return"


# --------------------------------------------------------------------------- #
# places
# --------------------------------------------------------------------------- #
def _find_places(original: str, folded: str) -> list[PlaceHit]:
    hits: list[PlaceHit] = []
    taken: list[tuple[int, int]] = []

    def claim(start: int, end: int) -> bool:
        for s, e in taken:
            if start < e and end > s:
                return False
        taken.append((start, end))
        return True

    # 1. Explicit uppercase airport codes in what the user actually typed.
    for match in re.finditer(r"\b([A-Z]{3})\b", original):
        code = match.group(1)
        if not airports.is_known(code):
            continue
        span = _span_in_folded(original, folded, match.span())
        if span and claim(*span):
            hits.append(PlaceHit(code, span[0], span[1], text=code))

    # 2. Lower-case codes, but only right after a directional cue, so ordinary
    #    words like "can", "per" or "sin" are not mistaken for airports.
    for match in _CODE_AFTER_CUE_RE.finditer(folded):
        code = match.group(1).upper()
        if not airports.is_known(code):
            continue
        span = match.span(1)
        if claim(*span):
            hits.append(PlaceHit(code, span[0], span[1], text=match.group(1)))

    # 3. City and country phrases.
    for match in _CITY_PHRASE_RE.finditer(folded):
        phrase = match.group(0)
        code = airports.resolve(phrase)
        if not code:
            continue
        if claim(*match.span()):
            hits.append(PlaceHit(code, match.start(), match.end(), text=phrase))

    hits.sort(key=lambda hit: hit.start)
    return hits


def _span_in_folded(original: str, folded: str, span: tuple[int, int]) -> tuple[int, int] | None:
    """Best-effort mapping of a span in the original text onto the folded text."""
    needle = _fold(original[span[0] : span[1]]).strip()
    if not needle:
        return None
    approx = folded.find(needle, max(0, span[0] - 6))
    if approx == -1:
        approx = folded.find(needle)
    if approx == -1:
        return None
    return (approx, approx + len(needle))


def _label_places(folded: str, hits: list[PlaceHit]) -> None:
    for hit in hits:
        window = folded[max(0, hit.start - 18) : hit.start]
        origin_at = max(
            (window.rfind(cue) for cue in _ORIGIN_CUES if cue in window), default=-1
        )
        dest_at = max(
            (window.rfind(cue) for cue in _DESTINATION_CUES if cue in window), default=-1
        )
        if origin_at == -1 and dest_at == -1:
            continue
        hit.role = "origin" if origin_at > dest_at else "destination"


def _assign_roles(hits: list[PlaceHit]) -> tuple[str | None, str | None]:
    origin = next((h.code for h in hits if h.role == "origin"), None)
    destination = next((h.code for h in hits if h.role == "destination"), None)
    for hit in hits:
        if hit.role != "unknown":
            continue
        if origin is None and destination is not None:
            origin = hit.code
        elif destination is None and origin is not None:
            destination = hit.code
        elif origin is None and destination is None:
            origin = hit.code
    return origin, destination


# --------------------------------------------------------------------------- #
# airline
# --------------------------------------------------------------------------- #
def _find_airline(original: str, folded: str) -> tuple[str | None, str | None]:
    for airline in sorted(airlines.AIRLINES.values(), key=lambda a: -len(a.name)):
        needle = _fold(airline.name).strip()
        if needle and re.search(rf"\b{re.escape(needle)}\b", folded):
            return airline.code, airline.name
    match = re.search(r"\b(?:on|with|via|flying|fly)\s+([A-Z0-9]{2})\b", original)
    if match and airlines.get(match.group(1)):
        code = match.group(1).upper()
        return code, airlines.display_name(code)
    match = re.search(r"\b(?:on|with|via)\s+([a-z][a-z .&'-]{2,28}?)\s*(?:airlines?|airways|air)\b", folded)
    if match:
        resolved = airlines.resolve(match.group(0))
        if resolved:
            return resolved, airlines.display_name(resolved)
        label = match.group(0)
        label = re.sub(r"^(on|with|via)\s+", "", label).strip()
        return None, label.title()
    return None, None


# --------------------------------------------------------------------------- #
# entry point
# --------------------------------------------------------------------------- #
def parse(message: str, *, today: date) -> Parsed:
    original = (message or "").strip()
    folded = _fold(original)
    result = Parsed()

    if not folded:
        result.intent = "empty"
        return result
    if _RESET_RE.search(folded):
        result.intent = "reset"
        return result
    if _HELP_RE.search(folded):
        result.intent = "help"
        return result

    if _ONE_WAY_RE.search(folded):
        result.one_way = True
    elif _ROUND_TRIP_RE.search(folded):
        result.one_way = False

    for pattern, cabin in _CABINS:
        if pattern.search(folded):
            result.cabin = cabin
            break

    adults_match = _ADULTS_RE.search(folded)
    if adults_match:
        result.adults = max(1, min(9, int(adults_match.group(1))))

    nights_match = _NIGHTS_RE.search(folded)
    if nights_match:
        count = int(nights_match.group(1))
        unit = nights_match.group(2)
        result.nights = count * 7 if unit.startswith("week") else count

    code, label = _find_airline(original, folded)
    result.airline = code
    result.airline_label = label

    dates = _find_dates(folded, today)
    _label_dates(folded, dates)
    result.dates = dates
    for hit in dates:
        if hit.role == "return" and result.return_date is None:
            result.return_date = hit.value
        elif hit.role == "depart" and result.depart_date is None:
            result.depart_date = hit.value
    unassigned = [h for h in dates if h.role == "unknown"]
    for hit in unassigned:
        if result.depart_date is None:
            result.depart_date = hit.value
        elif result.return_date is None:
            result.return_date = hit.value

    if (
        result.depart_date
        and result.return_date
        and result.return_date < result.depart_date
    ):
        result.depart_date, result.return_date = result.return_date, result.depart_date

    places = _find_places(original, folded)
    _label_places(folded, places)
    result.places = places
    result.origin, result.destination = _assign_roles(places)

    if _GREETING_RE.match(folded) and not result.found_anything:
        result.intent = "greeting"
    elif not result.found_anything:
        result.intent = "unparsed"
    return result
