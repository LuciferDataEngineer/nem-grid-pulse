"""Build the single-file dashboard from the marts."""

from __future__ import annotations

import json
from pathlib import Path

from nem_grid_pulse.publication import build_payload
from nem_grid_pulse.settings import repo_root


def build_dashboard() -> Path:
    root = repo_root()
    payload = build_payload()
    template = (root / "dashboard" / "template.html").read_text(encoding="utf-8")
    echarts = (root / "dashboard" / "vendor" / "echarts.min.js").read_text(encoding="utf-8")
    echarts = echarts.replace("</script>", "<\\/script>")
    data = json.dumps(payload, separators=(",", ":")).replace("<", "\\u003c")
    html = template.replace("/*__ECHARTS__*/", echarts).replace("__DATA_JSON__", data)
    destination = root / "dashboard" / "dist" / "index.html"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(html, encoding="utf-8")
    return destination
