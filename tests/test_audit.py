"""Tests for ``orca audit`` command."""

from __future__ import annotations

from orca_cli.core.config import save_profile, set_active_profile

# ── Helpers ────────────────────────────────────────────────────────────────

def _make_sg(name, sg_id, rules=None):
    return {
        "id": sg_id,
        "name": name,
        "security_group_rules": rules or [],
    }


def _ingress_rule(port_min=None, port_max=None, protocol="tcp",
                  remote="0.0.0.0/0", ethertype="IPv4"):
    rule = {
        "direction": "ingress",
        "ethertype": ethertype,
        "protocol": protocol,
        "remote_ip_prefix": remote,
        "port_range_min": port_min,
        "port_range_max": port_max,
    }
    return rule


def _egress_rule():
    return {"direction": "egress", "ethertype": "IPv4", "protocol": None,
            "remote_ip_prefix": None, "port_range_min": None, "port_range_max": None}


def _server(name, srv_id, key_name="my-key", status="ACTIVE", floating=False):
    addrs = {"private": [{"addr": "10.0.0.5", "OS-EXT-IPS:type": "fixed"}]}
    if floating:
        addrs["private"].append({"addr": "203.0.113.1", "OS-EXT-IPS:type": "floating"})
    return {
        "id": srv_id,
        "name": name,
        "key_name": key_name,
        "status": status,
        "addresses": addrs,
    }


def _volume(vol_id, encrypted=False):
    return {"id": vol_id, "encrypted": encrypted}


def _fip(fip_id, port_id=None):
    return {"id": fip_id, "floating_ip_address": "203.0.113.1", "port_id": port_id}


def _setup_mock(mock_client, sgs=None, servers=None, volumes=None, fips=None):
    """Configure mock_client.get to return appropriate data per URL."""
    sgs = sgs or []
    servers = servers or []
    volumes = volumes or []
    fips = fips or []

    def _get(url, **kwargs):
        if "security-groups" in url:
            return {"security_groups": sgs}
        if "servers/detail" in url:
            return {"servers": servers}
        if "volumes/detail" in url:
            return {"volumes": volumes}
        if "floatingips" in url:
            return {"floatingips": fips}
        return {}

    mock_client.get = _get
    mock_client.compute_url = "https://nova.example.com/v2.1"
    mock_client.network_url = "https://neutron.example.com"
    mock_client.volume_url = "https://cinder.example.com/v3"


# ── Tests ──────────────────────────────────────────────────────────────────


class TestAuditClean:
    """No findings at all."""

    def test_clean_project(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        _setup_mock(
            mock_client,
            sgs=[_make_sg("default", "sg-1", [_egress_rule()])],
            servers=[_server("web", "srv-1")],
            volumes=[_volume("vol-1", encrypted=True)],
            fips=[_fip("fip-1", port_id="port-1")],
        )

        result = invoke(["audit"])
        assert result.exit_code == 0
        assert "No security issues found" in result.output


class TestAuditSecurityGroups:

    def test_all_ports_open(self, invoke, config_dir, mock_client, sample_profile):
        """All ports open to 0.0.0.0/0 → CRITICAL."""
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        rule = _ingress_rule(port_min=None, port_max=None, protocol="tcp")
        _setup_mock(mock_client, sgs=[_make_sg("wide-open", "sg-1", [rule])])

        result = invoke(["audit"])
        assert result.exit_code == 0
        assert "CRITICAL" in result.output
        assert "All tcp ports open" in result.output

    def test_dangerous_port_ssh(self, invoke, config_dir, mock_client, sample_profile):
        """SSH (22) open to 0.0.0.0/0 → HIGH."""
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        rule = _ingress_rule(port_min=22, port_max=22, protocol="tcp")
        _setup_mock(mock_client, sgs=[_make_sg("ssh-open", "sg-1", [rule])])

        result = invoke(["audit"])
        assert result.exit_code == 0
        assert "HIGH" in result.output
        assert "22" in result.output
        assert "SSH" in result.output

    def test_dangerous_port_rdp(self, invoke, config_dir, mock_client, sample_profile):
        """RDP (3389) open to 0.0.0.0/0 → HIGH."""
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        rule = _ingress_rule(port_min=3389, port_max=3389, protocol="tcp")
        _setup_mock(mock_client, sgs=[_make_sg("rdp-open", "sg-1", [rule])])

        result = invoke(["audit"])
        assert result.exit_code == 0
        assert "HIGH" in result.output
        assert "3389" in result.output
        assert "RDP" in result.output

    def test_dangerous_port_in_range(self, invoke, config_dir, mock_client, sample_profile):
        """Port range 1-1000 includes multiple dangerous ports."""
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        rule = _ingress_rule(port_min=1, port_max=1000, protocol="tcp")
        _setup_mock(mock_client, sgs=[_make_sg("big-range", "sg-1", [rule])])

        result = invoke(["audit"])
        assert result.exit_code == 0
        assert "HIGH" in result.output
        assert "22" in result.output  # SSH in range
        assert "MEDIUM" in result.output  # Wide range finding

    def test_wide_port_range(self, invoke, config_dir, mock_client, sample_profile):
        """Port range > 100 → MEDIUM."""
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        rule = _ingress_rule(port_min=8000, port_max=9000, protocol="tcp")
        _setup_mock(mock_client, sgs=[_make_sg("wide", "sg-1", [rule])])

        result = invoke(["audit"])
        assert result.exit_code == 0
        assert "MEDIUM" in result.output
        assert "8000-9000" in result.output

    def test_safe_rule_ignored(self, invoke, config_dir, mock_client, sample_profile):
        """Restricted CIDR (not 0.0.0.0/0) → no finding."""
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        rule = _ingress_rule(port_min=22, port_max=22, protocol="tcp", remote="10.0.0.0/8")
        _setup_mock(mock_client, sgs=[_make_sg("restricted", "sg-1", [rule])])

        result = invoke(["audit"])
        assert result.exit_code == 0
        assert "No security issues found" in result.output

    def test_egress_ignored(self, invoke, config_dir, mock_client, sample_profile):
        """Egress rules are not checked."""
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        _setup_mock(mock_client, sgs=[_make_sg("default", "sg-1", [_egress_rule()])])

        result = invoke(["audit"])
        assert result.exit_code == 0
        assert "No security issues found" in result.output

    def test_ipv6_open(self, invoke, config_dir, mock_client, sample_profile):
        """All ports open to ::/0 → CRITICAL."""
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        rule = _ingress_rule(port_min=None, port_max=None, protocol="tcp",
                             remote="::/0", ethertype="IPv6")
        _setup_mock(mock_client, sgs=[_make_sg("ipv6-open", "sg-1", [rule])])

        result = invoke(["audit"])
        assert result.exit_code == 0
        assert "CRITICAL" in result.output

    def test_multiple_dangerous_ports(self, invoke, config_dir, mock_client, sample_profile):
        """Multiple dangerous port rules → multiple HIGH findings."""
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        rules = [
            _ingress_rule(port_min=22, port_max=22, protocol="tcp"),
            _ingress_rule(port_min=3306, port_max=3306, protocol="tcp"),
            _ingress_rule(port_min=6379, port_max=6379, protocol="tcp"),
        ]
        _setup_mock(mock_client, sgs=[_make_sg("multi", "sg-1", rules)])

        result = invoke(["audit"])
        assert result.exit_code == 0
        assert result.output.count("HIGH") >= 3
        assert "SSH" in result.output
        assert "MySQL" in result.output
        assert "Redis" in result.output


class TestAuditServers:

    def test_no_keypair(self, invoke, config_dir, mock_client, sample_profile):
        """Server without SSH key → MEDIUM."""
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        _setup_mock(mock_client, servers=[_server("nokey", "srv-1", key_name=None)])

        result = invoke(["audit"])
        assert result.exit_code == 0
        assert "MEDIUM" in result.output
        assert "No SSH key pair" in result.output

    def test_server_error_state(self, invoke, config_dir, mock_client, sample_profile):
        """Server in ERROR → LOW."""
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        _setup_mock(mock_client, servers=[_server("broken", "srv-1", status="ERROR")])

        result = invoke(["audit"])
        assert result.exit_code == 0
        assert "LOW" in result.output
        assert "ERROR state" in result.output

    def test_floating_ip_no_key(self, invoke, config_dir, mock_client, sample_profile):
        """Publicly exposed server without key → HIGH."""
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        _setup_mock(mock_client, servers=[
            _server("exposed", "srv-1", key_name=None, floating=True),
        ])

        result = invoke(["audit"])
        assert result.exit_code == 0
        assert "HIGH" in result.output
        assert "Publicly reachable" in result.output

    def test_server_with_key_ok(self, invoke, config_dir, mock_client, sample_profile):
        """Server with key pair and no floating IP → no finding."""
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        _setup_mock(mock_client, servers=[_server("good", "srv-1", key_name="mykey")])

        result = invoke(["audit"])
        assert result.exit_code == 0
        assert "No security issues found" in result.output


class TestAuditVolumes:

    def test_unencrypted_volumes(self, invoke, config_dir, mock_client, sample_profile):
        """Unencrypted volumes → LOW."""
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        _setup_mock(mock_client, volumes=[
            _volume("vol-1", encrypted=False),
            _volume("vol-2", encrypted=False),
            _volume("vol-3", encrypted=True),
        ])

        result = invoke(["audit"])
        assert result.exit_code == 0
        assert "LOW" in result.output
        assert "2 unencrypted volume" in result.output

    def test_all_encrypted_ok(self, invoke, config_dir, mock_client, sample_profile):
        """All volumes encrypted → no finding."""
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        _setup_mock(mock_client, volumes=[
            _volume("vol-1", encrypted=True),
            _volume("vol-2", encrypted=True),
        ])

        result = invoke(["audit"])
        assert result.exit_code == 0
        assert "No security issues found" in result.output


class TestAuditFloatingIPs:

    def test_unused_fips(self, invoke, config_dir, mock_client, sample_profile):
        """Unassociated floating IPs → LOW."""
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        _setup_mock(mock_client, fips=[
            _fip("fip-1", port_id=None),
            _fip("fip-2", port_id=None),
            _fip("fip-3", port_id="port-1"),
        ])

        result = invoke(["audit"])
        assert result.exit_code == 0
        assert "LOW" in result.output
        assert "Unassociated floating IPs" in result.output

    def test_all_fips_associated_ok(self, invoke, config_dir, mock_client, sample_profile):
        """All floating IPs associated → no finding."""
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        _setup_mock(mock_client, fips=[_fip("fip-1", port_id="port-1")])

        result = invoke(["audit"])
        assert result.exit_code == 0
        assert "No security issues found" in result.output


class TestAuditSeveritySorting:

    def test_findings_sorted_by_severity(self, invoke, config_dir, mock_client, sample_profile):
        """CRITICAL should appear before HIGH before MEDIUM before LOW."""
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        _setup_mock(
            mock_client,
            sgs=[_make_sg("open", "sg-1", [
                _ingress_rule(port_min=None, port_max=None, protocol="tcp"),  # CRITICAL
                _ingress_rule(port_min=22, port_max=22, protocol="tcp"),      # HIGH
            ])],
            servers=[_server("nokey", "srv-1", key_name=None)],              # MEDIUM
            volumes=[_volume("vol-1", encrypted=False)],                     # LOW
        )

        result = invoke(["audit"])
        assert result.exit_code == 0
        output = result.output
        crit_pos = output.index("CRITICAL")
        high_pos = output.index("HIGH")
        medium_pos = output.index("MEDIUM")
        low_pos = output.index("LOW")
        assert crit_pos < high_pos < medium_pos < low_pos


class TestAuditCombined:

    def test_mixed_findings(self, invoke, config_dir, mock_client, sample_profile):
        """Multiple issues across categories."""
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        _setup_mock(
            mock_client,
            sgs=[_make_sg("web", "sg-1", [
                _ingress_rule(port_min=22, port_max=22, protocol="tcp"),
            ])],
            servers=[
                _server("good", "srv-1"),
                _server("bad", "srv-2", key_name=None, status="ERROR"),
            ],
            volumes=[_volume("vol-1"), _volume("vol-2", encrypted=True)],
            fips=[_fip("fip-1"), _fip("fip-2", port_id="port-1")],
        )

        result = invoke(["audit"])
        assert result.exit_code == 0
        # Should have findings from SG, server, volume, and FIP
        assert "SSH" in result.output
        assert "No SSH key pair" in result.output
        assert "ERROR state" in result.output
        assert "unencrypted" in result.output
        assert "Unassociated" in result.output
        # Summary line with count
        assert "finding" in result.output


class TestAuditHelp:

    def test_help(self, invoke):
        result = invoke(["audit", "--help"])
        assert result.exit_code == 0
        assert "security audit" in result.output.lower()
