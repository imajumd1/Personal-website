"""Pre-filled search URLs for Kayak, Expedia, Google Flights, and Priceline.

Roma does not scrape any of them: their terms prohibit automated access, they defend
against it, and screen-scraped prices would be brittle and misleading. Instead Roma
hands the traveller a correct deep link per site so one click continues the same
search on the real source of truth.

URL shapes are the public search-form shapes each site accepts. They are built by
string construction with proper percent-encoding, and are verified structurally by
`roma/tests/test_roma.py`; sites can change their routing at any time.
"""

from __future__ import annotations

import urllib.parse

from .models import SearchQuery

KAYAK_CABIN = {"economy": "economy", "premium_economy": "premium", "business": "business", "first": "first"}
EXPEDIA_CABIN = {"economy": "economy", "premium_economy": "premiumeconomy", "business": "business", "first": "first"}
PRICELINE_CABIN = {"economy": "ECO", "premium_economy": "PEC", "business": "BUS", "first": "FST"}


def kayak_url(query: SearchQuery) -> str:
    # /flights/SFO-LHR/2026-10-12/2026-10-20/2adults/business?sort=price_a
    parts = [f"{query.origin}-{query.destination}", query.depart_date]
    if query.return_date:
        parts.append(query.return_date)
    if query.passengers > 1:
        parts.append(f"{query.passengers}adults")
    if query.cabin != "economy":
        parts.append(KAYAK_CABIN.get(query.cabin, "economy"))
    return "https://www.kayak.com/flights/" + "/".join(parts) + "?sort=price_a"


def google_flights_url(query: SearchQuery) -> str:
    # The documented ?q= form; Google parses the natural-language query itself.
    bits = [
        "Flights to", query.destination,
        "from", query.origin,
        "on", query.depart_date,
    ]
    if query.return_date:
        bits += ["through", query.return_date]
    if query.cabin != "economy":
        bits.append(query.cabin.replace("_", " "))
    if query.passengers > 1:
        bits.append(f"{query.passengers} passengers")
    return "https://www.google.com/travel/flights?" + urllib.parse.urlencode({"q": " ".join(bits)})


def expedia_url(query: SearchQuery) -> str:
    def leg(origin: str, destination: str, date: str) -> str:
        return f"from:{origin},to:{destination},departure:{_us_date(date)}TANYT"

    legs = [("leg1", leg(query.origin, query.destination, query.depart_date))]
    if query.return_date:
        legs.append(("leg2", leg(query.destination, query.origin, query.return_date)))

    params = [("trip", "roundtrip" if query.return_date else "oneway")]
    params += legs
    params += [
        ("passengers", f"adults:{query.passengers},children:0,infantinlap:N"),
        ("options", f"cabinclass:{EXPEDIA_CABIN.get(query.cabin, 'economy')}"),
        ("mode", "search"),
    ]
    return "https://www.expedia.com/Flights-Search?" + urllib.parse.urlencode(params)


def priceline_url(query: SearchQuery) -> str:
    # /m/fly/search/SFO-LHR-20261012/LHR-SFO-20261020/?cabin-class=ECO&num-adults=2
    slugs = [f"{query.origin}-{query.destination}-{_compact_date(query.depart_date)}"]
    if query.return_date:
        slugs.append(f"{query.destination}-{query.origin}-{_compact_date(query.return_date)}")
    params = urllib.parse.urlencode({
        "cabin-class": PRICELINE_CABIN.get(query.cabin, "ECO"),
        "num-adults": str(query.passengers),
    })
    return "https://www.priceline.com/m/fly/search/" + "/".join(slugs) + f"/?{params}"


SOURCES = [
    ("kayak", "Kayak", kayak_url),
    ("google_flights", "Google Flights", google_flights_url),
    ("expedia", "Expedia", expedia_url),
    ("priceline", "Priceline", priceline_url),
]


def build_all(query: SearchQuery) -> list[dict]:
    """One pre-filled deep link per source, in display order."""
    return [
        {"id": key, "label": label, "url": builder(query)}
        for key, label, builder in SOURCES
    ]


def _us_date(iso: str) -> str:
    year, month, day = iso.split("-")
    return f"{int(month)}/{int(day)}/{year}"


def _compact_date(iso: str) -> str:
    return iso.replace("-", "")
