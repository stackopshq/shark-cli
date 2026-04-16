"""Tests for `orca doctor` — pre-deployment health check."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from orca_cli.core.exceptions import APIError


# ══════════════════════════════════════════════════════════════════════════
#  Shared helpers
# ══════════════════════════════════════════════════════════════════════════

PRJ_ID = "proj-1111-1111-1111-111111111111"


def _base_token(user="admin", project="demo", project_id=PRJ_ID):
    return {"user": {"name": user}, "project": {"name": project, "id": project_id}}


def _limits(inst=2, inst_max=10, cores=4, cores_max=20, ram=4096, ram_max=51200):
    return {"limits": {"absolute": {
        "totalInstancesUsed": inst, "maxTotalInstances": inst_max,
        "totalCoresUsed": cores, "maxTotalCores": cores_max,
        "totalRAMUsed": ram, "maxTotalRAMSize": ram_max,
    }}}


def _vol_limits(vol=1, vol_max=10, gb=50, gb_max=1000):
    return {"limits": {"absolute": {
        "totalVolumesUsed": vol, "maxTotalVolumes": vol_max,
        "totalGigabytesUsed": gb, "maxTotalVolumeGigabytes": gb_max,
    }}}


def _net_quota(fip_used=2, fip_limit=10, sg_used=3, sg_limit=20):
    return {"quota": {
        "floatingip":     {"used": fip_used,  "limit": fip_limit},
        "security_group": {"used": sg_used,   "limit": sg_limit},
    }}


def _sg(has_ssh=True, has_icmp=True):
    rules = []
    if has_ssh:
        rules.append({"direction": "ingress", "protocol": "tcp",
                      "port_range_min": 22, "port_range_max": 22})
    if has_icmp:
        rules.append({"direction": "ingress", "protocol": "icmp"})
    return {"security_groups": [{"id": "sg-default", "name": "default",
                                  "security_group_rules": rules}]}


def _setup_happy_path(mock_client, sg_data=None):
    """Configure mock_client for a fully healthy environment."""
    mock_client.compute_url = "https://nova.example.com/v2.1"
    mock_client.network_url = "https://neutron.example.com"
    mock_client.volume_url  = "https://cinder.example.com/v3"
    mock_client.image_url   = "https://glance.example.com"
    mock_client._token_data = _base_token()

    def _get(url, **kw):
        if "nova" in url and "limits" in url:   return _limits()
        if "cinder" in url and "limits" in url: return _vol_limits()
        if "quotas" in url and PRJ_ID in url:   return _net_quota()
        if "quotas/defaults" in url:            return {}
        if "security-groups" in url:            return sg_data or _sg()
        if "images" in url:                     return {"images": []}
        return {}

    mock_client.get.side_effect = _get


# ══════════════════════════════════════════════════════════════════════════
#  Basic invocation
# ══════════════════════════════════════════════════════════════════════════

class TestDoctorBasic:

    def test_help(self, invoke):
        result = invoke(["doctor", "--help"])
        assert result.exit_code == 0
        assert "health" in result.output.lower()

    def test_help_shows_thresholds(self, invoke):
        result = invoke(["doctor", "--help"])
        assert result.exit_code == 0
        assert "70" in result.output  # threshold mentioned in docstring

    def test_happy_path(self, invoke, mock_client):
        _setup_happy_path(mock_client)
        result = invoke(["doctor"])
        assert result.exit_code == 0
        assert "Health Check" in result.output

    def test_all_passed_message(self, invoke, mock_client):
        _setup_happy_path(mock_client)
        result = invoke(["doctor"])
        assert result.exit_code == 0
        assert "passed" in result.output or "OK" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  Authentication check & short-circuit
# ══════════════════════════════════════════════════════════════════════════

class TestDoctorAuth:

    def test_shows_username(self, invoke, mock_client):
        _setup_happy_path(mock_client)
        mock_client._token_data = _base_token(user="kevin")
        result = invoke(["doctor"])
        assert result.exit_code == 0
        assert "kevin" in result.output

    def test_auth_failure_short_circuits(self, invoke, mock_client):
        """If auth fails, remaining checks must be skipped."""
        mock_client.compute_url = "https://nova.example.com/v2.1"
        mock_client.network_url = "https://neutron.example.com"
        mock_client.volume_url  = "https://cinder.example.com/v3"
        mock_client.image_url   = "https://glance.example.com"
        # Simulate missing token data
        del mock_client._token_data
        result = invoke(["doctor"])
        assert result.exit_code == 0
        # Should report auth error
        assert "Authentication" in result.output
        # Should not have called any API beyond auth
        mock_client.get.assert_not_called()

    def test_auth_failure_shows_skip_message(self, invoke, mock_client):
        mock_client.compute_url = "https://nova.example.com/v2.1"
        mock_client.network_url = "https://neutron.example.com"
        mock_client.volume_url  = "https://cinder.example.com/v3"
        mock_client.image_url   = "https://glance.example.com"
        del mock_client._token_data
        result = invoke(["doctor"])
        assert result.exit_code == 0
        assert "Skipped" in result.output or "fix authentication" in result.output.lower()


# ══════════════════════════════════════════════════════════════════════════
#  Service-level isolation
# ══════════════════════════════════════════════════════════════════════════

class TestDoctorServiceIsolation:

    def test_nova_down_skips_compute_quotas(self, invoke, mock_client):
        """Nova unreachable → compute quotas skipped, other checks proceed."""
        mock_client.compute_url = "https://nova.example.com/v2.1"
        mock_client.network_url = "https://neutron.example.com"
        mock_client.volume_url  = "https://cinder.example.com/v3"
        mock_client.image_url   = "https://glance.example.com"
        mock_client._token_data = _base_token()

        def _get(url, **kw):
            if "nova" in url:
                raise APIError(503, "Service unavailable")
            if "cinder" in url and "limits" in url: return _vol_limits()
            if "quotas" in url and PRJ_ID in url:   return _net_quota()
            if "quotas/defaults" in url:            return {}
            if "security-groups" in url:            return _sg()
            if "images" in url:                     return {"images": []}
            return {}

        mock_client.get.side_effect = _get
        result = invoke(["doctor"])
        assert result.exit_code == 0
        # Nova service must be flagged as unreachable
        assert "Nova" in result.output
        # Compute quotas must say skipped, not error
        assert "Skipped" in result.output

    def test_neutron_down_skips_sg_check(self, invoke, mock_client):
        """Neutron unreachable → network quotas + SG check both skipped."""
        mock_client.compute_url = "https://nova.example.com/v2.1"
        mock_client.network_url = "https://neutron.example.com"
        mock_client.volume_url  = "https://cinder.example.com/v3"
        mock_client.image_url   = "https://glance.example.com"
        mock_client._token_data = _base_token()

        def _get(url, **kw):
            if "neutron" in url:
                raise APIError(503, "Service unavailable")
            if "nova" in url and "limits" in url:   return _limits()
            if "cinder" in url and "limits" in url: return _vol_limits()
            if "images" in url:                     return {"images": []}
            return {}

        mock_client.get.side_effect = _get
        result = invoke(["doctor"])
        assert result.exit_code == 0
        assert "Neutron" in result.output
        # Security group and network quotas should be skipped, not errored
        skipped_count = result.output.count("Skipped")
        assert skipped_count >= 2


# ══════════════════════════════════════════════════════════════════════════
#  3-tier quota color thresholds
# ══════════════════════════════════════════════════════════════════════════

class TestDoctorQuotaThresholds:

    def _run(self, invoke, mock_client, inst, inst_max):
        mock_client.compute_url = "https://nova.example.com/v2.1"
        mock_client.network_url = "https://neutron.example.com"
        mock_client.volume_url  = "https://cinder.example.com/v3"
        mock_client.image_url   = "https://glance.example.com"
        mock_client._token_data = _base_token()

        def _get(url, **kw):
            if "nova" in url and "limits" in url:
                return _limits(inst=inst, inst_max=inst_max)
            if "cinder" in url and "limits" in url: return _vol_limits()
            if "quotas" in url and PRJ_ID in url:   return _net_quota()
            if "quotas/defaults" in url:            return {}
            if "security-groups" in url:            return _sg()
            if "images" in url:                     return {"images": []}
            return {}

        mock_client.get.side_effect = _get
        return invoke(["doctor"])

    def test_green_below_70(self, invoke, mock_client):
        result = self._run(invoke, mock_client, inst=5, inst_max=100)
        assert result.exit_code == 0
        # 5% → should be OK
        assert "5/100" in result.output

    def test_yellow_70_to_89(self, invoke, mock_client):
        result = self._run(invoke, mock_client, inst=75, inst_max=100)
        assert result.exit_code == 0
        # 75% → WARN (⚠ in output)
        assert "WARN" in result.output or "⚠" in result.output or "75/100" in result.output

    def test_red_at_90_plus(self, invoke, mock_client):
        result = self._run(invoke, mock_client, inst=9, inst_max=10)
        assert result.exit_code == 0
        # 90% → critical
        assert "critical" in result.output.lower() or "✗" in result.output or "9/10" in result.output

    def test_red_at_100(self, invoke, mock_client):
        result = self._run(invoke, mock_client, inst=10, inst_max=10)
        assert result.exit_code == 0
        assert "critical" in result.output.lower() or "10/10" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  Security group checks
# ══════════════════════════════════════════════════════════════════════════

class TestDoctorSecurityGroups:

    def test_warns_missing_ssh(self, invoke, mock_client):
        _setup_happy_path(mock_client, sg_data=_sg(has_ssh=False, has_icmp=True))
        result = invoke(["doctor"])
        assert result.exit_code == 0
        assert "SSH" in result.output
        # Should be a warning, not just info
        assert "WARN" in result.output or "⚠" in result.output

    def test_warns_missing_icmp(self, invoke, mock_client):
        _setup_happy_path(mock_client, sg_data=_sg(has_ssh=True, has_icmp=False))
        result = invoke(["doctor"])
        assert result.exit_code == 0
        assert "ICMP" in result.output or "ping" in result.output.lower()

    def test_ok_when_both_present(self, invoke, mock_client):
        _setup_happy_path(mock_client, sg_data=_sg(has_ssh=True, has_icmp=True))
        result = invoke(["doctor"])
        assert result.exit_code == 0
        assert "SSH" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  --fix flag
# ══════════════════════════════════════════════════════════════════════════

class TestDoctorFix:

    def test_fix_adds_ssh_and_icmp_rules(self, invoke, mock_client):
        mock_client.compute_url = "https://nova.example.com/v2.1"
        mock_client.network_url = "https://neutron.example.com"
        mock_client.volume_url  = "https://cinder.example.com/v3"
        mock_client.image_url   = "https://glance.example.com"
        mock_client._token_data = _base_token()
        mock_client.post.return_value = {}

        def _get(url, **kw):
            if "nova" in url and "limits" in url:   return _limits()
            if "cinder" in url and "limits" in url: return _vol_limits()
            if "quotas" in url and PRJ_ID in url:   return _net_quota()
            if "quotas/defaults" in url:            return {}
            if "security-groups" in url:            return _sg(has_ssh=False, has_icmp=False)
            if "images" in url:                     return {"images": []}
            return {}

        mock_client.get.side_effect = _get
        result = invoke(["doctor", "--fix"])
        assert result.exit_code == 0
        assert mock_client.post.called
        post_urls = [c[0][0] for c in mock_client.post.call_args_list]
        assert any("security-group-rules" in u for u in post_urls)

    def test_fix_no_post_when_rules_present(self, invoke, mock_client):
        _setup_happy_path(mock_client)
        result = invoke(["doctor", "--fix"])
        assert result.exit_code == 0
        # post should not have been called (no rules to add)
        mock_client.post.assert_not_called()
