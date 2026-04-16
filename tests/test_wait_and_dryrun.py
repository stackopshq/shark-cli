"""Tests for --wait and --dry-run flags, plus cache/waiter utilities."""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from orca_cli.core import cache
from orca_cli.core.waiter import wait_for_resource

# UUIDs that pass validate_id
SRV = "11111111-1111-1111-1111-111111111111"
VOL = "22222222-2222-2222-2222-222222222222"


# ══════════════════════════════════════════════════════════════════════════
#  Cache module
# ══════════════════════════════════════════════════════════════════════════

class TestCache:

    def test_miss_when_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr("orca_cli.core.cache._CACHE_DIR", tmp_path)
        assert cache.load(None, "servers") is None

    def test_save_and_hit(self, tmp_path, monkeypatch):
        monkeypatch.setattr("orca_cli.core.cache._CACHE_DIR", tmp_path)
        items = [{"id": "abc", "name": "my-vm"}]
        cache.save(None, "servers", items)
        assert cache.load(None, "servers") == items

    def test_expired_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.setattr("orca_cli.core.cache._CACHE_DIR", tmp_path)
        items = [{"id": "abc", "name": "my-vm"}]
        # Write with a timestamp 60 seconds in the past
        p = tmp_path / "default_servers.json"
        p.write_text(json.dumps({"ts": time.time() - 60, "items": items}))
        assert cache.load(None, "servers") is None

    def test_invalidate_removes_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr("orca_cli.core.cache._CACHE_DIR", tmp_path)
        cache.save(None, "servers", [{"id": "x"}])
        cache.invalidate(None, "servers")
        assert cache.load(None, "servers") is None

    def test_invalid_json_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.setattr("orca_cli.core.cache._CACHE_DIR", tmp_path)
        (tmp_path / "default_servers.json").write_text("not-json")
        assert cache.load(None, "servers") is None

    def test_profile_namespacing(self, tmp_path, monkeypatch):
        monkeypatch.setattr("orca_cli.core.cache._CACHE_DIR", tmp_path)
        cache.save("prod", "servers", [{"id": "prod-vm"}])
        cache.save("dev", "servers", [{"id": "dev-vm"}])
        assert cache.load("prod", "servers") == [{"id": "prod-vm"}]
        assert cache.load("dev", "servers") == [{"id": "dev-vm"}]


# ══════════════════════════════════════════════════════════════════════════
#  Waiter module
# ══════════════════════════════════════════════════════════════════════════

class TestWaitForResource:

    def _client(self, statuses: list[str]):
        """Mock client whose .get() cycles through status responses."""
        client = MagicMock()
        responses = iter([{"server": {"status": s}} for s in statuses])
        client.get.side_effect = lambda url, **kw: next(responses)
        return client

    def test_immediate_target(self):
        client = self._client(["ACTIVE"])
        wait_for_resource(client, "https://nova/servers/1", "server", "ACTIVE",
                          label="Server 1", timeout=10)
        assert client.get.call_count == 1

    def test_waits_through_build(self):
        client = self._client(["BUILD", "BUILD", "ACTIVE"])
        with patch("time.sleep"):
            wait_for_resource(client, "https://nova/servers/1", "server", "ACTIVE",
                              label="Server 1", timeout=30)
        assert client.get.call_count == 3

    def test_raises_on_error_status(self):
        client = self._client(["BUILD", "ERROR"])
        with patch("time.sleep"), pytest.raises(Exception, match="ERROR"):
            wait_for_resource(client, "https://nova/servers/1", "server", "ACTIVE",
                              label="Server 1", timeout=30)

    def test_raises_on_timeout(self):
        client = MagicMock()
        client.get.return_value = {"server": {"status": "BUILD"}}
        with patch("time.monotonic", side_effect=[0, 0, 400]):
            with patch("time.sleep"):
                with pytest.raises(Exception, match="Timeout"):
                    wait_for_resource(client, "https://nova/servers/1", "server", "ACTIVE",
                                      label="Server 1", timeout=300)

    def test_delete_mode_treats_404_as_success(self):
        from orca_cli.core.exceptions import APIError
        client = MagicMock()
        err = APIError(404, "Not found")
        client.get.side_effect = err
        with patch("time.sleep"):
            wait_for_resource(client, "https://nova/servers/1", "server", "DELETED",
                              label="Server 1", delete_mode=True, timeout=30)


# ══════════════════════════════════════════════════════════════════════════
#  server delete --dry-run
# ══════════════════════════════════════════════════════════════════════════

class TestServerDeleteDryRun:

    def test_dry_run_shows_info_and_does_not_delete(self, invoke, mock_client):
        mock_client.get.return_value = {
            "server": {"id": SRV, "name": "web-01", "status": "ACTIVE", "image": {"id": "img-1"}}
        }
        result = invoke(["server", "delete", SRV, "--dry-run"])
        assert result.exit_code == 0
        assert "Would delete" in result.output
        assert "web-01" in result.output
        assert "ACTIVE" in result.output
        mock_client.delete.assert_not_called()

    def test_dry_run_skips_confirmation(self, invoke, mock_client):
        mock_client.get.return_value = {
            "server": {"id": SRV, "name": "web-01", "status": "ACTIVE"}
        }
        result = invoke(["server", "delete", SRV, "--dry-run"])
        assert result.exit_code == 0
        mock_client.delete.assert_not_called()


# ══════════════════════════════════════════════════════════════════════════
#  server delete --wait
# ══════════════════════════════════════════════════════════════════════════

class TestServerDeleteWait:

    def test_wait_calls_waiter(self, invoke, mock_client):
        with patch("orca_cli.commands.server.wait_for_resource") as mock_wait:
            result = invoke(["server", "delete", SRV, "--yes", "--wait"])
        assert result.exit_code == 0
        mock_wait.assert_called_once()
        _, kwargs = mock_wait.call_args
        assert kwargs.get("delete_mode") is True


# ══════════════════════════════════════════════════════════════════════════
#  server create --wait
# ══════════════════════════════════════════════════════════════════════════

class TestServerCreateWait:

    def test_no_wait_prints_hint(self, invoke, mock_client):
        mock_client.post.return_value = {"server": {"id": "srv-new", "adminPass": ""}}
        result = invoke([
            "server", "create",
            "--name", "my-vm",
            "--flavor", "flv-1",
            "--image", "img-1",
        ])
        assert result.exit_code == 0
        assert "srv-new" in result.output
        assert "orca server show" in result.output

    def test_wait_invokes_waiter(self, invoke, mock_client):
        mock_client.post.return_value = {"server": {"id": "srv-new", "adminPass": ""}}
        with patch("orca_cli.commands.server.wait_for_resource") as mock_wait:
            result = invoke([
                "server", "create",
                "--name", "my-vm",
                "--flavor", "flv-1",
                "--image", "img-1",
                "--wait",
            ])
        assert result.exit_code == 0
        mock_wait.assert_called_once()
        _, kwargs = mock_wait.call_args
        assert kwargs.get("target_status") == "ACTIVE" or "ACTIVE" in str(mock_wait.call_args)


# ══════════════════════════════════════════════════════════════════════════
#  server start/stop/reboot --wait
# ══════════════════════════════════════════════════════════════════════════

class TestServerActionWait:

    def test_start_no_wait(self, invoke, mock_client):
        mock_client.post.return_value = {}
        result = invoke(["server", "start", SRV])
        assert result.exit_code == 0
        assert "Start" in result.output

    def test_start_with_wait(self, invoke, mock_client):
        mock_client.post.return_value = {}
        with patch("orca_cli.commands.server.wait_for_resource") as mock_wait:
            result = invoke(["server", "start", SRV, "--wait"])
        assert result.exit_code == 0
        mock_wait.assert_called_once()
        assert "ACTIVE" in str(mock_wait.call_args)

    def test_stop_with_wait(self, invoke, mock_client):
        mock_client.post.return_value = {}
        with patch("orca_cli.commands.server.wait_for_resource") as mock_wait:
            result = invoke(["server", "stop", SRV, "--wait"])
        assert result.exit_code == 0
        mock_wait.assert_called_once()
        assert "SHUTOFF" in str(mock_wait.call_args)

    def test_reboot_with_wait(self, invoke, mock_client):
        mock_client.post.return_value = {}
        with patch("orca_cli.commands.server.wait_for_resource") as mock_wait:
            result = invoke(["server", "reboot", SRV, "--wait"])
        assert result.exit_code == 0
        mock_wait.assert_called_once()
        assert "ACTIVE" in str(mock_wait.call_args)


# ══════════════════════════════════════════════════════════════════════════
#  volume create --wait / volume delete --dry-run / --wait
# ══════════════════════════════════════════════════════════════════════════

class TestVolumeCreateWait:

    def test_no_wait(self, invoke, mock_client):
        mock_client.post.return_value = {"volume": {"id": "vol-1", "name": "data", "size": 50}}
        result = invoke(["volume", "create", "--name", "data", "--size", "50"])
        assert result.exit_code == 0
        assert "vol-1" in result.output

    def test_wait_invokes_waiter(self, invoke, mock_client):
        mock_client.post.return_value = {"volume": {"id": "vol-1", "name": "data", "size": 50}}
        with patch("orca_cli.commands.volume.wait_for_resource") as mock_wait:
            result = invoke(["volume", "create", "--name", "data", "--size", "50", "--wait"])
        assert result.exit_code == 0
        mock_wait.assert_called_once()
        assert "available" in str(mock_wait.call_args)


class TestVolumeDeleteDryRun:

    def test_dry_run_shows_info(self, invoke, mock_client):
        mock_client.get.return_value = {
            "volume": {"id": VOL, "name": "data", "size": 50, "status": "available", "attachments": []}
        }
        result = invoke(["volume", "delete", VOL, "--dry-run"])
        assert result.exit_code == 0
        assert "Would delete" in result.output
        assert "data" in result.output
        assert "50" in result.output
        mock_client.delete.assert_not_called()

    def test_dry_run_warns_on_attached(self, invoke, mock_client):
        mock_client.get.return_value = {
            "volume": {"id": VOL, "name": "data", "size": 50, "status": "in-use",
                       "attachments": [{"server_id": SRV}]}
        }
        result = invoke(["volume", "delete", VOL, "--dry-run"])
        assert result.exit_code == 0
        assert "attached" in result.output
        mock_client.delete.assert_not_called()

    def test_wait_invokes_waiter(self, invoke, mock_client):
        with patch("orca_cli.commands.volume.wait_for_resource") as mock_wait:
            result = invoke(["volume", "delete", VOL, "--yes", "--wait"])
        assert result.exit_code == 0
        mock_wait.assert_called_once()
        _, kwargs = mock_wait.call_args
        assert kwargs.get("delete_mode") is True
