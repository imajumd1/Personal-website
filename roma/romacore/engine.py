"""The one engine every entry point goes through.

The web form, the chat, and the CLI all end up in :meth:`Engine.run`. That is
what makes a Roma answer mean the same thing regardless of how it was asked.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from . import airlines, airports, deeplinks, fares, llm, recommend, validation
from .config import Config
from .history import PriceHistory
from .models import CABIN_LABELS, CABINS, SearchRequest
from .providers import ProviderUnavailable, build_chain

# The same caveat, restated at three levels of the interface so it cannot be
# missed: once for the product, once for a result set, once for every price.
DISCLOSURE = {
    "product": (
        "Roma's fares are simulated by its own model. They are not market prices, "
        "they are not bookable here, and they should not be used to plan a real purchase."
    ),
    "result_set": (
        "Every price in this result set is a simulated estimate produced by Roma's "
        "fare model for this exact query."
    ),
    "fare": "Simulated estimate, not a market price.",
}


class Engine:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.history = PriceHistory(config.db_path)
        self.providers = build_chain(config)
        self.narrator = llm.build_narrator(config)

    # -- helpers ------------------------------------------------------------
    @staticmethod
    def today() -> date:
        return date.today()

    def meta(self) -> dict:
        return {
            "agent": "Roma",
            "tagline": "A flight-search agent that shows its work.",
            "today": self.today().isoformat(),
            "currency": self.config.currency,
            "cabins": [{"id": c, "label": CABIN_LABELS[c]} for c in CABINS],
            "airlines": airlines.options(),
            "airline_other": airlines.OTHER_SENTINEL,
            "booking_sites": [label for _, label, _ in deeplinks._BUILDERS],
            "validation_rules": [
                {"rule": rule, "describes": text} for rule, text in validation.RULES
            ],
            "recommendation_rules": [
                {"rule": rule, "describes": text} for rule, text in recommend.RULE_CATALOGUE
            ],
            "data_levels": list(fares.DATA_LEVELS.values()),
            "disclosure": DISCLOSURE,
            "providers": [p.describe() for p in self.providers],
            "language": self.narrator.describe(),
            "store": self.history.route_totals(),
        }

    # -- validation ---------------------------------------------------------
    def build_request(self, payload: dict) -> tuple[SearchRequest | None, list[dict]]:
        one_way = bool(payload.get("one_way"))
        return_raw = None if one_way else payload.get("return_date")
        request, errors = validation.validate(
            payload.get("origin"),
            payload.get("destination"),
            payload.get("depart_date"),
            return_raw,
            today=self.today(),
        )
        if errors:
            return None, [e.to_dict() for e in errors]

        assert request is not None
        request.cabin = validation.normalise_cabin(payload.get("cabin"))
        request.adults = validation.normalise_adults(payload.get("adults"))
        request.source = str(payload.get("source") or "form")

        airline_raw = str(payload.get("airline") or "").strip()
        if airline_raw.upper() == airlines.OTHER_SENTINEL:
            candidate = str(payload.get("airline_other") or "").strip()
        else:
            candidate = airline_raw
        resolved = airlines.resolve(candidate)
        request.airline = resolved
        if resolved:
            request.airline_label = airlines.display_name(resolved)
        elif candidate:
            # A carrier Roma has no reference data for. Honour the request and
            # say so on the offer rather than quietly searching every airline.
            request.airline_label = candidate
        else:
            request.airline_label = None
        return request, []

    # -- the search ---------------------------------------------------------
    def run(self, request: SearchRequest) -> dict:
        today = self.today()
        attempted: list[dict] = []
        result = None
        for provider in self.providers:
            if not provider.available():
                attempted.append({"provider": provider.name, "outcome": "unavailable"})
                continue
            try:
                result = provider.search(request, today=today)
                attempted.append({"provider": provider.name, "outcome": "used"})
                break
            except ProviderUnavailable as exc:
                attempted.append(
                    {"provider": provider.name, "outcome": "failed", "reason": str(exc)}
                )
            except Exception as exc:  # a provider must never take the agent down
                attempted.append(
                    {
                        "provider": provider.name,
                        "outcome": "error",
                        "reason": f"{type(exc).__name__}: {exc}",
                    }
                )
        if result is None or not result.offers:
            return {
                "ok": False,
                "kind": "no_offers",
                "query": request.to_dict(),
                "errors": [
                    {
                        "field": "form",
                        "rule": "provider_returned_nothing",
                        "message": "No provider could price this itinerary.",
                    }
                ],
                "provider": {"used": None, "attempted": attempted},
            }

        offers = result.offers
        cheapest = offers[0]

        backfilled = self.history.ensure_backfill(
            request,
            today=today,
            currency=self.config.currency,
            price_fn=lambda as_of: self._modelled_cheapest(request, as_of),
        )
        self.history.record(
            request,
            price=cheapest["price"],
            currency=cheapest["currency"],
            provider=result.provider,
            data_level=result.data_level,
            point_kind="observed",
            quoted_on=today,
        )
        stats = self.history.stats(request)

        rec = recommend.evaluate(
            current_price=float(cheapest["price"]),
            stats=stats,
            depart_date=request.depart_date,
            today=today,
            currency=self.config.currency,
        )

        level = fares.DATA_LEVELS[result.data_level]
        history_note = (
            "Price history for this query is modelled by Roma, not observed in a market."
            if stats.get("modeled_points")
            else "Price history for this query comes only from searches Roma has run."
        )

        facts = {
            "route": f"{request.origin}-{request.destination}",
            "origin": request.origin,
            "destination": request.destination,
            "depart_date": request.depart_date.isoformat(),
            "return_date": request.return_date.isoformat() if request.return_date else None,
            "cheapest_price": cheapest["price"],
            "currency": cheapest["currency"],
            "airline": cheapest["airline_name"],
            "stops": cheapest["stops"],
            "offer_count": len(offers),
            "data_level": level["label"],
            "verdict": rec.verdict,
            "rule_fired": rec.rule_fired,
            "recommendation_facts": rec.facts,
            "history": {
                "points": stats["points"],
                "min": stats["min"],
                "median": stats["median"],
                "max": stats["max"],
            },
        }
        fallback = self._summary_text(request, cheapest, rec, level, len(offers))
        summary, language = self.narrator.narrate("search_result", facts, fallback)

        return {
            "ok": True,
            "kind": "result",
            "query": request.to_dict(),
            "provider": {
                "used": result.provider,
                "attempted": attempted,
                "notes": result.notes,
            },
            "data_level": level,
            "disclosure": DISCLOSURE,
            "offers": offers,
            "cheapest": cheapest,
            "recommendation": rec.to_dict(),
            "history": {**stats, "backfilled_points": backfilled, "note": history_note},
            "deeplinks": deeplinks.build(request),
            "summary": summary,
            "summary_template": fallback,
            "language": language,
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }

    def search(self, payload: dict) -> dict:
        request, errors = self.build_request(payload)
        if errors:
            return {
                "ok": False,
                "kind": "validation",
                "errors": errors,
                "rules": [{"rule": r, "describes": t} for r, t in validation.RULES],
            }
        assert request is not None
        return self.run(request)

    # -- internals ----------------------------------------------------------
    def _modelled_cheapest(self, request: SearchRequest, as_of: date) -> float:
        offers = fares.build_offers(
            request,
            as_of=as_of,
            currency=self.config.currency,
            requested_airline=request.airline,
            requested_airline_label=request.airline_label,
        )
        return min(offer["price"] for offer in offers) if offers else 0.0

    def _summary_text(
        self,
        request: SearchRequest,
        cheapest: dict,
        rec: recommend.Recommendation,
        level: dict,
        offer_count: int,
    ) -> str:
        origin = airports.get(request.origin)
        destination = airports.get(request.destination)
        origin_label = origin.label if origin else request.origin
        destination_label = destination.label if destination else request.destination
        when = request.depart_date.isoformat()
        trip = (
            f"returning {request.return_date.isoformat()}"
            if request.return_date
            else "one way"
        )
        stops = cheapest["stops"]
        stop_text = "nonstop" if stops == 0 else f"{stops} stop" if stops == 1 else f"{stops} stops"
        verdict_word = {"buy": "Book it", "wait": "Hold off", "watch": "Keep watching"}[rec.verdict]
        return (
            f"{origin_label} to {destination_label}, {when}, {trip}: the cheapest of "
            f"{offer_count} options is {cheapest['currency']} {cheapest['price']:,.0f} "
            f"on {cheapest['airline_name']}, {stop_text}. "
            f"{level['label']}. {verdict_word} — {rec.headline} "
            f"(rule: {rec.rule_fired})."
        )
