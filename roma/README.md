# Roma

Roma is a standalone flight-search agent. You tell it a route and a date, in a
sentence or in a form, and it prices the trip, tells you whether today's price
looks worth taking, names the rule it used to decide, and hands you off to real
booking sites to check.

It runs as its own application on its own port. It is not part of any other
website, it has no build step, and it needs nothing outside the Python 3
standard library.

> **The fares are simulated.** Roma generates them with its own model. They are
> not market prices, they are not bookable, and they should not be used to plan
> a real purchase. This is stated in the interface at three levels: a standing
> notice on the page, a statement on every result set, and a badge on every
> individual price.

---

## Running it

```bash
cd roma
python3 run.py
```

Then open **<http://127.0.0.1:8787/>**.

No dependencies to install, no virtualenv required. Python 3.10 or newer.

### Choosing a port

The default is `8787`. Any of these override it, in order of priority:

```bash
python3 run.py --port 9000
ROMA_PORT=9000 python3 run.py
PORT=9000 python3 run.py          # so it works on hosts that inject $PORT
```

`--host` (or `ROMA_HOST`) changes the bind address; it defaults to `127.0.0.1`.

### One-shot searches from the command line

The CLI goes through the same engine as the web interface, so the two cannot
give different answers:

```bash
python3 run.py search --from SFO --to LHR --depart 2026-10-12 \
                      --return 2026-10-20 --airline BA
```

`--from` and `--to` take a city name or an IATA code. Add `--cabin business`,
`--adults 2`, or `--json` for the raw API payload. Leave `--return` off for a
one-way. It exits non-zero if the query fails validation.

### Tests

```bash
cd roma && python3 -m unittest discover
```

89 tests, standard library only, no network. They cover the three validation
rules, airport and airline resolution, fare-model determinism, each buy/wait
rule, price-history bucketing and de-duplication, the guard that stops a
language model authoring numbers, sentence parsing, multi-turn slot filling,
deep-link construction, and the HTTP surface including its refusal to serve
files outside its own directory.

---

## The two ways in

Both entry points build the same request object and call the same
`Engine.run`. There is one search implementation, not two.

**Conversation.** Type what you want. Roma extracts the route, the dates, the
airline, the cabin and the party size, and asks for whatever is missing one item
at a time:

```
you  : I want to go to Miami
Roma : Got to Miami (MIA). Which airport are you flying from?
you  : from Boston, leaving November 3 and back November 10
Roma : Boston (BOS) to Miami (MIA), 2026-11-03, returning 2026-11-10: the
       cheapest of 6 options is USD 406 on Southwest Airlines, 1 stop.
       Simulated estimate. Book it — this is the lowest Roma has seen for this
       query. (rule: at_or_below_observed_floor)
```

It understands ISO dates, `November 3`, `3 Nov`, `11/3`, `tomorrow`,
`next month`, `in 3 weeks`, `next friday`, `for 5 nights`, `one way`,
`business class`, `2 adults`, and airline names or codes. When it cannot find a
place or a date in your message it says so and asks again — it never guesses,
and it never silently re-runs your previous search.

**Form.** The same query as fields, with an accessible airport typeahead, a
round-trip/one-way toggle, cabin, party size, and an airline picker whose
**Other** option lets you name a carrier Roma does not list. If Roma has no
reference data for that carrier it prices it with a neutral airline index and
says so on every fare rather than quietly ignoring you.

---

## What Roma actually tells you

### Buy or wait, and why

Roma runs an ordered set of rules and reports the first one that fires as
`rule_fired`, along with the verdict, a confidence, and the arithmetic behind
it. The rules, in order:

| `rule_fired` | Verdict | Fires when |
|---|---|---|
| `insufficient_history` | watch | Fewer than 5 price points for this query |
| `at_or_below_observed_floor` | buy | Today's cheapest is at or under the lowest on record |
| `well_below_median` | buy | Today's cheapest is 8% or more under the median |
| `departure_within_fortnight` | buy | 14 days or fewer to departure |
| `far_above_median` | wait | 12% or more over the median with time left |
| `long_lead_time` | wait | 90 days or more to departure |
| `near_median` | watch | Anything else |

Every number in a recommendation is computed in Python from the price history
and the fare model. Nothing about the verdict is generated text.

### Price history

Roma keeps a SQLite table of price points per exact query (route, dates, cabin,
airline filter, party size) and distinguishes two kinds:

- **recorded** — a price Roma actually produced when someone ran that search.
  One per query per day, so clicking search repeatedly does not move the median.
- **backfilled** — Roma's fare model evaluated as of each of the previous 45
  days, so a route nobody has searched before still has a trend line.

The interface labels which is which, and the recommendation states the split.
The database lives at `roma/data/price_history.sqlite3`. It is generated at
runtime and is **not** committed — see `.gitignore`.

### Links out instead of scraping

Roma does not scrape, resell, or book. It builds the search URL you would have
built yourself for **Google Flights**, **Kayak**, **Expedia** and **Priceline**
and hands you over to check real prices there.

---

## Configuration

Everything is optional. With no environment set, Roma runs entirely offline with
simulated fares and deterministic phrasing.

### Real fares — the Amadeus seam

Set both of these and Roma puts the Amadeus Self-Service API in front of its
simulator:

| Variable | Meaning |
|---|---|
| `AMADEUS_CLIENT_ID` | Self-Service API key |
| `AMADEUS_CLIENT_SECRET` | Self-Service API secret |
| `AMADEUS_ENV` | `test` (default) or `production` |
| `AMADEUS_BASE_URL` | Override the host entirely |

When credentials are present, offers come back tagged `live_provider` instead of
`simulated`. If the call fails for any reason, Roma falls back to the simulator
and reports the provider chain and the failure reason in the response rather
than hiding it.

**This adapter has not been exercised against live Amadeus credentials.** The
request shaping, OAuth flow and response parsing are written and wired in, but
untested against the real service. Treat it as an integration point, not a
verified feature.

### Phrasing — the language-model seam

Roma's default voice is deterministic templates. No model is called and none is
needed. If you want a model to rephrase its summaries:

| Variable | Meaning |
|---|---|
| `ROMA_LLM_BASE_URL` | OpenAI-compatible base URL, e.g. `https://api.openai.com/v1` |
| `ROMA_LLM_API_KEY` | Bearer token |
| `ROMA_LLM_MODEL` | Model name (default `gpt-4o-mini`) |
| `ROMA_LLM_ENABLED` | Set to `0` to force templates even when configured |
| `ROMA_LLM_TIMEOUT` | Seconds (default 12) |

**The model never authors a number.** It is handed facts that were already
computed, told it may only reuse them verbatim, and then its draft is scanned:
any numeric token that does not appear in those facts causes the draft to be
thrown away and the template used instead. That check lives in
`romacore/llm.py`, not in the prompt — a model that ignores the instruction
still cannot get a made-up price onto the screen. Every response reports which
voice produced it, and why a draft was rejected if one was.

### Other settings

| Variable | Default | Meaning |
|---|---|---|
| `ROMA_PORT` / `PORT` | `8787` | Listen port |
| `ROMA_HOST` | `127.0.0.1` | Bind address |
| `ROMA_CURRENCY` | `USD` | Currency for quotes |
| `ROMA_DATA_DIR` | `roma/data` | Where the SQLite file lives |
| `ROMA_STATIC_DIR` | `roma/static` | Where the interface is served from |

---

## API

The interface is a client of this API; there is nothing it can do that you
cannot.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | Liveness |
| `GET` | `/api/meta` | Airlines, cabins, rule catalogues, data levels, disclosure text, active provider and voice |
| `GET` | `/api/airports?q=` | Airport typeahead |
| `POST` | `/api/search` | Structured search |
| `POST` | `/api/chat` | One conversational turn (`{session_id, message}`) |

`/api/search` returns either `{"ok": true, ...}` with offers, recommendation,
history, deep links and provenance, or `{"ok": false, "kind": "validation",
"errors": [...]}` where each error names the rule it broke.

### Validation

Three rules, each checked independently so one bad field does not mask another:

1. `route_known_and_distinct` — both endpoints resolve to airports Roma knows,
   and they are not the same airport.
2. `depart_date_valid_and_future` — the outbound date parses and has not passed.
3. `return_date_after_depart` — a return date, if given, is not before the
   outbound date.

---

## Accessibility

Roma is built to be usable without a mouse and without sight of the screen:
a tab pattern with arrow-key navigation, ARIA comboboxes for the airport
typeahead with active-descendant tracking and full keyboard selection, an error
summary that takes focus and links to the offending fields, `aria-invalid` and
per-field messages, a live-region transcript for the conversation, labelled SVG
for the price trend, a skip link, visible focus rings, and a reduced-motion
rule. The layout is a single column below 900px with comfortable touch targets.

---

## Layout

```
roma/
  run.py              entry point: serve, or one-shot search
  README.md
  .gitignore          keeps the SQLite database and local state out of git
  romacore/
    engine.py         the one search path every entry point uses
    server.py         stdlib HTTP server: API and static files
    conversation.py   multi-turn slot filling
    nlu.py            sentence to slots
    validation.py     the three rules
    fares.py          the deterministic fare model and the three data levels
    recommend.py      the buy/wait rules
    history.py        SQLite price history
    deeplinks.py      Google Flights, Kayak, Expedia, Priceline
    llm.py            optional phrasing, with the no-invented-numbers guard
    airports.py       airport data, typeahead, city and alias resolution
    airlines.py       carrier reference data
    models.py         the shared request object
    config.py         environment
    providers/        the fare seam: simulated (default) and Amadeus
  static/             Roma's own interface: HTML, CSS, JS, avatar
  tests/              python3 -m unittest discover
```

---

## Honest limits

- **Fares are simulated.** The model uses great-circle distance, cabin, month,
  day of week, advance purchase, trip length, stop count and a per-carrier
  index. It is plausible, deterministic and entirely made up.
- **The price history is mostly modelled**, not observed. Only the points from
  searches actually run on this machine are recorded observations.
- **Airline and airport data are a bundled subset** — roughly 160 airports and
  50 carriers, with coordinates accurate to a few kilometres. Routes are not
  checked for whether the carrier actually flies them.
- **The Amadeus adapter is unverified** against live credentials.
- **Deep links are constructed, not verified.** Booking sites change their URL
  formats; a link may land on a site's generic search rather than a prefilled
  one.
- **Sessions are in memory.** Restarting the server forgets conversations, and
  the last 500 are kept.
- Roma is a demonstration agent. It does not sell tickets and is not affiliated
  with any airline or booking site.
