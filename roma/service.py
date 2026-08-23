"""The single search backend. The form and the chat both come through here.

`RomaService.search` is the whole pipeline: validate → providers → record history →
recommend → phrase → deep links. `RomaService.chat` parses language into the same
`SearchQuery`, asks for whatever is missing, and then calls `search`. There is no
second engine and no second set of rules behind the chat.
"""

from __future__ import annotations

import datetime as dt
import threading
import time
import uuid
from pathlib import Path

from . import deeplinks
from .airlines import OTHER_OPTION, all_airlines, lookup_airline
from .airports import lookup_airport, search_airports
from .history import PriceHistory
from .intent import get_intent_parser
from .llm import llm_status
from .models import CABINS, PartialQuery, SearchQuery, validate
from .phrasing import get_phraser
from .providers import ProviderSet
from .recommendation import recommend

SIMULATED_NOTICE = (
    "Fares shown are simulated demonstration data generated locally, not live quotes. "
    "Use the source links to see real prices."
)

SLOT_QUESTIONS = {
    "origin": "Which airport are you leaving from? An IATA code like SFO or a city name both work.",
    "destination": "Where do you want to fly to?",
    "depart_date": "What date do you want to leave? A specific date works, and so does something like “early March”.",
}

CONVERSATION_TTL_SECONDS = 6 * 3600
MAX_CONVERSATIONS = 500


class RomaService:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.history = PriceHistory(self.root / "data" / "roma_history.db")
        self.providers = ProviderSet()
        self.parser = get_intent_parser()
        self.phraser = get_phraser()
        self._conversations: dict[str, dict] = {}
        self._lock = threading.Lock()

    # -- reference data -----------------------------------------------------

    def airports(self, query: str, limit: int = 8) -> list[dict]:
        return [a.to_dict() for a in search_airports(query, limit)]

    def airlines(self) -> list[dict]:
        return [a.to_dict() for a in all_airlines()] + [
            {"code": OTHER_OPTION, "name": "Other (type a name)"}
        ]

    def status(self) -> dict:
        llm = llm_status()
        return {
            "agent": "Roma",
            "providers": self.providers.describe(),
            "simulated_only": all(p.simulated for p in self.providers.active()),
            "intent_parser": self.parser.name,
            "phraser": self.phraser.name,
            "llm": llm,
            "cabins": [{"id": key, "label": label} for key, label in CABINS.items()],
            "routes_observed": self.history.route_count(),
        }

    # -- the one search path ------------------------------------------------

    def search(self, payload: dict) -> dict:
        """Run a search. Returns ``{"ok": True, ...}`` or ``{"ok": False, "field_errors": ...}``."""
        raw = dict(payload or {})
        notes: list[str] = []

        airline_code = str(raw.get("airline") or "").strip()
        airline_other = str(raw.get("airline_other") or "").strip()
        if airline_code.upper() == OTHER_OPTION:
            resolved = lookup_airline(airline_other)
            if resolved:
                raw["airline"] = resolved.code
                raw["airline_label"] = resolved.name
            elif airline_other:
                raw["airline"] = None
                raw["airline_label"] = airline_other
                notes.append(
                    f"“{airline_other}” is not an airline Roma knows, so results are not filtered by carrier."
                )
            else:
                raw["airline"] = None

        query, field_errors = validate(raw)
        if not query:
            return {"ok": False, "error": "That search needs a fix.", "field_errors": field_errors}

        offers, sources_used, provider_errors = self.providers.search(query)
        self.history.record(query, offers)
        stats = self.history.stats(query)

        percentile = None
        if offers:
            per_person = round(offers[0].price / max(1, query.passengers), 2)
            percentile = self.history.percentile_of(per_person, stats)

        rec = recommend(query, offers, stats, percentile)
        explanation = self.phraser.phrase(query, rec)
        simulated = any(o.simulated for o in offers) if offers else True

        if provider_errors:
            notes.extend(provider_errors)

        return {
            "ok": True,
            "query": query.to_dict(),
            "results": [offer.to_dict() for offer in offers],
            "recommendation": {**rec.to_dict(), "explanation": explanation, "phraser": self.phraser.name},
            "deep_links": deeplinks.build_all(query),
            "history": {
                "observation_days": stats.get("observation_days"),
                "total_observations": stats.get("total_observations"),
                "median": stats.get("median"),
                "min": stats.get("min"),
                "max": stats.get("max"),
                "trend": stats.get("trend"),
                "first_day": stats.get("first_day"),
                "last_day": stats.get("last_day"),
                "percentile_available": percentile is not None,
            },
            "data": {
                "simulated": simulated,
                "simulated_notice": SIMULATED_NOTICE if simulated else "",
                "sources_used": sources_used,
                "retrieved_at": offers[0].retrieved_at if offers else _now_iso(),
                "notes": notes,
            },
        }

    # -- conversation -------------------------------------------------------

    def chat(self, message: str, conversation_id: str | None = None) -> dict:
        text = str(message or "").strip()
        conversation_id = conversation_id or uuid.uuid4().hex
        state = self._get_state(conversation_id)

        if not text:
            return self._reply(conversation_id, "Tell me where you want to go and roughly when.", understood=False)

        if _is_reset(text):
            self._set_state(conversation_id, PartialQuery(), None)
            return self._reply(conversation_id, "Cleared. Where would you like to go?", understood=True)

        parsed = self.parser.parse(text)
        stored: PartialQuery = state["slots"]
        pending = state.get("pending")
        parsed = _apply_pending_slot(parsed, stored, pending)
        merged = stored.merge(parsed)

        if parsed.is_empty() and not merged.filled():
            return self._reply(
                conversation_id,
                "Roma could not find a route in that. Try something like “SFO to Tokyo in early March for two”, "
                "or fill in the search form and Roma will read it the same way.",
                understood=False,
            )

        missing = merged.missing_required()
        if missing:
            slot = missing[0]
            self._set_state(conversation_id, merged, slot)
            reply = _acknowledge(merged, parsed) + SLOT_QUESTIONS[slot]
            return self._reply(
                conversation_id, reply, understood=not parsed.is_empty(), needs=missing, slots=merged
            )

        result = self.search(merged.filled())
        if not result.get("ok"):
            errors = result.get("field_errors", {})
            slot = next(iter(errors), "depart_date")
            cleaned = PartialQuery(**{k: v for k, v in merged.filled().items() if k != slot})
            self._set_state(conversation_id, cleaned, slot)
            problem = errors.get(slot, "That did not work.")
            return self._reply(
                conversation_id,
                f"{problem} {SLOT_QUESTIONS.get(slot, 'Could you correct that detail?')}",
                understood=True,
                needs=[slot],
                slots=cleaned,
            )

        self._set_state(conversation_id, merged, None)
        reply = _search_reply(result, merged)
        return self._reply(conversation_id, reply, understood=True, search=result, slots=merged)

    # -- conversation state -------------------------------------------------

    def _get_state(self, conversation_id: str) -> dict:
        with self._lock:
            self._prune()
            state = self._conversations.get(conversation_id)
            if not state:
                state = {"slots": PartialQuery(), "pending": None, "updated": time.time()}
                self._conversations[conversation_id] = state
            return state

    def _set_state(self, conversation_id: str, slots: PartialQuery, pending: str | None) -> None:
        with self._lock:
            self._conversations[conversation_id] = {
                "slots": slots,
                "pending": pending,
                "updated": time.time(),
            }

    def _prune(self) -> None:
        cutoff = time.time() - CONVERSATION_TTL_SECONDS
        stale = [key for key, value in self._conversations.items() if value["updated"] < cutoff]
        for key in stale:
            self._conversations.pop(key, None)
        if len(self._conversations) > MAX_CONVERSATIONS:
            for key, _ in sorted(self._conversations.items(), key=lambda kv: kv[1]["updated"])[:100]:
                self._conversations.pop(key, None)

    def _reply(
        self,
        conversation_id: str,
        reply: str,
        *,
        understood: bool,
        needs: list[str] | None = None,
        search: dict | None = None,
        slots: PartialQuery | None = None,
    ) -> dict:
        return {
            "ok": True,
            "conversation_id": conversation_id,
            "reply": reply,
            "understood": understood,
            "needs": needs or [],
            "slots": slots.filled() if slots else {},
            "search": search,
            "parser": self.parser.name,
        }


def _apply_pending_slot(parsed: PartialQuery, stored: PartialQuery, pending: str | None) -> PartialQuery:
    """A one-word answer to "where from?" is an origin, not a destination.

    The parser has no memory, so it labels a bare place as a destination. When Roma
    was waiting on a specific slot, move the value into that slot instead.
    """
    if not pending:
        return parsed
    if pending == "origin" and not parsed.origin and parsed.destination and stored.destination:
        if parsed.destination != stored.destination:
            parsed.origin = parsed.destination
        parsed.destination = None
    elif pending == "destination" and not parsed.destination and parsed.origin and stored.origin:
        if parsed.origin != stored.origin:
            parsed.destination = parsed.origin
        parsed.origin = None
    return parsed


def _acknowledge(merged: PartialQuery, parsed: PartialQuery) -> str:
    """A short "here is what I have" line before a follow-up question."""
    have: list[str] = []
    if merged.origin and merged.destination:
        have.append(f"{merged.origin} to {merged.destination}")
    elif merged.destination:
        have.append(f"destination {_place_label(merged.destination)}")
    elif merged.origin:
        have.append(f"origin {_place_label(merged.origin)}")
    if merged.depart_date:
        have.append(f"leaving {merged.depart_date}")
    if merged.return_date:
        have.append(f"back {merged.return_date}")
    if merged.passengers and merged.passengers > 1:
        have.append(f"{merged.passengers} passengers")
    if merged.cabin and merged.cabin != "economy":
        have.append(CABINS.get(merged.cabin, merged.cabin).lower())
    if merged.airline_label:
        have.append(f"on {merged.airline_label}")

    prefix = f"Got {', '.join(have)}. " if have else ""
    notes = [note for note in (merged.notes or []) if note]
    if notes:
        prefix += f"Roma {notes[-1]}. "
    return prefix


def _search_reply(result: dict, merged: PartialQuery) -> str:
    query = result["query"]
    rec = result["recommendation"]
    legs = f"{query['origin']} to {query['destination']}, {query['depart_date']}"
    if query.get("return_date"):
        legs += f" returning {query['return_date']}"
    legs += f", {query['passengers']} passenger{'s' if query['passengers'] > 1 else ''}"
    legs += f", {query['cabin_label'].lower()}"
    if query.get("airline_label"):
        legs += f", {query['airline_label']}"

    lines = [f"Searched {legs}."]
    notes = [note for note in (merged.notes or []) if note]
    if notes:
        lines.append("Roma " + "; ".join(notes[-2:]) + ". Say a different date if that is wrong.")
    lines.append(rec["explanation"])
    if result["data"]["simulated"]:
        lines.append(SIMULATED_NOTICE)
    return "\n".join(lines)


def _place_label(code: str) -> str:
    airport = lookup_airport(code)
    return f"{airport.city} ({airport.code})" if airport else code


def _is_reset(text: str) -> bool:
    lowered = text.lower().strip(" .!?")
    return lowered in {
        "reset", "start over", "start again", "new search", "clear", "forget it",
        "restart", "never mind", "nevermind",
    }


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
