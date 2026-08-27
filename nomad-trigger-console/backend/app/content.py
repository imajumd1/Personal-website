"""Content personalization engine — generates SMS and Email copy."""

from __future__ import annotations

from .models import GoldenRecord, TriggerDefinition


def generate_sms(record: GoldenRecord, trigger: TriggerDefinition) -> str:
    name = record.display_first_name
    offer = trigger.nba_offer

    templates = {
        "TRG-101": f"Hi {name}! Prices to {record.last_search_destination or 'your destination'} just dropped. Save on flights + hotels — tap to see packages. Reply STOP to opt out.",
        "TRG-102": f"{name}, complete your trip! Top 3 hotels near your destination from ${int(record.total_booking_value * 0.15)}. Book in 15 min for extra savings. Reply STOP to opt out.",
        "TRG-104": f"Hi {name}! Check in now for tomorrow's flight from {record.preferred_home_airport}. Add priority boarding + checked bag from $29. Reply STOP to opt out.",
        "TRG-105": f"{name}, your flight is delayed {record.delay_minutes} min. We've reserved lounge access for you — tap to claim your pass or rebook instantly. Reply STOP to opt out.",
        "TRG-106": f"Welcome to {record.destination_city or 'your destination'}, {name}! 🌴 Top local experiences curated for you — tap to explore. Reply STOP to opt out.",
    }

    if trigger.trigger_id in templates:
        return templates[trigger.trigger_id]

    return f"Hi {name}! {offer} — personalized for your {record.travel_archetype} trip. Reply STOP to opt out."


def generate_email(record: GoldenRecord, trigger: TriggerDefinition) -> tuple[str, str]:
    name = record.display_first_name
    tier = record.one_key_tier
    cash = record.one_key_cash_balance

    subjects = {
        "TRG-101": f"{name}, prices dropped to {record.last_search_destination or 'your favorite destination'}",
        "TRG-102": f"Complete your trip, {name} — top hotel picks waiting",
        "TRG-103": f"Ground transport for your upcoming trip, {name}",
        "TRG-107": f"How was your stay, {name}? Share your review",
    }

    subject = subjects.get(trigger.trigger_id, f"{name}, your NOMAD travel offer awaits")

    body_parts = [
        f"Hi {name},",
        "",
        f"As a {tier} OneKey member, we have a personalized recommendation for you:",
        "",
        trigger.nba_offer,
        "",
    ]

    if "review" in trigger.nba_offer.lower() or trigger.trigger_id == "TRG-107":
        body_parts.extend([
            f"You earned ${cash:,.0f} OneKeyCash toward your next adventure!",
            "",
            "Share your experience and help fellow travelers.",
        ])
    elif "rental" in trigger.nba_offer.lower() or "transfer" in trigger.nba_offer.lower():
        body_parts.extend([
            f"Your trip from {record.preferred_home_airport} departs in {record.days_to_departure or 'soon'} days.",
            "Skip the taxi line — book airport transfer or rental car at member rates.",
        ])
    elif "price" in trigger.nba_offer.lower() or "package" in trigger.nba_offer.lower():
        body_parts.extend([
            f"You've been exploring {record.last_search_destination or 'great destinations'} —",
            "we found package savings based on your recent searches.",
        ])
    else:
        body_parts.append(f"Tailored for your {record.travel_archetype} travel style.")

    body_parts.extend([
        "",
        "— The NOMAD Team",
        "",
        "---",
        "You're receiving this because you subscribed to NOMAD travel updates.",
        "Unsubscribe | Manage Preferences | NOMAD Travel Inc., 123 Journey Way, San Francisco, CA",
    ])

    return subject, "\n".join(body_parts)
