"""Repository paths and the study window. All timestamps in the warehouse are NEM time."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

REGIONS: tuple[str, ...] = ("NSW1", "QLD1", "VIC1", "SA1", "TAS1")
PRICE_START = "202311"
PRICE_END = "202610"
GENERATION_YEARS: tuple[int, ...] = (2023, 2024, 2025, 2026)

USER_AGENT = (
    "nem-grid-pulse/1.0 (+https://github.com/LuciferDataEngineer/nem-grid-pulse; "
    "educational portfolio, respects public files)"
)

AEMO_PRICE_URL = "https://www.aemo.com.au/aemo/data/nem/priceanddemand/PRICE_AND_DEMAND_{yyyymm}_{region}.csv"
OPEN_ELECTRICITY_ENERGY_URL = "https://data.openelectricity.org.au/v4/stats/au/NEM/{region}/energy/{year}.json"

# Canonical colours shared by dim_region and the dashboard.
REGION_COLOURS = {
    "NSW1": "#E07A3D",
    "QLD1": "#7C3AED",
    "VIC1": "#2563EB",
    "SA1": "#DC2626",
    "TAS1": "#0F766E",
    "NEM": "#0A2540",
}

REGION_NAMES = {
    "NSW1": "New South Wales",
    "QLD1": "Queensland",
    "VIC1": "Victoria",
    "SA1": "South Australia",
    "TAS1": "Tasmania",
    "NEM": "National Electricity Market",
}


@lru_cache(maxsize=1)
def repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in [here, *here.parents]:
        if (candidate / "pyproject.toml").exists() and (candidate / "dbt").is_dir():
            return candidate
    raise RuntimeError("nem-grid-pulse repository root was not found")


def bronze_root() -> Path:
    return repo_root() / "data" / "bronze"


def warehouse_path() -> Path:
    return repo_root() / "data" / "warehouse" / "nem.duckdb"


def manifest_path() -> Path:
    return repo_root() / "data" / "manifest.json"


def watermark_path() -> Path:
    return repo_root() / "data" / "state" / "watermarks.json"


def price_url(region: str, yyyymm: str) -> str:
    return AEMO_PRICE_URL.format(yyyymm=yyyymm, region=region)


def generation_url(region: str, year: int) -> str:
    return OPEN_ELECTRICITY_ENERGY_URL.format(region=region, year=year)


def iter_months(start: str, end: str) -> list[str]:
    year, month = int(start[:4]), int(start[4:])
    end_year, end_month = int(end[:4]), int(end[4:])
    months: list[str] = []
    while (year, month) <= (end_year, end_month):
        months.append(f"{year}{month:02d}")
        month += 1
        if month == 13:
            month = 1
            year += 1
    return months


def month_label(yyyymm: str) -> str:
    return f"{yyyymm[:4]}-{yyyymm[4:]}"
