"""Provider protocol shared by the simulator and any real API adapter."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from ..models import SearchRequest


class ProviderUnavailable(RuntimeError):
    """Raised when a provider cannot answer and the engine should fall back."""


@dataclass
class ProviderResult:
    provider: str
    data_level: str
    offers: list[dict]
    notes: list[str] = field(default_factory=list)
    degraded_from: str | None = None


class FareProvider:
    """Base class. Subclasses implement :meth:`search`."""

    name = "base"

    def available(self) -> bool:
        return False

    def search(self, request: SearchRequest, *, today: date) -> ProviderResult:
        raise NotImplementedError

    def describe(self) -> dict:
        return {"name": self.name, "available": self.available()}
