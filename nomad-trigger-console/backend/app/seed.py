"""Generate 100 synthetic golden records and 7 baseline triggers."""

from __future__ import annotations

import hashlib
import random
import uuid
from datetime import datetime, timedelta

from .models import (
    Channel,
    ConditionClause,
    GoldenRecord,
    PriorityTier,
    StructuredCondition,
    TriggerDefinition,
    TriggerStatus,
)

FIRST_NAMES = [
    "Priya", "Marcus", "Elena", "James", "Aisha", "Chen", "Sofia", "David",
    "Amara", "Lucas", "Yuki", "Olivia", "Raj", "Emma", "Carlos", "Mei",
    "Noah", "Fatima", "Ethan", "Isabella", "Kwame", "Hannah", "Diego", "Lin",
    "Alexander", "Zara", "Benjamin", "Nadia", "Tyler", "Grace", "Omar", "Chloe",
    "Daniel", "Ava", "Kenji", "Mia", "Andre", "Lily", "Samuel", "Riya",
    "Michael", "Leila", "Chris", "Anna", "Jorge", "Kate", "Ryan", "Sana",
    "Kevin", "Nina", "Jason", "Tara", "Brian", "Jasmine", "Eric", "Violet",
    "Adam", "Maya", "Justin", "Claire", "Matt", "Diana", "Nick", "Ruby",
    "Tom", "Eva", "Alex", "Iris", "Jordan", "Luna", "Taylor", "Nova",
    "Casey", "Stella", "Morgan", "Jade", "Riley", "Pearl", "Quinn", "Rose",
    "Avery", "Sky", "Blake", "Wren", "Drew", "Fern", "Jamie", "Ivy",
    "Robin", "Sage", "Dakota", "River", "Phoenix", "Ocean", "Rowan", "Ash",
    "Harper", "Eden", "Reese", "Sloane", "Finley", "Emery", "Hayden", "Logan",
]

TIERS = ["Blue", "Silver", "Gold", "Platinum"]
ARCHETYPES = [
    "Family Vacationer", "Solo Business Traveler", "Weekend Escapist",
    "Group Traveler", "Luxury Seeker",
]
DESTINATIONS = [
    ("Maui, HI", "OGG"), ("Kyoto, JP", "KIX"), ("Paris, FR", "CDG"),
    ("Cancun, MX", "CUN"), ("London, UK", "LHR"), ("Barcelona, ES", "BCN"),
    ("New York, NY", "JFK"), ("Rome, IT", "FCO"), ("Bali, ID", "DPS"),
    ("Dubai, AE", "DXB"), ("Seattle, WA", "SEA"), ("Denver, CO", "DEN"),
    ("Miami, FL", "MIA"), ("Tokyo, JP", "NRT"), ("Sydney, AU", "SYD"),
]
AIRPORTS = ["SFO", "LAX", "ORD", "DFW", "ATL", "JFK", "SEA", "DEN", "MIA", "BOS"]
TIMEZONES = [
    "America/Los_Angeles", "America/New_York", "America/Chicago",
    "America/Denver", "Pacific/Honolulu", "Europe/London",
]


def _hash_email(name: str, idx: int) -> str:
    raw = f"{name.lower()}.{idx}@nomad-travel.demo"
    return hashlib.sha256(raw.encode()).hexdigest()


def _mask_phone(idx: int) -> str:
    return f"+1 •••-•••-{1000 + idx:04d}"[-15:]


def generate_golden_records(count: int = 100) -> list[GoldenRecord]:
    rng = random.Random(42)
    records: list[GoldenRecord] = []

    for i in range(count):
        name = FIRST_NAMES[i % len(FIRST_NAMES)]
        tier = rng.choices(TIERS, weights=[30, 35, 25, 10])[0]
        dest_idx = rng.randint(0, len(DESTINATIONS) - 1)
        dest_name, dest_iata = DESTINATIONS[dest_idx]
        has_sms = rng.random() > 0.15
        sms_ts = (datetime.utcnow() - timedelta(days=rng.randint(30, 400))).isoformat() + "Z" if has_sms else None
        email_status = rng.choices(["Subscribed", "Unsubscribed", "Pending"], weights=[85, 10, 5])[0]
        in_quiet = rng.random() < 0.12
        booking = rng.random() < 0.55
        flight_delayed = rng.random() < 0.08
        landed = rng.random() < 0.06
        cart_abandon = rng.random() < 0.15 and booking
        searches_24h = rng.randint(0, 4) if rng.random() < 0.2 else 0

        records.append(
            GoldenRecord(
                account_id=str(uuid.uuid4()),
                display_first_name=name,
                hashed_email=_hash_email(name, i),
                phone_masked=_mask_phone(i),
                one_key_tier=tier,
                one_key_cash_balance=round(rng.uniform(0, 2500), 2),
                preferred_home_airport=rng.choice(AIRPORTS),
                sms_opt_in_ts=sms_ts,
                email_subscription_status=email_status,
                quiet_hours_window="21:00–08:00",
                quiet_hours_timezone=rng.choice(TIMEZONES),
                last_search_origin=rng.choice(AIRPORTS),
                last_search_destination=dest_iata,
                last_search_dates=f"{(datetime.utcnow() + timedelta(days=rng.randint(14, 90))).strftime('%Y-%m-%d')}",
                property_detail_views_7d=rng.randint(0, 12),
                searches_same_destination_24h=searches_24h,
                cart_abandon_flag=cart_abandon,
                cart_abandon_component=rng.choice(["flight_only", "hotel_only"]) if cart_abandon else None,
                price_sensitivity_tier=rng.choice(["Budget", "Value", "Luxury"]),
                travel_archetype=rng.choice(ARCHETYPES),
                favorite_destinations=[dest_name] + [DESTINATIONS[rng.randint(0, len(DESTINATIONS) - 1)][0] for _ in range(rng.randint(0, 2))],
                active_booking_id=f"BK-{10000 + i}" if booking else None,
                booking_status=rng.choice(["Confirmed", "Pending"]) if booking else "None",
                component_types_booked=[rng.choice(["flight_only", "hotel_only", "package"])] if booking else [],
                total_booking_value=round(rng.uniform(200, 4500), 2) if booking else 0.0,
                days_to_departure=rng.randint(1, 45) if booking else None,
                flight_status="Delayed" if flight_delayed else rng.choice(["On Time", "On Time", "On Time", "Gate Change"]),
                delay_minutes=rng.randint(65, 180) if flight_delayed else 0,
                landed_flag=landed,
                at_airport_flag=flight_delayed or landed or rng.random() < 0.05,
                destination_city=dest_name.split(",")[0] if landed else None,
                hours_since_return=rng.randint(40, 72) if rng.random() < 0.1 else None,
                channel_affinity_score_sms=round(rng.uniform(0.2, 0.95), 2),
                channel_affinity_score_email=round(rng.uniform(0.2, 0.95), 2),
                propensity_insurance_purchase=round(rng.uniform(0.1, 0.9), 2),
                propensity_room_upgrade=round(rng.uniform(0.1, 0.9), 2),
                propensity_ground_transport=round(rng.uniform(0.1, 0.9), 2),
                clv_score=rng.randint(20, 98),
                clv_tier=rng.choice(["Bronze", "Silver", "Gold", "Platinum"]),
                predictive_personalization_opt_in=rng.random() > 0.08,
                local_time_at_location=datetime.utcnow().isoformat() + "Z",
                sms_sent_promotional_72h=rng.randint(0, 2),
                sms_sent_total_24h=rng.randint(0, 3),
                email_sent_marketing_24h=rng.randint(0, 2),
                in_quiet_hours=in_quiet,
            )
        )

    # Ensure at least one profile matches Priya sample from PRD
    records[0] = GoldenRecord(
        account_id=records[0].account_id,
        display_first_name="Priya",
        hashed_email=records[0].hashed_email,
        phone_masked=records[0].phone_masked,
        one_key_tier="Gold",
        one_key_cash_balance=1250.0,
        preferred_home_airport="SFO",
        sms_opt_in_ts="2025-11-02T14:20:00Z",
        email_subscription_status="Subscribed",
        quiet_hours_window="21:00–08:00",
        quiet_hours_timezone="America/Los_Angeles",
        last_search_destination="OGG",
        searches_same_destination_24h=3,
        favorite_destinations=["Maui, HI", "Kyoto, JP"],
        channel_affinity_score_sms=0.82,
        channel_affinity_score_email=0.47,
        price_sensitivity_tier="Value",
        clv_score=78,
        clv_tier="Gold",
        property_detail_views_7d=5,
        predictive_personalization_opt_in=True,
        local_time_at_location=datetime.utcnow().isoformat() + "Z",
        in_quiet_hours=False,
    )

    # Profile for quiet hours demo (commercial SMS blocked, no email fallback)
    records[1].in_quiet_hours = True
    records[1].sms_opt_in_ts = records[1].sms_opt_in_ts or datetime.utcnow().isoformat() + "Z"
    records[1].days_to_departure = 1
    records[1].booking_status = "Confirmed"
    records[1].active_booking_id = "BK-DEMO-QH"
    records[1].email_subscription_status = "Unsubscribed"
    records[1].display_first_name = "Marcus"

    # Profile for frequency cap demo (promotional SMS cap reached, no email fallback)
    records[2].sms_sent_promotional_72h = 1
    records[2].sms_opt_in_ts = records[2].sms_opt_in_ts or datetime.utcnow().isoformat() + "Z"
    records[2].cart_abandon_flag = True
    records[2].cart_abandon_component = "flight_only"
    records[2].email_subscription_status = "Unsubscribed"
    records[2].display_first_name = "Elena"

    return records


def get_baseline_triggers() -> list[TriggerDefinition]:
    now = datetime.utcnow()
    return [
        TriggerDefinition(
            trigger_id="TRG-101",
            name="Repeat Destination Search",
            lifecycle_phase="Inspiration / Search",
            condition_human="2+ searches to the same destination in 24h, no booking",
            condition_structured=StructuredCondition(
                event="search_repetition",
                clauses=[
                    ConditionClause(field="searches_same_destination_24h", operator=">=", value=2, description="Same destination searched 2+ times in 24h"),
                    ConditionClause(field="booking_status", operator="==", value="None", description="No active booking"),
                ],
                time_window="24h",
            ),
            priority_tier=PriorityTier.COMMERCIAL,
            suggested_channel=Channel.EMAIL,
            nba_offer="Price-drop alert or flight + hotel package savings",
            status=TriggerStatus.ACTIVE,
            created_by="Seed",
            last_modified=now,
            offer_value=75.0,
        ),
        TriggerDefinition(
            trigger_id="TRG-102",
            name="Cart Abandonment — Single Component",
            lifecycle_phase="Pre-Booking (Abandonment)",
            condition_human="Cart abandoned with a single component (e.g., flight booked, no hotel)",
            condition_structured=StructuredCondition(
                event="cart_abandon",
                clauses=[
                    ConditionClause(field="cart_abandon_flag", operator="==", value=True, description="Checkout was abandoned"),
                    ConditionClause(field="cart_abandon_component", operator="in", value=["flight_only", "hotel_only"], description="Single component in cart"),
                ],
            ),
            priority_tier=PriorityTier.COMMERCIAL,
            suggested_channel=Channel.SMS_OR_EMAIL,
            nba_offer="15-minute offer showing top 3 nearby hotel options",
            status=TriggerStatus.ACTIVE,
            created_by="Seed",
            last_modified=now,
            offer_value=120.0,
        ),
        TriggerDefinition(
            trigger_id="TRG-103",
            name="Pre-Trip Ground Transport",
            lifecycle_phase="Booking Confirmed",
            condition_human="Flight confirmed, 14 days before departure",
            condition_structured=StructuredCondition(
                event="pre_trip_ground",
                clauses=[
                    ConditionClause(field="booking_status", operator="==", value="Confirmed", description="Booking is confirmed"),
                    ConditionClause(field="days_to_departure", operator="==", value=14, description="Exactly 14 days to departure"),
                ],
            ),
            priority_tier=PriorityTier.COMMERCIAL,
            suggested_channel=Channel.EMAIL,
            nba_offer="Recommend rental car or airport transfer",
            status=TriggerStatus.ACTIVE,
            created_by="Seed",
            last_modified=now,
            offer_value=85.0,
        ),
        TriggerDefinition(
            trigger_id="TRG-104",
            name="24-Hour Pre-Departure Check-in",
            lifecycle_phase="Pre-Trip Prep",
            condition_human="24 hours to departure",
            condition_structured=StructuredCondition(
                event="pre_departure",
                clauses=[
                    ConditionClause(field="days_to_departure", operator="==", value=1, description="24 hours (1 day) to departure"),
                    ConditionClause(field="booking_status", operator="in", value=["Confirmed", "Pending"], description="Active booking exists"),
                ],
            ),
            priority_tier=PriorityTier.COMMERCIAL,
            suggested_channel=Channel.SMS,
            nba_offer="Mobile check-in link + priority boarding / checked-bag upsell",
            status=TriggerStatus.ACTIVE,
            created_by="Seed",
            last_modified=now,
            offer_value=45.0,
        ),
        TriggerDefinition(
            trigger_id="TRG-105",
            name="Flight Delay — Lounge Access",
            lifecycle_phase="Day of Travel (Disruption)",
            condition_human="Airline signals flight delay > 60 minutes",
            condition_structured=StructuredCondition(
                event="flight_delay",
                clauses=[
                    ConditionClause(field="flight_status", operator="==", value="Delayed", description="Flight is delayed"),
                    ConditionClause(field="delay_minutes", operator=">", value=60, description="Delay exceeds 60 minutes"),
                ],
            ),
            priority_tier=PriorityTier.OPERATIONAL,
            suggested_channel=Channel.SMS,
            nba_offer="Instant lounge-access pass or one-tap rebooking link",
            status=TriggerStatus.ACTIVE,
            created_by="Seed",
            last_modified=now,
            offer_value=200.0,
        ),
        TriggerDefinition(
            trigger_id="TRG-106",
            name="Post-Arrival Welcome",
            lifecycle_phase="Post-Arrival",
            condition_human="Flight-landed ping at destination airport",
            condition_structured=StructuredCondition(
                event="post_arrival",
                clauses=[
                    ConditionClause(field="landed_flag", operator="==", value=True, description="Traveler has landed"),
                    ConditionClause(field="at_airport_flag", operator="==", value=True, description="At destination airport"),
                ],
            ),
            priority_tier=PriorityTier.COMMERCIAL,
            suggested_channel=Channel.SMS,
            nba_offer="Welcome to [City] + top local activity recommendations",
            status=TriggerStatus.ACTIVE,
            created_by="Seed",
            last_modified=now,
            offer_value=60.0,
        ),
        TriggerDefinition(
            trigger_id="TRG-107",
            name="Post-Trip Review Request",
            lifecycle_phase="Post-Trip",
            condition_human="48 hours after return flight",
            condition_structured=StructuredCondition(
                event="post_trip",
                clauses=[
                    ConditionClause(field="hours_since_return", operator=">=", value=48, description="At least 48 hours since return"),
                ],
            ),
            priority_tier=PriorityTier.COMMERCIAL,
            suggested_channel=Channel.EMAIL,
            nba_offer="Request a property review + show OneKeyCash earned toward next trip",
            status=TriggerStatus.ACTIVE,
            created_by="Seed",
            last_modified=now,
            offer_value=30.0,
        ),
    ]
