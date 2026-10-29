"""Command line entry points used by the Makefile and Dagster."""

from __future__ import annotations

import argparse
import logging
import sys

from nem_grid_pulse.contracts import ContractBreachError
from nem_grid_pulse.http_client import UnexpectedStatusError
from nem_grid_pulse.ingest import ingest_all
from nem_grid_pulse.settings import PRICE_END, PRICE_START
from nem_grid_pulse.transform import run_dbt
from nem_grid_pulse.validate import validate_snapshot


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    parser = argparse.ArgumentParser(prog="nem-grid-pulse")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser("ingest", help="Incrementally land bronze Parquet")
    ingest.add_argument("--dataset", choices=["all", "price", "generation"], default="all")
    ingest.add_argument("--start", default=PRICE_START)
    ingest.add_argument("--end", default=PRICE_END)
    ingest.add_argument("--force", action="store_true")
    ingest.add_argument("--allow-source-failure", action="store_true")

    sub.add_parser("validate", help="Fail if the bronze snapshot breaks a contract")
    sub.add_parser("transform", help="Validate bronze, then dbt build")
    sub.add_parser("dashboard", help="Render the static dashboard from the marts")
    sub.add_parser("insights", help="Write INSIGHTS.md from the marts")

    args = parser.parse_args(argv)
    try:
        if args.command == "ingest":
            return ingest_all(
                dataset=args.dataset,
                start=args.start,
                end=args.end,
                force=args.force,
                allow_source_failure=args.allow_source_failure,
            )
        if args.command == "validate":
            validate_snapshot()
            return 0
        if args.command == "transform":
            validate_snapshot()
            run_dbt("build")
            return 0
        if args.command == "dashboard":
            from nem_grid_pulse.dashboard import build_dashboard

            build_dashboard()
            return 0
        if args.command == "insights":
            from nem_grid_pulse.insights import write_insights

            write_insights()
            return 0
    except (ContractBreachError, UnexpectedStatusError) as exc:
        logging.error("%s", exc)
        return 2
    print(f"unknown command {args.command}", file=sys.stderr)
    return 2
