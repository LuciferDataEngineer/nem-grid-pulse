"""High-watermark state. A complete partition is not downloaded again."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_watermarks(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"price_demand": {}, "generation_daily": {}}
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.setdefault("price_demand", {})
    payload.setdefault("generation_daily", {})
    return payload


def save_watermarks(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def should_skip(watermarks: dict[str, Any], dataset: str, key: str, *, force: bool) -> bool:
    if force:
        return False
    entry = watermarks.get(dataset, {}).get(key)
    if not entry:
        return False
    return bool(entry.get("complete"))
