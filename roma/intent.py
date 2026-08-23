"""Natural language → structured query.

Two implementations sit behind :class:`IntentParser`:

* :class:`HeuristicIntentParser` — regex and keyword rules, always available, the default.
* :class:`LLMIntentParser` — optional, selected by ``ROMA_LLM_PROVIDER``. Its output is
  never trusted directly: it is re-parsed into a :class:`PartialQuery` and must survive
  :func:`roma.models.validate` before anything acts on it, and it may only ever produce
  *query fields* — it is structurally incapable of returning a price or a verdict because
  those keys are dropped here.
"""

from __future__ import annotations

import datetime as dt
import re

from .airlines import find_airline_in_text, lookup_airline
from .airports import city_tokens, lookup_airport
from .dates import resolve_trip_dates
from .llm import LLMUnavailable, get_llm_client
from .models import PartialQuery, normalize_cabin

# Fields an intent parser is allowed to fill. Anything else an LLM returns is discarded.
ALLOWED_FIELDS = (
    "origin", "destination", "depart_date", "return_date",
    "passengers", "cabin", "airline",
)

CABIN_PATTERNS = [
    (r"\b(first class|first-class)\b", "first"),
    (r"\b(business class|business-class|business)\b", "business"),
    (r"\b(premium economy|premium-economy|premium)\b", "premium_economy"),
    (r"\b(economy|coach|cheap seats)\b", "economy"),
]

PASSENGER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "a couple": 2, "couple": 2,
}

_CITY_TOKENS = city_tokens()

# IATA codes that are also ordinary English words. Honoured after an explicit
# "from"/"to" marker, ignored when loosely scanning a sentence for place names.
AMBIGUOUS_CODES = {"MAN", "CAN", "PER", "BUD", "SEA", "MAD", "DEN", "SIN", "GIG", "DEL", "HEL"}


class IntentParser:
    name = "base"

    def parse(self, message: str, ref: dt.date | None = None) -> PartialQuery:
        raise NotImplementedError


class HeuristicIntentParser(IntentParser):
    """Keyword and regex extraction. No network, no model, fully deterministic."""

    name = "heuristic"

    def parse(self, message: str, ref: dt.date | None = None) -> PartialQuery:
        text = str(message or "")
        lowered = _clean(text)
        partial = PartialQuery(source="heuristic")

        origin, destination = self._places(lowered)
        partial.origin = origin
        partial.destination = destination

        dates = resolve_trip_dates(lowered, ref)
        partial.depart_date = dates["depart_date"]
        partial.return_date = dates["return_date"]
        if dates["depart_date"]:
            partial.date_precision = dates["date_precision"]
        partial.notes = list(dates["notes"])

        passengers = self._passengers(lowered)
        if passengers:
            partial.passengers = passengers

        for pattern, cabin in CABIN_PATTERNS:
            if re.search(pattern, lowered):
                partial.cabin = cabin
                break

        airline = self._airline(lowered)
        if airline:
            partial.airline = airline.code
            partial.airline_label = airline.name

        return partial

    # -- extraction helpers -------------------------------------------------

    def _places(self, text: str) -> tuple[str | None, str | None]:
        origin = destination = None

        pair = re.search(
            r"\b(?:from\s+)?([a-z]{3}|[a-z][a-z .'-]{2,24}?)\s+(?:to|->|→|-)\s+([a-z]{3}|[a-z][a-z .'-]{2,24}?)"
            r"(?=\s+(?:on|in|for|from|at|next|early|mid|late|this|around|departing|leaving|oct|nov|dec|jan|feb|mar|apr|may|jun|jul|aug|sep|\d)|[,.?!]|$)",
            text,
        )
        if pair:
            origin = _resolve_place(pair.group(1))
            destination = _resolve_place(pair.group(2))

        if not origin:
            origin = _first_place(r"\b(?:from|leaving(?:\s+from)?|departing(?:\s+from)?|out of)\s+([a-z][a-z .'-]{1,24})", text)
        if not destination:
            destination = _first_place(r"\b(?:to|into|toward|towards|visit(?:ing)?)\s+([a-z][a-z .'-]{1,24})", text, exclude=origin)

        # Bare mentions: "SFO LHR March 3" or "Tokyo in early March"
        if not (origin and destination):
            mentions = _city_mentions(text)
            codes = [c for c in mentions if c not in (origin, destination)]
            if origin and not destination and codes:
                destination = codes[0]
            elif destination and not origin and codes:
                origin = codes[0]
            elif not origin and not destination and len(codes) >= 2:
                origin, destination = codes[0], codes[1]
            elif not origin and not destination and len(codes) == 1:
                destination = codes[0]

        return origin, destination

    def _passengers(self, text: str) -> int | None:
        m = re.search(r"\b(\d{1,2})\s*(?:adults?|passengers?|people|persons?|pax|travel(?:l)?ers?|tickets?|seats?)\b", text)
        if m:
            return _clamp_passengers(int(m.group(1)))
        m = re.search(r"\b(one|two|three|four|five|six|seven|eight|nine)\s+(?:adults?|passengers?|people|persons?|of us|travel(?:l)?ers?|tickets?|seats?)\b", text)
        if m:
            return _clamp_passengers(PASSENGER_WORDS[m.group(1)])
        m = re.search(r"\b(?:for|get|take|book|fly)\s+(\d{1,2})\b(?!\s*(?:st|nd|rd|th|:|/|-))", text)
        if m and int(m.group(1)) <= 9 and not re.search(r"\b(?:for|get|take|book|fly)\s+\d{1,2}\s*(?:am|pm)", text):
            return _clamp_passengers(int(m.group(1)))
        if re.search(r"\b(just me|solo|myself|alone|one ticket|single traveller|single traveler)\b", text):
            return 1
        if re.search(r"\b(my (?:wife|husband|partner|spouse) and i|me and my (?:wife|husband|partner|spouse)|the two of us|two of us|both of us|couple of us)\b", text):
            return 2
        if re.search(r"\b(?:family of)\s+(\d{1,2})\b", text):
            return _clamp_passengers(int(re.search(r"\b(?:family of)\s+(\d{1,2})\b", text).group(1)))
        return None

    def _airline(self, text: str):
        m = re.search(r"\b(?:on|with|via|flying|prefer(?:ably)?)\s+([a-z][a-z ]{2,24})", text)
        if m:
            airline = lookup_airline(m.group(1).strip())
            if airline:
                return airline
        m = re.search(r"\b(?:on|with|via)\s+([A-Za-z]{2})\b", text)
        if m:
            airline = lookup_airline(m.group(1).upper())
            if airline:
                return airline
        return find_airline_in_text(text)


class LLMIntentParser(IntentParser):
    """Optional model-backed parser. Falls back to heuristics on any problem."""

    name = "llm"

    def __init__(self, client, fallback: IntentParser):
        self.client = client
        self.fallback = fallback
        self.name = f"llm:{client.provider}"

    def parse(self, message: str, ref: dt.date | None = None) -> PartialQuery:
        ref = ref or dt.date.today()
        try:
            raw = self.client.complete_json(
                system=(
                    "You extract flight search fields from a traveller's message. "
                    "Reply with JSON only. Keys: origin, destination, depart_date, return_date, "
                    "passengers, cabin, airline. Use IATA airport codes for origin/destination, "
                    "ISO YYYY-MM-DD for dates, an integer for passengers, one of "
                    "economy/premium_economy/business/first for cabin, and an airline name or IATA "
                    "code for airline. Omit anything the message does not state. "
                    "Never include prices, fares, recommendations, or commentary."
                    f" Today is {ref.isoformat()}."
                ),
                user=str(message or ""),
            )
        except LLMUnavailable:
            return self.fallback.parse(message, ref)

        partial = _partial_from_llm(raw)
        if partial is None or partial.is_empty():
            return self.fallback.parse(message, ref)

        # The model may see structure the heuristics missed, but it must not erase
        # what the heuristics found: heuristic values fill the gaps.
        heuristic = self.fallback.parse(message, ref)
        merged = heuristic.merge(partial)
        merged.source = self.name
        return merged


def _partial_from_llm(raw: dict) -> PartialQuery | None:
    """Re-derive a PartialQuery from model JSON, dropping every unexpected key."""
    if not isinstance(raw, dict):
        return None
    partial = PartialQuery(source="llm")
    for key in ALLOWED_FIELDS:
        value = raw.get(key)
        if value in (None, "", []):
            continue
        if key in ("origin", "destination"):
            airport = lookup_airport(str(value))
            if airport:
                setattr(partial, key, airport.code)
        elif key in ("depart_date", "return_date"):
            try:
                setattr(partial, key, dt.date.fromisoformat(str(value).strip()).isoformat())
            except ValueError:
                continue
        elif key == "passengers":
            try:
                partial.passengers = _clamp_passengers(int(value))
            except (TypeError, ValueError):
                continue
        elif key == "cabin":
            partial.cabin = normalize_cabin(value)
        elif key == "airline":
            airline = lookup_airline(str(value))
            if airline:
                partial.airline = airline.code
                partial.airline_label = airline.name
    return partial


def _clean(text: str) -> str:
    text = str(text or "").lower().replace("—", "-").replace("–", "-")
    text = re.sub(r"[“”\"']", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _clamp_passengers(value: int) -> int:
    return max(1, min(9, int(value)))


def _resolve_place(fragment: str) -> str | None:
    """Find the longest airport-resolvable phrase inside a captured fragment."""
    fragment = str(fragment or "").strip(" .,'-")
    if not fragment:
        return None
    words = [w for w in re.split(r"[\s]+", fragment) if w]
    for width in range(len(words), 0, -1):
        for start in range(0, len(words) - width + 1):
            airport = lookup_airport(" ".join(words[start:start + width]))
            if airport:
                return airport.code
    return None


def _first_place(pattern: str, text: str, exclude: str | None = None) -> str | None:
    """Try every match of `pattern`; return the first place that resolves."""
    for m in re.finditer(pattern, text):
        code = _resolve_place(m.group(1))
        if code and code != exclude:
            return code
    return None


def _city_mentions(text: str) -> list[str]:
    """Codes for city names / IATA codes mentioned, in order of appearance."""
    found: list[tuple[int, str]] = []
    padded = f" {text} "
    for phrase, code in _CITY_TOKENS:
        index = padded.find(f" {phrase} ")
        if index >= 0:
            found.append((index, code))
            # Mask the phrase so "San Francisco" cannot also register as SAN.
            padded = padded[:index + 1] + "#" * len(phrase) + padded[index + 1 + len(phrase):]
    for m in re.finditer(r"\b([a-z]{3})\b", padded):
        code = m.group(1).upper()
        if code in AMBIGUOUS_CODES:
            continue
        airport = lookup_airport(code)
        if airport:
            found.append((m.start(), airport.code))
    ordered: list[str] = []
    for _, code in sorted(found, key=lambda pair: pair[0]):
        if code not in ordered:
            ordered.append(code)
    return ordered


def get_intent_parser() -> IntentParser:
    """Heuristics unless an LLM provider is configured and usable."""
    heuristic = HeuristicIntentParser()
    client = get_llm_client()
    if client is None:
        return heuristic
    return LLMIntentParser(client, heuristic)
