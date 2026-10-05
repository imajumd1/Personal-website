"""Hand-off links to real booking sites.

Roma does not scrape and does not book. It builds the search URL you would have
built yourself and hands you over to the site that actually sells the ticket.
"""

from __future__ import annotations

from urllib.parse import quote, urlencode

from .models import SearchRequest

_CABIN_KAYAK = {
    "economy": "e",
    "premium_economy": "p",
    "business": "b",
    "first": "f",
}
_CABIN_EXPEDIA = {
    "economy": "economy",
    "premium_economy": "premium",
    "business": "business",
    "first": "first",
}
_CABIN_PRICELINE = {
    "economy": "ECO",
    "premium_economy": "PEC",
    "business": "BUS",
    "first": "FST",
}
_CABIN_WORDS = {
    "economy": "economy",
    "premium_economy": "premium economy",
    "business": "business class",
    "first": "first class",
}


def _kayak(request: SearchRequest) -> str:
    legs = f"{request.origin}-{request.destination}/{request.depart_date.isoformat()}"
    if request.return_date:
        legs += f"/{request.return_date.isoformat()}"
    cabin = _CABIN_KAYAK.get(request.cabin, "e")
    return (
        f"https://www.kayak.com/flights/{legs}"
        f"/{request.adults}adults?sort=bestflight_a&fs=cfc={cabin}"
    )


def _google_flights(request: SearchRequest) -> str:
    words = [
        "Flights",
        f"from {request.origin}",
        f"to {request.destination}",
        f"on {request.depart_date.isoformat()}",
    ]
    if request.return_date:
        words.append(f"through {request.return_date.isoformat()}")
    else:
        words.append("one way")
    words.append(_CABIN_WORDS.get(request.cabin, "economy"))
    if request.airline:
        words.append(f"on {request.airline}")
    return "https://www.google.com/travel/flights?q=" + quote(" ".join(words))


def _expedia(request: SearchRequest) -> str:
    legs = [
        f"leg1=from:{request.origin},to:{request.destination},"
        f"departure:{request.depart_date.isoformat()}TANYT"
    ]
    trip = "oneway"
    if request.return_date:
        trip = "roundtrip"
        legs.append(
            f"leg2=from:{request.destination},to:{request.origin},"
            f"departure:{request.return_date.isoformat()}TANYT"
        )
    tail = "&".join(
        [f"trip={trip}", *legs, f"passengers=adults:{request.adults}", "mode=search"]
    )
    cabin = _CABIN_EXPEDIA.get(request.cabin, "economy")
    return f"https://www.expedia.com/Flights-Search?{tail}&options=cabinclass:{cabin}"


def _priceline(request: SearchRequest) -> str:
    depart = request.depart_date.strftime("%Y%m%d")
    legs = f"{request.origin}-{request.destination}-{depart}"
    if request.return_date:
        legs += f"/{request.destination}-{request.origin}-{request.return_date.strftime('%Y%m%d')}"
    query = urlencode(
        {
            "cabin-class": _CABIN_PRICELINE.get(request.cabin, "ECO"),
            "num-adults": request.adults,
        }
    )
    return f"https://www.priceline.com/m/fly/search/{legs}/?{query}"


_BUILDERS = (
    ("google_flights", "Google Flights", _google_flights),
    ("kayak", "Kayak", _kayak),
    ("expedia", "Expedia", _expedia),
    ("priceline", "Priceline", _priceline),
)


def build(request: SearchRequest) -> list[dict]:
    """One deep link per booking site, in the order Roma presents them."""
    return [
        {
            "id": site_id,
            "site": label,
            "url": builder(request),
            "note": "Opens that site's own search. Roma does not book or resell.",
        }
        for site_id, label, builder in _BUILDERS
    ]
