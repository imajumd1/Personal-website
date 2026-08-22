"""Shared value objects passed between the layers of the agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from . import airports

CABINS: tuple[str, ...] = ("economy", "premium_economy", "business", "first")

CABIN_LABELS: dict[str, str] = {
    "economy": "Economy",
    "premium_economy": "Premium economy",
    "business": "Business",
    "first": "First",
}


@dataclass
class SearchRequest:
    """One fully-specified flight question, however it was asked."""

    origin: str
    destination: str
    depart_date: date
    return_date: date | None = None
    airline: str | None = None
    airline_label: str | None = None
    cabin: str = "economy"
    adults: int = 1
    source: str = "form"

    @property
    def round_trip(self) -> bool:
        return self.return_date is not None

    @property
    def route(self) -> str:
        return f"{self.origin}-{self.destination}"

    @property
    def trip_nights(self) -> int | None:
        if self.return_date is None:
            return None
        return (self.return_date - self.depart_date).days

    def days_until_departure(self, today: date) -> int:
        return (self.depart_date - today).days

    def cache_key(self) -> str:
        parts = [
            self.origin,
            self.destination,
            self.depart_date.isoformat(),
            self.return_date.isoformat() if self.return_date else "oneway",
            (self.airline or "any").upper(),
            self.cabin,
            str(self.adults),
        ]
        return "|".join(parts)

    def describe(self) -> str:
        origin = airports.get(self.origin)
        destination = airports.get(self.destination)
        origin_label = origin.label if origin else self.origin
        destination_label = destination.label if destination else self.destination
        when = self.depart_date.isoformat()
        if self.return_date:
            return f"{origin_label} to {destination_label}, {when}, returning {self.return_date.isoformat()}"
        return f"{origin_label} to {destination_label}, {when}, one way"

    def to_dict(self) -> dict:
        return {
            "origin": self.origin,
            "destination": self.destination,
            "origin_label": (airports.get(self.origin).label if airports.get(self.origin) else self.origin),
            "destination_label": (
                airports.get(self.destination).label if airports.get(self.destination) else self.destination
            ),
            "depart_date": self.depart_date.isoformat(),
            "return_date": self.return_date.isoformat() if self.return_date else None,
            "round_trip": self.round_trip,
            "trip_nights": self.trip_nights,
            "airline": self.airline,
            "airline_label": self.airline_label,
            "cabin": self.cabin,
            "cabin_label": CABIN_LABELS.get(self.cabin, self.cabin),
            "adults": self.adults,
            "source": self.source,
        }


@dataclass
class ValidationError:
    field: str
    rule: str
    message: str

    def to_dict(self) -> dict:
        return {"field": self.field, "rule": self.rule, "message": self.message}


@dataclass
class FareOffer:
    """One priced itinerary option."""

    airline_code: str
    airline_name: str
    price: float
    currency: str
    stops: int
    outbound_duration_minutes: int
    return_duration_minutes: int | None
    fare_basis: str
    provider: str
    data_level: str
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "airline_code": self.airline_code,
            "airline_name": self.airline_name,
            "price": round(self.price, 2),
            "currency": self.currency,
            "stops": self.stops,
            "outbound_duration_minutes": self.outbound_duration_minutes,
            "return_duration_minutes": self.return_duration_minutes,
            "fare_basis": self.fare_basis,
            "provider": self.provider,
            "data_level": self.data_level,
            "notes": list(self.notes),
        }
