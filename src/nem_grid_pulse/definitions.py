"""Dagster assets. Materialise with:

dagster asset materialize -m nem_grid_pulse.definitions --select '*'
"""

from __future__ import annotations

from dagster import AssetExecutionContext, Definitions, asset

from nem_grid_pulse.ingest import ingest_all
from nem_grid_pulse.transform import run_dbt
from nem_grid_pulse.validate import validate_snapshot


@asset(group_name="bronze")
def bronze_market_data(context: AssetExecutionContext) -> None:
    context.log.info("Landing AEMO price and demand and Open Electricity generation")
    code = ingest_all()
    if code != 0:
        raise RuntimeError(f"ingest exited {code}")


@asset(group_name="warehouse", deps=[bronze_market_data])
def dbt_marts(context: AssetExecutionContext) -> None:
    context.log.info("Validating contracts and building dbt models")
    validate_snapshot()
    run_dbt("build")


@asset(group_name="publish", deps=[dbt_marts])
def grid_pulse_dashboard(context: AssetExecutionContext) -> None:
    from nem_grid_pulse.dashboard import build_dashboard
    from nem_grid_pulse.insights import write_insights

    insights = write_insights()
    dashboard = build_dashboard()
    context.log.info("Wrote %s and %s", insights, dashboard)


defs = Definitions(assets=[bronze_market_data, dbt_marts, grid_pulse_dashboard])
