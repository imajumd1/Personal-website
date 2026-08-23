"""Turning a computed recommendation into Roma's voice.

The default phraser is a template. An optional LLM phraser can rewrite the same
facts more fluently, but it is handed *only* the numbers the engine already computed,
and its output is rejected outright if it contains any figure that was not in that
handoff. A model can therefore change the wording and never the arithmetic.
"""

from __future__ import annotations

import re

from .llm import LLMUnavailable, get_llm_client
from .models import SearchQuery
from .recommendation import Recommendation

NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)*")

VERDICT_OPENERS = {
    "buy_now": "Book it.",
    "wait": "Wait.",
    "watch_closely": "Watch this one.",
    "exceptional_price": "This is a genuinely good price.",
    "insufficient_data": "Roma cannot call this one.",
}


class Phraser:
    name = "template"

    def phrase(self, query: SearchQuery, rec: Recommendation) -> str:
        raise NotImplementedError


class TemplatePhraser(Phraser):
    """Deterministic sentences assembled from the engine's own fields."""

    name = "template"

    def phrase(self, query: SearchQuery, rec: Recommendation) -> str:
        lines = [
            f"{VERDICT_OPENERS.get(rec.verdict, rec.verdict_label)} "
            f"Verdict: {rec.verdict_label.lower()}, confidence {rec.confidence}."
        ]
        lines.extend(rec.reasoning)
        if rec.dollars_at_stake:
            lines.append(f"About ${rec.dollars_at_stake:,.0f} is at stake. {rec.dollars_basis}")
        else:
            lines.append(rec.dollars_basis or "Nothing measurable is at stake on the numbers Roma has.")
        lines.append(f"Look again by {rec.revisit_by}. {rec.revisit_reason}")
        if rec.confidence_notes:
            lines.append("Why confidence is capped at low: " + " ".join(rec.confidence_notes))
        return "\n".join(line.strip() for line in lines if line and line.strip())


class LLMPhraser(Phraser):
    """Optional rewrite of the template output. Numbers are policed, not trusted."""

    name = "llm"

    def __init__(self, client, fallback: Phraser):
        self.client = client
        self.fallback = fallback
        self.name = f"llm:{client.provider}"

    def phrase(self, query: SearchQuery, rec: Recommendation) -> str:
        baseline = self.fallback.phrase(query, rec)
        facts = _facts_block(query, rec)
        try:
            text = self.client.complete_text(
                system=(
                    "You are Roma, a calm, factual flight-search assistant. Rewrite the supplied "
                    "facts as 3-5 short sentences of plain English. Use only the numbers, dates and "
                    "names given. Never invent a price, a percentage, a date, or a verdict. Never add "
                    "urgency, scarcity, or marketing language. No emoji, no exclamation marks."
                ),
                user=facts,
            )
        except LLMUnavailable:
            return baseline

        if not _numbers_are_allowed(text, facts):
            return baseline
        if len(text) > 1200:
            return baseline
        return text.strip()


def _facts_block(query: SearchQuery, rec: Recommendation) -> str:
    parts = [
        f"route: {query.origin} to {query.destination}",
        f"depart: {query.depart_date}",
        f"return: {query.return_date or 'one way'}",
        f"passengers: {query.passengers}",
        f"cabin: {query.cabin}",
        f"verdict: {rec.verdict_label}",
        f"confidence: {rec.confidence}",
        f"rule_fired: {rec.rule_fired}",
        f"cheapest_total: {rec.best_price}",
        f"cheapest_per_person: {rec.price_per_person}",
        f"dollars_at_stake: {rec.dollars_at_stake}",
        f"dollars_basis: {rec.dollars_basis}",
        f"revisit_by: {rec.revisit_by}",
        f"revisit_reason: {rec.revisit_reason}",
        f"observation_days: {rec.observation_days}",
        f"percentile: {rec.percentile if rec.percentile is not None else 'not available'}",
        f"median_seen: {rec.median_seen if rec.median_seen is not None else 'not available'}",
        f"simulated_data: {rec.simulated}",
        "reasoning: " + " ".join(rec.reasoning),
        "confidence_notes: " + " ".join(rec.confidence_notes),
    ]
    return "\n".join(parts)


def _numbers_are_allowed(text: str, facts: str) -> bool:
    """Reject any figure the engine did not put in the facts handoff."""
    allowed = {_normalize_number(n) for n in NUMBER_RE.findall(facts)}
    for token in NUMBER_RE.findall(text):
        if _normalize_number(token) not in allowed:
            return False
    return True


def _normalize_number(token: str) -> str:
    token = token.replace(",", "")
    if "." in token:
        token = token.rstrip("0").rstrip(".")
    return token.lstrip("0") or "0"


def get_phraser() -> Phraser:
    template = TemplatePhraser()
    client = get_llm_client()
    if client is None:
        return template
    return LLMPhraser(client, template)
