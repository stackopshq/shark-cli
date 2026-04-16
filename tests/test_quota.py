"""Tests for ``orca quota`` command."""

from __future__ import annotations

from orca_cli.core.config import save_profile, set_active_profile

# ── Helpers ────────────────────────────────────────────────────────────────


def _setup_mock(mock_client, nova=None, cinder=None, neutron_quotas=None,
                nets=0, subnets=0, ports=0, routers=0, fips=0, sgs=0):
    mock_client.compute_url = "https://nova.example.com/v2.1"
    mock_client.volume_url = "https://cinder.example.com/v3"
    mock_client.network_url = "https://neutron.example.com"
    mock_client._project_id = "proj-1"

    nova = nova or {
        "limits": {"absolute": {
            "totalInstancesUsed": 3, "maxTotalInstances": 10,
            "totalCoresUsed": 8, "maxTotalCores": 20,
            "totalRAMUsed": 16384, "maxTotalRAMSize": 51200,
            "maxTotalKeypairs": 100,
            "totalServerGroupsUsed": 1, "maxServerGroups": 10,
        }}
    }
    cinder = cinder or {
        "limits": {"absolute": {
            "totalVolumesUsed": 5, "maxTotalVolumes": 20,
            "totalGigabytesUsed": 250, "maxTotalVolumeGigabytes": 1000,
            "totalSnapshotsUsed": 2, "maxTotalSnapshots": 10,
            "totalBackupsUsed": 1, "maxTotalBackups": 10,
            "totalBackupGigabytesUsed": 50, "maxTotalBackupGigabytes": 500,
        }}
    }
    neutron_quotas = neutron_quotas or {
        "network": 50, "subnet": 100, "port": 200,
        "router": 10, "floatingip": 20, "security_group": 50,
        "security_group_rule": 200,
    }

    def _get(url, **kwargs):
        # Nova limits
        if "/limits" in url and "nova" in url:
            return nova
        # Cinder limits
        if "/limits" in url and "cinder" in url:
            return cinder
        # Neutron quotas
        if "/quotas" in url:
            return {"quotas": [neutron_quotas]}
        # Neutron resource counts
        if "/networks" in url:
            return {"networks": [{}] * nets}
        if "/subnets" in url:
            return {"subnets": [{}] * subnets}
        if "/ports" in url:
            return {"ports": [{}] * ports}
        if "/routers" in url:
            return {"routers": [{}] * routers}
        if "/floatingips" in url:
            return {"floatingips": [{}] * fips}
        if "/security-groups" in url:
            return {"security_groups": [{}] * sgs}
        return {}

    mock_client.get = _get


# ══════════════════════════════════════════════════════════════════════════
#  quota
# ══════════════════════════════════════════════════════════════════════════


class TestQuota:

    def test_quota_basic(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client, nets=5, subnets=8, ports=30,
                    routers=2, fips=4, sgs=6)

        result = invoke(["quota"])
        assert result.exit_code == 0
        assert "Compute" in result.output
        assert "Volume" in result.output
        assert "Network" in result.output
        assert "Instances" in result.output

    def test_quota_shows_used(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["quota"])
        assert result.exit_code == 0
        assert "3" in result.output   # totalInstancesUsed
        assert "8" in result.output   # totalCoresUsed

    def test_quota_shows_limits(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["quota"])
        assert result.exit_code == 0
        assert "10" in result.output   # maxTotalInstances
        assert "20" in result.output   # maxTotalCores

    def test_quota_unlimited(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        nova = {"limits": {"absolute": {
            "totalInstancesUsed": 0, "maxTotalInstances": -1,
            "totalCoresUsed": 0, "maxTotalCores": -1,
            "totalRAMUsed": 0, "maxTotalRAMSize": -1,
            "maxTotalKeypairs": -1,
            "totalServerGroupsUsed": 0, "maxServerGroups": -1,
        }}}
        _setup_mock(mock_client, nova=nova)

        result = invoke(["quota"])
        assert result.exit_code == 0
        assert "unlimited" in result.output

    def test_quota_network_counts(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client, nets=12, subnets=15, fips=7)

        result = invoke(["quota"])
        assert result.exit_code == 0
        assert "12" in result.output
        assert "15" in result.output
        assert "7" in result.output

    def test_quota_nova_unavailable(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        mock_client.compute_url = "https://nova.example.com/v2.1"
        mock_client.volume_url = "https://cinder.example.com/v3"
        mock_client.network_url = "https://neutron.example.com"
        mock_client._project_id = "proj-1"

        def _get(url, **kwargs):
            if "nova" in url:
                raise Exception("Nova down")
            if "cinder" in url and "/limits" in url:
                return {"limits": {"absolute": {
                    "totalVolumesUsed": 1, "maxTotalVolumes": 10,
                    "totalGigabytesUsed": 50, "maxTotalVolumeGigabytes": 500,
                    "totalSnapshotsUsed": 0, "maxTotalSnapshots": 10,
                    "totalBackupsUsed": 0, "maxTotalBackups": 10,
                    "totalBackupGigabytesUsed": 0, "maxTotalBackupGigabytes": 500,
                }}}
            if "/quotas" in url:
                return {"quotas": [{"network": 50, "subnet": 100, "port": 200,
                                    "router": 10, "floatingip": 20,
                                    "security_group": 50, "security_group_rule": 200}]}
            if "/networks" in url:
                return {"networks": []}
            if "/subnets" in url:
                return {"subnets": []}
            if "/ports" in url:
                return {"ports": []}
            if "/routers" in url:
                return {"routers": []}
            if "/floatingips" in url:
                return {"floatingips": []}
            if "/security-groups" in url:
                return {"security_groups": []}
            return {}

        mock_client.get = _get

        result = invoke(["quota"])
        assert result.exit_code == 0
        assert "unavailable" in result.output
        assert "Volume" in result.output  # other sections still render


# ══════════════════════════════════════════════════════════════════════════
#  _row helper
# ══════════════════════════════════════════════════════════════════════════


class TestRow:

    def test_row_percentage(self):
        from orca_cli.commands.quota import _row
        r = _row("Compute", "Instances", 3, 10)
        assert r["service"] == "Compute"
        assert r["resource"] == "Instances"
        assert r["used"] == "3"
        assert r["limit"] == "10"
        assert "30%" in r["usage"]

    def test_row_unlimited(self):
        from orca_cli.commands.quota import _row
        r = _row("Compute", "Instances", 5, -1)
        assert r["limit"] == "unlimited"
        assert r["usage"] == "—"

    def test_row_dash_used(self):
        from orca_cli.commands.quota import _row
        r = _row("Compute", "Key Pairs", "—", 100)
        assert r["used"] == "—"
        assert r["usage"] == "—"

    def test_row_zero_limit(self):
        from orca_cli.commands.quota import _row
        r = _row("Network", "FIPs", 0, 0)
        assert r["usage"] == "—"  # ZeroDivisionError handled

    def test_row_high_usage_yellow(self):
        from orca_cli.commands.quota import _row
        r = _row("Compute", "vCPUs", 17, 20)
        assert "yellow" in r["usage"]
        assert "85%" in r["usage"]

    def test_row_critical_usage_red(self):
        from orca_cli.commands.quota import _row
        r = _row("Compute", "vCPUs", 19, 20)
        assert "red" in r["usage"]
        assert "95%" in r["usage"]

    def test_row_low_usage_green(self):
        from orca_cli.commands.quota import _row
        r = _row("Compute", "vCPUs", 5, 20)
        assert "green" in r["usage"]
        assert "25%" in r["usage"]


# ══════════════════════════════════════════════════════════════════════════
#  Help
# ══════════════════════════════════════════════════════════════════════════


class TestQuotaHelp:

    def test_quota_help(self, invoke):
        result = invoke(["quota", "--help"])
        assert result.exit_code == 0
        assert "quota" in result.output.lower()
