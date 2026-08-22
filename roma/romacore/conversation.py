"""Multi-turn chat on top of the same engine the form uses.

Roma collects three things — where from, where to, and when — asking for one at
a time, then runs exactly the search the form would have run.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta

from . import airlines, airports, nlu
from .engine import Engine

MAX_SESSIONS = 500

_ASK = {
    "destination": "Where would you like to fly to? A city or a 3-letter airport code both work.",
    "origin": "Which airport are you flying from?",
    "depart_date": "What date do you want to fly out? A date like 2026-11-03 or \u201cNovember 3\u201d is fine.",
    "return_date": "Is this a round trip? Give me a return date, or say one way.",
}

_HELP = (
    "Roma searches flights and tells you whether today's price looks worth taking. "
    "Give it a route and a date \u2014 for example \u201cSFO to London on October 12, "
    "back October 20\u201d \u2014 or use the form. Every fare Roma shows is simulated by "
    "its own model, and it links you out to Google Flights, Kayak, Expedia and "
    "Priceline to see real prices."
)


@dataclass
class Slots:
    origin: str | None = None
    destination: str | None = None
    depart_date: date | None = None
    return_date: date | None = None
    one_way: bool | None = None
    airline: str | None = None
    airline_label: str | None = None
    cabin: str = "economy"
    adults: int = 1
    awaiting: str | None = None
    asked_return: bool = False

    def to_dict(self) -> dict:
        origin = airports.get(self.origin)
        destination = airports.get(self.destination)
        return {
            "origin": self.origin,
            "origin_label": origin.label if origin else None,
            "destination": self.destination,
            "destination_label": destination.label if destination else None,
            "depart_date": self.depart_date.isoformat() if self.depart_date else None,
            "return_date": self.return_date.isoformat() if self.return_date else None,
            "one_way": self.one_way,
            "airline": self.airline,
            "airline_label": self.airline_label,
            "cabin": self.cabin,
            "adults": self.adults,
            "awaiting": self.awaiting,
        }


class Conversation:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self._sessions: dict[str, Slots] = {}
        self._order: list[str] = []
        self._lock = threading.Lock()

    # -- session bookkeeping ------------------------------------------------
    def _slots(self, session_id: str) -> Slots:
        with self._lock:
            slots = self._sessions.get(session_id)
            if slots is None:
                slots = Slots()
                self._sessions[session_id] = slots
                self._order.append(session_id)
                while len(self._order) > MAX_SESSIONS:
                    self._sessions.pop(self._order.pop(0), None)
            return slots

    def _reset(self, session_id: str) -> Slots:
        with self._lock:
            slots = Slots()
            self._sessions[session_id] = slots
            return slots

    @staticmethod
    def new_session_id() -> str:
        return uuid.uuid4().hex

    # -- the turn -----------------------------------------------------------
    def handle(self, session_id: str, message: str) -> dict:
        today = self.engine.today()
        parsed = nlu.parse(message, today=today)

        if parsed.intent == "empty":
            return self._reply(session_id, "collecting", "Say something and Roma will try to help.")
        if parsed.intent == "reset":
            self._reset(session_id)
            return self._reply(
                session_id, "collecting", "Cleared. Where would you like to fly?"
            )
        if parsed.intent == "help":
            return self._reply(session_id, "help", _HELP)

        slots = self._slots(session_id)
        awaiting = slots.awaiting
        self._merge(slots, parsed, awaiting=awaiting, today=today)

        if parsed.intent == "greeting" and not self._has_any(slots):
            slots.awaiting = "destination"
            return self._reply(
                session_id,
                "collecting",
                "Roma here. It searches flights and tells you whether today's price looks "
                "worth taking. " + _ASK["destination"],
            )

        if parsed.intent == "unparsed":
            # Never guess, and never quietly re-run the last search instead of
            # answering. Say what was not understood and what is still needed.
            if awaiting is not None:
                return self._reply(
                    session_id,
                    "unparsed",
                    "Roma did not find anything it understood in that. " + _ASK[awaiting],
                    awaiting=awaiting,
                )
            if self._has_any(slots):
                return self._reply(
                    session_id,
                    "unparsed",
                    "Roma could not find a place, a date or an airline in that, so it has "
                    "not changed anything. " + self._acknowledge(slots) + " Give it a new "
                    "route and date, or say \u201cstart over\u201d to clear it.",
                )
            return self._reply(
                session_id,
                "unparsed",
                "Roma could not find a route or a date in that. It needs somewhere to fly "
                "from, somewhere to fly to, and a date \u2014 for example \u201cBoston to "
                "Miami on November 3\u201d. " + _ASK["destination"],
                awaiting="destination",
            )

        missing = self._first_missing(slots)
        if missing:
            slots.awaiting = missing
            if missing == "return_date":
                slots.asked_return = True
            return self._reply(
                session_id, "collecting", self._acknowledge(slots) + " " + _ASK[missing], awaiting=missing
            )

        slots.awaiting = None
        payload = {
            "origin": slots.origin,
            "destination": slots.destination,
            "depart_date": slots.depart_date.isoformat() if slots.depart_date else None,
            "return_date": slots.return_date.isoformat() if slots.return_date else None,
            "one_way": bool(slots.one_way) or slots.return_date is None,
            "cabin": slots.cabin,
            "adults": slots.adults,
            "airline": slots.airline,
            "source": "chat",
        }
        if slots.airline is None and slots.airline_label:
            payload["airline"] = airlines.OTHER_SENTINEL
            payload["airline_other"] = slots.airline_label
        result = self.engine.search(payload)
        if not result.get("ok"):
            messages = [e["message"] for e in result.get("errors", [])]
            # Clear whatever the user must restate so the next turn can fix it.
            for error in result.get("errors", []):
                field_name = error.get("field")
                if field_name == "origin":
                    slots.origin = None
                elif field_name == "destination":
                    slots.destination = None
                elif field_name == "depart_date":
                    slots.depart_date = None
                elif field_name == "return_date":
                    slots.return_date = None
            awaiting_next = self._first_missing(slots)
            slots.awaiting = awaiting_next
            return self._reply(
                session_id,
                "error",
                "Roma cannot run that yet. " + " ".join(messages),
                awaiting=awaiting_next,
                result=result,
            )

        return self._reply(session_id, "result", result["summary"], result=result)

    # -- merging ------------------------------------------------------------
    def _merge(self, slots: Slots, parsed: nlu.Parsed, *, awaiting: str | None, today: date) -> None:
        unknown_places = [p for p in parsed.places if p.role == "unknown"]
        if awaiting in {"origin", "destination"} and len(unknown_places) == 1:
            # A bare answer to a direct question fills the slot that was asked.
            setattr(slots, awaiting, unknown_places[0].code)
            other = "destination" if awaiting == "origin" else "origin"
            explicit = parsed.destination if other == "destination" else parsed.origin
            if explicit and explicit != unknown_places[0].code:
                setattr(slots, other, explicit)
        else:
            if parsed.origin:
                slots.origin = parsed.origin
            if parsed.destination:
                slots.destination = parsed.destination

        if awaiting == "depart_date" and parsed.depart_date is None and parsed.return_date:
            slots.depart_date = parsed.return_date
        else:
            if parsed.depart_date:
                slots.depart_date = parsed.depart_date
            if parsed.return_date:
                slots.return_date = parsed.return_date
                slots.one_way = False

        if awaiting == "return_date":
            if parsed.one_way:
                slots.one_way = True
                slots.return_date = None
            elif parsed.depart_date and parsed.return_date is None:
                slots.return_date = parsed.depart_date
                slots.one_way = False
        elif parsed.one_way is not None:
            slots.one_way = parsed.one_way
            if parsed.one_way:
                slots.return_date = None

        if parsed.nights and slots.depart_date and slots.return_date is None and not slots.one_way:
            slots.return_date = slots.depart_date + timedelta(days=parsed.nights)
            slots.one_way = False

        if parsed.airline or parsed.airline_label:
            slots.airline = parsed.airline
            slots.airline_label = parsed.airline_label
        if parsed.cabin:
            slots.cabin = parsed.cabin
        if parsed.adults:
            slots.adults = parsed.adults

    @staticmethod
    def _has_any(slots: Slots) -> bool:
        return any((slots.origin, slots.destination, slots.depart_date, slots.return_date))

    @staticmethod
    def _first_missing(slots: Slots) -> str | None:
        if not slots.destination:
            return "destination"
        if not slots.origin:
            return "origin"
        if not slots.depart_date:
            return "depart_date"
        if slots.return_date is None and slots.one_way is None and not slots.asked_return:
            return "return_date"
        return None

    @staticmethod
    def _acknowledge(slots: Slots) -> str:
        known: list[str] = []
        if slots.origin:
            airport = airports.get(slots.origin)
            known.append(f"from {airport.label if airport else slots.origin}")
        if slots.destination:
            airport = airports.get(slots.destination)
            known.append(f"to {airport.label if airport else slots.destination}")
        if slots.depart_date:
            known.append(f"out on {slots.depart_date.isoformat()}")
        if slots.return_date:
            known.append(f"back on {slots.return_date.isoformat()}")
        if not known:
            return ""
        return "Got " + ", ".join(known) + "."

    # -- response shaping ---------------------------------------------------
    def _reply(
        self,
        session_id: str,
        state: str,
        text: str,
        *,
        awaiting: str | None = None,
        result: dict | None = None,
    ) -> dict:
        slots = self._slots(session_id)
        if awaiting is not None:
            slots.awaiting = awaiting
        payload = {
            "ok": True,
            "session_id": session_id,
            "state": state,
            "reply": text.strip(),
            "awaiting": slots.awaiting,
            "slots": slots.to_dict(),
            "result": result,
        }
        return payload
