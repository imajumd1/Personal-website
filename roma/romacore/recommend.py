"""The explainable buy/wait rule engine.

Rules are ordered and the first match wins. Every result names the rule that
fired (``rule_fired``), the verdict, a confidence, and the arithmetic that got
it there. All numbers are computed here in Python; no language model is
involved in producing or adjusting any figure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

FLOOR_TOLERANCE = 1.005
BARGAIN_RATIO = 0.92
EXPENSIVE_RATIO = 1.12
LAST_CALL_DAYS = 14
EARLY_DAYS = 90


@dataclass
class Recommendation:
    rule_fired: str
    verdict: str  # "buy" | "wait" | "watch"
    headline: str
    confidence: str  # "low" | "medium" | "high"
    facts: list[str] = field(default_factory=list)
    inputs: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "rule_fired": self.rule_fired,
            "verdict": self.verdict,
            "headline": self.headline,
            "confidence": self.confidence,
            "facts": list(self.facts),
            "inputs": dict(self.inputs),
        }


RULE_CATALOGUE: tuple[tuple[str, str], ...] = (
    ("insufficient_history", "Too few price points on this query to call a trend."),
    ("at_or_below_observed_floor", "Today's cheapest fare matches or beats the lowest price on record."),
    ("well_below_median", "Today's cheapest fare sits materially below the median for this query."),
    ("departure_within_fortnight", "Departure is close enough that fares usually only climb."),
    ("far_above_median", "Today's cheapest fare is well above the median with time left to wait."),
    ("long_lead_time", "Departure is far enough out that the cheaper window has not opened yet."),
    ("near_median", "Today's cheapest fare is close to the median for this query."),
)


def _money(value: float, currency: str) -> str:
    return f"{currency} {value:,.0f}" if value >= 100 else f"{currency} {value:,.2f}"


def _pct(part: float, whole: float) -> str:
    if not whole:
        return "0%"
    return f"{abs(part - whole) / whole * 100:.0f}%"


def evaluate(
    *,
    current_price: float,
    stats: dict,
    depart_date: date,
    today: date,
    currency: str,
) -> Recommendation:
    """Run the rules in order and return the first one that fires."""
    days_out = (depart_date - today).days
    points = int(stats.get("points") or 0)
    observed = int(stats.get("observed_points") or 0)
    modeled = int(stats.get("modeled_points") or 0)
    floor = stats.get("min")
    mid = stats.get("median")
    ceiling = stats.get("max")

    inputs = {
        "current_price": round(current_price, 2),
        "currency": currency,
        "days_to_departure": days_out,
        "history_points": points,
        "observed_points": observed,
        "modeled_points": modeled,
        "history_min": floor,
        "history_median": mid,
        "history_max": ceiling,
        "window_days": stats.get("window_days"),
        "thresholds": {
            "bargain_ratio": BARGAIN_RATIO,
            "expensive_ratio": EXPENSIVE_RATIO,
            "last_call_days": LAST_CALL_DAYS,
            "early_days": EARLY_DAYS,
        },
    }

    provenance = (
        f"History for this query holds {points} price points "
        f"({observed} observed from real searches, {modeled} modelled by Roma)."
    )

    if not stats.get("has_trend") or floor is None or mid is None:
        return Recommendation(
            rule_fired="insufficient_history",
            verdict="watch",
            headline="Not enough history to advise yet.",
            confidence="low",
            facts=[
                provenance,
                f"Roma needs at least 5 points before it will call a trend; it has {points}.",
                f"Today's cheapest simulated fare is {_money(current_price, currency)}.",
            ],
            inputs=inputs,
        )

    if current_price <= floor * FLOOR_TOLERANCE:
        return Recommendation(
            rule_fired="at_or_below_observed_floor",
            verdict="buy",
            headline="This is the lowest Roma has seen for this query.",
            confidence="high" if observed else "medium",
            facts=[
                f"Today's cheapest simulated fare is {_money(current_price, currency)}.",
                f"The lowest price on record for this query is {_money(floor, currency)}.",
                f"The median across the history window is {_money(mid, currency)}.",
                provenance,
            ],
            inputs=inputs,
        )

    if current_price <= mid * BARGAIN_RATIO:
        return Recommendation(
            rule_fired="well_below_median",
            verdict="buy",
            headline="Priced below the usual level for this query.",
            confidence="medium",
            facts=[
                f"Today's cheapest simulated fare is {_money(current_price, currency)}, "
                f"{_pct(current_price, mid)} under the {_money(mid, currency)} median.",
                f"The lowest price on record is {_money(floor, currency)}.",
                f"Departure is {days_out} days away.",
                provenance,
            ],
            inputs=inputs,
        )

    if days_out <= LAST_CALL_DAYS:
        return Recommendation(
            rule_fired="departure_within_fortnight",
            verdict="buy",
            headline="Close to departure — waiting rarely helps here.",
            confidence="medium",
            facts=[
                f"Departure is {days_out} days away, inside the {LAST_CALL_DAYS}-day window "
                "where Roma's fare model raises prices sharply.",
                f"Today's cheapest simulated fare is {_money(current_price, currency)} "
                f"against a {_money(mid, currency)} median.",
                provenance,
            ],
            inputs=inputs,
        )

    if current_price >= mid * EXPENSIVE_RATIO:
        return Recommendation(
            rule_fired="far_above_median",
            verdict="wait",
            headline="Above the usual level, with time left to wait.",
            confidence="medium",
            facts=[
                f"Today's cheapest simulated fare is {_money(current_price, currency)}, "
                f"{_pct(current_price, mid)} over the {_money(mid, currency)} median.",
                f"The lowest price on record is {_money(floor, currency)}.",
                f"Departure is {days_out} days away, so there is room for the price to move.",
                provenance,
            ],
            inputs=inputs,
        )

    if days_out >= EARLY_DAYS:
        return Recommendation(
            rule_fired="long_lead_time",
            verdict="wait",
            headline="Early days — the cheaper window has not opened yet.",
            confidence="low",
            facts=[
                f"Departure is {days_out} days away, beyond the {EARLY_DAYS}-day mark.",
                f"Roma's fare model prices this query cheapest between 6 and 12 weeks out.",
                f"Today's cheapest simulated fare is {_money(current_price, currency)} "
                f"against a {_money(mid, currency)} median.",
                provenance,
            ],
            inputs=inputs,
        )

    return Recommendation(
        rule_fired="near_median",
        verdict="watch",
        headline="Ordinary pricing — nothing to act on today.",
        confidence="low",
        facts=[
            f"Today's cheapest simulated fare is {_money(current_price, currency)}, "
            f"within {_pct(current_price, mid)} of the {_money(mid, currency)} median.",
            f"The recorded range is {_money(floor, currency)} to {_money(ceiling, currency)}.",
            f"Departure is {days_out} days away.",
            provenance,
        ],
        inputs=inputs,
    )
