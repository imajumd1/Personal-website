"""The three validation rules every search must pass, web or CLI.

1. ``route_known_and_distinct`` — both endpoints resolve to airports Roma knows,
   and they are not the same airport.
2. ``depart_date_valid_and_future`` — the outbound date parses and is not in the
   past.
3. ``return_date_after_depart`` — a return date, if given, parses and is not
   before the outbound date.

Rules run independently so one bad field does not hide another.
"""

from __future__ import annotations

from datetime import date, datetime

from . import airports
from .models import CABINS, SearchRequest, ValidationError

RULES: tuple[tuple[str, str], ...] = (
    ("route_known_and_distinct", "Origin and destination must be different airports Roma recognises."),
    ("depart_date_valid_and_future", "The departure date must be a real date that has not already passed."),
    ("return_date_after_depart", "A return date must fall on or after the departure date."),
)

MAX_TRIP_NIGHTS = 365
MAX_DAYS_AHEAD = 400


def parse_date(raw: str | None) -> date | None:
    """Accept ISO ``YYYY-MM-DD`` only; anything else is a validation problem."""
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def validate(
    origin_raw: str | None,
    destination_raw: str | None,
    depart_raw: str | None,
    return_raw: str | None,
    *,
    today: date,
) -> tuple[SearchRequest | None, list[ValidationError]]:
    """Validate raw input and, when it is clean, build a :class:`SearchRequest`."""
    errors: list[ValidationError] = []

    # --- Rule 1: route ---
    origin = airports.resolve(origin_raw)
    destination = airports.resolve(destination_raw)
    if not (origin_raw or "").strip():
        errors.append(
            ValidationError("origin", "route_known_and_distinct", "Tell Roma which airport you are flying from.")
        )
    elif origin is None:
        errors.append(
            ValidationError(
                "origin",
                "route_known_and_distinct",
                f"Roma does not recognise \u201c{str(origin_raw).strip()}\u201d. Try a city name or a 3-letter airport code.",
            )
        )
    if not (destination_raw or "").strip():
        errors.append(
            ValidationError(
                "destination", "route_known_and_distinct", "Tell Roma which airport you are flying to."
            )
        )
    elif destination is None:
        errors.append(
            ValidationError(
                "destination",
                "route_known_and_distinct",
                f"Roma does not recognise \u201c{str(destination_raw).strip()}\u201d. Try a city name or a 3-letter airport code.",
            )
        )
    if origin and destination and origin == destination:
        errors.append(
            ValidationError(
                "destination",
                "route_known_and_distinct",
                f"Origin and destination are both {origin}. Pick two different airports.",
            )
        )

    # --- Rule 2: departure date ---
    depart = parse_date(depart_raw)
    if not (depart_raw or "").strip():
        errors.append(
            ValidationError("depart_date", "depart_date_valid_and_future", "Pick a departure date.")
        )
    elif depart is None:
        errors.append(
            ValidationError(
                "depart_date",
                "depart_date_valid_and_future",
                f"\u201c{str(depart_raw).strip()}\u201d is not a date Roma can read. Use YYYY-MM-DD.",
            )
        )
    elif depart < today:
        errors.append(
            ValidationError(
                "depart_date",
                "depart_date_valid_and_future",
                f"{depart.isoformat()} is in the past. Roma cannot price a flight that has already left.",
            )
        )
    elif (depart - today).days > MAX_DAYS_AHEAD:
        errors.append(
            ValidationError(
                "depart_date",
                "depart_date_valid_and_future",
                f"{depart.isoformat()} is more than {MAX_DAYS_AHEAD} days out; airlines have not published those fares yet.",
            )
        )

    # --- Rule 3: return date ---
    return_date = parse_date(return_raw)
    has_return_text = bool((return_raw or "").strip())
    if has_return_text and return_date is None:
        errors.append(
            ValidationError(
                "return_date",
                "return_date_after_depart",
                f"\u201c{str(return_raw).strip()}\u201d is not a date Roma can read. Use YYYY-MM-DD or leave it empty for one way.",
            )
        )
    elif return_date and depart and return_date < depart:
        errors.append(
            ValidationError(
                "return_date",
                "return_date_after_depart",
                f"The return date {return_date.isoformat()} is before the departure date {depart.isoformat()}.",
            )
        )
    elif return_date and depart and (return_date - depart).days > MAX_TRIP_NIGHTS:
        errors.append(
            ValidationError(
                "return_date",
                "return_date_after_depart",
                f"That is a {(return_date - depart).days}-night trip. Roma prices trips up to {MAX_TRIP_NIGHTS} nights.",
            )
        )

    if errors:
        return None, errors

    assert origin and destination and depart  # guarded by the rules above
    return (
        SearchRequest(
            origin=origin,
            destination=destination,
            depart_date=depart,
            return_date=return_date,
        ),
        [],
    )


def normalise_cabin(raw: str | None) -> str:
    if not raw:
        return "economy"
    candidate = str(raw).strip().lower().replace(" ", "_").replace("-", "_")
    return candidate if candidate in CABINS else "economy"


def normalise_adults(raw) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return 1
    return max(1, min(9, value))
