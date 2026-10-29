"""Idempotent ingestion of AEMO price and demand and Open Electricity daily energy."""

from __future__ import annotations

import hashlib
import io
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from nem_grid_pulse.contracts import ContractBreachError, enforce, load_contract
from nem_grid_pulse.http_client import (
    MissingDatasetError,
    SourceUnavailableError,
    UnexpectedStatusError,
    fetch_bytes,
    make_client,
)
from nem_grid_pulse.settings import (
    GENERATION_YEARS,
    PRICE_END,
    PRICE_START,
    REGIONS,
    bronze_root,
    generation_url,
    iter_months,
    manifest_path,
    month_label,
    price_url,
    repo_root,
    watermark_path,
)
from nem_grid_pulse.watermark import load_watermarks, save_watermarks, should_skip

logger = logging.getLogger(__name__)

PRICE_COLUMNS = ["REGION", "SETTLEMENTDATE", "TOTALDEMAND", "RRP", "PERIODTYPE"]


@dataclass
class LandedFile:
    dataset: str
    path: str
    source_url: str
    source_sha256: str
    parquet_sha256: str
    fetched_at: str
    rows: int
    bytes: int
    complete: bool
    watermark_dataset: str
    watermark_key: str


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    return path.relative_to(repo_root()).as_posix()


def _write_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False, compression="snappy")


def _closing_timestamp(yyyymm: str) -> datetime:
    year, month = int(yyyymm[:4]), int(yyyymm[4:])
    if month == 12:
        return datetime(year + 1, 1, 1)
    return datetime(year, month + 1, 1)


def _naive_utc(fetched_at: str) -> pd.Timestamp:
    stamp = pd.Timestamp(fetched_at)
    if stamp.tzinfo is not None:
        stamp = stamp.tz_convert("UTC").tz_localize(None)
    return stamp


def parse_price_csv(content: bytes, region: str, source_url: str, source_sha: str, fetched_at: str) -> pd.DataFrame:
    frame = pd.read_csv(io.BytesIO(content), encoding="utf-8-sig")
    frame.columns = [str(column).strip() for column in frame.columns]
    if list(frame.columns) != PRICE_COLUMNS:
        raise ContractBreachError(f"unexpected AEMO columns for {region} {source_url}: {list(frame.columns)}")
    if not frame["REGION"].eq(region).all():
        raise ContractBreachError(f"{source_url} contains a region other than {region}")
    settled = pd.to_datetime(frame["SETTLEMENTDATE"], format="%Y/%m/%d %H:%M:%S", errors="coerce")
    landed = pd.DataFrame(
        {
            "region": frame["REGION"].astype("string"),
            "settlement_ts": settled,
            "total_demand_mw": pd.to_numeric(frame["TOTALDEMAND"], errors="coerce"),
            "rrp": pd.to_numeric(frame["RRP"], errors="coerce"),
            "period_type": frame["PERIODTYPE"].astype("string"),
            "source_url": source_url,
            "source_sha256": source_sha,
            "ingested_at": _naive_utc(fetched_at),
        }
    )
    return landed.sort_values("settlement_ts").reset_index(drop=True)


def price_month_is_complete(frame: pd.DataFrame, yyyymm: str) -> bool:
    closing = pd.Timestamp(_closing_timestamp(yyyymm))
    return bool((frame["settlement_ts"] == closing).any())


def parse_generation_json(
    content: bytes,
    region: str,
    source_url: str,
    source_sha: str,
    fetched_at: str,
) -> pd.DataFrame:
    payload = json.loads(content)
    if payload.get("region") != region:
        raise ContractBreachError(f"{source_url} region is {payload.get('region')}, expected {region}")
    rows: list[dict[str, Any]] = []
    for series in payload.get("data", []):
        if series.get("data_type") != "energy" or not series.get("fuel_tech"):
            continue
        history = series.get("history") or {}
        if history.get("interval") != "1d":
            raise ContractBreachError(f"{source_url} {series.get('id')} interval is not 1d")
        if series.get("units") != "GWh":
            raise ContractBreachError(f"{source_url} {series.get('id')} units are {series.get('units')}")
        start = date.fromisoformat(str(history["start"])[:10])
        for offset, value in enumerate(history.get("data") or []):
            rows.append(
                {
                    "region": region,
                    "trading_date": start + timedelta(days=offset),
                    "fuel_tech": series["fuel_tech"],
                    "energy_gwh": value,
                    "units": "GWh",
                    "source_url": source_url,
                    "source_sha256": source_sha,
                    "ingested_at": _naive_utc(fetched_at),
                }
            )
    if not rows:
        raise ContractBreachError(f"{source_url} contained no energy series")
    frame = pd.DataFrame(rows)
    frame["trading_date"] = pd.to_datetime(frame["trading_date"])
    frame["energy_gwh"] = pd.to_numeric(frame["energy_gwh"], errors="coerce")
    return frame.sort_values(["trading_date", "fuel_tech"]).reset_index(drop=True)


def _land_price(region: str, yyyymm: str, client) -> LandedFile:
    url = price_url(region, yyyymm)
    fetched_at = _now()
    raw = fetch_bytes(url, client, max_bytes=20_000_000)
    digest = _sha256(raw)
    frame = parse_price_csv(raw, region, url, digest, fetched_at)
    contract = load_contract("price_demand.yaml")
    enforce(frame, contract, f"{region} {yyyymm}")
    complete = price_month_is_complete(frame, yyyymm)
    path = bronze_root() / "price_demand" / f"region={region}" / f"month={month_label(yyyymm)}" / "part.parquet"
    _write_parquet(frame, path)
    parquet_hash = _sha256(path.read_bytes())
    logger.info(
        "landed price %s %s rows=%s complete=%s",
        region,
        yyyymm,
        len(frame),
        complete,
    )
    return LandedFile(
        dataset="aemo_price_and_demand",
        path=_rel(path),
        source_url=url,
        source_sha256=digest,
        parquet_sha256=parquet_hash,
        fetched_at=fetched_at,
        rows=len(frame),
        bytes=path.stat().st_size,
        complete=complete,
        watermark_dataset="price_demand",
        watermark_key=f"{region}|{yyyymm}",
    )


def _generation_year_is_complete(frame: pd.DataFrame, year: int) -> bool:
    if frame.empty:
        return False
    last_day = pd.Timestamp(frame["trading_date"].max()).date()
    return last_day >= date(year, 12, 31)


def _land_generation(region: str, year: int, client) -> LandedFile:
    url = generation_url(region, year)
    fetched_at = _now()
    raw = fetch_bytes(url, client, max_bytes=5_000_000)
    digest = _sha256(raw)
    frame = parse_generation_json(raw, region, url, digest, fetched_at)
    contract = load_contract("generation_daily.yaml")
    enforce(frame, contract, f"{region} {year}")
    complete = _generation_year_is_complete(frame, year)
    path = bronze_root() / "generation_daily" / f"region={region}" / f"year={year}" / "part.parquet"
    _write_parquet(frame, path)
    parquet_hash = _sha256(path.read_bytes())
    logger.info(
        "landed generation %s %s rows=%s complete=%s",
        region,
        year,
        len(frame),
        complete,
    )
    return LandedFile(
        dataset="open_electricity_generation_daily",
        path=_rel(path),
        source_url=url,
        source_sha256=digest,
        parquet_sha256=parquet_hash,
        fetched_at=fetched_at,
        rows=len(frame),
        bytes=path.stat().st_size,
        complete=complete,
        watermark_dataset="generation_daily",
        watermark_key=f"{region}|{year}",
    )


def _write_manifest(entries: dict[str, dict[str, Any]]) -> None:
    files = [entries[key] for key in sorted(entries)]
    parquet_paths = {_rel(path) for path in bronze_root().rglob("*.parquet")}
    known = {entry["path"] for entry in files}
    missing = sorted(parquet_paths - known)
    orphan = sorted(known - parquet_paths)
    if missing or orphan:
        raise ContractBreachError(f"manifest drift missing={missing[:5]} orphan={orphan[:5]}")
    payload = {
        "version": 1,
        "generator": "nem-grid-pulse",
        "study_window": {
            "price_start": PRICE_START,
            "price_end": PRICE_END,
            "regions": list(REGIONS),
            "generation_years": list(GENERATION_YEARS),
            "timezone": "NEM time (AEST, UTC+10, no daylight saving)",
        },
        "files": files,
    }
    path = manifest_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _manifest_from_watermarks(watermarks: dict[str, Any]) -> dict[str, dict[str, Any]]:
    entries: dict[str, dict[str, Any]] = {}
    for dataset, keys in watermarks.items():
        for key, meta in keys.items():
            path = meta.get("path")
            if not path:
                continue
            if dataset == "price_demand":
                region, yyyymm = key.split("|")
                source_url = price_url(region, yyyymm)
                public_dataset = "aemo_price_and_demand"
            else:
                region, year = key.split("|")
                source_url = generation_url(region, int(year))
                public_dataset = "open_electricity_generation_daily"
            file_path = repo_root() / path
            entries[path] = {
                "dataset": public_dataset,
                "path": path,
                "source_url": source_url,
                "source_sha256": meta["source_sha256"],
                "parquet_sha256": meta["parquet_sha256"],
                "fetched_at": meta["fetched_at"],
                "rows": meta["rows"],
                "bytes": file_path.stat().st_size if file_path.exists() else meta.get("bytes", 0),
                "complete": meta["complete"],
            }
    return entries


def ingest_all(
    *,
    dataset: str = "all",
    start: str = PRICE_START,
    end: str = PRICE_END,
    force: bool = False,
    allow_source_failure: bool = False,
    workers: int = 4,
) -> int:
    """Download new partitions. Returns a process exit code."""
    logging.getLogger("httpx").setLevel(logging.WARNING)
    watermarks = load_watermarks(watermark_path())
    jobs: list[tuple[str, tuple]] = []

    if dataset in {"all", "price"}:
        for region in REGIONS:
            for yyyymm in iter_months(start, end):
                key = f"{region}|{yyyymm}"
                if should_skip(watermarks, "price_demand", key, force=force):
                    logger.info("skip complete price partition %s", key)
                    continue
                jobs.append(("price", (region, yyyymm)))

    if dataset in {"all", "generation"}:
        for region in REGIONS:
            for year in GENERATION_YEARS:
                key = f"{region}|{year}"
                if should_skip(watermarks, "generation_daily", key, force=force):
                    logger.info("skip complete generation partition %s", key)
                    continue
                jobs.append(("generation", (region, year)))

    if not jobs:
        logger.info("nothing to ingest; watermarks are current")
        _write_manifest(_manifest_from_watermarks(watermarks))
        return 0

    source_failures: list[str] = []
    contract_failures: list[Exception] = []
    try:
        with make_client() as client:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {}
                for kind, args in jobs:
                    if kind == "price":
                        futures[pool.submit(_land_price, args[0], args[1], client)] = (kind, args)
                    else:
                        futures[pool.submit(_land_generation, args[0], args[1], client)] = (kind, args)
                for future in as_completed(futures):
                    kind, args = futures[future]
                    try:
                        landed = future.result()
                    except (MissingDatasetError, SourceUnavailableError) as exc:
                        source_failures.append(f"{kind} {args}: {exc}")
                        logger.warning("source unavailable for %s %s: %s", kind, args, exc)
                        continue
                    except (ContractBreachError, UnexpectedStatusError) as exc:
                        contract_failures.append(exc)
                        logger.error("contract breach for %s %s: %s", kind, args, exc)
                        continue
                    except Exception as exc:
                        contract_failures.append(exc)
                        logger.exception("failed to land %s %s", kind, args)
                        continue
                    watermarks[landed.watermark_dataset][landed.watermark_key] = {
                        "complete": landed.complete,
                        "rows": landed.rows,
                        "parquet_sha256": landed.parquet_sha256,
                        "source_sha256": landed.source_sha256,
                        "fetched_at": landed.fetched_at,
                        "path": landed.path,
                        "bytes": landed.bytes,
                    }
    finally:
        save_watermarks(watermark_path(), watermarks)

    if not contract_failures:
        _write_manifest(_manifest_from_watermarks(watermarks))
    if contract_failures:
        raise contract_failures[0]

    if source_failures:
        logger.error("%s source failures", len(source_failures))
        for failure in source_failures:
            logger.error(failure)
        if allow_source_failure:
            logger.warning("continuing because --allow-source-failure is set")
            return 0
        return 1
    return 0
