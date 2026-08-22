"""The provider interface every fare source implements.

Adding a source means adding a module here and registering it — the UI, the history
store, and the recommendation engine never learn its name.
"""

from __future__ import annotations

import datetime as dt

from ..models import FareOffer, SearchQuery


class FareProvider:
    #: stable identifier stored with every observation
    name = "base"
    #: human label shown in the UI
    label = "Base provider"
    #: True when quotes are generated rather than retrieved from a market
    simulated = True

    def available(self) -> bool:
        """Can this provider run right now (credentials present, etc.)?"""
        return False

    def search(self, query: SearchQuery) -> list[FareOffer]:
        raise NotImplementedError

    def describe(self) -> dict:
        return {
            "name": self.name,
            "label": self.label,
            "simulated": self.simulated,
            "available": self.available(),
        }

    @staticmethod
    def now_iso() -> str:
        return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
