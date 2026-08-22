"""Provider registry: real sources first, simulated fares as the always-there floor."""

from __future__ import annotations

from ..models import FareOffer, SearchQuery
from .amadeus import AmadeusProvider
from .base import FareProvider
from .simulated import SimulatedProvider

__all__ = ["FareProvider", "AmadeusProvider", "SimulatedProvider", "ProviderSet"]


class ProviderSet:
    """Runs every available provider and merges their offers.

    Registration order is preference order. A provider that raises is recorded in
    ``errors`` and skipped; the search still returns whatever the others produced.
    """

    def __init__(self, providers: list[FareProvider] | None = None):
        self.providers: list[FareProvider] = providers if providers is not None else [
            AmadeusProvider(),
            SimulatedProvider(),
        ]

    def active(self) -> list[FareProvider]:
        return [p for p in self.providers if p.available()]

    def search(self, query: SearchQuery) -> tuple[list[FareOffer], list[str], list[str]]:
        """Return ``(offers, sources_used, errors)``."""
        offers: list[FareOffer] = []
        used: list[str] = []
        errors: list[str] = []
        for provider in self.active():
            try:
                found = provider.search(query)
            except Exception as exc:  # noqa: BLE001 - one bad source must not break a search
                errors.append(f"{provider.name}: {exc}")
                continue
            if found:
                offers.extend(found)
                used.append(provider.name)
        offers.sort(key=lambda o: o.price)
        return offers, used, errors

    def describe(self) -> list[dict]:
        return [p.describe() for p in self.providers]
