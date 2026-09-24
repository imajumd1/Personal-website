"""Roma — a standalone flight-search agent built on the Python standard library.

``romacore`` holds the whole agent: airport data, request validation, the fare
provider seam, the SQLite price-history store, the buy/wait rule engine, the
natural-language layer, and the HTTP server that serves both the JSON API and
Roma's own static UI. Nothing here imports a third-party package.

The web path and the CLI path both go through :class:`romacore.engine.Engine`,
so a search means the same thing however it was asked for.
"""

from __future__ import annotations

AGENT_NAME = "Roma"
AGENT_TAGLINE = "A flight-search agent that shows its work."
VERSION = "1.0.0"

__all__ = ["AGENT_NAME", "AGENT_TAGLINE", "VERSION"]
