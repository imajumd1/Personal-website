"""Natural-language trigger parser — pattern-based MVP (LLM-ready interface)."""

from __future__ import annotations

import re
from typing import Any

from .models import (
    Channel,
    ConditionClause,
    ParsedTriggerDraft,
    PriorityTier,
    StructuredCondition,
)

FIELD_ALIASES: dict[str, str] = {
    "flight delay": "delay_minutes",
    "delayed": "delay_minutes",
    "delay": "delay_minutes",
    "gold member": "one_key_tier",
    "platinum member": "one_key_tier",
    "gold or platinum": "one_key_tier",
    "loyalty tier": "one_key_tier",
    "tier": "one_key_tier",
    "cart abandon": "cart_abandon_flag",
    "abandoned cart": "cart_abandon_flag",
    "cart abandoned": "cart_abandon_flag",
    "search": "searches_same_destination_24h",
    "searches": "searches_same_destination_24h",
    "landed": "landed_flag",
    "flight landed": "landed_flag",
    "departure": "days_to_departure",
    "before departure": "days_to_departure",
    "booking confirmed": "booking_status",
    "return flight": "hours_since_return",
    "after return": "hours_since_return",
    "post-trip": "hours_since_return",
    "post trip": "hours_since_return",
    "lounge": "flight_status",
    "rebooking": "flight_status",
}

LIFECYCLE_KEYWORDS: dict[str, str] = {
    "search": "Inspiration / Search",
    "price drop": "Inspiration / Search",
    "abandon": "Pre-Booking (Abandonment)",
    "cart": "Pre-Booking (Abandonment)",
    "confirmed": "Booking Confirmed",
    "departure": "Pre-Trip Prep",
    "check-in": "Pre-Trip Prep",
    "delay": "Day of Travel (Disruption)",
    "disruption": "Day of Travel (Disruption)",
    "landed": "Post-Arrival",
    "arrival": "Post-Arrival",
    "welcome": "Post-Arrival",
    "return": "Post-Trip",
    "review": "Post-Trip",
}


def _extract_tier_condition(text: str) -> ConditionClause | None:
    lower = text.lower()
    if re.search(r"gold\s+or\s+platinum|platinum\s+or\s+gold", lower):
        return ConditionClause(
            field="one_key_tier",
            operator="in",
            value=["Gold", "Platinum"],
            description="Gold or Platinum loyalty tier",
        )
    if "gold member" in lower or "gold tier" in lower:
        return ConditionClause(field="one_key_tier", operator="==", value="Gold", description="Gold loyalty tier")
    if "platinum member" in lower or "platinum tier" in lower:
        return ConditionClause(field="one_key_tier", operator="==", value="Platinum", description="Platinum loyalty tier")
    return None


def _extract_delay_condition(text: str) -> ConditionClause | None:
    match = re.search(r"delay(?:ed)?\s+(?:more\s+than|over|>\s*|exceeds?\s+)?(\d+)\s*min", text.lower())
    if match:
        minutes = int(match.group(1))
        return ConditionClause(
            field="delay_minutes",
            operator=">",
            value=minutes,
            description=f"Flight delay exceeds {minutes} minutes",
        )
    if "flight delay" in text.lower() or "delayed" in text.lower():
        return ConditionClause(
            field="delay_minutes",
            operator=">",
            value=60,
            description="Flight delay exceeds 60 minutes",
        )
    return None


def _extract_search_condition(text: str) -> ConditionClause | None:
    match = re.search(r"(\d+)\+?\s*searches?\s+(?:to\s+)?(?:the\s+)?same\s+destination", text.lower())
    if match:
        count = int(match.group(1))
        return ConditionClause(
            field="searches_same_destination_24h",
            operator=">=",
            value=count,
            description=f"{count}+ searches to same destination in 24h",
        )
    if "search" in text.lower() and "destination" in text.lower():
        return ConditionClause(
            field="searches_same_destination_24h",
            operator=">=",
            value=2,
            description="2+ searches to same destination in 24h",
        )
    return None


def _extract_cart_condition(text: str) -> list[ConditionClause]:
    lower = text.lower()
    if "cart" in lower and ("abandon" in lower or "abandoned" in lower):
        return [
            ConditionClause(field="cart_abandon_flag", operator="==", value=True, description="Cart was abandoned"),
            ConditionClause(
                field="cart_abandon_component",
                operator="in",
                value=["flight_only", "hotel_only"],
                description="Single component in cart",
            ),
        ]
    return []


def _extract_departure_condition(text: str) -> ConditionClause | None:
    lower = text.lower()
    if re.search(r"24\s*hours?\s+(?:to\s+)?departure", lower):
        return ConditionClause(field="days_to_departure", operator="==", value=1, description="24 hours to departure")
    match = re.search(r"(\d+)\s*days?\s+before\s+departure", lower)
    if match:
        days = int(match.group(1))
        return ConditionClause(field="days_to_departure", operator="==", value=days, description=f"{days} days before departure")
    return None


def _extract_landed_condition(text: str) -> list[ConditionClause]:
    lower = text.lower()
    if "landed" in lower or "post-arrival" in lower or "welcome to" in lower:
        return [
            ConditionClause(field="landed_flag", operator="==", value=True, description="Traveler has landed"),
            ConditionClause(field="at_airport_flag", operator="==", value=True, description="At destination airport"),
        ]
    return []


def _extract_return_condition(text: str) -> ConditionClause | None:
    match = re.search(r"(\d+)\s*hours?\s+after\s+return", text.lower())
    if match:
        hours = int(match.group(1))
        return ConditionClause(field="hours_since_return", operator=">=", value=hours, description=f"{hours}+ hours after return")
    if "post-trip" in text.lower() or "post trip" in text.lower() or "review" in text.lower():
        return ConditionClause(field="hours_since_return", operator=">=", value=48, description="48+ hours after return")
    return None


def _infer_channel(text: str) -> Channel:
    lower = text.lower()
    if any(w in lower for w in ["text them", "send sms", "text ", " sms"]):
        return Channel.SMS
    if "email" in lower:
        return Channel.EMAIL
    if any(w in lower for w in ["delay", "lounge", "landed", "check-in", "urgent"]):
        return Channel.SMS
    if any(w in lower for w in ["hotel options", "package", "review", "rental car"]):
        return Channel.EMAIL
    return Channel.SMS_OR_EMAIL


def _infer_priority(text: str) -> PriorityTier:
    lower = text.lower()
    if any(w in lower for w in ["delay", "cancellation", "gate change", "disruption", "urgent", "operational"]):
        return PriorityTier.OPERATIONAL
    return PriorityTier.COMMERCIAL


def _infer_lifecycle(text: str, clauses: list[ConditionClause]) -> str:
    lower = text.lower()
    for keyword, phase in LIFECYCLE_KEYWORDS.items():
        if keyword in lower:
            return phase
    fields = {c.field for c in clauses}
    if "delay_minutes" in fields or "flight_status" in fields:
        return "Day of Travel (Disruption)"
    if "landed_flag" in fields:
        return "Post-Arrival"
    if "hours_since_return" in fields:
        return "Post-Trip"
    if "cart_abandon_flag" in fields:
        return "Pre-Booking (Abandonment)"
    if "searches_same_destination_24h" in fields:
        return "Inspiration / Search"
    if "days_to_departure" in fields:
        return "Pre-Trip Prep"
    return "Custom"


def _extract_offer(text: str) -> str:
    lower = text.lower()
    patterns = [
        (r"lounge[- ]access", "Instant lounge-access pass or one-tap rebooking link"),
        (r"hotel", "Top nearby hotel options with member pricing"),
        (r"price[- ]drop", "Price-drop alert with package savings"),
        (r"review", "Request a property review + OneKeyCash summary"),
        (r"rental car|ground transport|airport transfer", "Recommend rental car or airport transfer"),
        (r"check-in|boarding|bag", "Mobile check-in link + priority boarding upsell"),
        (r"welcome|activit", "Welcome message + top local activity recommendations"),
        (r"rebook", "One-tap rebooking link with fare protection"),
    ]
    for pattern, offer in patterns:
        if re.search(pattern, lower):
            return offer
    return "Personalized travel offer based on traveler profile"


def _detect_ambiguities(text: str, clauses: list[ConditionClause]) -> list[str]:
    ambiguities: list[str] = []
    lower = text.lower()

    unknown_terms = re.findall(r"@(\w+)", text)
    known_fields = set(FIELD_ALIASES.values()) | {c.field for c in clauses}
    for term in unknown_terms:
        if term not in known_fields:
            ambiguities.append(f"Unknown field reference '@{term}' — did you mean a golden-record attribute?")

    if not clauses:
        ambiguities.append("Could not map your description to specific profile conditions. Try mentioning fields like 'flight delay', 'cart abandoned', or 'Gold member'.")

    vague = ["soon", "recently", "often", "sometimes", "maybe"]
    for word in vague:
        if word in lower:
            ambiguities.append(f"Ambiguous time reference '{word}' — specify a threshold (e.g., '60 minutes', '24 hours', '2 searches').")

    if "member" in lower and not any(c.field == "one_key_tier" for c in clauses):
        ambiguities.append("'member' mentioned but tier not specified — clarify: Blue, Silver, Gold, or Platinum?")

    return ambiguities


def parse_trigger_text(text: str) -> ParsedTriggerDraft:
    text = text.strip()
    clauses: list[ConditionClause] = []

    for extractor in [_extract_tier_condition, _extract_delay_condition, _extract_search_condition, _extract_departure_condition, _extract_return_condition]:
        result = extractor(text)
        if result:
            clauses.append(result)

    clauses.extend(_extract_cart_condition(text))
    clauses.extend(_extract_landed_condition(text))

    if _extract_delay_condition(text):
        clauses.append(ConditionClause(field="flight_status", operator="==", value="Delayed", description="Flight is delayed"))

    if any(c.field == "days_to_departure" for c in clauses):
        clauses.append(ConditionClause(field="booking_status", operator="in", value=["Confirmed", "Pending"], description="Active booking exists"))

    # Deduplicate by field
    seen: set[str] = set()
    unique_clauses: list[ConditionClause] = []
    for c in clauses:
        key = f"{c.field}:{c.operator}:{c.value}"
        if key not in seen:
            seen.add(key)
            unique_clauses.append(c)
    clauses = unique_clauses

    ambiguities = _detect_ambiguities(text, clauses)
    lifecycle = _infer_lifecycle(text, clauses)
    channel = _infer_channel(text)
    priority = _infer_priority(text)
    offer = _extract_offer(text)

    # Generate name from trigger intent
    lower = text.lower()
    if "delay" in lower and "lounge" in lower:
        name = "Flight Delay — Lounge Access (Custom)"
    elif "delay" in lower:
        name = "Flight Delay Offer"
    elif "cart" in lower or "abandon" in lower:
        name = "Cart Abandonment Offer"
    elif "search" in lower or "destination" in lower:
        name = "Destination Search Trigger"
    elif "landed" in lower or "welcome" in lower:
        name = "Post-Arrival Welcome"
    elif "review" in lower or "return" in lower:
        name = "Post-Trip Review Request"
    elif "when" in lower:
        name = text.split("when", 1)[-1].strip()[:50].title()
    else:
        name = text[:50] + ("..." if len(text) > 50 else "")

    time_window = None
    if "24h" in text.lower() or "24 hour" in text.lower() or "24 hours" in text.lower():
        time_window = "24h"

    confidence = 1.0 if clauses and not ambiguities else (0.6 if clauses else 0.3)

    return ParsedTriggerDraft(
        name=name,
        lifecycle_phase=lifecycle,
        condition_human=text,
        condition_structured=StructuredCondition(
            event=lifecycle.lower().replace(" ", "_").replace("/", "_"),
            clauses=clauses,
            time_window=time_window,
        ),
        priority_tier=priority,
        suggested_channel=channel,
        nba_offer=offer,
        ambiguities=ambiguities,
        confidence=confidence,
    )


def get_field_dictionary() -> list[dict[str, Any]]:
    """Golden-record field dictionary for @ autocomplete."""
    return [
        {"field": "one_key_tier", "type": "Enum", "description": "Loyalty tier: Blue, Silver, Gold, Platinum"},
        {"field": "delay_minutes", "type": "Int", "description": "Minutes flight is delayed"},
        {"field": "flight_status", "type": "Enum", "description": "On Time, Delayed, Cancelled, Gate Change"},
        {"field": "searches_same_destination_24h", "type": "Int", "description": "Searches to same destination in 24h"},
        {"field": "cart_abandon_flag", "type": "Bool", "description": "Whether checkout was abandoned"},
        {"field": "cart_abandon_component", "type": "Enum", "description": "flight_only, hotel_only, package"},
        {"field": "days_to_departure", "type": "Int", "description": "Days until departure"},
        {"field": "booking_status", "type": "Enum", "description": "Confirmed, Pending, Cancelled, None"},
        {"field": "landed_flag", "type": "Bool", "description": "Traveler has landed at destination"},
        {"field": "at_airport_flag", "type": "Bool", "description": "Traveler is at airport"},
        {"field": "hours_since_return", "type": "Int", "description": "Hours since return flight"},
        {"field": "sms_opt_in_ts", "type": "Timestamp", "description": "SMS consent timestamp (TCPA)"},
        {"field": "email_subscription_status", "type": "Enum", "description": "Subscribed, Unsubscribed, Pending"},
        {"field": "channel_affinity_score_sms", "type": "Float", "description": "SMS open/click likelihood 0–1"},
        {"field": "channel_affinity_score_email", "type": "Float", "description": "Email open/click likelihood 0–1"},
        {"field": "clv_score", "type": "Int", "description": "Customer lifetime value score 0–100"},
        {"field": "travel_archetype", "type": "Enum", "description": "Behavioral segment"},
        {"field": "favorite_destinations", "type": "Array", "description": "Ranked favorite destinations"},
        {"field": "last_search_destination", "type": "IATA", "description": "Most recent search destination"},
        {"field": "in_quiet_hours", "type": "Bool", "description": "Currently in quiet hours window"},
    ]
