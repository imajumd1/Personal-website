"""The language seam.

Roma's default voice is deterministic templates (:class:`HeuristicNarrator`).
If an OpenAI-compatible endpoint is configured, :class:`LLMNarrator` may rephrase
the same already-computed facts into a friendlier sentence.

The hard rule: **the model never authors numbers.** It is given the numbers as
facts, told it may only reuse them verbatim, and its output is then scanned. Any
numeric token that was not in the supplied facts causes the draft to be thrown
away and the template answer used instead. Enforcement is in
:func:`unauthorised_numbers`, not in the prompt alone.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request

_NUMBER_RE = re.compile(r"\d+(?:[,\u202f\s]\d{3})*(?:\.\d+)?")

_SYSTEM_PROMPT = (
    "You are Roma, a flight-search agent. You will receive a JSON object of "
    "facts that were already computed by deterministic code. Write one or two "
    "short, plain sentences summarising them for a traveller.\n"
    "Hard rules:\n"
    "1. You must not invent, estimate, adjust, round or compute any number. "
    "Every digit you write must appear verbatim in the facts you were given.\n"
    "2. If a number is not in the facts, describe it in words or leave it out.\n"
    "3. Never claim a fare is real, live or bookable unless the facts say the "
    "data level is a live provider.\n"
    "4. No emoji, no exclamation marks, no urgency, no sales language.\n"
    "5. Do not add a greeting or a sign-off."
)


def _numbers_in(text: str) -> set[float]:
    found: set[float] = set()
    for match in _NUMBER_RE.finditer(text or ""):
        raw = re.sub(r"[,\u202f\s]", "", match.group(0))
        try:
            found.add(float(raw))
        except ValueError:
            continue
    return found


def allowed_numbers(facts) -> set[float]:
    """Every number the model is permitted to echo, plus rounded variants."""
    allowed: set[float] = set()

    def walk(node) -> None:
        if isinstance(node, bool) or node is None:
            return
        if isinstance(node, (int, float)):
            allowed.add(float(node))
            allowed.add(float(round(float(node))))
            allowed.add(round(float(node), 2))
            return
        if isinstance(node, str):
            allowed.update(_numbers_in(node))
            return
        if isinstance(node, dict):
            for value in node.values():
                walk(value)
            return
        if isinstance(node, (list, tuple, set)):
            for value in node:
                walk(value)

    walk(facts)
    # Digits inside dates and codes are already covered by the string walk.
    return allowed


def unauthorised_numbers(text: str, facts) -> list[float]:
    """Numbers in ``text`` that do not appear anywhere in ``facts``."""
    permitted = allowed_numbers(facts)
    offenders = []
    for number in sorted(_numbers_in(text)):
        if number in permitted:
            continue
        if any(abs(number - candidate) < 0.005 for candidate in permitted):
            continue
        offenders.append(number)
    return offenders


class HeuristicNarrator:
    """Deterministic phrasing. Always available, never surprising."""

    mode = "heuristic"
    configured = False

    def narrate(self, kind: str, facts: dict, fallback_text: str) -> tuple[str, dict]:
        return fallback_text, {"mode": self.mode, "used_model": False, "reason": None}

    def describe(self) -> dict:
        return {"mode": self.mode, "configured": False, "model": None}


class LLMNarrator:
    """Optional rephrasing layer, guarded so it cannot introduce numbers."""

    mode = "llm"
    configured = True

    def __init__(self, config) -> None:
        self.config = config

    def _call(self, facts: dict) -> str:
        body = json.dumps(
            {
                "model": self.config.llm_model,
                "temperature": 0.2,
                "max_tokens": 220,
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": json.dumps(facts, default=str)},
                ],
            }
        ).encode("utf-8")
        url = self.config.llm_base_url.rstrip("/") + "/chat/completions"
        req = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config.llm_api_key}",
            },
        )
        with urllib.request.urlopen(req, timeout=self.config.llm_timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        choices = payload.get("choices") or []
        if not choices:
            raise ValueError("no choices returned")
        return (choices[0].get("message") or {}).get("content", "").strip()

    def narrate(self, kind: str, facts: dict, fallback_text: str) -> tuple[str, dict]:
        try:
            draft = self._call({"kind": kind, **facts})
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError,
                json.JSONDecodeError, OSError) as exc:
            return fallback_text, {
                "mode": self.mode,
                "used_model": False,
                "reason": f"model call failed: {type(exc).__name__}",
            }
        if not draft:
            return fallback_text, {
                "mode": self.mode,
                "used_model": False,
                "reason": "model returned nothing",
            }
        offenders = unauthorised_numbers(draft, facts)
        if offenders:
            return fallback_text, {
                "mode": self.mode,
                "used_model": False,
                "reason": (
                    "draft rejected: model wrote numbers not present in the facts "
                    f"({', '.join(str(n) for n in offenders[:5])})"
                ),
            }
        return draft, {"mode": self.mode, "used_model": True, "reason": None}

    def describe(self) -> dict:
        return {"mode": self.mode, "configured": True, "model": self.config.llm_model}


def build_narrator(config):
    """The LLM when configured, otherwise heuristics. Heuristics are default."""
    if config.llm_configured:
        return LLMNarrator(config)
    return HeuristicNarrator()
