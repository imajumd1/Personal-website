"""The buy/wait engine — the part of Roma that is not a black box.

Every verdict carries the rule that produced it (``rule_fired``), the sentences behind
it, the dollar amount at stake and what that amount means, a date to look again, and a
confidence level that is *capped at low* whenever the underlying data is simulated,
thin, or stale. Percentiles are only ever quoted with at least five observation days.

All arithmetic lives here. No language model is consulted, and none can override a
verdict: the phrasing layer receives this object already computed.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field, asdict

from .models import FareOffer, SearchQuery, parse_iso_date

MIN_DAYS_FOR_PERCENTILE = 5
STALE_AFTER_DAYS = 14

VERDICT_LABELS = {
    "buy_now": "Buy now",
    "wait": "Wait",
    "watch_closely": "Watch closely",
    "exceptional_price": "Exceptional price",
    "insufficient_data": "Not enough data",
}

CONFIDENCE_ORDER = ["low", "medium", "high"]


@dataclass
class Recommendation:
    verdict: str
    rule_fired: str
    confidence: str
    confidence_notes: list[str] = field(default_factory=list)
    reasoning: list[str] = field(default_factory=list)
    dollars_at_stake: float = 0.0
    dollars_basis: str = ""
    revisit_by: str = ""
    revisit_reason: str = ""
    best_price: float | None = None
    price_per_person: float | None = None
    currency: str = "USD"
    percentile: float | None = None
    observation_days: int = 0
    median_seen: float | None = None
    low_seen: float | None = None
    high_seen: float | None = None
    trend: str | None = None
    simulated: bool = True
    passengers: int = 1

    @property
    def verdict_label(self) -> str:
        return VERDICT_LABELS.get(self.verdict, self.verdict)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["verdict_label"] = self.verdict_label
        return data


def recommend(query: SearchQuery, offers: list[FareOffer], stats: dict, percentile: float | None) -> Recommendation:
    """Compute the verdict. Pure function of its inputs — safe to unit test."""
    today = dt.date.today()
    depart = parse_iso_date(query.depart_date) or today
    days_ahead = max(0, (depart - today).days)
    simulated = any(o.simulated for o in offers) if offers else True

    if not offers:
        rec = Recommendation(
            verdict="insufficient_data",
            rule_fired="no_offers_returned",
            confidence="low",
            reasoning=["No priced itineraries came back for this route and date, so there is nothing to judge."],
            dollars_basis="No fares to compare.",
            revisit_by=_clamp(today + dt.timedelta(days=1), today, depart),
            revisit_reason="Try again with a nearby date or a different airport pair.",
            simulated=simulated,
            passengers=query.passengers,
        )
        rec.confidence_notes.append("No data at all: confidence is low by definition.")
        return rec

    best = offers[0]
    per_person = round(best.price / max(1, query.passengers), 2)
    prices = sorted(round(o.price / max(1, query.passengers), 2) for o in offers)
    spread = round(prices[-1] - prices[0], 2)
    observation_days = int(stats.get("observation_days") or 0)
    median = stats.get("median")
    trend = stats.get("trend")

    reasoning: list[str] = [
        f"Cheapest option Roma found: {_money(per_person)} per person"
        + (f", {_money(best.price)} for {query.passengers} passengers" if query.passengers > 1 else "")
        + f", on {best.airline_name}, {'nonstop' if best.stops == 0 else str(best.stops) + ' stop'}."
    ]

    if percentile is None:
        reasoning.append(
            f"Roma has {observation_days} day{'' if observation_days == 1 else 's'} of price history for this "
            f"route and date — fewer than the {MIN_DAYS_FOR_PERCENTILE} needed to place today's fare in a "
            "percentile, so no percentile is quoted."
        )
    else:
        reasoning.append(
            f"Across {observation_days} observation days, today's cheapest fare sits at the "
            f"{_ordinal(percentile)} percentile of what Roma has seen (median {_money(median)})."
        )
        if trend:
            reasoning.append(f"The daily low has been {trend} over that window.")

    verdict, rule, confidence, extra, dollars, basis, revisit_days, revisit_reason = _apply_rules(
        days_ahead=days_ahead,
        percentile=percentile,
        median=median,
        per_person=per_person,
        spread=spread,
        trend=trend,
        passengers=query.passengers,
    )
    reasoning.extend(extra)

    rec = Recommendation(
        verdict=verdict,
        rule_fired=rule,
        confidence=confidence,
        reasoning=reasoning,
        dollars_at_stake=dollars,
        dollars_basis=basis,
        revisit_by=_clamp(today + dt.timedelta(days=revisit_days), today, depart),
        revisit_reason=revisit_reason,
        best_price=round(best.price, 2),
        price_per_person=per_person,
        currency=best.currency,
        percentile=percentile,
        observation_days=observation_days,
        median_seen=median,
        low_seen=stats.get("min"),
        high_seen=stats.get("max"),
        trend=trend,
        simulated=simulated,
        passengers=query.passengers,
    )
    _cap_confidence(rec, query, stats, simulated)
    return rec


def _apply_rules(
    *,
    days_ahead: int,
    percentile: float | None,
    median: float | None,
    per_person: float,
    spread: float,
    trend: str | None,
    passengers: int,
):
    """Return the first matching rule's outputs. Order is the policy."""
    history_dollars = round(abs(per_person - median) * passengers, 2) if median is not None else 0.0
    history_basis = "Difference between this fare and the median fare Roma has recorded for this route and date."
    spread_dollars = round(spread * passengers, 2)
    spread_basis = (
        "Gap between the cheapest and most expensive option in this search — what choosing badly costs today, "
        "not a forecast."
    )

    if percentile is not None and percentile <= 10:
        return (
            "exceptional_price", "history_bottom_decile", "medium",
            ["This is in the bottom tenth of everything Roma has recorded for this route and date."],
            history_dollars, history_basis, 1,
            "Fares this low rarely hold: check again tomorrow only if you are not ready to book.",
        )
    if percentile is not None and percentile <= 30:
        return (
            "buy_now", "history_low_percentile", "medium",
            ["Today's fare is in the cheaper third of Roma's record for this route, and waiting has historically cost more than it saved."],
            history_dollars, history_basis, 2,
            "Two days is enough to confirm nothing cheaper appears.",
        )
    if percentile is not None and percentile >= 70 and days_ahead >= 21:
        return (
            "wait", "history_high_percentile_with_runway", "medium",
            [f"Today's fare is in the expensive third of Roma's record, and there are {days_ahead} days before departure — enough runway for a better fare to appear."],
            history_dollars, history_basis, 7,
            "A week is long enough for a fare drop to show up while still leaving booking time.",
        )
    if percentile is not None and percentile >= 70:
        return (
            "watch_closely", "history_high_percentile_short_runway", "low",
            [f"The fare is high against Roma's record, but only {days_ahead} days remain, and fares in the final three weeks usually rise rather than fall."],
            history_dollars, history_basis, 1,
            "Check daily; inside three weeks a better fare is unlikely but not impossible.",
        )
    if percentile is not None:
        return (
            "watch_closely", "history_mid_percentile", "medium",
            ["Today's fare is mid-range against Roma's record: no clear signal either way."],
            history_dollars, history_basis, 3,
            "Three days is a reasonable interval for a mid-range fare.",
        )

    # -- cold start: no usable history for this route+date yet ---------------
    if days_ahead <= 6:
        return (
            "buy_now", "cold_start_departure_imminent", "low",
            [f"Departure is {days_ahead} day{'' if days_ahead == 1 else 's'} out. Roma does not have enough history for this route to place the fare, and the reliable pattern is that fares inside a week rise, not fall."],
            spread_dollars, spread_basis, 1,
            "There is effectively no time left for prices to improve.",
        )
    if days_ahead <= 13:
        return (
            "buy_now", "cold_start_inside_two_weeks", "low",
            [f"Departure is {days_ahead} days out. Roma cannot place this fare against history yet, and the last two weeks before departure is where fares typically climb."],
            spread_dollars, spread_basis, 2,
            "Booking soon avoids the usual last-fortnight increase.",
        )
    if days_ahead <= 89:
        return (
            "watch_closely", "cold_start_in_booking_window", "low",
            [f"Departure is {days_ahead} days out, inside the window where fares normally move most. Roma does not have enough history for this route to read a direction, so it will not guess one."],
            spread_dollars, spread_basis, 5,
            "Roma records every search: five days from now it will have real history for this route.",
        )
    return (
        "wait", "cold_start_far_horizon", "low",
        [f"Departure is {days_ahead} days out. Fares this far ahead are usually unoptimized placeholders, and there is plenty of time for a better one."],
        spread_dollars, spread_basis, 14,
        "Nothing is decided this far out; look again in two weeks.",
    )


def _cap_confidence(rec: Recommendation, query: SearchQuery, stats: dict, simulated: bool) -> None:
    """Hard cap: simulated, thin, stale, or approximate input can never exceed low."""
    caps: list[str] = []
    if simulated:
        caps.append("Fares in this search are simulated, not live market quotes.")
    if rec.observation_days < MIN_DAYS_FOR_PERCENTILE:
        caps.append(
            f"Only {rec.observation_days} observation day"
            f"{'' if rec.observation_days == 1 else 's'} of history for this route and date."
        )
    stale = stats.get("stale_days")
    if isinstance(stale, int) and stale > STALE_AFTER_DAYS:
        caps.append(f"The newest observation for this route is {stale} days old.")
    if query.date_precision != "exact":
        caps.append("The travel date was inferred from an approximate phrase, so the fare may not be the one you want.")

    if caps:
        rec.confidence = "low"
        rec.confidence_notes = caps


def _clamp(target: dt.date, today: dt.date, depart: dt.date) -> str:
    """Revisit dates must be in the future and before departure."""
    latest = depart - dt.timedelta(days=1)
    if latest < today:
        latest = today
    if target > latest:
        target = latest
    if target < today:
        target = today
    return target.isoformat()


def _money(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"${value:,.0f}" if float(value).is_integer() or value >= 100 else f"${value:,.2f}"


def _ordinal(value: float) -> str:
    number = int(round(value))
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"
