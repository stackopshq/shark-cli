"""Tests for orca_cli.core.cache — 30 s TTL completion cache."""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import patch

from orca_cli.core import cache


def _patch_dir(tmp_path: Path):
    return patch.object(cache, "_CACHE_DIR", tmp_path)


class TestCache:

    def test_save_then_load_roundtrip(self, tmp_path):
        with _patch_dir(tmp_path):
            cache.save("p", "servers", [{"id": "1"}])
            assert cache.load("p", "servers") == [{"id": "1"}]

    def test_load_missing_returns_none(self, tmp_path):
        with _patch_dir(tmp_path):
            assert cache.load("p", "nonexistent") is None

    def test_load_expired_returns_none(self, tmp_path):
        with _patch_dir(tmp_path):
            stale = tmp_path / "p_servers.json"
            stale.write_text(json.dumps({"ts": time.time() - 3600, "items": [{"id": "x"}]}))
            assert cache.load("p", "servers") is None

    def test_load_corrupt_returns_none(self, tmp_path):
        """Exception paths swallow — never crash the shell."""
        with _patch_dir(tmp_path):
            corrupt = tmp_path / "p_servers.json"
            corrupt.write_text("{not json")
            assert cache.load("p", "servers") is None

    def test_save_to_unwritable_swallows(self, tmp_path):
        """save() never raises — completion must never break."""
        bad = tmp_path / "nope" / "nested"
        # Make the parent a file so mkdir fails
        (tmp_path / "nope").write_text("blocker")
        with patch.object(cache, "_CACHE_DIR", bad):
            cache.save("p", "servers", [{"id": "1"}])  # should not raise

    def test_invalidate_removes_entry(self, tmp_path):
        with _patch_dir(tmp_path):
            cache.save("p", "servers", [{"id": "1"}])
            cache.invalidate("p", "servers")
            assert cache.load("p", "servers") is None

    def test_invalidate_missing_is_noop(self, tmp_path):
        with _patch_dir(tmp_path):
            cache.invalidate("p", "never-existed")  # should not raise

    def test_default_profile_name_when_none(self, tmp_path):
        with _patch_dir(tmp_path):
            cache.save(None, "servers", [{"id": "1"}])
            assert (tmp_path / "default_servers.json").exists()
