"""Runtime configuration, read once from the environment.

Every knob has a working default so that ``python3 run.py`` needs no setup.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
DATA_DIR = BASE_DIR / "data"

DEFAULT_PORT = 8787
DEFAULT_HOST = "127.0.0.1"


def _first_env(*names: str) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value is not None and value.strip():
            return value.strip()
    return None


def _int_env(*names: str, default: int) -> int:
    raw = _first_env(*names)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _bool_env(*names: str, default: bool = False) -> bool:
    raw = _first_env(*names)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Config:
    """Immutable snapshot of the environment Roma was started with."""

    host: str
    port: int
    static_dir: Path
    data_dir: Path
    db_path: Path
    currency: str

    amadeus_client_id: str | None
    amadeus_client_secret: str | None
    amadeus_base_url: str

    llm_base_url: str | None
    llm_api_key: str | None
    llm_model: str
    llm_enabled: bool
    llm_timeout: float

    @property
    def amadeus_configured(self) -> bool:
        return bool(self.amadeus_client_id and self.amadeus_client_secret)

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_enabled and self.llm_base_url and self.llm_api_key)

    def describe(self) -> dict:
        """Non-secret summary, safe to hand to the browser."""
        return {
            "fare_provider": "amadeus" if self.amadeus_configured else "simulated",
            "amadeus_configured": self.amadeus_configured,
            "language_mode": "llm" if self.llm_configured else "heuristic",
            "llm_model": self.llm_model if self.llm_configured else None,
            "currency": self.currency,
        }


def load_config(port_override: int | None = None, host_override: str | None = None) -> Config:
    port = port_override if port_override is not None else _int_env(
        "ROMA_PORT", "PORT", default=DEFAULT_PORT
    )
    data_dir = Path(_first_env("ROMA_DATA_DIR") or DATA_DIR)
    amadeus_env = (_first_env("AMADEUS_ENV") or "test").lower()
    amadeus_host = (
        "https://api.amadeus.com"
        if amadeus_env in {"prod", "production", "live"}
        else "https://test.api.amadeus.com"
    )
    return Config(
        host=host_override or _first_env("ROMA_HOST") or DEFAULT_HOST,
        port=port,
        static_dir=Path(_first_env("ROMA_STATIC_DIR") or STATIC_DIR),
        data_dir=data_dir,
        db_path=data_dir / "price_history.sqlite3",
        currency=(_first_env("ROMA_CURRENCY") or "USD").upper(),
        amadeus_client_id=_first_env("AMADEUS_CLIENT_ID"),
        amadeus_client_secret=_first_env("AMADEUS_CLIENT_SECRET"),
        amadeus_base_url=_first_env("AMADEUS_BASE_URL") or amadeus_host,
        llm_base_url=_first_env("ROMA_LLM_BASE_URL"),
        llm_api_key=_first_env("ROMA_LLM_API_KEY"),
        llm_model=_first_env("ROMA_LLM_MODEL") or "gpt-4o-mini",
        llm_enabled=_bool_env("ROMA_LLM_ENABLED", default=True),
        llm_timeout=float(_int_env("ROMA_LLM_TIMEOUT", default=12)),
    )
