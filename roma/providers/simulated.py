"""Deterministic synthetic fares so Roma runs with zero credentials.

Nothing here touches a network or a real market. Prices come from great-circle
distance, cabin, advance-purchase window, seasonality, and a per-airline factor,
seeded so the same query always returns the same quotes. Every offer it returns is
flagged ``simulated=True``, which the API, the UI badge, and the confidence cap in
the recommendation engine all key off.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import random

from ..airlines import AIRLINES, Airline, lookup_airline
from ..airports import distance_km, lookup_airport
from ..models import FareOffer, SearchQuery, parse_iso_date
from .base import FareProvider

CABIN_MULTIPLIER = {"economy": 1.0, "premium_economy": 1.95, "business": 4.3, "first": 7.5}

REGION_BY_COUNTRY = {
    "United States": "americas", "Canada": "americas", "Mexico": "americas",
    "Brazil": "americas", "Argentina": "americas", "Chile": "americas",
    "Peru": "americas", "Colombia": "americas", "Panama": "americas",
    "United Kingdom": "europe", "Ireland": "europe", "France": "europe",
    "Netherlands": "europe", "Belgium": "europe", "Germany": "europe",
    "Switzerland": "europe", "Austria": "europe", "Denmark": "europe",
    "Sweden": "europe", "Norway": "europe", "Finland": "europe", "Spain": "europe",
    "Portugal": "europe", "Italy": "europe", "Greece": "europe", "Turkey": "europe",
    "Czechia": "europe", "Poland": "europe", "Hungary": "europe", "Iceland": "europe",
    "United Arab Emirates": "middle-east", "Qatar": "middle-east", "Israel": "middle-east",
    "Egypt": "africa", "South Africa": "africa", "Kenya": "africa", "Nigeria": "africa",
    "India": "asia", "Nepal": "asia", "Sri Lanka": "asia", "Singapore": "asia",
    "Thailand": "asia", "Malaysia": "asia", "Indonesia": "asia", "Philippines": "asia",
    "Vietnam": "asia", "Hong Kong": "asia", "Taiwan": "asia", "China": "asia",
    "South Korea": "asia", "Japan": "asia",
    "Australia": "oceania", "New Zealand": "oceania", "Fiji": "oceania",
}

# Rough demand shape by departure month (1-indexed), northern-hemisphere leisure travel.
MONTH_FACTOR = [1.0, 0.90, 0.92, 0.97, 1.00, 1.04, 1.12, 1.14, 1.02, 0.96, 0.98, 1.10, 1.16]


class SimulatedProvider(FareProvider):
    name = "simulated"
    label = "Roma simulated market"
    simulated = True

    def available(self) -> bool:
        return True

    def search(self, query: SearchQuery) -> list[FareOffer]:
        origin = lookup_airport(query.origin)
        destination = lookup_airport(query.destination)
        if not origin or not destination:
            return []

        km = max(200.0, distance_km(origin, destination))
        rng = random.Random(_seed(query))
        retrieved_at = self.now_iso()

        carriers = self._carriers(origin.country, destination.country, km)
        requested = lookup_airline(query.airline) if query.airline else None
        if requested:
            carriers = [requested] + [c for c in carriers if c.code != requested.code]

        offers: list[FareOffer] = []
        for index, airline in enumerate(carriers[:7]):
            for variant in range(2 if index < 3 else 1):
                offers.append(self._offer(query, origin, destination, km, airline, variant, rng, retrieved_at))

        if requested:
            offers = [o for o in offers if o.airline == requested.code] or offers

        offers.sort(key=lambda o: o.price)
        return offers[:8]

    # -- internals ----------------------------------------------------------

    def _carriers(self, origin_country: str, destination_country: str, km: float) -> list[Airline]:
        origin_region = REGION_BY_COUNTRY.get(origin_country, "americas")
        destination_region = REGION_BY_COUNTRY.get(destination_country, "americas")
        wanted = {origin_region, destination_region}
        if origin_region != destination_region and km > 6000:
            wanted.add("middle-east")
        if origin_country == destination_country == "United States":
            wanted.add("domestic")
        pool = [a for a in AIRLINES.values() if a.region in wanted]
        pool.sort(key=lambda a: a.code)
        return pool

    def _offer(
        self,
        query: SearchQuery,
        origin,
        destination,
        km: float,
        airline: Airline,
        variant: int,
        rng: random.Random,
        retrieved_at: str,
    ) -> FareOffer:
        depart = parse_iso_date(query.depart_date) or dt.date.today()
        days_ahead = max(0, (depart - dt.date.today()).days)

        base = _distance_base(km)
        if not query.return_date:
            base *= 0.62

        price = base
        price *= CABIN_MULTIPLIER.get(query.cabin, 1.0)
        price *= _advance_factor(days_ahead)
        price *= MONTH_FACTOR[depart.month]
        price *= 1.06 if depart.weekday() in (4, 6) else 1.0
        price *= _airline_factor(airline.code, query.origin, query.destination)

        long_haul = km > 4200
        stops = 0
        if long_haul and variant == 1:
            stops = 1
        elif long_haul and airline.region not in (
            REGION_BY_COUNTRY.get(origin.country), REGION_BY_COUNTRY.get(destination.country)
        ):
            stops = 1
        elif not long_haul and variant == 1:
            stops = 1
        if stops:
            price *= 0.86

        price *= 1.0 + rng.uniform(-0.045, 0.055)
        price = round(price * query.passengers, 2)

        cruise_minutes = int(km / 13.6) + 35
        duration = cruise_minutes + (95 + int(rng.uniform(0, 70)) if stops else 0)
        depart_hour = (6 + (hash(airline.code + str(variant)) % 15)) % 24
        depart_minutes = depart_hour * 60 + (15 * (variant + hash(airline.code) % 4)) % 60
        arrive_minutes = depart_minutes + duration

        return FareOffer(
            price=price,
            currency="USD",
            airline=airline.code,
            airline_name=airline.name,
            origin=query.origin,
            destination=query.destination,
            depart_date=query.depart_date,
            return_date=query.return_date,
            cabin=query.cabin,
            stops=stops,
            duration_minutes=duration,
            depart_time=_clock(depart_minutes),
            arrive_time=_clock(arrive_minutes),
            source=self.name,
            simulated=True,
            retrieved_at=retrieved_at,
            fare_basis=f"SIM-{airline.code}{'X' if stops else 'N'}{query.cabin[:3].upper()}",
        )


def _distance_base(km: float) -> float:
    """Round-trip economy anchor price for a distance, in USD."""
    if km <= 1200:
        return 70 + km * 0.11
    if km <= 5000:
        return 202 + (km - 1200) * 0.055
    return 411 + (km - 5000) * 0.035


def _advance_factor(days_ahead: int) -> float:
    if days_ahead <= 3:
        return 1.62
    if days_ahead <= 6:
        return 1.48
    if days_ahead <= 13:
        return 1.33
    if days_ahead <= 20:
        return 1.17
    if days_ahead <= 59:
        return 1.0
    if days_ahead <= 119:
        return 0.95
    return 1.04


def _airline_factor(code: str, origin: str, destination: str) -> float:
    digest = hashlib.sha256(f"{code}|{origin}|{destination}".encode()).digest()
    return 0.88 + (digest[0] / 255.0) * 0.30


def _seed(query: SearchQuery) -> int:
    key = "|".join([
        query.origin, query.destination, query.depart_date, query.return_date or "-",
        query.cabin, str(query.passengers), query.airline or "-",
    ])
    return int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "big")


def _clock(minutes: int) -> str:
    minutes %= 24 * 60
    return f"{minutes // 60:02d}:{minutes % 60:02d}"
