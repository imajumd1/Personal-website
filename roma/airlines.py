"""Airline table for the form dropdown, intent matching, and simulated fares.

`region` is used only by the simulated provider to decide which carriers plausibly
serve a route; it is a rough heuristic, not route authority.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Airline:
    code: str
    name: str
    region: str
    aliases: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"code": self.code, "name": self.name}


_ROWS = [
    ("AA", "American Airlines", "americas", ("american",)),
    ("DL", "Delta Air Lines", "americas", ("delta",)),
    ("UA", "United Airlines", "americas", ("united",)),
    ("AS", "Alaska Airlines", "americas", ("alaska",)),
    ("B6", "JetBlue", "americas", ("jet blue",)),
    ("WN", "Southwest Airlines", "domestic", ("southwest",)),
    ("AC", "Air Canada", "americas", ()),
    ("AM", "Aeromexico", "americas", ()),
    ("LA", "LATAM Airlines", "americas", ("latam",)),
    ("BA", "British Airways", "europe", ("british",)),
    ("VS", "Virgin Atlantic", "europe", ("virgin",)),
    ("AF", "Air France", "europe", ()),
    ("KL", "KLM", "europe", ("klm royal dutch",)),
    ("LH", "Lufthansa", "europe", ()),
    ("IB", "Iberia", "europe", ()),
    ("AZ", "ITA Airways", "europe", ("ita", "alitalia")),
    ("LX", "SWISS", "europe", ("swiss air",)),
    ("SK", "SAS", "europe", ("scandinavian",)),
    ("TP", "TAP Air Portugal", "europe", ("tap",)),
    ("TK", "Turkish Airlines", "europe", ("turkish",)),
    ("EI", "Aer Lingus", "europe", ()),
    ("FI", "Icelandair", "europe", ()),
    ("EK", "Emirates", "middle-east", ()),
    ("QR", "Qatar Airways", "middle-east", ("qatar",)),
    ("EY", "Etihad Airways", "middle-east", ("etihad",)),
    ("SV", "Saudia", "middle-east", ()),
    ("AI", "Air India", "asia", ()),
    ("SQ", "Singapore Airlines", "asia", ("singapore air",)),
    ("CX", "Cathay Pacific", "asia", ("cathay",)),
    ("NH", "ANA", "asia", ("all nippon",)),
    ("JL", "Japan Airlines", "asia", ("jal",)),
    ("KE", "Korean Air", "asia", ("korean",)),
    ("OZ", "Asiana Airlines", "asia", ("asiana",)),
    ("TG", "Thai Airways", "asia", ("thai",)),
    ("MH", "Malaysia Airlines", "asia", ()),
    ("VN", "Vietnam Airlines", "asia", ()),
    ("QF", "Qantas", "oceania", ()),
    ("NZ", "Air New Zealand", "oceania", ()),
    ("SA", "South African Airways", "africa", ()),
    ("ET", "Ethiopian Airlines", "africa", ("ethiopian",)),
    ("KQ", "Kenya Airways", "africa", ()),
]

AIRLINES: dict[str, Airline] = {r[0]: Airline(r[0], r[1], r[2], r[3]) for r in _ROWS}

OTHER_OPTION = "OTHER"


def all_airlines() -> list[Airline]:
    return sorted(AIRLINES.values(), key=lambda a: a.name)


def lookup_airline(text: str) -> Airline | None:
    raw = str(text or "").strip()
    if not raw:
        return None
    if raw.upper() in AIRLINES:
        return AIRLINES[raw.upper()]
    key = re.sub(r"[^a-z0-9 ]+", " ", raw.lower()).strip()
    key = re.sub(r"\s+(airlines?|airways|air lines)$", "", key).strip()
    for airline in AIRLINES.values():
        name = airline.name.lower()
        short = re.sub(r"\s+(airlines?|airways|air lines)$", "", name).strip()
        if key in (name, short) or key in airline.aliases:
            return airline
    return None


def find_airline_in_text(text: str) -> Airline | None:
    """Longest-name-first scan so "British Airways" wins over "British"."""
    haystack = " " + re.sub(r"[^a-z0-9 ]+", " ", str(text or "").lower()) + " "
    candidates: list[tuple[int, Airline]] = []
    for airline in AIRLINES.values():
        names = [airline.name.lower(), *airline.aliases]
        for name in names:
            if f" {name} " in haystack:
                candidates.append((len(name), airline))
    if not candidates:
        return None
    return max(candidates, key=lambda pair: pair[0])[1]
