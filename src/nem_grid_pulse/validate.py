"""Re-check the committed bronze snapshot against contracts and the manifest."""

from __future__ import annotations

import hashlib
import json
import logging

import pandas as pd

from nem_grid_pulse.contracts import ContractBreachError, enforce, load_contract
from nem_grid_pulse.settings import bronze_root, manifest_path, repo_root

logger = logging.getLogger(__name__)
MAX_PARQUET_BYTES = 50 * 1024 * 1024


def _sha256(path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_snapshot() -> None:
    manifest_file = manifest_path()
    if not manifest_file.exists():
        raise ContractBreachError(f"manifest not found at {manifest_file}")
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    files = manifest.get("files", [])
    if not files:
        raise ContractBreachError("manifest has no files")

    on_disk = {path.relative_to(repo_root()).as_posix() for path in bronze_root().rglob("*.parquet")}
    listed = {entry["path"] for entry in files}
    if on_disk != listed:
        raise ContractBreachError(
            f"manifest does not match bronze files missing={sorted(on_disk - listed)[:5]} "
            f"extra={sorted(listed - on_disk)[:5]}"
        )

    price_contract = load_contract("price_demand.yaml")
    generation_contract = load_contract("generation_daily.yaml")
    for entry in files:
        path = repo_root() / entry["path"]
        size = path.stat().st_size
        if size > MAX_PARQUET_BYTES:
            raise ContractBreachError(f"{entry['path']} is {size} bytes, over 50 MB")
        actual = _sha256(path)
        if actual != entry["parquet_sha256"]:
            raise ContractBreachError(f"sha256 mismatch for {entry['path']}")
        frame = pd.read_parquet(path)
        if len(frame) != entry["rows"]:
            raise ContractBreachError(
                f"row count mismatch for {entry['path']}: file {len(frame)} manifest {entry['rows']}"
            )
        contract = price_contract if entry["dataset"] == "aemo_price_and_demand" else generation_contract
        enforce(frame, contract, entry["path"])
    logger.info("validated %s bronze files", len(files))
