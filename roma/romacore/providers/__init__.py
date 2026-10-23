"""The fare-provider seam.

A provider takes a :class:`romacore.models.SearchRequest` and returns priced
offers. :class:`SimulatedProvider` always works and is the default.
:class:`AmadeusProvider` talks to a real API and activates only when credentials
are present; when it fails for any reason the engine falls back to the simulator
and says so rather than pretending.
"""

from __future__ import annotations

from .base import FareProvider, ProviderResult, ProviderUnavailable
from .simulated import SimulatedProvider
from .amadeus import AmadeusProvider

__all__ = [
    "FareProvider",
    "ProviderResult",
    "ProviderUnavailable",
    "SimulatedProvider",
    "AmadeusProvider",
    "build_chain",
]


def build_chain(config) -> list[FareProvider]:
    """Providers in priority order for this configuration."""
    chain: list[FareProvider] = []
    if config.amadeus_configured:
        chain.append(AmadeusProvider(config))
    chain.append(SimulatedProvider(config))
    return chain
