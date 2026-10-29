"""Run the dbt-duckdb project against the local warehouse."""

from __future__ import annotations

import os
import subprocess

from nem_grid_pulse.settings import bronze_root, repo_root, warehouse_path


def run_dbt(command: str = "build") -> None:
    root = repo_root()
    warehouse_path().parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["DUCKDB_PATH"] = str(warehouse_path())
    env["BRONZE_ROOT"] = str(bronze_root())
    env["DBT_SEND_ANONYMOUS_USAGE_STATS"] = "false"
    subprocess.run(
        [
            "dbt",
            command,
            "--project-dir",
            str(root / "dbt"),
            "--profiles-dir",
            str(root / "dbt"),
        ],
        cwd=root,
        env=env,
        check=True,
    )
