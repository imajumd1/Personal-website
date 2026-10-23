"""SQLite price history.

Two kinds of row live in the same table and are always distinguishable:

``observed``
    A price Roma actually produced for a search someone ran, recorded at the
    time it ran.
``modeled``
    A backfilled point: Roma's fare model evaluated as of an earlier date, so a
    brand-new route still has a trend line to reason about. These are clearly
    reported as modelled rather than observed everywhere they are used.

The database file is local state and is not committed.
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from statistics import median

from .models import SearchRequest

BACKFILL_DAYS = 45
MIN_POINTS_FOR_TREND = 5

_SCHEMA = """
CREATE TABLE IF NOT EXISTS price_points (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    route         TEXT    NOT NULL,
    origin        TEXT    NOT NULL,
    destination   TEXT    NOT NULL,
    depart_date   TEXT    NOT NULL,
    return_date   TEXT,
    airline       TEXT,
    cabin         TEXT    NOT NULL,
    adults        INTEGER NOT NULL DEFAULT 1,
    price         REAL    NOT NULL,
    currency      TEXT    NOT NULL,
    provider      TEXT    NOT NULL,
    data_level    TEXT    NOT NULL,
    point_kind    TEXT    NOT NULL,
    quoted_on     TEXT    NOT NULL,
    recorded_at   TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_price_points_query
    ON price_points (route, cabin, depart_date, quoted_on);
CREATE TABLE IF NOT EXISTS backfills (
    query_key  TEXT PRIMARY KEY,
    created_at TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class PriceHistory:
    """Thin, thread-safe-by-connection-per-call wrapper over one SQLite file."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    # -- writing ------------------------------------------------------------
    def record(
        self,
        request: SearchRequest,
        *,
        price: float,
        currency: str,
        provider: str,
        data_level: str,
        point_kind: str,
        quoted_on: date,
    ) -> None:
        with self._connect() as conn:
            # One point per query per day. Searching the same thing five times
            # in a minute must not move the median.
            conn.execute(
                """
                DELETE FROM price_points
                 WHERE route = ? AND depart_date = ? AND IFNULL(return_date,'') = ?
                   AND cabin = ? AND IFNULL(airline,'') = ? AND adults = ?
                   AND quoted_on = ? AND point_kind = ?
                """,
                (
                    request.route,
                    request.depart_date.isoformat(),
                    request.return_date.isoformat() if request.return_date else "",
                    request.cabin,
                    request.airline_key,
                    request.adults,
                    quoted_on.isoformat(),
                    point_kind,
                ),
            )
            conn.execute(
                """
                INSERT INTO price_points (
                    route, origin, destination, depart_date, return_date, airline,
                    cabin, adults, price, currency, provider, data_level,
                    point_kind, quoted_on, recorded_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    request.route,
                    request.origin,
                    request.destination,
                    request.depart_date.isoformat(),
                    request.return_date.isoformat() if request.return_date else None,
                    request.airline_key,
                    request.cabin,
                    request.adults,
                    float(price),
                    currency,
                    provider,
                    data_level,
                    point_kind,
                    quoted_on.isoformat(),
                    _now(),
                ),
            )

    def ensure_backfill(
        self,
        request: SearchRequest,
        *,
        today: date,
        currency: str,
        price_fn,
        days: int = BACKFILL_DAYS,
    ) -> int:
        """Fill in a modelled trail for a query Roma has not seen before.

        ``price_fn(as_of)`` must return the price the model would have quoted on
        that date. Returns the number of rows inserted.
        """
        key = request.cache_key()
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT 1 FROM backfills WHERE query_key = ?", (key,)
            ).fetchone()
            if existing:
                return 0
            rows = []
            for offset in range(days, 0, -1):
                as_of = today - timedelta(days=offset)
                if as_of >= request.depart_date:
                    continue
                rows.append(
                    (
                        request.route,
                        request.origin,
                        request.destination,
                        request.depart_date.isoformat(),
                        request.return_date.isoformat() if request.return_date else None,
                        request.airline_key,
                        request.cabin,
                        request.adults,
                        float(price_fn(as_of)),
                        currency,
                        "simulated",
                        "simulated",
                        "modeled",
                        as_of.isoformat(),
                        _now(),
                    )
                )
            if rows:
                conn.executemany(
                    """
                    INSERT INTO price_points (
                        route, origin, destination, depart_date, return_date, airline,
                        cabin, adults, price, currency, provider, data_level,
                        point_kind, quoted_on, recorded_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    rows,
                )
            conn.execute(
                "INSERT OR REPLACE INTO backfills (query_key, created_at) VALUES (?, ?)",
                (key, _now()),
            )
            return len(rows)

    # -- reading ------------------------------------------------------------
    def stats(self, request: SearchRequest) -> dict:
        """Summary statistics for the exact query, newest point last."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT price, quoted_on, point_kind, data_level
                  FROM price_points
                 WHERE route = ?
                   AND depart_date = ?
                   AND IFNULL(return_date,'') = ?
                   AND cabin = ?
                   AND IFNULL(airline,'') = ?
                   AND adults = ?
                 ORDER BY quoted_on ASC, id ASC
                """,
                (
                    request.route,
                    request.depart_date.isoformat(),
                    request.return_date.isoformat() if request.return_date else "",
                    request.cabin,
                    request.airline_key,
                    request.adults,
                ),
            ).fetchall()

        prices = [float(r["price"]) for r in rows]
        if not prices:
            return {
                "points": 0,
                "observed_points": 0,
                "modeled_points": 0,
                "min": None,
                "max": None,
                "median": None,
                "first": None,
                "latest": None,
                "series": [],
                "window_days": 0,
                "has_trend": False,
            }
        observed = sum(1 for r in rows if r["point_kind"] == "observed")
        first_day = date.fromisoformat(rows[0]["quoted_on"])
        last_day = date.fromisoformat(rows[-1]["quoted_on"])
        return {
            "points": len(prices),
            "observed_points": observed,
            "modeled_points": len(prices) - observed,
            "min": round(min(prices), 2),
            "max": round(max(prices), 2),
            "median": round(median(prices), 2),
            "first": round(prices[0], 2),
            "latest": round(prices[-1], 2),
            "series": [
                {
                    "date": r["quoted_on"],
                    "price": round(float(r["price"]), 2),
                    "kind": r["point_kind"],
                }
                for r in rows
            ],
            "window_days": (last_day - first_day).days,
            "has_trend": len(prices) >= MIN_POINTS_FOR_TREND,
        }

    def route_totals(self) -> dict:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS points,
                       COUNT(DISTINCT route) AS routes,
                       SUM(CASE WHEN point_kind = 'observed' THEN 1 ELSE 0 END) AS observed
                  FROM price_points
                """
            ).fetchone()
        return {
            "points": int(row["points"] or 0),
            "routes": int(row["routes"] or 0),
            "observed": int(row["observed"] or 0),
        }
