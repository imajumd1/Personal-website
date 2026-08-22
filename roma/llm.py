"""Optional LLM seam. Off by default; heuristics run when nothing is configured.

Configuration (environment only — never committed):

* ``ROMA_LLM_PROVIDER`` — ``openai`` or ``anthropic``. Unset means no LLM at all.
* ``OPENAI_API_KEY`` / ``ANTHROPIC_API_KEY`` — credentials for the chosen provider.
* ``ROMA_LLM_MODEL`` — optional model override.
* ``ROMA_LLM_TIMEOUT`` — seconds, default 8.

The client exposes exactly two capabilities: return JSON for an intent parse, and
return prose for a phrasing pass. It has no access to fares, history, or the
recommendation engine, so a model cannot author a number that reaches the user:
callers re-validate structured output and reject prose containing unknown figures.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


class LLMUnavailable(RuntimeError):
    """Raised for any failure — unset key, timeout, bad status, unparseable body."""


class LLMClient:
    def __init__(self, provider: str, api_key: str, model: str, timeout: float):
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    # -- transport ----------------------------------------------------------

    def _post(self, url: str, payload: dict, headers: dict) -> dict:
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(url, data=body, method="POST")
        request.add_header("Content-Type", "application/json")
        for key, value in headers.items():
            request.add_header(key, value)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, ValueError) as exc:
            raise LLMUnavailable(f"{self.provider} request failed: {exc}") from exc

    def _complete(self, system: str, user: str, max_tokens: int) -> str:
        if self.provider == "anthropic":
            data = self._post(
                "https://api.anthropic.com/v1/messages",
                {
                    "model": self.model,
                    "max_tokens": max_tokens,
                    "system": system,
                    "messages": [{"role": "user", "content": user}],
                },
                {"x-api-key": self.api_key, "anthropic-version": "2023-06-01"},
            )
            blocks = data.get("content") or []
            text = "".join(b.get("text", "") for b in blocks if isinstance(b, dict))
        else:
            data = self._post(
                "https://api.openai.com/v1/chat/completions",
                {
                    "model": self.model,
                    "max_tokens": max_tokens,
                    "temperature": 0,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                },
                {"Authorization": f"Bearer {self.api_key}"},
            )
            choices = data.get("choices") or []
            text = (choices[0].get("message", {}).get("content") if choices else "") or ""
        text = text.strip()
        if not text:
            raise LLMUnavailable(f"{self.provider} returned an empty completion")
        return text

    # -- capabilities -------------------------------------------------------

    def complete_json(self, system: str, user: str, max_tokens: int = 400) -> dict:
        text = self._complete(system, user, max_tokens)
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            raise LLMUnavailable("no JSON object in completion")
        try:
            parsed = json.loads(text[start:end + 1])
        except ValueError as exc:
            raise LLMUnavailable(f"unparseable JSON: {exc}") from exc
        if not isinstance(parsed, dict):
            raise LLMUnavailable("JSON was not an object")
        return parsed

    def complete_text(self, system: str, user: str, max_tokens: int = 320) -> str:
        return self._complete(system, user, max_tokens)


DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-haiku-latest",
}
KEY_VARS = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}


def llm_status() -> dict:
    provider = os.environ.get("ROMA_LLM_PROVIDER", "").strip().lower()
    if not provider:
        return {"configured": False, "provider": None, "reason": "ROMA_LLM_PROVIDER not set"}
    if provider not in DEFAULT_MODELS:
        return {"configured": False, "provider": provider, "reason": f"unknown provider “{provider}”"}
    if not os.environ.get(KEY_VARS[provider], "").strip():
        return {"configured": False, "provider": provider, "reason": f"{KEY_VARS[provider]} not set"}
    return {"configured": True, "provider": provider, "reason": ""}


def get_llm_client() -> LLMClient | None:
    status = llm_status()
    if not status["configured"]:
        return None
    provider = status["provider"]
    try:
        timeout = float(os.environ.get("ROMA_LLM_TIMEOUT", "8"))
    except ValueError:
        timeout = 8.0
    return LLMClient(
        provider=provider,
        api_key=os.environ[KEY_VARS[provider]].strip(),
        model=os.environ.get("ROMA_LLM_MODEL", "").strip() or DEFAULT_MODELS[provider],
        timeout=timeout,
    )
