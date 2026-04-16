"""Tests for ``orca usage`` command."""

from __future__ import annotations

from orca_cli.core.config import save_profile, set_active_profile


# ── Helpers ────────────────────────────────────────────────────────────────


def _setup_mock(mock_client, server_usages=None, empty=False):
    mock_client.compute_url = "https://nova.example.com/v2.1"

    if empty:
        tenant_usages = []
    else:
        server_usages = server_usages or [
            {"name": "web-1", "instance_id": "srv-1", "state": "active",
             "vcpus": 2, "memory_mb": 4096, "local_gb": 20,
             "hours": 720.5, "started_at": "2025-01-01T00:00:00",
             "ended_at": None},
            {"name": "db-1", "instance_id": "srv-2", "state": "active",
             "vcpus": 4, "memory_mb": 8192, "local_gb": 100,
             "hours": 360.0, "started_at": "2025-01-15T00:00:00",
             "ended_at": "2025-01-31T00:00:00"},
        ]
        tenant_usages = [{
            "total_vcpus_usage": 1441.0,
            "total_memory_mb_usage": 2949120.0,
            "total_local_gb_usage": 14420.0,
            "total_hours": 1080.5,
            "server_usages": server_usages,
        }]

    def _get(url, **kwargs):
        if "os-simple-tenant-usage" in url:
            return {"tenant_usages": tenant_usages}
        return {}

    mock_client.get = _get


# ══════════════════════════════════════════════════════════════════════════
#  usage
# ══════════���═══════════════════════════════════════════════════════════════


class TestUsage:

    def test_usage_basic(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["usage"])
        assert result.exit_code == 0
        assert "web-1" in result.output
        assert "db-1" in result.output
        assert "720" in result.output

    def test_usage_empty(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client, empty=True)

        result = invoke(["usage"])
        assert result.exit_code == 0
        assert "No usage data" in result.output

    def test_usage_with_dates(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["usage", "--start", "2025-01-01", "--end", "2025-01-31"])
        assert result.exit_code == 0
        assert "web-1" in result.output

    def test_usage_summary(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["usage"])
        assert result.exit_code == 0
        assert "vCPU" in result.output
        assert "1441" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  Help
# ══════════════════════════════════════════════════════════════════════════


class TestUsageHelp:

    def test_usage_help(self, invoke):
        result = invoke(["usage", "--help"])
        assert result.exit_code == 0
        assert "--start" in result.output
        assert "--end" in result.output
