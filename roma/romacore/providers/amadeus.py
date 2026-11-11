"""Amadeus Self-Service adapter — the seam for real fares.

Activates only when ``AMADEUS_CLIENT_ID`` and ``AMADEUS_CLIENT_SECRET`` are set.
Without them :meth:`available` returns ``False`` and the engine uses the
simulator, so the default experience never depends on a network call.

This adapter has not been exercised against live Amadeus credentials in this
repository. Treat it as a wired-up integration point, not a tested one.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date

from .. import airlines, fares
from ..models import SearchRequest
from .base import FareProvider, ProviderResult, ProviderUnavailable

_TRAVEL_CLASS = {
    "economy": "ECONOMY",
    "premium_economy": "PREMIUM_ECONOMY",
    "business": "BUSINESS",
    "first": "FIRST",
}

_DURATION_RE = re.compile(
    r"^P(?:(?P<days>\d+)D)?(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?)?$"
)


def parse_iso_duration(value: str | None) -> int:
    """``PT11H35M`` -> minutes. Returns 0 for anything unparseable."""
    if not value:
        return 0
    match = _DURATION_RE.match(value.strip().upper())
    if not match:
        return 0
    days = int(match.group("days") or 0)
    hours = int(match.group("hours") or 0)
    minutes = int(match.group("minutes") or 0)
    return days * 1440 + hours * 60 + minutes


class AmadeusProvider(FareProvider):
    name = "amadeus"

    def __init__(self, config) -> None:
        self.config = config
        self._token: str | None = None
        self._token_expires_at: float = 0.0

    def available(self) -> bool:
        return bool(self.config.amadeus_configured)

    # -- transport ----------------------------------------------------------
    def _post_form(self, path: str, fields: dict) -> dict:
        url = f"{self.config.amadeus_base_url}{path}"
        body = urllib.parse.urlencode(fields).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))

    def _get_json(self, path: str, params: dict) -> dict:
        query = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        url = f"{self.config.amadeus_base_url}{path}?{query}"
        req = urllib.request.Request(
            url,
            method="GET",
            headers={
                "Authorization": f"Bearer {self._access_token()}",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))

    def _access_token(self) -> str:
        if self._token and time.time() < self._token_expires_at - 30:
            return self._token
        payload = self._post_form(
            "/v1/security/oauth2/token",
            {
                "grant_type": "client_credentials",
                "client_id": self.config.amadeus_client_id,
                "client_secret": self.config.amadeus_client_secret,
            },
        )
        token = payload.get("access_token")
        if not token:
            raise ProviderUnavailable("Amadeus did not return an access token.")
        self._token = token
        self._token_expires_at = time.time() + float(payload.get("expires_in") or 1800)
        return token

    # -- search -------------------------------------------------------------
    def search(self, request: SearchRequest, *, today: date) -> ProviderResult:
        if not self.available():
            raise ProviderUnavailable("Amadeus credentials are not configured.")
        params = {
            "originLocationCode": request.origin,
            "destinationLocationCode": request.destination,
            "departureDate": request.depart_date.isoformat(),
            "returnDate": request.return_date.isoformat() if request.return_date else None,
            "adults": request.adults,
            "travelClass": _TRAVEL_CLASS.get(request.cabin, "ECONOMY"),
            "currencyCode": self.config.currency,
            "includedAirlineCodes": request.airline or None,
            "max": 12,
            "nonStop": "false",
        }
        try:
            payload = self._get_json("/v2/shopping/flight-offers", params)
        except urllib.error.HTTPError as exc:  # pragma: no cover - needs credentials
            detail = exc.read().decode("utf-8", "replace")[:300]
            raise ProviderUnavailable(f"Amadeus returned HTTP {exc.code}: {detail}") from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ProviderUnavailable(f"Amadeus request failed: {exc}") from exc

        offers = self._to_offers(payload)
        if not offers:
            raise ProviderUnavailable("Amadeus returned no offers for this query.")
        return ProviderResult(
            provider=self.name,
            data_level=fares.LEVEL_LIVE,
            offers=offers,
            notes=["Fares returned by the Amadeus Self-Service API for this query."],
        )

    def _to_offers(self, payload: dict) -> list[dict]:
        results: list[dict] = []
        for offer in payload.get("data") or []:
            price_block = offer.get("price") or {}
            try:
                total = float(price_block.get("grandTotal") or price_block.get("total"))
            except (TypeError, ValueError):
                continue
            itineraries = offer.get("itineraries") or []
            if not itineraries:
                continue
            outbound = itineraries[0]
            inbound = itineraries[1] if len(itineraries) > 1 else None
            segments = outbound.get("segments") or []
            carrier = (offer.get("validatingAirlineCodes") or [None])[0]
            if not carrier and segments:
                carrier = (segments[0].get("carrierCode") or "").upper() or None
            results.append(
                {
                    "airline_code": carrier or "\u2014",
                    "airline_name": airlines.display_name(carrier, carrier),
                    "price": round(total, 2),
                    "currency": price_block.get("currency") or self.config.currency,
                    "stops": max(0, len(segments) - 1),
                    "outbound_duration_minutes": parse_iso_duration(outbound.get("duration")),
                    "return_duration_minutes": (
                        parse_iso_duration(inbound.get("duration")) if inbound else None
                    ),
                    "fare_basis": (
                        "Refundable"
                        if (offer.get("pricingOptions") or {}).get("refundableFare")
                        else "Non-refundable"
                    ),
                    "provider": self.name,
                    "data_level": fares.LEVEL_LIVE,
                    "notes": [],
                }
            )
        results.sort(key=lambda item: item["price"])
        return results[:6]

    def describe(self) -> dict:
        return {
            "name": self.name,
            "available": self.available(),
            "data_level": fares.LEVEL_LIVE,
            "base_url": self.config.amadeus_base_url,
            "verified": False,
        }
