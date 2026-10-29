"""Write INSIGHTS.md from the marts."""

from __future__ import annotations

import json
from pathlib import Path

from nem_grid_pulse.publication import build_payload, render_markdown
from nem_grid_pulse.settings import repo_root


def write_insights() -> Path:
    payload = build_payload()
    path = repo_root() / "INSIGHTS.md"
    path.write_text(render_markdown(payload), encoding="utf-8")
    stats = repo_root() / "reports" / "headline_stats.json"
    stats.parent.mkdir(parents=True, exist_ok=True)
    stats.write_text(json.dumps(payload["narrative"], indent=2) + "\n", encoding="utf-8")
    return path
