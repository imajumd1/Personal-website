#!/usr/bin/env python3
"""Roma — standalone flight-search agent.

    python3 run.py                      start the agent on http://127.0.0.1:8787/
    python3 run.py serve --port 9000    start it somewhere else
    python3 run.py search --from SFO --to LHR --depart 2026-10-12 \
                          --return 2026-10-20 --airline BA

The ``search`` subcommand goes through exactly the same engine as the web UI, so
the two cannot drift apart.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from romacore import VERSION  # noqa: E402
from romacore.config import DEFAULT_HOST, DEFAULT_PORT, load_config  # noqa: E402
from romacore.engine import Engine  # noqa: E402
from romacore.models import CABINS  # noqa: E402
from romacore.server import serve  # noqa: E402


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="roma",
        description="Roma, a standalone flight-search agent. Every fare it quotes is simulated.",
    )
    parser.add_argument("--version", action="version", version=f"Roma {VERSION}")
    parser.add_argument("--host", default=None, help=f"bind address (default {DEFAULT_HOST})")
    parser.add_argument(
        "--port", type=int, default=None, help=f"port (default {DEFAULT_PORT}, or $ROMA_PORT / $PORT)"
    )

    sub = parser.add_subparsers(dest="command")

    sub.add_parser("serve", help="run the web agent (this is the default)")

    search_parser = sub.add_parser("search", help="run one search and print the answer")
    search_parser.add_argument("--from", dest="origin", required=True, help="origin city or IATA code")
    search_parser.add_argument("--to", dest="destination", required=True, help="destination city or IATA code")
    search_parser.add_argument("--depart", required=True, help="outbound date, YYYY-MM-DD")
    search_parser.add_argument("--return", dest="return_date", default=None, help="return date, YYYY-MM-DD")
    search_parser.add_argument("--airline", default=None, help="airline name or IATA code")
    search_parser.add_argument("--cabin", default="economy", choices=list(CABINS))
    search_parser.add_argument("--adults", type=int, default=1)
    search_parser.add_argument("--json", action="store_true", help="print the raw API payload")
    return parser


def _print_result(result: dict) -> int:
    if not result.get("ok"):
        print("Roma cannot run that search:\n", file=sys.stderr)
        for error in result.get("errors", []):
            print(f"  - [{error['rule']}] {error['message']}", file=sys.stderr)
        return 2

    query = result["query"]
    print(f"Roma \u2014 {query['origin_label']} to {query['destination_label']}")
    print(f"  out {query['depart_date']}" + (f", back {query['return_date']}" if query["return_date"] else ", one way"))
    print(f"  {result['data_level']['label']}: {result['data_level']['detail']}")
    print()
    print("  Fares")
    for offer in result["offers"]:
        stops = "nonstop" if offer["stops"] == 0 else f"{offer['stops']} stop(s)"
        hours, minutes = divmod(offer["outbound_duration_minutes"], 60)
        print(
            f"    {offer['currency']} {offer['price']:>9,.2f}  {offer['airline_name']:<24} "
            f"{stops:<10} {hours}h {minutes:02d}m  [{offer['data_level']}]"
        )
    print()
    rec = result["recommendation"]
    print(f"  Verdict: {rec['verdict'].upper()} ({rec['confidence']} confidence)")
    print(f"  Rule fired: {rec['rule_fired']}")
    print(f"  {rec['headline']}")
    for fact in rec["facts"]:
        print(f"    \u2022 {fact}")
    print()
    history = result["history"]
    print(
        f"  History: {history['points']} points "
        f"({history['observed_points']} observed, {history['modeled_points']} modelled) "
        f"over {history['window_days']} days"
    )
    print(f"  {history['note']}")
    print()
    print("  Check real prices")
    for link in result["deeplinks"]:
        print(f"    {link['site']:<16} {link['url']}")
    print()
    print(f"  {result['disclosure']['product']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    command = args.command or "serve"

    if command == "search":
        config = load_config()
        engine = Engine(config)
        result = engine.search(
            {
                "origin": args.origin,
                "destination": args.destination,
                "depart_date": args.depart,
                "return_date": args.return_date,
                "one_way": args.return_date is None,
                "airline": args.airline,
                "cabin": args.cabin,
                "adults": args.adults,
                "source": "cli",
            }
        )
        if args.json:
            print(json.dumps(result, indent=2, default=str))
            return 0 if result.get("ok") else 2
        return _print_result(result)

    serve(load_config(port_override=args.port, host_override=args.host))
    return 0


if __name__ == "__main__":
    sys.exit(main())
