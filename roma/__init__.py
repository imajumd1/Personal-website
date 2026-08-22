"""Roma — a flight-search travel agent that runs on the Python standard library.

Public entry point is :func:`get_service`, which the site server calls to handle
``/api/roma/*``. Everything below it is plain stdlib: no pip installs, no build step.
"""

from __future__ import annotations

from pathlib import Path

__all__ = ["get_service", "AGENT_NAME"]

AGENT_NAME = "Roma"

_service = None


def get_service(root: Path | str | None = None):
    """Return the process-wide :class:`roma.service.RomaService` singleton."""
    global _service
    if _service is None:
        from .service import RomaService

        base = Path(root) if root else Path(__file__).resolve().parent.parent
        _service = RomaService(base)
    return _service
