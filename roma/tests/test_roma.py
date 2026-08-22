"""Unit tests for Roma. Run from the repo root: python3 -m unittest discover roma/tests"""

from __future__ import annotations

import datetime as dt
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from roma import deeplinks
from roma.dates import resolve_trip_dates
from roma.history import PriceHistory
from roma.intent import HeuristicIntentParser
from roma.models import SearchQuery, validate
from roma.phrasing import TemplatePhraser, _numbers_are_allowed
from roma.providers.simulated import SimulatedProvider
from roma.recommendation import recommend
from roma.service import RomaService

REF = dt.date(2026, 8, 22)


class DateLanguageTests(unittest.TestCase):
    def test_explicit_range(self):
        out = resolve_trip_dates("sfo to london oct 12 to oct 20", REF)
        self.assertEqual(out["depart_date"], "2026-10-12")
        self.assertEqual(out["return_date"], "2026-10-20")
        self.assertEqual(out["date_precision"], "exact")

    def test_early_month_is_approximate_and_rolls_year(self):
        out = resolve_trip_dates("tokyo in early march", REF)
        self.assertEqual(out["depart_date"], "2027-03-05")
        self.assertEqual(out["date_precision"], "approximate")
        self.assertTrue(out["notes"])

    def test_next_weekday(self):
        out = resolve_trip_dates("leaving next friday", REF)
        self.assertEqual(out["depart_date"], "2026-08-28")

    def test_same_month_short_range(self):
        out = resolve_trip_dates("dec 3-9", REF)
        self.assertEqual(out["depart_date"], "2026-12-03")
        self.assertEqual(out["return_date"], "2026-12-09")

    def test_duration_phrase(self):
        out = resolve_trip_dates("oct 12 for a week", REF)
        self.assertEqual(out["return_date"], "2026-10-19")


class IntentTests(unittest.TestCase):
    def setUp(self):
        self.parser = HeuristicIntentParser()

    def test_full_sentence(self):
        p = self.parser.parse("SFO to London Oct 12 to Oct 20 on British Airways", REF)
        self.assertEqual(p.origin, "SFO")
        self.assertEqual(p.destination, "LHR")
        self.assertEqual(p.depart_date, "2026-10-12")
        self.assertEqual(p.return_date, "2026-10-20")
        self.assertEqual(p.airline, "BA")

    def test_vague_with_passengers(self):
        p = self.parser.parse("cheapest way to get two of us to Tokyo in early March", REF)
        self.assertEqual(p.destination, "NRT")
        self.assertEqual(p.passengers, 2)
        self.assertEqual(p.depart_date, "2027-03-05")
        self.assertIsNone(p.origin)
        self.assertEqual(p.missing_required(), ["origin"])

    def test_destination_only(self):
        p = self.parser.parse("I want to go to Miami", REF)
        self.assertEqual(p.destination, "MIA")
        self.assertEqual(p.missing_required(), ["origin", "depart_date"])

    def test_gibberish_is_empty(self):
        p = self.parser.parse("asdkjh qwlekj zzzz", REF)
        self.assertTrue(p.is_empty())

    def test_cabin_and_count(self):
        p = self.parser.parse("business class from JFK to Paris on Nov 3 for 3 people", REF)
        self.assertEqual((p.origin, p.destination), ("JFK", "CDG"))
        self.assertEqual(p.cabin, "business")
        self.assertEqual(p.passengers, 3)


class ValidationTests(unittest.TestCase):
    def test_past_date_rejected(self):
        _, errors = validate({"origin": "SFO", "destination": "LHR", "depart_date": "2020-01-01"})
        self.assertIn("depart_date", errors)

    def test_same_airports_rejected(self):
        _, errors = validate({"origin": "SFO", "destination": "sfo", "depart_date": _future(30)})
        self.assertIn("destination", errors)

    def test_return_before_depart_rejected(self):
        _, errors = validate({
            "origin": "SFO", "destination": "LHR",
            "depart_date": _future(30), "return_date": _future(20),
        })
        self.assertIn("return_date", errors)

    def test_city_names_resolve(self):
        query, errors = validate({"origin": "san francisco", "destination": "Tokyo", "depart_date": _future(40)})
        self.assertEqual(errors, {})
        self.assertEqual((query.origin, query.destination), ("SFO", "NRT"))


class SimulatedProviderTests(unittest.TestCase):
    def test_deterministic_and_labelled(self):
        query = SearchQuery("SFO", "LHR", _future(60), _future(68), 2, "economy")
        first = SimulatedProvider().search(query)
        second = SimulatedProvider().search(query)
        self.assertTrue(first)
        self.assertEqual([o.price for o in first], [o.price for o in second])
        self.assertTrue(all(o.simulated for o in first))
        self.assertTrue(all(o.price > 0 for o in first))

    def test_business_costs_more_than_economy(self):
        base = SearchQuery("SFO", "LHR", _future(60), None, 1, "economy")
        business = SearchQuery("SFO", "LHR", _future(60), None, 1, "business")
        cheap = min(o.price for o in SimulatedProvider().search(base))
        pricey = min(o.price for o in SimulatedProvider().search(business))
        self.assertGreater(pricey, cheap)

    def test_airline_filter(self):
        query = SearchQuery("SFO", "LHR", _future(60), None, 1, "economy", airline="BA")
        offers = SimulatedProvider().search(query)
        self.assertTrue(offers)
        self.assertEqual({o.airline for o in offers}, {"BA"})


class DeepLinkTests(unittest.TestCase):
    def setUp(self):
        self.query = SearchQuery("SFO", "LHR", "2026-10-12", "2026-10-20", 2, "business")
        self.links = {link["id"]: link["url"] for link in deeplinks.build_all(self.query)}

    def test_all_four_sources(self):
        self.assertEqual(set(self.links), {"kayak", "google_flights", "expedia", "priceline"})

    def test_kayak_shape(self):
        self.assertEqual(
            self.links["kayak"],
            "https://www.kayak.com/flights/SFO-LHR/2026-10-12/2026-10-20/2adults/business?sort=price_a",
        )

    def test_google_shape(self):
        self.assertIn("google.com/travel/flights?q=", self.links["google_flights"])
        self.assertIn("SFO", self.links["google_flights"])
        self.assertIn("2026-10-12", self.links["google_flights"])

    def test_expedia_shape(self):
        url = self.links["expedia"]
        self.assertIn("expedia.com/Flights-Search?", url)
        self.assertIn("leg1=from%3ASFO%2Cto%3ALHR%2Cdeparture%3A10%2F12%2F2026TANYT", url)
        self.assertIn("trip=roundtrip", url)

    def test_priceline_shape(self):
        url = self.links["priceline"]
        self.assertIn("priceline.com/m/fly/search/SFO-LHR-20261012/LHR-SFO-20261020/", url)
        self.assertIn("cabin-class=BUS", url)

    def test_one_way_omits_return(self):
        one_way = SearchQuery("SFO", "LHR", "2026-10-12", None, 1, "economy")
        links = {link["id"]: link["url"] for link in deeplinks.build_all(one_way)}
        self.assertNotIn("2026-10-20", links["kayak"])
        self.assertIn("trip=oneway", links["expedia"])


class RecommendationTests(unittest.TestCase):
    def setUp(self):
        self.query = SearchQuery("SFO", "LHR", _future(45), _future(55), 2, "economy")
        self.offers = SimulatedProvider().search(self.query)

    def test_no_percentile_without_five_observation_days(self):
        stats = {"observation_days": 2, "median": None, "daily_low": [("2026-08-20", 500.0)]}
        rec = recommend(self.query, self.offers, stats, None)
        self.assertIsNone(rec.percentile)
        self.assertEqual(rec.confidence, "low")
        self.assertTrue(any("fewer than the 5" in line for line in rec.reasoning))
        self.assertTrue(rec.rule_fired.startswith("cold_start"))

    def test_simulated_data_caps_confidence(self):
        stats = {"observation_days": 30, "median": 900.0, "daily_low": [("d", 900.0)] * 30, "trend": "flat"}
        rec = recommend(self.query, self.offers, stats, 5.0)
        self.assertEqual(rec.verdict, "exceptional_price")
        self.assertEqual(rec.confidence, "low")
        self.assertTrue(any("simulated" in note for note in rec.confidence_notes))

    def test_high_percentile_with_runway_says_wait(self):
        stats = {"observation_days": 20, "median": 300.0, "daily_low": [("d", 300.0)] * 20, "trend": "rising"}
        rec = recommend(self.query, self.offers, stats, 85.0)
        self.assertEqual(rec.verdict, "wait")
        self.assertEqual(rec.rule_fired, "history_high_percentile_with_runway")
        self.assertGreater(rec.dollars_at_stake, 0)

    def test_no_offers_is_insufficient_data(self):
        rec = recommend(self.query, [], {"observation_days": 0}, None)
        self.assertEqual(rec.verdict, "insufficient_data")
        self.assertEqual(rec.rule_fired, "no_offers_returned")

    def test_revisit_date_is_before_departure(self):
        soon = SearchQuery("SFO", "LAX", _future(2), None, 1, "economy")
        rec = recommend(soon, SimulatedProvider().search(soon), {"observation_days": 1, "daily_low": []}, None)
        self.assertLess(rec.revisit_by, soon.depart_date)
        self.assertEqual(rec.verdict, "buy_now")

    def test_every_verdict_names_a_rule(self):
        for days in (2, 10, 40, 200):
            query = SearchQuery("SFO", "LHR", _future(days), None, 1, "economy")
            rec = recommend(query, SimulatedProvider().search(query), {"observation_days": 0, "daily_low": []}, None)
            self.assertTrue(rec.rule_fired)
            self.assertTrue(rec.reasoning)
            self.assertTrue(rec.revisit_by)


class HistoryTests(unittest.TestCase):
    def test_percentile_needs_five_days(self):
        with tempfile.TemporaryDirectory() as tmp:
            history = PriceHistory(Path(tmp) / "h.db")
            query = SearchQuery("SFO", "LHR", _future(30), None, 1, "economy")
            offers = SimulatedProvider().search(query)
            history.record(query, offers)
            stats = history.stats(query)
            self.assertEqual(stats["observation_days"], 1)
            self.assertIsNone(history.percentile_of(offers[0].price, stats))
            # Backfill five distinct days directly to prove the gate opens.
            with history._connect() as conn:
                for index in range(5):
                    conn.execute(
                        "INSERT INTO fare_observations (origin, destination, depart_date, return_date,"
                        " cabin, passengers, airline, price, currency, source, simulated, observed_at,"
                        " observed_day) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (query.origin, query.destination, query.depart_date, None, "economy", 1, "AA",
                         500.0 + index * 10, "USD", "simulated", 1, f"2026-01-0{index + 1}T00:00:00+00:00",
                         f"2026-01-0{index + 1}"),
                    )
            stats = history.stats(query)
            self.assertGreaterEqual(stats["observation_days"], 6)
            self.assertIsNotNone(history.percentile_of(505.0, stats))


class PhrasingGuardTests(unittest.TestCase):
    def test_template_phrasing_mentions_verdict_and_revisit(self):
        query = SearchQuery("SFO", "LHR", _future(45), None, 1, "economy")
        offers = SimulatedProvider().search(query)
        rec = recommend(query, offers, {"observation_days": 1, "daily_low": []}, None)
        text = TemplatePhraser().phrase(query, rec)
        self.assertIn(rec.revisit_by, text)
        self.assertIn("confidence low", text)

    def test_llm_output_with_invented_number_is_rejected(self):
        facts = "cheapest_total: 812.5\nrevisit_by: 2026-09-01\nobservation_days: 3"
        self.assertTrue(_numbers_are_allowed("Cheapest is 812.50 today; look again 2026-09-01.", facts))
        self.assertFalse(_numbers_are_allowed("You could save $240 by waiting.", facts))


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.service = RomaService(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_form_search_is_labelled_simulated(self):
        result = self.service.search({
            "origin": "SFO", "destination": "NRT", "depart_date": _future(50),
            "return_date": _future(60), "passengers": 2, "cabin": "economy",
        })
        self.assertTrue(result["ok"])
        self.assertTrue(result["data"]["simulated"])
        self.assertTrue(all(offer["simulated"] for offer in result["results"]))
        self.assertEqual(len(result["deep_links"]), 4)
        self.assertTrue(result["recommendation"]["rule_fired"])
        self.assertEqual(result["recommendation"]["confidence"], "low")

    def test_form_errors_surface_per_field(self):
        result = self.service.search({"origin": "SFO", "destination": "SFO", "depart_date": _future(5)})
        self.assertFalse(result["ok"])
        self.assertIn("destination", result["field_errors"])

    def test_other_airline_freetext_resolves(self):
        result = self.service.search({
            "origin": "SFO", "destination": "LHR", "depart_date": _future(30),
            "airline": "OTHER", "airline_other": "Virgin Atlantic",
        })
        self.assertTrue(result["ok"])
        self.assertEqual({offer["airline"] for offer in result["results"]}, {"VS"})

    def test_unknown_other_airline_is_noted_not_fatal(self):
        result = self.service.search({
            "origin": "SFO", "destination": "LHR", "depart_date": _future(30),
            "airline": "OTHER", "airline_other": "Air Nowhere",
        })
        self.assertTrue(result["ok"])
        self.assertTrue(any("Air Nowhere" in note for note in result["data"]["notes"]))

    def test_chat_slot_filling_completes_search(self):
        first = self.service.chat("I want to go to Miami")
        conversation = first["conversation_id"]
        self.assertIn("origin", first["needs"])
        self.assertIsNone(first["search"])

        second = self.service.chat("from Boston", conversation)
        self.assertIn("depart_date", second["needs"])

        third = self.service.chat("next month", conversation)
        self.assertIsNotNone(third["search"])
        self.assertEqual(third["search"]["query"]["origin"], "BOS")
        self.assertEqual(third["search"]["query"]["destination"], "MIA")

    def test_chat_and_form_share_the_engine(self):
        chat = self.service.chat("SFO to London Oct 12 to Oct 20")
        query = chat["search"]["query"]
        form = self.service.search({
            "origin": query["origin"], "destination": query["destination"],
            "depart_date": query["depart_date"], "return_date": query["return_date"],
            "passengers": query["passengers"], "cabin": query["cabin"],
        })
        self.assertEqual(
            chat["search"]["recommendation"]["rule_fired"],
            form["recommendation"]["rule_fired"],
        )
        self.assertEqual(
            [o["price"] for o in chat["search"]["results"]],
            [o["price"] for o in form["results"]],
        )

    def test_chat_gibberish_degrades_gracefully(self):
        reply = self.service.chat("asdkjh qwlekj zzzz")
        self.assertTrue(reply["ok"])
        self.assertFalse(reply["understood"])
        self.assertIsNone(reply["search"])
        self.assertIn("SFO to Tokyo", reply["reply"])

    def test_heuristics_are_the_default(self):
        status = self.service.status()
        self.assertEqual(status["intent_parser"], "heuristic")
        self.assertEqual(status["phraser"], "template")
        self.assertFalse(status["llm"]["configured"])
        self.assertTrue(status["simulated_only"])


def _future(days: int) -> str:
    return (dt.date.today() + dt.timedelta(days=days)).isoformat()


if __name__ == "__main__":
    unittest.main()
