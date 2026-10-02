"""The default provider: Roma's own deterministic fare model.

Always available, never a market price.
"""

from __future__ import annotations

from datetime import date

from .. import fares
from ..models import SearchRequest
from .base import FareProvider, ProviderResult


class SimulatedProvider(FareProvider):
    name = "simulated"

    def __init__(self, config) -> None:
        self.config = config

    def available(self) -> bool:
        return True

    def search(self, request: SearchRequest, *, today: date) -> ProviderResult:
        offers = fares.build_offers(
            request,
            as_of=today,
            currency=self.config.currency,
            requested_airline=request.airline,
            requested_airline_label=request.airline_label,
        )
        return ProviderResult(
            provider=self.name,
            data_level=fares.LEVEL_SIMULATED,
            offers=offers,
            notes=[
                "Fares below come from Roma's own model. They are not market "
                "prices and cannot be booked here.",
            ],
        )

    def describe(self) -> dict:
        return {
            "name": self.name,
            "available": True,
            "data_level": fares.LEVEL_SIMULATED,
        }
