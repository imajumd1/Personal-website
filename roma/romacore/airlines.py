"""Airline reference data for the form's picker and the chat parser.

``price_index`` is a coarse positioning multiplier used only by the simulated
fare provider — low-cost carriers sit below 1.0, full-service premium carriers
above it. It is a modelling assumption, not a published figure.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# code, name, region, price_index, long_haul_capable
_ROWS: tuple[tuple[str, str, str, float, bool], ...] = (
    ("AA", "American Airlines", "North America", 1.00, True),
    ("AC", "Air Canada", "North America", 1.02, True),
    ("AS", "Alaska Airlines", "North America", 0.94, False),
    ("B6", "JetBlue", "North America", 0.90, True),
    ("DL", "Delta Air Lines", "North America", 1.04, True),
    ("F9", "Frontier Airlines", "North America", 0.68, False),
    ("NK", "Spirit Airlines", "North America", 0.66, False),
    ("UA", "United Airlines", "North America", 1.02, True),
    ("WN", "Southwest Airlines", "North America", 0.88, False),
    ("AV", "Avianca", "Latin America", 0.95, True),
    ("CM", "Copa Airlines", "Latin America", 0.96, True),
    ("LA", "LATAM Airlines", "Latin America", 0.98, True),
    ("AF", "Air France", "Europe", 1.08, True),
    ("AY", "Finnair", "Europe", 1.05, True),
    ("AZ", "ITA Airways", "Europe", 1.02, True),
    ("BA", "British Airways", "Europe", 1.10, True),
    ("EI", "Aer Lingus", "Europe", 0.95, True),
    ("FR", "Ryanair", "Europe", 0.60, False),
    ("IB", "Iberia", "Europe", 1.01, True),
    ("KL", "KLM", "Europe", 1.07, True),
    ("LH", "Lufthansa", "Europe", 1.12, True),
    ("LX", "SWISS", "Europe", 1.14, True),
    ("OS", "Austrian Airlines", "Europe", 1.06, True),
    ("SK", "SAS", "Europe", 1.03, True),
    ("TK", "Turkish Airlines", "Europe", 0.97, True),
    ("TP", "TAP Air Portugal", "Europe", 0.93, True),
    ("U2", "easyJet", "Europe", 0.62, False),
    ("VS", "Virgin Atlantic", "Europe", 1.06, True),
    ("EK", "Emirates", "Middle East", 1.09, True),
    ("EY", "Etihad Airways", "Middle East", 1.05, True),
    ("QR", "Qatar Airways", "Middle East", 1.08, True),
    ("SV", "Saudia", "Middle East", 0.99, True),
    ("ET", "Ethiopian Airlines", "Africa", 0.94, True),
    ("KQ", "Kenya Airways", "Africa", 0.98, True),
    ("MS", "EgyptAir", "Africa", 0.92, True),
    ("SA", "South African Airways", "Africa", 1.00, True),
    ("AI", "Air India", "Asia", 0.96, True),
    ("BR", "EVA Air", "Asia", 1.04, True),
    ("CI", "China Airlines", "Asia", 1.00, True),
    ("CX", "Cathay Pacific", "Asia", 1.07, True),
    ("JL", "Japan Airlines", "Asia", 1.11, True),
    ("KE", "Korean Air", "Asia", 1.05, True),
    ("MH", "Malaysia Airlines", "Asia", 0.95, True),
    ("NH", "ANA", "Asia", 1.12, True),
    ("OZ", "Asiana Airlines", "Asia", 1.02, True),
    ("SQ", "Singapore Airlines", "Asia", 1.13, True),
    ("TG", "Thai Airways", "Asia", 0.98, True),
    ("VN", "Vietnam Airlines", "Asia", 0.93, True),
    ("6E", "IndiGo", "Asia", 0.72, False),
    ("NZ", "Air New Zealand", "Oceania", 1.06, True),
    ("QF", "Qantas", "Oceania", 1.10, True),
    ("VA", "Virgin Australia", "Oceania", 0.96, True),
)


@dataclass(frozen=True)
class Airline:
    code: str
    name: str
    region: str
    price_index: float
    long_haul: bool

    def to_dict(self) -> dict:
        return {"code": self.code, "name": self.name, "region": self.region}


AIRLINES: dict[str, Airline] = {row[0]: Airline(*row) for row in _ROWS}

OTHER_SENTINEL = "OTHER"


def options() -> list[dict]:
    """Picker options, alphabetical by name, for the form UI."""
    return [a.to_dict() for a in sorted(AIRLINES.values(), key=lambda a: a.name)]


def _fold(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


_NAME_INDEX = {_fold(a.name): code for code, a in AIRLINES.items()}
_NAME_INDEX.update(
    {
        "american": "AA",
        "united": "UA",
        "delta": "DL",
        "southwest": "WN",
        "jetblue": "B6",
        "alaska": "AS",
        "britishairways": "BA",
        "ba": "BA",
        "virgin": "VS",
        "airfrance": "AF",
        "klmroyaldutchairlines": "KL",
        "swissair": "LX",
        "turkish": "TK",
        "tap": "TP",
        "aerlingus": "EI",
        "emirates": "EK",
        "qatar": "QR",
        "etihad": "EY",
        "singaporeair": "SQ",
        "cathay": "CX",
        "jal": "JL",
        "ana": "NH",
        "koreanair": "KE",
        "airindia": "AI",
        "indigo": "6E",
        "qantas": "QF",
        "airnewzealand": "NZ",
        "ethiopian": "ET",
        "latam": "LA",
        "copa": "CM",
        "avianca": "AV",
        "aircanada": "AC",
        "lufthansa": "LH",
        "iberia": "IB",
        "ita": "AZ",
        "alitalia": "AZ",
        "finnair": "AY",
        "ryanair": "FR",
        "easyjet": "U2",
        "spirit": "NK",
        "frontier": "F9",
    }
)


def get(code: str | None) -> Airline | None:
    if not code:
        return None
    return AIRLINES.get(code.strip().upper())


def resolve(text: str | None) -> str | None:
    """Map a code or spoken airline name to a known IATA airline code."""
    if not text:
        return None
    raw = text.strip()
    if raw.upper() in AIRLINES:
        return raw.upper()
    folded = _fold(raw)
    if not folded:
        return None
    if folded in _NAME_INDEX:
        return _NAME_INDEX[folded]
    for key, code in _NAME_INDEX.items():
        if len(folded) >= 4 and (key.startswith(folded) or folded.startswith(key)):
            return code
    return None


def display_name(code: str | None, fallback_label: str | None = None) -> str:
    airline = get(code)
    if airline:
        return airline.name
    if fallback_label:
        return fallback_label.strip()
    return "Airline not specified"


def price_index(code: str | None) -> float:
    airline = get(code)
    if airline:
        return airline.price_index
    return 1.0
