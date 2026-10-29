from pathlib import Path

import duckdb
import pytest

from nem_grid_pulse.settings import warehouse_path


@pytest.fixture(scope="module")
def connection():
    path = warehouse_path()
    if not path.exists():
        pytest.skip("warehouse has not been built")
    return duckdb.connect(str(path), read_only=True)


def test_flat_load_peak_identity(connection):
    gap = connection.execute(
        """
        select max(abs(
            peak_operational_demand_mw
            - baseline_peak_operational_demand_mw
            - added_mw_on_series
        ))
        from marts.mart_datacentre_load_scenarios
        """
    ).fetchone()[0]
    assert gap < 0.05


def test_every_scenario_row_is_labelled_illustrative(connection):
    forecast_rows = connection.execute(
        """
        select count(*)
        from marts.mart_datacentre_load_scenarios
        where is_forecast or model_id <> 'illustrative_flat_load_v1'
        """
    ).fetchone()[0]
    assert forecast_rows == 0


def test_regions_and_window_cover_the_study(connection):
    row = connection.execute(
        """
        select min(trading_date), max(trading_date), count(distinct region_id)
        from marts.fct_price_demand_30min
        """
    ).fetchone()
    assert str(row[0]).startswith("2023-11")
    assert str(row[1]).startswith("2026-10")
    assert row[2] == 5
    assert Path(warehouse_path()).stat().st_size > 0
