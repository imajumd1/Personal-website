"""Decisioning & arbitration engine — Section 10 rules."""

from __future__ import annotations

from .models import Channel, GoldenRecord, PriorityTier, TriggerDefinition


def check_guardrails(
    record: GoldenRecord, trigger: TriggerDefinition, channel: str
) -> tuple[bool, str | None]:
    """Return (allowed, block_reason)."""
    is_operational = trigger.priority_tier == PriorityTier.OPERATIONAL

    if channel == "SMS":
        if not record.sms_opt_in_ts:
            return False, "TCPA: No SMS opt-in consent (sms_opt_in_ts is null)"

        if not is_operational and record.in_quiet_hours:
            return False, f"Quiet hours: Marketing SMS blocked during {record.quiet_hours_window} ({record.quiet_hours_timezone})"

        if not is_operational and record.sms_sent_promotional_72h >= 1:
            return False, "Frequency cap: Max 1 promotional SMS per 72 hours already reached"

        if record.sms_sent_total_24h >= 3:
            return False, "Frequency cap: Max 3 total SMS per 24 hours already reached"

    if channel == "Email":
        if record.email_subscription_status != "Subscribed":
            return False, f"CAN-SPAM: Email subscription status is '{record.email_subscription_status}'"

        if not is_operational and record.email_sent_marketing_24h >= 1:
            return False, "Frequency cap: Max 1 marketing email per 24 hours already reached"

    return True, None


def select_channel(
    record: GoldenRecord, trigger: TriggerDefinition
) -> tuple[str, str]:
    """Select channel and return (channel, reason)."""
    suggested = trigger.suggested_channel

    if suggested == Channel.EMAIL:
        return "Email", "Trigger configured for Email channel"

    if suggested == Channel.SMS:
        if record.sms_opt_in_ts:
            return "SMS", "Trigger configured for SMS; traveler has opt-in consent"
        return "Email", "SMS selected but no opt-in — automatic Email fallback (Rule 4)"

    # SMS if opted in, else Email
    is_urgent = (
        trigger.priority_tier == PriorityTier.OPERATIONAL
        or (record.days_to_departure is not None and record.days_to_departure < 1)
    )

    if is_urgent and record.sms_opt_in_ts:
        return "SMS", f"High urgency ({trigger.priority_tier.value}); SMS preferred for time-sensitive action"

    if trigger.nba_offer and any(kw in trigger.nba_offer.lower() for kw in ["hotel", "package", "options", "guide"]):
        if record.channel_affinity_score_email >= record.channel_affinity_score_sms:
            return "Email", "High complexity offer; Email preferred for multi-option content"

    if record.sms_opt_in_ts:
        if record.channel_affinity_score_sms > record.channel_affinity_score_email:
            return (
                "SMS",
                f"SMS affinity {record.channel_affinity_score_sms:.2f} > Email affinity {record.channel_affinity_score_email:.2f}",
            )
        if record.channel_affinity_score_email > record.channel_affinity_score_sms:
            return (
                "Email",
                f"Email affinity {record.channel_affinity_score_email:.2f} > SMS affinity {record.channel_affinity_score_sms:.2f}",
            )
        return "SMS", "Channel affinities tied; SMS selected for urgency"

    return "Email", "No SMS opt-in — automatic Email fallback (Rule 4)"


def get_arbitration_rules(trigger: TriggerDefinition) -> dict:
    cap_bucket = "Operational SMS exempt from promotional cap" if trigger.priority_tier == PriorityTier.OPERATIONAL else "Promotional SMS (max 1/72h)"
    return {
        "priority_tier": trigger.priority_tier.value,
        "priority_rule": "Operational triggers always outrank Commercial (Rule 1)",
        "frequency_cap_bucket": cap_bucket,
        "expected_value_formula": "Propensity Score × Offer Value (Rule 2)",
        "channel_routing": "Urgency → SMS; complexity → Email; affinity breaks ties (Rule 4)",
        "offer_value": trigger.offer_value,
    }
