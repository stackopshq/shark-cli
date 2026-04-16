"""Tests for ``orca ip`` commands."""

from __future__ import annotations

from orca_cli.core.config import save_profile, set_active_profile


# ── Helpers ────────────────────────────────────────────────────────────────

TARGET_IP = "10.0.0.15"
FIP_IP = "203.0.113.42"


def _setup_mock(mock_client, fips=None, ports=None, servers=None,
                routers=None, subnets=None, lbs=None):
    fips = fips or []
    ports = ports or []
    servers = servers or []
    routers = routers or []
    subnets = subnets or []
    lbs = lbs or []

    mock_client.compute_url = "https://nova.example.com/v2.1"
    mock_client.network_url = "https://neutron.example.com"
    mock_client.load_balancer_url = "https://octavia.example.com"

    def _get(url, **kwargs):
        if "/floatingips" in url:
            return {"floatingips": fips}
        if "/ports" in url:
            return {"ports": ports}
        if "servers/detail" in url:
            return {"servers": servers}
        if "/routers" in url:
            return {"routers": routers}
        if "/subnets" in url:
            return {"subnets": subnets}
        if "/lbaas/loadbalancers" in url:
            return {"loadbalancers": lbs}
        return {}

    mock_client.get = _get


# ══════════════════════════════════════════════════════════════════════════
#  ip whois
# ══════════════════════════════════════════════════════════════════════════


class TestIpWhois:

    def test_find_floating_ip(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client, fips=[{
            "id": "fip-1", "floating_ip_address": FIP_IP,
            "fixed_ip_address": "10.0.0.5", "port_id": "port-1", "status": "ACTIVE",
        }])

        result = invoke(["ip", "whois", FIP_IP])
        assert result.exit_code == 0
        assert "floating-ip" in result.output
        assert "fip-1" in result.output

    def test_find_fixed_side_of_fip(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client, fips=[{
            "id": "fip-1", "floating_ip_address": FIP_IP,
            "fixed_ip_address": TARGET_IP, "port_id": "port-1", "status": "ACTIVE",
        }])

        result = invoke(["ip", "whois", TARGET_IP])
        assert result.exit_code == 0
        assert "fixed side" in result.output

    def test_find_port(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client, ports=[{
            "id": "port-1", "device_owner": "compute:nova", "device_id": "srv-1",
            "mac_address": "fa:16:3e:aa:bb:cc", "network_id": "net-1",
            "fixed_ips": [{"ip_address": TARGET_IP, "subnet_id": "sub-1"}],
        }])

        result = invoke(["ip", "whois", TARGET_IP])
        assert result.exit_code == 0
        assert "port" in result.output
        assert "port-1" in result.output

    def test_find_server(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client, servers=[{
            "id": "srv-1", "name": "web-1", "status": "ACTIVE",
            "addresses": {"private": [{"addr": TARGET_IP, "OS-EXT-IPS:type": "fixed"}]},
        }])

        result = invoke(["ip", "whois", TARGET_IP])
        assert result.exit_code == 0
        assert "server" in result.output
        assert "web-1" in result.output

    def test_find_router_gateway(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client, routers=[{
            "id": "rtr-1", "name": "main-rtr",
            "external_gateway_info": {
                "external_fixed_ips": [{"ip_address": FIP_IP, "subnet_id": "sub-ext"}],
            },
        }])

        result = invoke(["ip", "whois", FIP_IP])
        assert result.exit_code == 0
        assert "router" in result.output
        assert "main-rtr" in result.output

    def test_find_subnet_gateway(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client, subnets=[{
            "id": "sub-1", "name": "private-sub", "cidr": "10.0.0.0/24",
            "gateway_ip": TARGET_IP, "network_id": "net-1", "allocation_pools": [],
        }])

        result = invoke(["ip", "whois", TARGET_IP])
        assert result.exit_code == 0
        assert "subnet" in result.output
        assert "gateway" in result.output

    def test_find_subnet_pool(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client, subnets=[{
            "id": "sub-1", "name": "private-sub", "cidr": "10.0.0.0/24",
            "gateway_ip": "10.0.0.1", "network_id": "net-1",
            "allocation_pools": [{"start": "10.0.0.10", "end": "10.0.0.200"}],
        }])

        result = invoke(["ip", "whois", TARGET_IP])
        assert result.exit_code == 0
        assert "pool" in result.output

    def test_find_loadbalancer(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client, lbs=[{
            "id": "lb-1", "name": "my-lb",
            "vip_address": TARGET_IP, "provisioning_status": "ACTIVE",
        }])

        result = invoke(["ip", "whois", TARGET_IP])
        assert result.exit_code == 0
        assert "load-balancer" in result.output

    def test_no_results(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["ip", "whois", "192.168.99.99"])
        assert result.exit_code == 0
        assert "No resource found" in result.output

    def test_multiple_results(self, invoke, config_dir, mock_client, sample_profile):
        """An IP can appear in both a port and a server."""
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client,
                    ports=[{
                        "id": "port-1", "device_owner": "compute:nova", "device_id": "srv-1",
                        "mac_address": "fa:16:3e:aa:bb:cc", "network_id": "net-1",
                        "fixed_ips": [{"ip_address": TARGET_IP}],
                    }],
                    servers=[{
                        "id": "srv-1", "name": "web-1", "status": "ACTIVE",
                        "addresses": {"private": [{"addr": TARGET_IP, "OS-EXT-IPS:type": "fixed"}]},
                    }])

        result = invoke(["ip", "whois", TARGET_IP])
        assert result.exit_code == 0
        assert "port" in result.output
        assert "server" in result.output

    def test_lb_failure_ignored(self, invoke, config_dir, mock_client, sample_profile):
        """If LB service is unavailable, whois still works."""
        save_profile("p", sample_profile)
        set_active_profile("p")
        mock_client.compute_url = "https://nova.example.com/v2.1"
        mock_client.network_url = "https://neutron.example.com"
        mock_client.load_balancer_url = "https://octavia.example.com"

        def _get(url, **kwargs):
            if "/lbaas/" in url:
                raise Exception("service unavailable")
            if "/floatingips" in url:
                return {"floatingips": []}
            if "/ports" in url:
                return {"ports": []}
            if "servers/detail" in url:
                return {"servers": []}
            if "/routers" in url:
                return {"routers": []}
            if "/subnets" in url:
                return {"subnets": []}
            return {}

        mock_client.get = _get

        result = invoke(["ip", "whois", "1.2.3.4"])
        assert result.exit_code == 0
        assert "No resource found" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  _ip_in_range
# ══════════════════════════════════════════════════════════════════════════


class TestIpInRange:

    def test_ip_in_range(self):
        from orca_cli.commands.ip_whois import _ip_in_range
        assert _ip_in_range("10.0.0.50", "10.0.0.10", "10.0.0.200") is True

    def test_ip_at_start(self):
        from orca_cli.commands.ip_whois import _ip_in_range
        assert _ip_in_range("10.0.0.10", "10.0.0.10", "10.0.0.200") is True

    def test_ip_at_end(self):
        from orca_cli.commands.ip_whois import _ip_in_range
        assert _ip_in_range("10.0.0.200", "10.0.0.10", "10.0.0.200") is True

    def test_ip_outside_range(self):
        from orca_cli.commands.ip_whois import _ip_in_range
        assert _ip_in_range("10.0.0.5", "10.0.0.10", "10.0.0.200") is False

    def test_invalid_ip(self):
        from orca_cli.commands.ip_whois import _ip_in_range
        assert _ip_in_range("not-an-ip", "10.0.0.10", "10.0.0.200") is False


# ══════════════════════════════════════════════════════════════════════════
#  Help
# ══════════════════════════════════════════════════════════════════════════


class TestIpHelp:

    def test_ip_help(self, invoke):
        result = invoke(["ip", "--help"])
        assert result.exit_code == 0
        assert "whois" in result.output

    def test_ip_whois_help(self, invoke):
        result = invoke(["ip", "whois", "--help"])
        assert result.exit_code == 0
