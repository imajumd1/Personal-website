"""Amadeus Flight Offers Search adapter — real request shape, credentials from env.

Activated only when both ``AMADEUS_CLIENT_ID`` and ``AMADEUS_CLIENT_SECRET`` are
present in the environment. ``AMADEUS_HOST`` selects the sandbox
(``test.api.amadeus.com``, default) or production (``api.amadeus.com``).

Nothing here is committed and nothing is required: without credentials the provider
reports itself unavailable and Roma runs on simulated fares alone.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

from ..airlines import AIRLINES
from ..models import FareOffer, SearchQuery
from .base import FareProvider

CABIN_TO_AMADEUS = {
    "economy": "ECONOMY",
    "premium_economy": "PREMIUM_ECONOMY",
    "business": "BUSINESS",
    "first": "FIRST",
}


class AmadeusError(RuntimeError):
    pass


class AmadeusProvider(FareProvider):
    name = "amadeus"
    label = "Amadeus Flight Offers"
    simulated = False

    def __init__(self, timeout: float | None = None):
        self.client_id = os.environ.get("AMADEUS_CLIENT_ID", "").strip()
        self.client_secret = os.environ.get("AMADEUS_CLIENT_SECRET", "").strip()
        self.host = os.environ.get("AMADEUS_HOST", "test.api.amadeus.com").strip()
        try:
            self.timeout = timeout if timeout is not None else float(os.environ.get("AMADEUS_TIMEOUT", "10"))
        except ValueError:
            self.timeout = 10.0
        self._token = ""
        self._token_expires_at = 0.0

    def available(self) -> bool:
        return bool(self.client_id and self.client_secret)

    # -- auth ---------------------------------------------------------------

    def _access_token(self) -> str:
        if self._token and time.time() < self._token_expires_at - 30:
            return self._token
        body = urllib.parse.urlencode({
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }).encode()
        request = urllib.request.Request(
            f"https://{self.host}/v1/security/oauth2/token", data=body, method="POST"
        )
        request.add_header("Content-Type", "application/x-www-form-urlencoded")
        payload = self._send(request)
        token = payload.get("access_token")
        if not token:
            raise AmadeusError("Amadeus token response had no access_token")
        self._token = token
        self._token_expires_at = time.time() + float(payload.get("expires_in") or 1799)
        return self._token

    def _send(self, request: urllib.request.Request) -> dict:
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8")[:400]
            except Exception:  # noqa: BLE001 - diagnostics only
                pass
            raise AmadeusError(f"Amadeus HTTP {exc.code}: {detail}") from exc
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            raise AmadeusError(f"Amadeus request failed: {exc}") from exc

    # -- search -------------------------------------------------------------

    def search(self, query: SearchQuery) -> list[FareOffer]:
        if not self.available():
            return []
        params = {
            "originLocationCode": query.origin,
            "destinationLocationCode": query.destination,
            "departureDate": query.depart_date,
            "adults": str(query.passengers),
            "travelClass": CABIN_TO_AMADEUS.get(query.cabin, "ECONOMY"),
            "currencyCode": "USD",
            "max": "12",
        }
        if query.return_date:
            params["returnDate"] = query.return_date
        if query.airline and query.airline.upper() in AIRLINES:
            params["includedAirlineCodes"] = query.airline.upper()

        url = f"https://{self.host}/v2/shopping/flight-offers?" + urllib.parse.urlencode(params)
        request = urllib.request.Request(url, method="GET")
        request.add_header("Authorization", f"Bearer {self._access_token()}")
        request.add_header("Accept", "application/vnd.amadeus+json")
        payload = self._send(request)

        retrieved_at = self.now_iso()
        offers: list[FareOffer] = []
        for raw in payload.get("data") or []:
            offer = self._to_offer(raw, query, retrieved_at)
            if offer:
                offers.append(offer)
        offers.sort(key=lambda o: o.price)
        return offers

    def _to_offer(self, raw: dict, query: SearchQuery, retrieved_at: str) -> FareOffer | None:
        try:
            itineraries = raw["itineraries"]
            outbound = itineraries[0]
            segments = outbound["segments"]
            first, last = segments[0], segments[-1]
            price = float(raw["price"]["grandTotal"])
            currency = raw["price"].get("currency", "USD")
        except (KeyError, IndexError, TypeError, ValueError):
            return None

        carrier = raw.get("validatingAirlineCodes", [None])[0] or first.get("carrierCode", "")
        airline_name = AIRLINES[carrier].name if carrier in AIRLINES else (carrier or "Unknown carrier")
        depart_at = str(first.get("departure", {}).get("at", ""))
        arrive_at = str(last.get("arrival", {}).get("at", ""))

        return FareOffer(
            price=price,
            currency=currency,
            airline=carrier,
            airline_name=airline_name,
            origin=query.origin,
            destination=query.destination,
            depart_date=depart_at[:10] or query.depart_date,
            return_date=query.return_date,
            cabin=query.cabin,
            stops=max(0, len(segments) - 1),
            duration_minutes=_iso_duration_minutes(outbound.get("duration", "")),
            depart_time=depart_at[11:16],
            arrive_time=arrive_at[11:16],
            source=self.name,
            simulated=False,
            retrieved_at=retrieved_at,
            fare_basis=str(raw.get("id", "")),
        )


def _iso_duration_minutes(value: str) -> int:
    """Parse an ISO-8601 duration such as PT11H35M into minutes."""
    text = str(value or "").upper().replace("PT", "")
    minutes = 0
    number = ""
    for char in text:
        if char.isdigit():
            number += char
        elif char == "H":
            minutes += int(number or 0) * 60
            number = ""
        elif char == "M":
            minutes += int(number or 0)
            number = ""
        elif char == "D":
            minutes += int(number or 0) * 1440
            number = ""
        else:
            number = ""
    return minutes
