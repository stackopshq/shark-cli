"""Tests for ``orca hypervisor`` commands."""

from __future__ import annotations

import json

SAMPLE_HYPERVISORS = {
    "hypervisors": [
        {
            "id": 1,
            "hypervisor_hostname": "compute-01",
            "hypervisor_type": "QEMU",
            "state": "up",
            "status": "enabled",
            "vcpus": 32,
            "vcpus_used": 30,         # 93.75 % — RED
            "memory_mb": 131072,       # 128 GB
            "memory_mb_used": 65536,   # 50 % — GREEN
            "local_gb": 1000,
            "local_gb_used": 800,      # 80 % — YELLOW
            "running_vms": 25,
        },
        {
            "id": 2,
            "hypervisor_hostname": "compute-02",
            "hypervisor_type": "QEMU",
            "state": "up",
            "status": "enabled",
            "vcpus": 32,
            "vcpus_used": 8,           # 25 %
            "memory_mb": 131072,
            "memory_mb_used": 16384,   # 12.5 %
            "local_gb": 1000,
            "local_gb_used": 100,      # 10 %
            "running_vms": 4,
        },
        {
            "id": 3,
            "hypervisor_hostname": "compute-03",
            "hypervisor_type": "QEMU",
            "state": "down",
            "status": "disabled",
            "vcpus": 32,
            "vcpus_used": 16,          # 50 %
            "memory_mb": 131072,
            "memory_mb_used": 100000,  # ~76 % — YELLOW
            "local_gb": 1000,
            "local_gb_used": 500,      # 50 %
            "running_vms": 12,
        },
    ]
}


class TestHypervisorList:

    def test_list(self, invoke, mock_client, write_config, sample_profile):
        write_config({"active_profile": "p", "profiles": {"p": sample_profile}})
        mock_client.get.return_value = SAMPLE_HYPERVISORS
        result = invoke(["hypervisor", "list"])
        assert result.exit_code == 0
        assert "compute-01" in result.output
        assert "compute-02" in result.output


def _hostnames(invoke_result):
    """Extract ordered hostnames from `hypervisor usage -f json` output."""
    return [r["Hostname"] for r in json.loads(invoke_result.output)]


class TestHypervisorUsage:
    """Verify the new ``usage`` command — fill rate + sorting."""

    def test_default_sort_by_max(self, invoke, mock_client, write_config, sample_profile):
        """Default sort = 'max' descending: compute-01 (94 % CPU) first, then
        compute-03 (76 % RAM), then compute-02 (25 % CPU)."""
        write_config({"active_profile": "p", "profiles": {"p": sample_profile}})
        mock_client.get.return_value = SAMPLE_HYPERVISORS
        result = invoke(["hypervisor", "usage", "-f", "json"])
        assert result.exit_code == 0
        assert _hostnames(result) == ["compute-01", "compute-03", "compute-02"]

    def test_sort_by_cpu(self, invoke, mock_client, write_config, sample_profile):
        write_config({"active_profile": "p", "profiles": {"p": sample_profile}})
        mock_client.get.return_value = SAMPLE_HYPERVISORS
        result = invoke(["hypervisor", "usage", "--sort-by", "cpu", "-f", "json"])
        assert result.exit_code == 0
        # CPU: compute-01 (94 %) > compute-03 (50 %) > compute-02 (25 %)
        assert _hostnames(result) == ["compute-01", "compute-03", "compute-02"]

    def test_sort_by_ram(self, invoke, mock_client, write_config, sample_profile):
        write_config({"active_profile": "p", "profiles": {"p": sample_profile}})
        mock_client.get.return_value = SAMPLE_HYPERVISORS
        result = invoke(["hypervisor", "usage", "--sort-by", "ram", "-f", "json"])
        assert result.exit_code == 0
        # RAM: compute-03 (~76 %) > compute-01 (50 %) > compute-02 (12.5 %)
        assert _hostnames(result) == ["compute-03", "compute-01", "compute-02"]

    def test_sort_by_vms(self, invoke, mock_client, write_config, sample_profile):
        write_config({"active_profile": "p", "profiles": {"p": sample_profile}})
        mock_client.get.return_value = SAMPLE_HYPERVISORS
        result = invoke(["hypervisor", "usage", "--sort-by", "vms", "-f", "json"])
        assert result.exit_code == 0
        # VMs: 25 > 12 > 4
        assert _hostnames(result) == ["compute-01", "compute-03", "compute-02"]

    def test_reverse_sort(self, invoke, mock_client, write_config, sample_profile):
        write_config({"active_profile": "p", "profiles": {"p": sample_profile}})
        mock_client.get.return_value = SAMPLE_HYPERVISORS
        result = invoke(["hypervisor", "usage", "--reverse", "-f", "json"])
        assert result.exit_code == 0
        # Least-loaded first now
        assert _hostnames(result) == ["compute-02", "compute-03", "compute-01"]

    def test_threshold_filters(self, invoke, mock_client, write_config, sample_profile):
        """--threshold 80 keeps only compute-01 (94 % CPU)."""
        write_config({"active_profile": "p", "profiles": {"p": sample_profile}})
        mock_client.get.return_value = SAMPLE_HYPERVISORS
        result = invoke(["hypervisor", "usage", "--threshold", "80", "-f", "json"])
        assert result.exit_code == 0
        assert _hostnames(result) == ["compute-01"]

    def test_threshold_above_all(self, invoke, mock_client, write_config, sample_profile):
        write_config({"active_profile": "p", "profiles": {"p": sample_profile}})
        mock_client.get.return_value = SAMPLE_HYPERVISORS
        result = invoke(["hypervisor", "usage", "--threshold", "99", "-f", "json"])
        assert result.exit_code == 0
        assert json.loads(result.output) == []

    def test_top_n_limits(self, invoke, mock_client, write_config, sample_profile):
        write_config({"active_profile": "p", "profiles": {"p": sample_profile}})
        mock_client.get.return_value = SAMPLE_HYPERVISORS
        result = invoke(["hypervisor", "usage", "--top", "1", "-f", "json"])
        assert result.exit_code == 0
        assert _hostnames(result) == ["compute-01"]

    def test_handles_zero_total(self, invoke, mock_client, write_config, sample_profile):
        """Hypervisor with 0 totals (placement-only or stale) shouldn't crash."""
        write_config({"active_profile": "p", "profiles": {"p": sample_profile}})
        mock_client.get.return_value = {"hypervisors": [{
            "id": 99,
            "hypervisor_hostname": "ghost",
            "state": "down",
            "vcpus": 0, "vcpus_used": 0,
            "memory_mb": 0, "memory_mb_used": 0,
            "local_gb": 0, "local_gb_used": 0,
            "running_vms": 0,
        }]}
        result = invoke(["hypervisor", "usage", "-f", "json"])
        assert result.exit_code == 0
        assert _hostnames(result) == ["ghost"]

    def test_empty_list(self, invoke, mock_client, write_config, sample_profile):
        write_config({"active_profile": "p", "profiles": {"p": sample_profile}})
        mock_client.get.return_value = {"hypervisors": []}
        result = invoke(["hypervisor", "usage"])
        assert result.exit_code == 0
        assert "No hypervisors" in result.output

    def test_calls_correct_endpoint(self, invoke, mock_client, write_config, sample_profile):
        write_config({"active_profile": "p", "profiles": {"p": sample_profile}})
        mock_client.get.return_value = SAMPLE_HYPERVISORS
        result = invoke(["hypervisor", "usage"])
        assert result.exit_code == 0
        called_url = mock_client.get.call_args[0][0]
        assert called_url.endswith("/os-hypervisors/detail")
