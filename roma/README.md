# Roma — flight search agent

Roma is a flight-search agent built into this site. It takes a route in plain language or
from a form, returns fares, explains whether the fare is worth taking today, and hands the
same search to Kayak, Google Flights, Expedia, and Priceline.

Python 3 standard library only: no pip installs, no third-party packages, no build step.

## Run it

```bash
cd website        # repo root
python3 server.py
```

Then open **http://127.0.0.1:8080/roma.html** (also linked from the site nav under *More → Roma*).

Two entry points, one backend:

- **Chat** — “cheapest way to get two of us to Tokyo in early March”. Roma parses what it
  can, asks a specific question for anything missing, and remembers the conversation so the
  next message completes the search.
- **Form** — From, To, depart, optional return, passengers, cabin, and an airline dropdown
  whose *Other* option reveals a free-text field. Airport fields accept IATA codes and city
  names with typeahead.

Both call the same `RomaService.search`, the same provider set, and the same recommendation
engine. There is no second code path behind the chat.

## The fares are simulated

**Prices are locally generated demonstration data, not live quotes.** They are deterministic
(same query, same fares) and derived from great-circle distance, cabin, advance-purchase
window, seasonality, and a per-airline factor. Simulated data is labelled in three places so
a demo price cannot be mistaken for a real one:

1. a banner at the top of the page,
2. a `Simulated` badge on every result row, and
3. `simulated: true` in the API response, on each offer and on the search as a whole.

Every price also carries its provenance: the source that produced it and the retrieval
timestamp.

Roma does **not** scrape Kayak, Expedia, Google Flights, or Priceline. Their terms prohibit
automated access, they defend against it, and scraped prices would be brittle and
misleading. Instead Roma builds a correct pre-filled search URL for each so one click
continues on the real site.

## Buy or wait, and why

The recommendation is deliberately not a black box. Every verdict carries:

| Field | Meaning |
|-------|---------|
| `verdict` | `buy_now`, `wait`, `watch_closely`, `exceptional_price`, or `insufficient_data` |
| `rule_fired` | the exact rule that produced the verdict, so it is auditable |
| `confidence` | `low`, `medium`, or `high` — **hard-capped at low** whenever data is simulated, thin, stale, or the date was inferred from a vague phrase |
| `reasoning` | plain-language sentences, including what Roma does *not* know |
| `dollars_at_stake` + `dollars_basis` | the amount and what the amount actually measures |
| `revisit_by` + `revisit_reason` | a concrete date to look again, always before departure |
| `percentile` | omitted entirely with fewer than five observation days |

Percentiles are never quoted from a thin sample: with fewer than five distinct observation
days Roma says so in words and falls back to structural rules (how far out the departure
is), which are labelled `cold_start_*`.

## Price history (SQLite)

Every search records its offers in `data/roma_history.db` (gitignored — it is local runtime
data). Aggregates feed straight back into the engine.

Sample size is measured in **distinct observation days**, not rows: one search returning
eight offers is one look at the market, not eight. History therefore genuinely improves with
repeated use, and the cold-start path is explicit rather than invented certainty.

## Amadeus (optional, real)

Sources sit behind `roma/providers/base.py`, so a new one can be added without touching the
UI or the recommendation engine. `roma/providers/amadeus.py` is a real adapter — OAuth2
client-credentials token, `GET /v2/shopping/flight-offers`, `urllib.request`, offer parsing
— activated only by environment variables:

| Variable | Purpose |
|----------|---------|
| `AMADEUS_CLIENT_ID` | API key |
| `AMADEUS_CLIENT_SECRET` | API secret |
| `AMADEUS_HOST` | `test.api.amadeus.com` (default) or `api.amadeus.com` |
| `AMADEUS_TIMEOUT` | request timeout in seconds, default 10 |

No credentials are committed. Without them the provider reports itself unavailable and Roma
runs fully offline on simulated fares. A provider that errors is recorded and skipped; the
search still returns what the others produced.

## LLM seam (optional, off by default)

Two narrow interfaces, both defaulting to local implementations:

- **intent parser** — natural language → structured query. Default: regex and keyword
  heuristics (`roma/intent.py`).
- **phraser** — computed recommendation → plain-language explanation. Default: templates
  (`roma/phrasing.py`).

| Variable | Purpose |
|----------|---------|
| `ROMA_LLM_PROVIDER` | `openai` or `anthropic`. Unset means no LLM is used at all |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | credentials for the chosen provider |
| `ROMA_LLM_MODEL` | optional model override |
| `ROMA_LLM_TIMEOUT` | seconds, default 8 |

With none of these set, Roma is fully heuristic and never makes a network call.

### The model never authors a number

This is enforced by code structure, not by a comment:

- The LLM client exposes exactly two calls, and neither has access to fares, history, or the
  engine.
- A structured query from the LLM path is rebuilt field by field, unknown keys are dropped,
  and it must pass the same `roma.models.validate` gate as the form — valid IATA codes, sane
  dates, sane passenger counts — or the heuristic parse is used instead.
- Prices, the verdict, dollars at stake, and the revisit date are always computed by
  `roma/recommendation.py`. The phraser receives them already computed, and any rewrite
  containing a figure that was not in that handoff is rejected in favour of the template.
- Every failure mode — no key, timeout, bad status, unparseable output — degrades to the
  heuristic path.

## API

| Endpoint | Method | Notes |
|----------|--------|-------|
| `/api/roma/search` | POST | `{origin, destination, depart_date, return_date, passengers, cabin, airline, airline_other}` → results, recommendation, deep links, history, provenance. `400` with `field_errors` when invalid |
| `/api/roma/chat` | POST | `{message, conversation_id}` → `{reply, needs, slots, search}`; `search` is populated once every required slot is filled |
| `/api/roma/airports` | GET | `?q=` typeahead over the airport table |
| `/api/roma/airlines` | GET | dropdown options, including `OTHER` |
| `/api/roma/status` | GET | which providers, parser, and phraser are live |

All responses use the site's existing `{"ok": ...}` envelope.

## Layout

```
roma/
├── models.py          value objects + the single validation gate
├── airports.py        IATA/city table with coordinates
├── airlines.py        carrier table
├── dates.py           exact and vague date language
├── intent.py          heuristic parser + validated LLM parser
├── llm.py             optional LLM client (two capabilities only)
├── providers/
│   ├── base.py        provider interface
│   ├── simulated.py   deterministic synthetic fares
│   └── amadeus.py     real Amadeus adapter
├── deeplinks.py       Kayak / Google Flights / Expedia / Priceline URLs
├── history.py         SQLite observed-fare history
├── recommendation.py  buy/wait rules, rule_fired, confidence caps
├── phrasing.py        template phrasing + policed LLM rewrite
├── service.py         the one search path, plus conversation state
└── tests/test_roma.py unit tests
```

## Tests

```bash
cd website
python3 -m unittest discover -s roma/tests -t .
```

Covers date language, intent extraction, validation rules, deterministic fares, deep-link
shapes, the percentile gate, confidence capping, the LLM number guard, chat slot filling,
and that chat and form produce identical results for the same query.
