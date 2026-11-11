"""Tests for Roma. Standard library only.

    cd roma && python3 -m unittest discover
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from romacore import airlines, airports, deeplinks, fares, llm, nlu, recommend, validation
from romacore.config import load_config
from romacore.conversation import Conversation
from romacore.engine import Engine
from romacore.history import PriceHistory
from romacore.models import SearchRequest
from romacore.providers.amadeus import parse_iso_duration
from romacore.server import build_server

TODAY = date(2026, 8, 22)
SOON = TODAY + timedelta(days=60)
LATER = TODAY + timedelta(days=67)


def request_for(**kwargs) -> SearchRequest:
    base = dict(origin="BOS", destination="MIA", depart_date=SOON, return_date=LATER)
    base.update(kwargs)
    return SearchRequest(**base)


class TempEngine:
    """An engine with its own throwaway database."""

    def __enter__(self):
        self._dir = tempfile.TemporaryDirectory()
        self._previous = os.environ.get("ROMA_DATA_DIR")
        os.environ["ROMA_DATA_DIR"] = self._dir.name
        self.engine = Engine(load_config())
        return self.engine

    def __exit__(self, *exc):
        if self._previous is None:
            os.environ.pop("ROMA_DATA_DIR", None)
        else:
            os.environ["ROMA_DATA_DIR"] = self._previous
        self._dir.cleanup()
        return False


# --------------------------------------------------------------------------- #
class AirportTests(unittest.TestCase):
    def test_resolves_codes_cities_and_aliases(self):
        self.assertEqual(airports.resolve("MIA"), "MIA")
        self.assertEqual(airports.resolve("miami"), "MIA")
        self.assertEqual(airports.resolve("the big apple"), "JFK")
        self.assertEqual(airports.resolve("London Heathrow"), "LHR")

    def test_resolves_the_shape_the_typeahead_writes_back(self):
        self.assertEqual(airports.resolve("Boston (BOS)"), "BOS")
        self.assertEqual(airports.resolve("New York (EWR)"), "EWR")
        self.assertEqual(airports.resolve("boston bos"), "BOS")

    def test_rejects_unknown_places(self):
        for text in ("Narnia", "ZZZ", "", None, "   "):
            self.assertIsNone(airports.resolve(text), text)

    def test_typeahead_ranks_exact_city_first(self):
        results = airports.search("lond")
        self.assertEqual(results[0]["iata"], "LHR")
        self.assertTrue(all(r["city"] == "London" for r in results))

    def test_typeahead_handles_no_match(self):
        self.assertEqual(airports.search("zzzz"), [])

    def test_distance_is_symmetric_and_sane(self):
        there = airports.distance_km("SFO", "LHR")
        back = airports.distance_km("LHR", "SFO")
        self.assertAlmostEqual(there, back, places=6)
        self.assertGreater(there, 8000)
        self.assertLess(there, 9200)

    def test_roma_is_not_an_alias_for_rome(self):
        """The agent's name must not be read as a destination."""
        self.assertIsNone(airports.resolve("roma"))
        self.assertEqual(airports.resolve("rome"), "FCO")


class ValidationTests(unittest.TestCase):
    def rules_fired(self, **kwargs):
        args = {"origin_raw": "BOS", "destination_raw": "MIA",
                "depart_raw": SOON.isoformat(), "return_raw": None}
        args.update(kwargs)
        _, errors = validation.validate(
            args["origin_raw"], args["destination_raw"],
            args["depart_raw"], args["return_raw"], today=TODAY)
        return [e.rule for e in errors]

    def test_clean_input_produces_a_request(self):
        request, errors = validation.validate(
            "Boston (BOS)", "miami", SOON.isoformat(), LATER.isoformat(), today=TODAY)
        self.assertEqual(errors, [])
        self.assertEqual((request.origin, request.destination), ("BOS", "MIA"))
        self.assertTrue(request.round_trip)
        self.assertEqual(request.trip_nights, 7)

    def test_rule_one_unknown_airport(self):
        self.assertEqual(self.rules_fired(origin_raw="Narnia"), ["route_known_and_distinct"])

    def test_rule_one_missing_airport(self):
        self.assertEqual(self.rules_fired(destination_raw=""), ["route_known_and_distinct"])

    def test_rule_one_identical_endpoints(self):
        self.assertEqual(self.rules_fired(destination_raw="Boston"), ["route_known_and_distinct"])

    def test_rule_two_departure_in_the_past(self):
        self.assertEqual(self.rules_fired(depart_raw="2020-01-01"),
                         ["depart_date_valid_and_future"])

    def test_rule_two_unreadable_departure(self):
        self.assertEqual(self.rules_fired(depart_raw="next tuesday"),
                         ["depart_date_valid_and_future"])

    def test_rule_two_absurdly_far_out(self):
        far = (TODAY + timedelta(days=500)).isoformat()
        self.assertEqual(self.rules_fired(depart_raw=far), ["depart_date_valid_and_future"])

    def test_rule_three_return_before_departure(self):
        self.assertEqual(
            self.rules_fired(depart_raw=LATER.isoformat(), return_raw=SOON.isoformat()),
            ["return_date_after_depart"])

    def test_rule_three_unreadable_return(self):
        self.assertEqual(self.rules_fired(return_raw="whenever"), ["return_date_after_depart"])

    def test_departure_today_is_allowed(self):
        self.assertEqual(self.rules_fired(depart_raw=TODAY.isoformat()), [])

    def test_all_three_rules_report_independently(self):
        fired = self.rules_fired(
            origin_raw="Atlantis", destination_raw="Narnia",
            depart_raw="2019-03-03", return_raw="2019-01-01")
        self.assertEqual(sorted(set(fired)), [
            "depart_date_valid_and_future", "return_date_after_depart", "route_known_and_distinct"])


class FareModelTests(unittest.TestCase):
    def offers(self, **kwargs):
        return fares.build_offers(
            request_for(**kwargs), as_of=TODAY, currency="USD",
            requested_airline=kwargs.get("airline"), requested_airline_label=None)

    def test_offers_are_deterministic(self):
        self.assertEqual(self.offers(), self.offers())

    def test_offers_are_sorted_cheapest_first(self):
        prices = [o["price"] for o in self.offers()]
        self.assertEqual(prices, sorted(prices))

    def test_every_price_is_labelled_simulated(self):
        for offer in self.offers():
            self.assertEqual(offer["data_level"], fares.LEVEL_SIMULATED)
            self.assertEqual(offer["provider"], "simulated")

    def test_there_are_exactly_three_data_levels(self):
        self.assertEqual(len(fares.DATA_LEVELS), 3)
        for level in fares.DATA_LEVELS.values():
            self.assertTrue(level["label"] and level["detail"] and level["short"])

    def test_longer_route_costs_more(self):
        near = min(o["price"] for o in self.offers())
        far = min(o["price"] for o in self.offers(destination="LHR"))
        self.assertGreater(far, near)

    def test_business_costs_more_than_economy(self):
        economy = min(o["price"] for o in self.offers())
        business = min(o["price"] for o in self.offers(cabin="business"))
        self.assertGreater(business, economy)

    def test_booking_later_costs_more_than_booking_early(self):
        request = request_for()
        early = fares.model_price(request, "AA", as_of=TODAY, stops=1)
        late = fares.model_price(request, "AA", as_of=request.depart_date - timedelta(days=3), stops=1)
        self.assertGreater(late, early)

    def test_requested_airline_is_the_only_one_quoted(self):
        for offer in self.offers(airline="BA", destination="LHR"):
            self.assertEqual(offer["airline_code"], "BA")

    def test_unknown_carrier_is_quoted_and_flagged(self):
        offers = fares.build_offers(
            request_for(), as_of=TODAY, currency="USD",
            requested_airline=None, requested_airline_label="Kitefin Air")
        self.assertTrue(offers)
        for offer in offers:
            self.assertEqual(offer["airline_name"], "Kitefin Air")
            self.assertTrue(offer["notes"], "an unknown carrier must carry a caveat")


class RecommendationTests(unittest.TestCase):
    def fire(self, price, stats, days_out=60):
        return recommend.evaluate(
            current_price=price, stats=stats, depart_date=TODAY + timedelta(days=days_out),
            today=TODAY, currency="USD")

    @staticmethod
    def stats(points=30, low=800.0, mid=900.0, high=1000.0, observed=1):
        return {"points": points, "observed_points": observed,
                "modeled_points": points - observed, "min": low, "median": mid,
                "max": high, "window_days": 45, "has_trend": points >= 5}

    def test_insufficient_history(self):
        result = self.fire(900.0, self.stats(points=2))
        self.assertEqual(result.rule_fired, "insufficient_history")
        self.assertEqual(result.verdict, "watch")
        self.assertEqual(result.confidence, "low")

    def test_at_or_below_observed_floor(self):
        result = self.fire(800.0, self.stats())
        self.assertEqual(result.rule_fired, "at_or_below_observed_floor")
        self.assertEqual(result.verdict, "buy")

    def test_well_below_median(self):
        result = self.fire(820.0, self.stats(low=700.0))
        self.assertEqual(result.rule_fired, "well_below_median")
        self.assertEqual(result.verdict, "buy")

    def test_departure_within_fortnight(self):
        result = self.fire(900.0, self.stats(), days_out=9)
        self.assertEqual(result.rule_fired, "departure_within_fortnight")
        self.assertEqual(result.verdict, "buy")

    def test_far_above_median(self):
        result = self.fire(1200.0, self.stats())
        self.assertEqual(result.rule_fired, "far_above_median")
        self.assertEqual(result.verdict, "wait")

    def test_long_lead_time(self):
        result = self.fire(900.0, self.stats(), days_out=200)
        self.assertEqual(result.rule_fired, "long_lead_time")
        self.assertEqual(result.verdict, "wait")

    def test_near_median(self):
        result = self.fire(910.0, self.stats())
        self.assertEqual(result.rule_fired, "near_median")
        self.assertEqual(result.verdict, "watch")

    def test_every_result_names_a_catalogued_rule_and_shows_its_inputs(self):
        catalogue = {rule for rule, _ in recommend.RULE_CATALOGUE}
        for price, days in ((800.0, 60), (1200.0, 60), (900.0, 9), (900.0, 200), (910.0, 60)):
            result = self.fire(price, self.stats(), days_out=days)
            self.assertIn(result.rule_fired, catalogue)
            self.assertIn(result.verdict, {"buy", "wait", "watch"})
            self.assertTrue(result.facts)
            self.assertEqual(result.inputs["current_price"], price)
            self.assertEqual(result.inputs["days_to_departure"], days)


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.store = PriceHistory(Path(self.dir.name) / "history.sqlite3")

    def tearDown(self):
        self.dir.cleanup()

    def record(self, request, price, quoted_on=TODAY, kind="observed"):
        self.store.record(request, price=price, currency="USD", provider="simulated",
                          data_level=fares.LEVEL_SIMULATED, point_kind=kind, quoted_on=quoted_on)

    def test_empty_history_reports_no_trend(self):
        stats = self.store.stats(request_for())
        self.assertEqual(stats["points"], 0)
        self.assertFalse(stats["has_trend"])
        self.assertIsNone(stats["median"])

    def test_same_day_searches_do_not_stack(self):
        request = request_for()
        for price in (900.0, 910.0, 920.0):
            self.record(request, price)
        stats = self.store.stats(request)
        self.assertEqual(stats["points"], 1)
        self.assertEqual(stats["latest"], 920.0)

    def test_separate_days_accumulate(self):
        request = request_for()
        self.record(request, 900.0, quoted_on=TODAY - timedelta(days=1))
        self.record(request, 950.0, quoted_on=TODAY)
        stats = self.store.stats(request)
        self.assertEqual(stats["points"], 2)
        self.assertEqual(stats["min"], 900.0)
        self.assertEqual(stats["max"], 950.0)
        self.assertEqual(stats["window_days"], 1)

    def test_an_unresolved_carrier_gets_its_own_bucket(self):
        anyone = request_for()
        named = request_for()
        named.airline_label = "Kitefin Air"
        self.record(anyone, 900.0)
        self.record(named, 1500.0)
        self.assertEqual(self.store.stats(anyone)["points"], 1)
        self.assertEqual(self.store.stats(anyone)["latest"], 900.0)
        self.assertEqual(self.store.stats(named)["latest"], 1500.0)

    def test_a_different_airline_filter_is_a_different_query(self):
        anyone = request_for()
        with_ba = request_for(airline="BA")
        self.record(anyone, 900.0)
        self.record(with_ba, 1400.0)
        self.assertEqual(self.store.stats(anyone)["latest"], 900.0)
        self.assertEqual(self.store.stats(with_ba)["latest"], 1400.0)

    def test_backfill_runs_once_and_is_labelled_modelled(self):
        request = request_for()
        first = self.store.ensure_backfill(request, today=TODAY, currency="USD",
                                           price_fn=lambda as_of: 900.0, days=10)
        second = self.store.ensure_backfill(request, today=TODAY, currency="USD",
                                            price_fn=lambda as_of: 900.0, days=10)
        self.assertEqual(first, 10)
        self.assertEqual(second, 0)
        stats = self.store.stats(request)
        self.assertEqual(stats["modeled_points"], 10)
        self.assertEqual(stats["observed_points"], 0)

    def test_recorded_and_modelled_points_stay_distinguishable(self):
        request = request_for()
        self.store.ensure_backfill(request, today=TODAY, currency="USD",
                                   price_fn=lambda as_of: 900.0, days=6)
        self.record(request, 850.0)
        stats = self.store.stats(request)
        self.assertEqual(stats["modeled_points"], 6)
        self.assertEqual(stats["observed_points"], 1)
        self.assertEqual(stats["points"], 7)
        kinds = {point["kind"] for point in stats["series"]}
        self.assertEqual(kinds, {"modeled", "observed"})


class LanguageSeamTests(unittest.TestCase):
    facts = {"cheapest_price": 1160.13, "currency": "USD",
             "depart_date": "2026-10-12", "history": {"min": 1137.0, "median": 1192.5}}

    def test_heuristics_are_the_default(self):
        narrator = llm.build_narrator(load_config())
        self.assertIsInstance(narrator, llm.HeuristicNarrator)
        self.assertEqual(narrator.mode, "heuristic")

    def test_heuristic_narrator_returns_the_template_untouched(self):
        text, info = llm.HeuristicNarrator().narrate("search_result", self.facts, "the template")
        self.assertEqual(text, "the template")
        self.assertFalse(info["used_model"])

    def test_faithful_text_passes(self):
        text = "The cheapest is USD 1,160.13 on 2026-10-12, median USD 1192.50."
        self.assertEqual(llm.unauthorised_numbers(text, self.facts), [])

    def test_an_invented_price_is_caught(self):
        self.assertEqual(
            llm.unauthorised_numbers("It should fall to USD 950 next week.", self.facts), [950.0])

    def test_an_invented_percentage_is_caught(self):
        self.assertEqual(llm.unauthorised_numbers("Save 42% by waiting.", self.facts), [42.0])

    def test_rounding_a_supplied_number_is_allowed(self):
        self.assertEqual(llm.unauthorised_numbers("about USD 1160", self.facts), [])

    def test_numbers_nested_anywhere_in_the_facts_are_permitted(self):
        self.assertEqual(llm.unauthorised_numbers("median USD 1192.5", self.facts), [])

    def test_a_rejected_draft_falls_back_to_the_template(self):
        class Inventing(llm.LLMNarrator):
            def __init__(self):
                pass
            mode = "llm"

            def _call(self, facts):
                return "Prices will drop to USD 199 tomorrow."

        text, info = Inventing().narrate("search_result", self.facts, "the template")
        self.assertEqual(text, "the template")
        self.assertFalse(info["used_model"])
        self.assertIn("199", info["reason"])

    def test_a_faithful_draft_is_accepted(self):
        class Faithful(llm.LLMNarrator):
            def __init__(self):
                pass
            mode = "llm"

            def _call(self, facts):
                return "The cheapest is USD 1160.13."

        text, info = Faithful().narrate("search_result", self.facts, "the template")
        self.assertEqual(text, "The cheapest is USD 1160.13.")
        self.assertTrue(info["used_model"])


class DeepLinkTests(unittest.TestCase):
    def test_all_four_sites_are_offered(self):
        links = deeplinks.build(request_for())
        self.assertEqual([link["id"] for link in links],
                         ["google_flights", "kayak", "expedia", "priceline"])

    def test_round_trip_carries_both_dates(self):
        for link in deeplinks.build(request_for()):
            self.assertIn(SOON.isoformat().replace("-", "") if link["id"] == "priceline"
                          else SOON.isoformat(), link["url"])

    def test_one_way_does_not_claim_a_return(self):
        links = deeplinks.build(request_for(return_date=None))
        expedia = next(link for link in links if link["id"] == "expedia")
        self.assertIn("trip=oneway", expedia["url"])
        self.assertNotIn("leg2", expedia["url"])

    def test_every_url_is_https(self):
        for link in deeplinks.build(request_for()):
            self.assertTrue(link["url"].startswith("https://"), link["url"])


class NluTests(unittest.TestCase):
    def parse(self, text):
        return nlu.parse(text, today=TODAY)

    def test_a_full_request_yields_every_slot(self):
        parsed = self.parse("Find me a round trip from SFO to London on October 12 "
                            "returning October 20 on British Airways")
        self.assertEqual(parsed.origin, "SFO")
        self.assertEqual(parsed.destination, "LHR")
        self.assertEqual(parsed.depart_date, date(2026, 10, 12))
        self.assertEqual(parsed.return_date, date(2026, 10, 20))
        self.assertEqual(parsed.airline, "BA")

    def test_a_destination_only_message(self):
        parsed = self.parse("I want to go to Miami")
        self.assertEqual(parsed.destination, "MIA")
        self.assertIsNone(parsed.origin)
        self.assertIsNone(parsed.depart_date)

    def test_direction_words_assign_the_right_ends(self):
        parsed = self.parse("from Boston, leaving November 3 and back November 10")
        self.assertEqual(parsed.origin, "BOS")
        self.assertEqual(parsed.depart_date, date(2026, 11, 3))
        self.assertEqual(parsed.return_date, date(2026, 11, 10))

    def test_gibberish_is_reported_as_unparsed(self):
        parsed = self.parse("asdkjh qwe zzz")
        self.assertEqual(parsed.intent, "unparsed")
        self.assertFalse(parsed.found_anything)

    def test_ordinary_words_are_not_mistaken_for_airport_codes(self):
        parsed = self.parse("I can see how per diem sin taxes add up")
        self.assertIsNone(parsed.origin)
        self.assertIsNone(parsed.destination)

    def test_date_formats(self):
        cases = {
            "SFO to LHR on 2026-10-12": date(2026, 10, 12),
            "SFO to LHR on Oct 12": date(2026, 10, 12),
            "SFO to LHR on 12 October": date(2026, 10, 12),
            "SFO to LHR tomorrow": TODAY + timedelta(days=1),
            "SFO to LHR in 3 weeks": TODAY + timedelta(days=21),
            "SFO to LHR next month": TODAY + timedelta(days=30),
        }
        for text, expected in cases.items():
            self.assertEqual(self.parse(text).depart_date, expected, text)

    def test_bare_month_day_rolls_to_the_next_occurrence(self):
        self.assertEqual(self.parse("SFO to LHR on January 5").depart_date, date(2027, 1, 5))

    def test_one_way_and_cabin_and_party_size(self):
        parsed = self.parse("one way from LAX to Tokyo in business class for 3 adults")
        self.assertTrue(parsed.one_way)
        self.assertEqual(parsed.cabin, "business")
        self.assertEqual(parsed.adults, 3)

    def test_trip_length_in_nights(self):
        self.assertEqual(self.parse("SFO to DEN for 5 nights").nights, 5)

    def test_reversed_dates_are_straightened_out(self):
        parsed = self.parse("SFO to LHR on October 20 through October 12")
        self.assertEqual(parsed.depart_date, date(2026, 10, 12))
        self.assertEqual(parsed.return_date, date(2026, 10, 20))

    def test_help_and_reset_are_recognised(self):
        self.assertEqual(self.parse("help").intent, "help")
        self.assertEqual(self.parse("start over").intent, "reset")
        self.assertEqual(self.parse("hello").intent, "greeting")


class ConversationTests(unittest.TestCase):
    def test_multi_turn_slot_filling_reaches_a_result(self):
        with TempEngine() as engine:
            chat = Conversation(engine)
            first = chat.handle("s", "I want to go to Miami")
            self.assertEqual(first["state"], "collecting")
            self.assertEqual(first["awaiting"], "origin")
            self.assertEqual(first["slots"]["destination"], "MIA")
            self.assertIsNone(first["result"])

            second = chat.handle("s", "from Boston, leaving November 3 and back November 10")
            self.assertEqual(second["state"], "result")
            self.assertTrue(second["result"]["ok"])
            self.assertEqual(second["result"]["query"]["origin"], "BOS")
            self.assertEqual(second["result"]["query"]["destination"], "MIA")

    def test_a_bare_answer_fills_the_slot_that_was_asked(self):
        with TempEngine() as engine:
            chat = Conversation(engine)
            chat.handle("s", "I want to go to Paris")
            reply = chat.handle("s", "Boston")
            self.assertEqual(reply["slots"]["origin"], "BOS")
            self.assertEqual(reply["slots"]["destination"], "CDG")

    def test_gibberish_never_reruns_the_previous_search(self):
        with TempEngine() as engine:
            chat = Conversation(engine)
            chat.handle("s", "Boston to Miami on November 3, back November 10")
            reply = chat.handle("s", "asdkjh qwe zzz")
            self.assertEqual(reply["state"], "unparsed")
            self.assertIsNone(reply["result"])
            self.assertIn("could not find", reply["reply"])

    def test_gibberish_on_a_fresh_session_asks_for_what_it_needs(self):
        with TempEngine() as engine:
            reply = Conversation(engine).handle("s", "asdkjh qwe zzz")
            self.assertEqual(reply["state"], "unparsed")
            self.assertEqual(reply["awaiting"], "destination")

    def test_reset_clears_the_slots(self):
        with TempEngine() as engine:
            chat = Conversation(engine)
            chat.handle("s", "Boston to Miami on November 3")
            reply = chat.handle("s", "start over")
            self.assertIsNone(reply["slots"]["origin"])
            self.assertIsNone(reply["slots"]["destination"])

    def test_one_way_answer_completes_the_query(self):
        with TempEngine() as engine:
            chat = Conversation(engine)
            chat.handle("s", "I want to go to Paris")
            chat.handle("s", "from JFK")
            asked = chat.handle("s", "December 5")
            self.assertEqual(asked["awaiting"], "return_date")
            reply = chat.handle("s", "one way")
            self.assertEqual(reply["state"], "result")
            self.assertIsNone(reply["result"]["query"]["return_date"])

    def test_sessions_do_not_leak_into_each_other(self):
        with TempEngine() as engine:
            chat = Conversation(engine)
            chat.handle("a", "I want to go to Miami")
            reply = chat.handle("b", "I want to go to Paris")
            self.assertEqual(reply["slots"]["destination"], "CDG")
            self.assertEqual(chat.handle("a", "help")["state"], "help")


class EngineTests(unittest.TestCase):
    def test_a_good_search_returns_the_whole_answer(self):
        with TempEngine() as engine:
            result = engine.search({
                "origin": "Boston (BOS)", "destination": "Miami (MIA)",
                "depart_date": SOON.isoformat(), "return_date": LATER.isoformat(),
                "one_way": False, "cabin": "economy", "adults": "2", "source": "form"})
            self.assertTrue(result["ok"])
            self.assertTrue(result["offers"])
            self.assertEqual(result["cheapest"], result["offers"][0])
            self.assertIn(result["recommendation"]["rule_fired"],
                          {rule for rule, _ in recommend.RULE_CATALOGUE})
            self.assertEqual(len(result["deeplinks"]), 4)
            self.assertEqual(sorted(result["disclosure"]), ["fare", "product", "result_set"])
            self.assertEqual(result["data_level"]["id"], fares.LEVEL_SIMULATED)
            self.assertEqual(result["provider"]["used"], "simulated")
            self.assertEqual(result["language"]["mode"], "heuristic")

    def test_a_bad_search_returns_named_rules_and_no_prices(self):
        with TempEngine() as engine:
            result = engine.search({"origin": "Narnia", "destination": "",
                                    "depart_date": "2001-01-01", "return_date": "2000-01-01"})
            self.assertFalse(result["ok"])
            self.assertEqual(result["kind"], "validation")
            self.assertNotIn("offers", result)
            self.assertEqual([rule["rule"] for rule in result["rules"]],
                             [rule for rule, _ in validation.RULES])
            for error in result["errors"]:
                self.assertIn(error["rule"], {rule for rule, _ in validation.RULES})

    def test_the_other_airline_option_is_honoured(self):
        with TempEngine() as engine:
            known = engine.search({"origin": "SFO", "destination": "LHR",
                                   "depart_date": SOON.isoformat(), "one_way": True,
                                   "airline": "OTHER", "airline_other": "Aer Lingus"})
            self.assertEqual(known["query"]["airline"], "EI")

            unknown = engine.search({"origin": "SFO", "destination": "LHR",
                                     "depart_date": SOON.isoformat(), "one_way": True,
                                     "airline": "OTHER", "airline_other": "Kitefin Air"})
            self.assertIsNone(unknown["query"]["airline"])
            self.assertEqual(unknown["query"]["airline_label"], "Kitefin Air")
            self.assertTrue(all(o["notes"] for o in unknown["offers"]))

    def test_the_chat_and_the_form_agree(self):
        with TempEngine() as engine:
            form = engine.search({"origin": "BOS", "destination": "MIA",
                                  "depart_date": "2026-11-03", "return_date": "2026-11-10",
                                  "one_way": False, "source": "form"})
            chat = Conversation(engine).handle(
                "s", "Boston to Miami on November 3, back November 10")
            self.assertEqual(chat["result"]["cheapest"]["price"], form["cheapest"]["price"])
            self.assertEqual(chat["result"]["recommendation"]["rule_fired"],
                             form["recommendation"]["rule_fired"])

    def test_meta_describes_every_seam(self):
        with TempEngine() as engine:
            meta = engine.meta()
            self.assertEqual(len(meta["validation_rules"]), 3)
            self.assertEqual(len(meta["data_levels"]), 3)
            self.assertEqual(len(meta["recommendation_rules"]), len(recommend.RULE_CATALOGUE))
            self.assertEqual(meta["booking_sites"],
                             ["Google Flights", "Kayak", "Expedia", "Priceline"])
            self.assertIn("simulated", [p["name"] for p in meta["providers"]])
            self.assertTrue(meta["airlines"])
            self.assertEqual(meta["airline_other"], airlines.OTHER_SENTINEL)


class AmadeusSeamTests(unittest.TestCase):
    def test_the_provider_is_absent_without_credentials(self):
        with TempEngine() as engine:
            self.assertEqual([p.name for p in engine.providers], ["simulated"])

    def test_iso_durations_parse(self):
        self.assertEqual(parse_iso_duration("PT11H35M"), 695)
        self.assertEqual(parse_iso_duration("PT45M"), 45)
        self.assertEqual(parse_iso_duration("P1DT2H"), 1560)
        self.assertEqual(parse_iso_duration("nonsense"), 0)
        self.assertEqual(parse_iso_duration(None), 0)


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.TemporaryDirectory()
        os.environ["ROMA_DATA_DIR"] = cls.dir.name
        cls.httpd = build_server(load_config(port_override=0))
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        os.environ.pop("ROMA_DATA_DIR", None)
        cls.dir.cleanup()

    def url(self, path):
        return f"http://127.0.0.1:{self.port}{path}"

    def get(self, path):
        with urllib.request.urlopen(self.url(path)) as response:
            return response.status, response.headers.get("Content-Type"), response.read()

    def post(self, path, payload):
        request = urllib.request.Request(
            self.url(path), data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read())

    def test_health(self):
        status, _, body = self.get("/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["agent"], "Roma")

    def test_it_serves_its_own_interface(self):
        status, content_type, body = self.get("/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", content_type)
        self.assertIn(b"<title>Roma", body)

    def test_it_serves_its_own_assets(self):
        for path, expected in (("/roma.css", "text/css"), ("/roma.js", "text/javascript"),
                               ("/roma-avatar.svg", "image/svg+xml")):
            status, content_type, body = self.get(path)
            self.assertEqual(status, 200, path)
            self.assertIn(expected, content_type, path)
            self.assertTrue(body)

    def test_it_refuses_to_serve_anything_outside_its_own_directory(self):
        for path in ("/../run.py", "/../romacore/engine.py", "/../../server.py"):
            try:
                status, _, _ = self.get(path)
            except urllib.error.HTTPError as exc:
                status = exc.code
            self.assertEqual(status, 404, path)

    def test_typeahead(self):
        _, _, body = self.get("/api/airports?q=mia")
        self.assertEqual(json.loads(body)["results"][0]["iata"], "MIA")

    def test_search_endpoint(self):
        payload = self.post("/api/search", {
            "origin": "BOS", "destination": "MIA", "depart_date": SOON.isoformat(),
            "return_date": LATER.isoformat(), "one_way": False})
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["offers"])

    def test_search_endpoint_reports_validation(self):
        payload = self.post("/api/search", {"origin": "Narnia", "destination": "MIA",
                                            "depart_date": "2020-01-01"})
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["kind"], "validation")

    def test_chat_endpoint_issues_and_keeps_a_session(self):
        first = self.post("/api/chat", {"message": "I want to go to Miami"})
        self.assertTrue(first["session_id"])
        self.assertEqual(first["awaiting"], "origin")
        second = self.post("/api/chat", {"session_id": first["session_id"],
                                         "message": "from Boston on " + SOON.isoformat()})
        self.assertEqual(second["session_id"], first["session_id"])
        self.assertEqual(second["slots"]["origin"], "BOS")

    def test_unknown_api_route(self):
        try:
            self.get("/api/nope")
        except urllib.error.HTTPError as exc:
            self.assertEqual(exc.code, 404)
        else:
            self.fail("expected a 404")


if __name__ == "__main__":
    unittest.main(verbosity=2)
