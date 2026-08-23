"""Shared value objects and query validation for Roma.

Validation lives here rather than in the intent parser so that every path into the
engine — the structured form, the heuristic parser, and the optional LLM parser —
is checked by exactly the same code.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field, asdict
from typing import Any

from .airports import lookup_airport

CABINS = {
    "economy": "Economy",
    "premium_economy": "Premium economy",
    "business": "Business",
    "first": "First",
}

MAX_PASSENGERS = 9
MAX_DAYS_AHEAD = 365

REQUIRED_SLOTS = ("origin", "destination", "depart_date")


def today() -> dt.date:
    return dt.date.today()


def parse_iso_date(value: str) -> dt.date | None:
    try:
        return dt.date.fromisoformat(str(value).strip())
    except (TypeError, ValueError):
        return None


@dataclass
class SearchQuery:
    """A fully specified, validated flight search."""

    origin: str
    destination: str
    depart_date: str
    return_date: str | None = None
    passengers: int = 1
    cabin: str = "economy"
    airline: str | None = None
    airline_label: str | None = None
    date_precision: str = "exact"  # "exact" or "approximate" (e.g. "early March")

    @property
    def round_trip(self) -> bool:
        return bool(self.return_date)

    @property
    def days_ahead(self) -> int:
        depart = parse_iso_date(self.depart_date)
        return (depart - today()).days if depart else 0

    @property
    def trip_length(self) -> int | None:
        depart = parse_iso_date(self.depart_date)
        ret = parse_iso_date(self.return_date) if self.return_date else None
        if depart and ret:
            return (ret - depart).days
        return None

    def route_key(self) -> str:
        return f"{self.origin}-{self.destination}"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["round_trip"] = self.round_trip
        data["days_ahead"] = self.days_ahead
        data["cabin_label"] = CABINS.get(self.cabin, self.cabin)
        return data


@dataclass
class PartialQuery:
    """What a parser managed to extract. Any field may be missing."""

    origin: str | None = None
    destination: str | None = None
    depart_date: str | None = None
    return_date: str | None = None
    passengers: int | None = None
    cabin: str | None = None
    airline: str | None = None
    airline_label: str | None = None
    date_precision: str | None = None
    notes: list[str] = field(default_factory=list)
    source: str = "heuristic"

    def filled(self) -> dict[str, Any]:
        out = {}
        for key in (
            "origin", "destination", "depart_date", "return_date",
            "passengers", "cabin", "airline", "airline_label", "date_precision",
        ):
            value = getattr(self, key)
            if value not in (None, "", []):
                out[key] = value
        return out

    def missing_required(self) -> list[str]:
        return [slot for slot in REQUIRED_SLOTS if not getattr(self, slot)]

    def is_empty(self) -> bool:
        return not self.filled()

    def merge(self, other: "PartialQuery") -> "PartialQuery":
        """Return a copy of self with any fields set on `other` overriding."""
        merged = PartialQuery(**self.filled())
        for key, value in other.filled().items():
            setattr(merged, key, value)
        merged.notes = (list(self.notes) + list(other.notes))[-4:]
        merged.source = other.source or self.source
        return merged


@dataclass
class FareOffer:
    """One priced itinerary from one provider."""

    price: float
    currency: str
    airline: str
    airline_name: str
    origin: str
    destination: str
    depart_date: str
    return_date: str | None
    cabin: str
    stops: int
    duration_minutes: int
    depart_time: str
    arrive_time: str
    source: str
    simulated: bool
    retrieved_at: str
    fare_basis: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["price_total"] = round(self.price, 2)
        data["duration_label"] = f"{self.duration_minutes // 60}h {self.duration_minutes % 60:02d}m"
        data["stops_label"] = (
            "Nonstop" if self.stops == 0 else f"{self.stops} stop" + ("s" if self.stops > 1 else "")
        )
        return data


def normalize_cabin(value: Any) -> str:
    raw = str(value or "economy").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "coach": "economy",
        "eco": "economy",
        "econ": "economy",
        "premium": "premium_economy",
        "premium_econ": "premium_economy",
        "premiumeconomy": "premium_economy",
        "biz": "business",
        "business_class": "business",
        "first_class": "first",
    }
    raw = aliases.get(raw, raw)
    return raw if raw in CABINS else "economy"


def validate(partial: PartialQuery | dict[str, Any]) -> tuple[SearchQuery | None, dict[str, str]]:
    """Validate a partial/raw query into a :class:`SearchQuery`.

    Returns ``(query, field_errors)``. ``query`` is None when anything is wrong.
    This is the single gate every search passes through, including LLM-parsed input.
    """
    raw = partial.filled() if isinstance(partial, PartialQuery) else dict(partial or {})
    errors: dict[str, str] = {}

    origin_code = None
    destination_code = None

    for field_name in ("origin", "destination"):
        value = str(raw.get(field_name) or "").strip()
        if not value:
            errors[field_name] = "Required."
            continue
        airport = lookup_airport(value)
        if not airport:
            errors[field_name] = f"“{value}” is not an airport Roma recognizes. Try an IATA code such as SFO."
            continue
        if field_name == "origin":
            origin_code = airport.code
        else:
            destination_code = airport.code

    if origin_code and destination_code and origin_code == destination_code:
        errors["destination"] = "Origin and destination are the same airport."

    depart = parse_iso_date(raw.get("depart_date") or "")
    if not raw.get("depart_date"):
        errors["depart_date"] = "Required."
    elif not depart:
        errors["depart_date"] = "Use a date in YYYY-MM-DD form."
    elif depart < today():
        errors["depart_date"] = "That date is in the past."
    elif (depart - today()).days > MAX_DAYS_AHEAD:
        errors["depart_date"] = f"Roma only searches {MAX_DAYS_AHEAD} days ahead."

    return_iso = raw.get("return_date") or None
    ret = None
    if return_iso:
        ret = parse_iso_date(return_iso)
        if not ret:
            errors["return_date"] = "Use a date in YYYY-MM-DD form."
        elif depart and ret < depart:
            errors["return_date"] = "Return is before departure."
        elif ret < today():
            errors["return_date"] = "That date is in the past."

    passengers = raw.get("passengers") or 1
    try:
        passengers = int(passengers)
    except (TypeError, ValueError):
        passengers = 0
    if passengers < 1 or passengers > MAX_PASSENGERS:
        errors["passengers"] = f"Between 1 and {MAX_PASSENGERS} passengers."

    if errors:
        return None, errors

    airline = str(raw.get("airline") or "").strip() or None
    query = SearchQuery(
        origin=origin_code,
        destination=destination_code,
        depart_date=depart.isoformat(),
        return_date=ret.isoformat() if ret else None,
        passengers=passengers,
        cabin=normalize_cabin(raw.get("cabin")),
        airline=airline,
        airline_label=str(raw.get("airline_label") or "").strip() or airline,
        date_precision=raw.get("date_precision") or "exact",
    )
    return query, {}
