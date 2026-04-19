"""Tests for ``orca find`` — universal resource search."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from orca_cli.commands import find as find_mod
from orca_cli.core.config import save_profile, set_active_profile

# ══════════════════════════════════════════════════════════════════════════
#  Unit tests — per-resource searchers
# ══════════════════════════════════════════════════════════════════════════


def _client(**urls):
    c = MagicMock()
    c.compute_url = urls.get("compute", "https://nova")
    c.network_url = urls.get("network", "https://neutron")
    c.volume_url = urls.get("volume", "https://cinder")
    c.image_url = urls.get("image", "https://glance")
    return c


class TestSafeList:

    def test_returns_list_from_key(self):
        c = _client()
        c.get.return_value = {"items": [{"id": "1"}]}
        assert find_mod._safe_list(c, "http://x", "items") == [{"id": "1"}]

    def test_swallows_exception(self):
        c = _client()
        c.get.side_effect = RuntimeError("api down")
        assert find_mod._safe_list(c, "http://x", "items") == []

    def test_missing_key_returns_empty(self):
        c = _client()
        c.get.return_value = {"other": []}
        assert find_mod._safe_list(c, "http://x", "items") == []

    def test_none_value_coerced_to_empty(self):
        c = _client()
        c.get.return_value = {"items": None}
        assert find_mod._safe_list(c, "http://x", "items") == []


class TestFindServers:

    def test_match_on_name(self):
        c = _client()
        c.get.return_value = {"servers": [{"id": "s1", "name": "web-prod"}]}
        hits = find_mod._find_servers(c, "web")
        assert len(hits) == 1
        assert hits[0][1] == "name"

    def test_match_on_id_substring(self):
        c = _client()
        c.get.return_value = {"servers": [{"id": "abc12345", "name": "x"}]}
        hits = find_mod._find_servers(c, "bc123")
        assert len(hits) == 1
        assert hits[0][1] == "id"

    def test_match_on_ip(self):
        c = _client()
        c.get.return_value = {"servers": [{
            "id": "s1", "name": "web",
            "addresses": {"net": [{"addr": "203.0.113.10"}]},
        }]}
        hits = find_mod._find_servers(c, "203.0.113")
        assert len(hits) == 1
        assert "ip=203.0.113.10" in hits[0][1]

    def test_no_match(self):
        c = _client()
        c.get.return_value = {"servers": [{"id": "s1", "name": "db"}]}
        assert find_mod._find_servers(c, "web") == []


class TestFindPorts:

    def test_match_on_fixed_ip(self):
        c = _client()
        c.get.return_value = {"ports": [{
            "id": "p1", "name": "", "status": "ACTIVE",
            "fixed_ips": [{"ip_address": "10.0.0.5"}],
        }]}
        hits = find_mod._find_ports(c, "10.0.0.5")
        assert len(hits) == 1
        assert "ip=10.0.0.5" in hits[0][1]

    def test_match_on_mac(self):
        c = _client()
        c.get.return_value = {"ports": [{
            "id": "p1", "name": "", "mac_address": "fa:16:3e:00:00:01",
        }]}
        hits = find_mod._find_ports(c, "fa:16:3e:00:00:01")
        assert len(hits) == 1
        assert "mac=" in hits[0][1]

    def test_match_on_device_id(self):
        c = _client()
        c.get.return_value = {"ports": [{
            "id": "p1", "device_id": "srv-aaaa1111",
        }]}
        hits = find_mod._find_ports(c, "srv-aaaa")
        assert len(hits) == 1
        assert "device_id=" in hits[0][1]


class TestFindFloatingIps:

    def test_match_on_floating_address(self):
        c = _client()
        c.get.return_value = {"floatingips": [{
            "id": "f1", "floating_ip_address": "203.0.113.5",
        }]}
        hits = find_mod._find_floatingips(c, "203.0.113.5")
        assert "floating=" in hits[0][1]

    def test_match_on_fixed_address(self):
        c = _client()
        c.get.return_value = {"floatingips": [{
            "id": "f1",
            "floating_ip_address": "203.0.113.5",
            "fixed_ip_address": "10.0.0.42",
        }]}
        hits = find_mod._find_floatingips(c, "10.0.0.42")
        assert "fixed=10.0.0.42" in hits[0][1]


class TestFindSubnets:

    def test_match_on_cidr(self):
        c = _client()
        c.get.return_value = {"subnets": [
            {"id": "sub1", "name": "priv", "cidr": "10.0.0.0/24"},
        ]}
        hits = find_mod._find_subnets(c, "10.0.0.0/24")
        assert "cidr=10.0.0.0/24" in hits[0][1]


class TestFindKeypairs:

    def test_match_on_fingerprint(self):
        c = _client()
        c.get.return_value = {"keypairs": [
            {"keypair": {"name": "my-key",
                         "fingerprint": "aa:bb:cc:dd:ee:ff:00:11:22:33:44:55"}},
        ]}
        hits = find_mod._find_keypairs(c, "aa:bb:cc")
        assert "fingerprint=" in hits[0][1]

    def test_match_on_name(self):
        c = _client()
        c.get.return_value = {"keypairs": [
            {"keypair": {"name": "admin-key", "fingerprint": "xxx"}},
        ]}
        hits = find_mod._find_keypairs(c, "admin")
        assert hits[0][1] == "name"


class TestFindRouters:

    def test_match_on_external_gateway_ip(self):
        c = _client()
        c.get.return_value = {"routers": [{
            "id": "r1", "name": "edge",
            "external_gateway_info": {
                "external_fixed_ips": [{"ip_address": "203.0.113.1"}]
            },
        }]}
        hits = find_mod._find_routers(c, "203.0.113.1")
        assert "gw=" in hits[0][1]


class TestFindVolumesImagesNetworksSgs:
    """Plain name/id matches for the simpler resource types."""

    def test_volumes(self):
        c = _client()
        c.get.return_value = {"volumes": [{"id": "v1", "name": "db-disk"}]}
        assert find_mod._find_volumes(c, "db")[0][1] == "name"

    def test_images(self):
        c = _client()
        c.get.return_value = {"images": [{"id": "i1", "name": "ubuntu-24.04"}]}
        assert find_mod._find_images(c, "ubuntu")[0][1] == "name"

    def test_networks(self):
        c = _client()
        c.get.return_value = {"networks": [{"id": "n1", "name": "private"}]}
        assert find_mod._find_networks(c, "priv")[0][1] == "name"

    def test_security_groups(self):
        c = _client()
        c.get.return_value = {"security_groups": [{"id": "sg1", "name": "default"}]}
        assert find_mod._find_security_groups(c, "default")[0][1] == "name"


# ══════════════════════════════════════════════════════════════════════════
#  Extra column
# ══════════════════════════════════════════════════════════════════════════


class TestExtraColumn:

    def test_server_extra(self):
        assert find_mod._extra("servers", {"status": "ACTIVE"}) == "ACTIVE"

    def test_port_extra_attached(self):
        out = find_mod._extra("ports", {"status": "ACTIVE", "device_id": "srv-1"})
        assert "attached" in out

    def test_port_extra_free(self):
        assert find_mod._extra("ports", {"status": "DOWN", "device_id": ""}) == "DOWN"

    def test_volume_extra(self):
        out = find_mod._extra("volumes", {"size": 50, "status": "in-use"})
        assert "50GB" in out and "in-use" in out

    def test_network_shared(self):
        assert find_mod._extra("networks", {"shared": True, "status": "ACTIVE"}) == "shared"

    def test_network_not_shared(self):
        assert find_mod._extra("networks", {"shared": False, "status": "ACTIVE"}) == "ACTIVE"

    def test_subnet_cidr(self):
        assert find_mod._extra("subnets", {"cidr": "10.0.0.0/24"}) == "10.0.0.0/24"

    def test_keypair_type(self):
        assert find_mod._extra("keypairs", {"type": "ssh"}) == "ssh"

    def test_unknown_type(self):
        assert find_mod._extra("unknown", {}) == ""


# ══════════════════════════════════════════════════════════════════════════
#  Integration — orca find
# ══════════════════════════════════════════════════════════════════════════


def _setup_profile(mock_client, sample_profile):
    save_profile("test", sample_profile)
    set_active_profile("test")
    mock_client.compute_url = "https://nova.example.com/v2.1"
    mock_client.network_url = "https://neutron.example.com"
    mock_client.volume_url = "https://cinder.example.com/v3"
    mock_client.image_url = "https://glance.example.com"


def _url_dispatcher(responses: dict):
    """Return a side_effect fn mapping URL substring → payload."""
    def _get(url, **kw):
        for substr, payload in responses.items():
            if substr in url:
                return payload
        return {}
    return _get


class TestFindHelp:

    def test_help(self, invoke):
        result = invoke(["find", "--help"])
        assert result.exit_code == 0
        assert "Universal search" in result.output


class TestFindIntegration:

    def test_ip_lookup_hits_server_and_port(
        self, invoke, mock_client, config_dir, sample_profile
    ):
        _setup_profile(mock_client, sample_profile)
        mock_client.get.side_effect = _url_dispatcher({
            "servers/detail": {"servers": [{
                "id": "srv-aaaa1111", "name": "web", "status": "ACTIVE",
                "addresses": {"n": [{"addr": "10.0.0.5"}]},
            }]},
            "v2.0/ports": {"ports": [{
                "id": "port-1", "name": "", "status": "ACTIVE",
                "fixed_ips": [{"ip_address": "10.0.0.5"}],
            }]},
            "v2.0/floatingips": {"floatingips": []},
            "v2.0/networks": {"networks": []},
            "v2.0/subnets": {"subnets": []},
            "v2.0/security-groups": {"security_groups": []},
            "v2.0/routers": {"routers": []},
            "volumes/detail": {"volumes": []},
            "v2/images": {"images": []},
            "os-keypairs": {"keypairs": []},
        })

        result = invoke(["find", "10.0.0.5"])
        assert result.exit_code == 0, result.output
        assert "Servers" in result.output
        assert "Ports" in result.output
        assert "10.0.0.5" in result.output
        assert "2 match" in result.output

    def test_no_match_shows_yellow_message(
        self, invoke, mock_client, config_dir, sample_profile
    ):
        _setup_profile(mock_client, sample_profile)
        mock_client.get.return_value = {}  # every key missing → every searcher returns []

        result = invoke(["find", "nonexistent"])
        assert result.exit_code == 0
        assert "No matches" in result.output

    def test_type_filter_restricts_searchers(
        self, invoke, mock_client, config_dir, sample_profile
    ):
        _setup_profile(mock_client, sample_profile)
        mock_client.get.side_effect = _url_dispatcher({
            "servers/detail": {"servers": [
                {"id": "s1", "name": "web", "status": "ACTIVE"}
            ]},
        })

        result = invoke(["find", "web", "-t", "servers"])
        assert result.exit_code == 0
        # Only servers fetched, never volumes/ports/etc.
        calls = [c.args[0] for c in mock_client.get.call_args_list]
        assert any("servers/detail" in u for u in calls)
        assert not any("volumes" in u for u in calls)
        assert not any("ports" in u for u in calls)

    def test_exception_in_one_searcher_does_not_break_others(
        self, invoke, mock_client, config_dir, sample_profile
    ):
        """If Neutron is down but Nova works, we still get server matches."""
        _setup_profile(mock_client, sample_profile)

        def _get(url, **kw):
            if "neutron" in url or "v2.0/" in url:
                raise RuntimeError("neutron down")
            if "servers/detail" in url:
                return {"servers": [
                    {"id": "s1", "name": "web", "status": "ACTIVE"}
                ]}
            return {}
        mock_client.get.side_effect = _get

        result = invoke(["find", "web"])
        assert result.exit_code == 0
        assert "Servers" in result.output

    @pytest.mark.parametrize("bad_type", ["foo", "server", "vms"])
    def test_invalid_type_rejected(
        self, invoke, mock_client, config_dir, sample_profile, bad_type
    ):
        _setup_profile(mock_client, sample_profile)
        result = invoke(["find", "x", "-t", bad_type])
        assert result.exit_code != 0
