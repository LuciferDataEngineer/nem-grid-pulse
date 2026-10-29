"""Data contracts. The YAML file is the source of truth; pydantic checks the file itself."""

from __future__ import annotations

from typing import Any

import pandas as pd
import yaml
from pydantic import BaseModel, Field

from nem_grid_pulse.settings import repo_root


class ContractBreachError(RuntimeError):
    """Raised when a raw file or bronze partition violates its contract."""


class ColumnRule(BaseModel):
    type: str
    required: bool = True
    nullable: bool = False
    min: float | None = None
    max: float | None = None
    allowed: list[str] | None = None


class DatasetContract(BaseModel):
    dataset: str
    version: int
    description: str = ""
    unique_key: list[str] = Field(default_factory=list)
    min_rows: int = 1
    max_rows: int | None = None
    columns: dict[str, ColumnRule]


def load_contract(name: str) -> DatasetContract:
    path = repo_root() / "contracts" / name
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return DatasetContract.model_validate(payload)


def validate_frame(df: pd.DataFrame, contract: DatasetContract) -> list[str]:
    errors: list[str] = []
    if len(df) < contract.min_rows:
        errors.append(f"row count {len(df)} is below min_rows {contract.min_rows}")
    if contract.max_rows is not None and len(df) > contract.max_rows:
        errors.append(f"row count {len(df)} is above max_rows {contract.max_rows}")

    for name, rule in contract.columns.items():
        if name not in df.columns:
            if rule.required:
                errors.append(f"missing column {name}")
            continue
        series = df[name]
        nulls = int(series.isna().sum())
        if nulls and not rule.nullable:
            errors.append(f"{name} has {nulls} nulls")
        present = series.dropna()
        if rule.allowed is not None and not present.empty:
            allowed = set(rule.allowed)
            unexpected = sorted({str(value) for value in present.unique() if str(value) not in allowed})
            if unexpected:
                errors.append(f"{name} has values outside {sorted(allowed)}: {unexpected[:8]}")
        if rule.min is not None and not present.empty:
            numeric = pd.to_numeric(present, errors="coerce")
            if numeric.isna().any():
                errors.append(f"{name} has non-numeric values")
            elif float(numeric.min()) < rule.min:
                errors.append(f"{name} min {float(numeric.min())} is below {rule.min}")
        if rule.max is not None and not present.empty:
            numeric = pd.to_numeric(present, errors="coerce")
            if numeric.notna().any() and float(numeric.max()) > rule.max:
                errors.append(f"{name} max {float(numeric.max())} is above {rule.max}")

    if contract.unique_key and set(contract.unique_key).issubset(df.columns):
        duplicates = int(df.duplicated(contract.unique_key).sum())
        if duplicates:
            errors.append(f"duplicate key rows on {contract.unique_key}: {duplicates}")
    return errors


def enforce(df: pd.DataFrame, contract: DatasetContract, context: str) -> None:
    errors = validate_frame(df, contract)
    if errors:
        detail = "; ".join(errors)
        raise ContractBreachError(f"{contract.dataset} contract failed for {context}: {detail}")


def contract_as_dict(contract: DatasetContract) -> dict[str, Any]:
    return contract.model_dump()
