import hashlib
import json

import pytest

from nem_grid_pulse.settings import manifest_path, repo_root


def test_committed_snapshot_matches_the_manifest():
    path = manifest_path()
    if not path.exists():
        pytest.skip("bronze snapshot has not been ingested")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    files = manifest["files"]
    assert files, "manifest is empty"
    listed = {entry["path"] for entry in files}
    on_disk = {
        item.relative_to(repo_root()).as_posix() for item in (repo_root() / "data" / "bronze").rglob("*.parquet")
    }
    assert listed == on_disk
    for entry in files:
        file_path = repo_root() / entry["path"]
        assert file_path.stat().st_size < 50 * 1024 * 1024
        digest = hashlib.sha256(file_path.read_bytes()).hexdigest()
        assert digest == entry["parquet_sha256"]
        assert entry["source_url"].startswith("https://")
        assert entry["fetched_at"]
        assert entry["rows"] > 0
