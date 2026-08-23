"""Observed-fare history in SQLite, following the site's "stdlib only" rule.

One row per offer Roma has ever seen for a route+date. The recommendation engine reads
aggregates from here, and deliberately treats *distinct observation days* — not row
count — as the measure of how much history exists, because a single search returning
eight offers is one look at the market, not eight.
"""

from __future__ import annotations

import datetime as dt
import sqlite3
import threading
from pathlib import Path

from .models import FareOffer, SearchQuery

SCHEMA = """
CREATE TABLE IF NOT EXISTS fare_observations (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    origin        TEXT    NOT NULL,
    destination   TEXT    NOT NULL,
    depart_date   TEXT    NOT NULL,
    return_date   TEXT,
    cabin         TEXT    NOT NULL,
    passengers    INTEGER NOT NULL,
    airline       TEXT,
    price         REAL    NOT NULL,
    currency      TEXT    NOT NULL,
    source        TEXT    NOT NULL,
    simulated     INTEGER NOT NULL,
    observed_at   TEXT    NOT NULL,
    observed_day  TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_fare_route
    ON fare_observations (origin, destination, depart_date, cabin);
CREATE INDEX IF NOT EXISTS idx_fare_observed_day
    ON fare_observations (observed_day);
"""


class PriceHistory:
    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=5.0)
        conn.row_factory = sqlite3.Row
        return conn

    def record(self, query: SearchQuery, offers: list[FareOffer]) -> int:
        """Persist every offer from one search. Returns rows written."""
        if not offers:
            return 0
        rows = [
            (
                offer.origin, offer.destination, offer.depart_date, offer.return_date,
                offer.cabin, query.passengers, offer.airline, float(offer.price),
                offer.currency, offer.source, 1 if offer.simulated else 0,
                offer.retrieved_at, offer.retrieved_at[:10],
            )
            for offer in offers
        ]
        with self._lock, self._connect() as conn:
            conn.executemany(
                "INSERT INTO fare_observations (origin, destination, depart_date, return_date,"
                " cabin, passengers, airline, price, currency, source, simulated, observed_at,"
                " observed_day) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                rows,
            )
        return len(rows)

    def stats(self, query: SearchQuery) -> dict:
        """Aggregate history for this route+date+cabin, normalized per passenger.

        ``observation_days`` is the honest sample size: how many separate days Roma has
        looked at this route. ``daily_low`` is the cheapest fare seen on each of those
        days, which is what a traveller actually could have paid.
        """
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT observed_day, MIN(price / MAX(passengers, 1)) AS low,"
                " MAX(simulated) AS any_simulated, MAX(observed_at) AS last_seen"
                " FROM fare_observations"
                " WHERE origin = ? AND destination = ? AND depart_date = ? AND cabin = ?"
                " GROUP BY observed_day ORDER BY observed_day",
                (query.origin, query.destination, query.depart_date, query.cabin),
            ).fetchall()

        daily_low = [(row["observed_day"], round(float(row["low"]), 2)) for row in rows]
        prices = [price for _, price in daily_low]
        stats = {
            "observation_days": len(daily_low),
            "total_observations": 0,
            "daily_low": daily_low,
            "min": min(prices) if prices else None,
            "max": max(prices) if prices else None,
            "median": _median(prices) if prices else None,
            "first_day": daily_low[0][0] if daily_low else None,
            "last_day": daily_low[-1][0] if daily_low else None,
            "any_simulated": any(bool(row["any_simulated"]) for row in rows),
            "last_seen": max((row["last_seen"] for row in rows), default=None),
            "stale_days": None,
            "trend": None,
        }

        with self._lock, self._connect() as conn:
            stats["total_observations"] = conn.execute(
                "SELECT COUNT(*) FROM fare_observations"
                " WHERE origin = ? AND destination = ? AND depart_date = ? AND cabin = ?",
                (query.origin, query.destination, query.depart_date, query.cabin),
            ).fetchone()[0]

        if stats["last_day"]:
            try:
                stats["stale_days"] = (dt.date.today() - dt.date.fromisoformat(stats["last_day"])).days
            except ValueError:
                stats["stale_days"] = None

        if len(prices) >= 4:
            half = len(prices) // 2
            earlier = _mean(prices[:half])
            later = _mean(prices[half:])
            if earlier:
                change = (later - earlier) / earlier
                if change > 0.04:
                    stats["trend"] = "rising"
                elif change < -0.04:
                    stats["trend"] = "falling"
                else:
                    stats["trend"] = "flat"
        return stats

    def percentile_of(self, price: float, stats: dict) -> float | None:
        """Where `price` sits in the observed daily lows, or None when the sample is
        too small to quote a percentile honestly (fewer than 5 observation days)."""
        prices = [p for _, p in stats.get("daily_low", [])]
        if len(prices) < 5:
            return None
        at_or_below = sum(1 for p in prices if p <= price)
        return round(100.0 * at_or_below / len(prices), 1)

    def route_count(self) -> int:
        with self._lock, self._connect() as conn:
            return conn.execute(
                "SELECT COUNT(DISTINCT origin || destination || depart_date) FROM fare_observations"
            ).fetchone()[0]


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return round(ordered[mid], 2)
    return round((ordered[mid - 1] + ordered[mid]) / 2, 2)


def _mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 2) if values else 0.0
