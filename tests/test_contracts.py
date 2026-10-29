import pandas as pd
import pytest

from nem_grid_pulse.contracts import ContractBreachError, enforce, load_contract


def _price_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "region": ["NSW1", "NSW1"],
            "settlement_ts": pd.to_datetime(["2025-09-01 00:05:00", "2025-09-01 00:10:00"]),
            "total_demand_mw": [7000.0, -20.0],
            "rrp": [80.0, -1000.0],
            "period_type": ["TRADE", "TRADE"],
            "source_url": ["https://example.test/a", "https://example.test/a"],
            "source_sha256": ["abc", "abc"],
            "ingested_at": pd.to_datetime(["2026-10-28 00:00:00", "2026-10-28 00:00:00"]),
        }
    )


def _contract():
    return load_contract("price_demand.yaml").model_copy(update={"min_rows": 1})


def test_price_contract_accepts_negative_south_australian_demand():
    enforce(_price_frame(), _contract(), "sample")


def test_price_contract_rejects_a_price_above_the_cap_bound():
    frame = _price_frame()
    frame.loc[0, "rrp"] = 80_000
    with pytest.raises(ContractBreachError, match="rrp"):
        enforce(frame, _contract(), "sample")


def test_price_contract_rejects_duplicate_intervals():
    frame = pd.concat([_price_frame(), _price_frame()], ignore_index=True)
    with pytest.raises(ContractBreachError, match="duplicate"):
        enforce(frame, _contract(), "sample")
