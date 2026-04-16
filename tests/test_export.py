"""Tests for ``orca export`` command."""

from __future__ import annotations

import json

from orca_cli.core.config import save_profile, set_active_profile

# ── Helpers ────────────────────────────────────────────────────────────────

IMG_ID = "img-1111"
SRV_ID = "srv-2222"
VOL_ID = "vol-3333"
NET_ID = "net-4444"
SUB_ID = "sub-5555"
RTR_ID = "rtr-6666"
FIP_ID = "fip-7777"
SG_ID = "sg-8888"
PORT_ID = "port-9999"


def _server(srv_id=SRV_ID, name="web-1", status="ACTIVE", image_id=IMG_ID):
    return {
        "id": srv_id,
        "name": name,
        "status": status,
        "flavor": {"original_name": "m1.small", "id": "flv-1"},
        "image": {"id": image_id},
        "key_name": "mykey",
        "addresses": {
            "private-net": [
                {"addr": "10.0.0.5", "OS-EXT-IPS:type": "fixed", "OS-EXT-IPS:port_id": PORT_ID},
            ],
        },
        "security_groups": [{"name": "default"}],
        "os-extended-volumes:volumes_attached": [{"volumeId": VOL_ID, "device": "/dev/vda"}],
        "created": "2025-01-01T00:00:00Z",
    }


def _volume(vol_id=VOL_ID, name="boot-vol", status="in-use", attached_srv=SRV_ID):
    attachments = [{"server_id": attached_srv}] if attached_srv else []
    return {
        "id": vol_id,
        "name": name,
        "size": 50,
        "status": status,
        "volume_type": "ssd",
        "bootable": "true",
        "attachments": attachments,
    }


def _network(net_id=NET_ID, name="private-net", subnet_ids=None):
    return {
        "id": net_id,
        "name": name,
        "subnets": subnet_ids or [SUB_ID],
    }


def _subnet(sub_id=SUB_ID, name="private-sub", cidr="10.0.0.0/24"):
    return {
        "id": sub_id,
        "name": name,
        "cidr": cidr,
        "gateway_ip": "10.0.0.1",
        "dns_nameservers": ["8.8.8.8"],
        "allocation_pools": [{"start": "10.0.0.10", "end": "10.0.0.200"}],
    }


def _router(rtr_id=RTR_ID, name="main-router", ext_net_id=NET_ID):
    return {
        "id": rtr_id,
        "name": name,
        "external_gateway_info": {"network_id": ext_net_id},
    }


def _floating_ip(fip_id=FIP_ID, ip="203.0.113.10", port_id=PORT_ID):
    return {
        "id": fip_id,
        "floating_ip_address": ip,
        "status": "ACTIVE",
        "port_id": port_id,
    }


def _security_group(sg_id=SG_ID, name="default"):
    return {
        "id": sg_id,
        "name": name,
        "security_group_rules": [
            {
                "direction": "ingress",
                "protocol": "tcp",
                "port_range_min": 22,
                "port_range_max": 22,
                "remote_ip_prefix": "0.0.0.0/0",
            },
        ],
    }


def _image(img_id=IMG_ID, name="Ubuntu 22.04", size=2147483648):
    return {
        "id": img_id,
        "name": name,
        "status": "active",
        "size": size,
        "min_disk": 20,
        "min_ram": 512,
    }


def _keypair(name="mykey"):
    return {
        "keypair": {
            "name": name,
            "fingerprint": "aa:bb:cc:dd",
            "type": "ssh",
        }
    }


def _setup_full_mock(mock_client):
    """Wire up mock_client.get to return full infrastructure data."""
    mock_client.compute_url = "https://nova.example.com/v2.1"
    mock_client.network_url = "https://neutron.example.com"
    mock_client.volume_url = "https://cinder.example.com/v3"
    mock_client.image_url = "https://glance.example.com"

    def _get(url, **kwargs):
        # Images
        if "/v2/images" in url:
            return {"images": [_image()]}
        # Servers
        if "servers/detail" in url:
            return {"servers": [_server()]}
        # Volumes
        if "volumes/detail" in url:
            return {"volumes": [_volume()]}
        # Subnets
        if "/subnets" in url:
            return {"subnets": [_subnet()]}
        # Networks
        if "/networks" in url:
            return {"networks": [_network()]}
        # Router interface ports
        if "/ports" in url:
            params = kwargs.get("params", {})
            if params.get("device_owner") == "network:router_interface":
                return {"ports": [{
                    "device_id": RTR_ID,
                    "fixed_ips": [{"subnet_id": SUB_ID, "ip_address": "10.0.0.1"}],
                }]}
            return {"ports": [{"id": PORT_ID, "device_id": SRV_ID}]}
        # Routers
        if "/routers" in url:
            return {"routers": [_router()]}
        # Floating IPs
        if "/floatingips" in url:
            return {"floatingips": [_floating_ip()]}
        # Security groups
        if "/security-groups" in url:
            return {"security_groups": [_security_group()]}
        # Keypairs
        if "/os-keypairs" in url:
            return {"keypairs": [_keypair()]}
        return {}

    mock_client.get = _get


# ══════════════════════════════════════════════════════════════════════════
#  Default export (YAML, all resources)
# ══════════════════════════════════════════════════════════════════════════


class TestExportDefault:

    def test_yaml_output(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_full_mock(mock_client)

        result = invoke(["export"])
        assert result.exit_code == 0
        assert "# orca infrastructure export" in result.output
        assert "servers" in result.output
        assert "volumes" in result.output

    def test_contains_server(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_full_mock(mock_client)

        result = invoke(["export"])
        assert "web-1" in result.output
        assert "m1.small" in result.output

    def test_contains_volume(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_full_mock(mock_client)

        result = invoke(["export"])
        assert "boot-vol" in result.output
        assert "ssd" in result.output

    def test_contains_network(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_full_mock(mock_client)

        result = invoke(["export"])
        assert "private-net" in result.output
        assert "10.0.0.0/24" in result.output

    def test_contains_router(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_full_mock(mock_client)

        result = invoke(["export"])
        assert "main-router" in result.output

    def test_contains_floating_ip(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_full_mock(mock_client)

        result = invoke(["export"])
        assert "203.0.113.10" in result.output

    def test_contains_security_group(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_full_mock(mock_client)

        result = invoke(["export"])
        assert "default" in result.output

    def test_contains_keypair(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_full_mock(mock_client)

        result = invoke(["export"])
        assert "mykey" in result.output
        assert "aa:bb:cc:dd" in result.output

    def test_contains_image(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_full_mock(mock_client)

        result = invoke(["export"])
        assert "Ubuntu 22.04" in result.output

    def test_yaml_header_has_profile(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_full_mock(mock_client)

        result = invoke(["export"])
        assert "# Profile:" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  JSON format
# ══════════════════════════════════════════════════════════════════════════


class TestExportJSON:

    def test_json_output(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_full_mock(mock_client)

        result = invoke(["export", "-f", "json"])
        assert result.exit_code == 0
        # Should be valid JSON (strip Rich markup if any)
        # The JSON is printed via console.print, find the JSON block
        output = result.output
        # Find the JSON object in output
        start = output.index("{")
        end = output.rindex("}") + 1
        data = json.loads(output[start:end])
        assert "servers" in data
        assert "volumes" in data

    def test_json_no_yaml_header(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_full_mock(mock_client)

        result = invoke(["export", "-f", "json"])
        assert "# orca infrastructure export" not in result.output


# ══════════════════════════════════════════════════════════════════════════
#  Resource filtering (--resources)
# ══════════════════════════════════════════════════════════════════════════


class TestExportResourceFilter:

    def test_single_resource(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_full_mock(mock_client)

        result = invoke(["export", "-r", "servers"])
        assert result.exit_code == 0
        assert "web-1" in result.output

    def test_multiple_resources(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_full_mock(mock_client)

        result = invoke(["export", "-r", "servers,volumes"])
        assert result.exit_code == 0
        assert "web-1" in result.output
        assert "boot-vol" in result.output

    def test_invalid_resource_type(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_full_mock(mock_client)

        result = invoke(["export", "-r", "bogus"])
        assert result.exit_code != 0

    def test_only_keypairs(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_full_mock(mock_client)

        result = invoke(["export", "-r", "keypairs", "-f", "json"])
        assert result.exit_code == 0
        output = result.output
        start = output.index("{")
        end = output.rindex("}") + 1
        data = json.loads(output[start:end])
        assert "keypairs" in data
        # Other resource types should not appear
        assert "servers" not in data
        assert "volumes" not in data


# ══════════════════════════════════════════════════════════════════════════
#  Output to file (--output)
# ══════════════════════════════════════════════════════════════════════════


class TestExportFile:

    def test_output_to_file(self, invoke, config_dir, mock_client, sample_profile, tmp_path):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_full_mock(mock_client)

        out_file = tmp_path / "infra.yaml"
        result = invoke(["export", "-o", str(out_file)])
        assert result.exit_code == 0
        assert out_file.exists()
        content = out_file.read_text()
        assert "servers" in content

    def test_output_json_to_file(self, invoke, config_dir, mock_client, sample_profile, tmp_path):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_full_mock(mock_client)

        out_file = tmp_path / "infra.json"
        result = invoke(["export", "-f", "json", "-o", str(out_file)])
        assert result.exit_code == 0
        data = json.loads(out_file.read_text())
        assert "servers" in data

    def test_output_creates_parent_dirs(self, invoke, config_dir, mock_client, sample_profile, tmp_path):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_full_mock(mock_client)

        out_file = tmp_path / "subdir" / "nested" / "infra.yaml"
        result = invoke(["export", "-o", str(out_file)])
        assert result.exit_code == 0
        assert out_file.exists()


# ══════════════════════════════════════════════════════════════════════════
#  Cross-resolution (names resolved from IDs)
# ══════════════════════════════════════════════════════════════════════════


class TestExportCrossResolution:

    def test_server_image_resolved(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_full_mock(mock_client)

        result = invoke(["export", "-r", "servers", "-f", "json"])
        output = result.output
        start = output.index("{")
        end = output.rindex("}") + 1
        data = json.loads(output[start:end])
        srv = data["servers"][0]
        assert srv["image"] == "Ubuntu 22.04"

    def test_volume_attached_server_resolved(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_full_mock(mock_client)

        result = invoke(["export", "-r", "volumes", "-f", "json"])
        output = result.output
        start = output.index("{")
        end = output.rindex("}") + 1
        data = json.loads(output[start:end])
        vol = data["volumes"][0]
        assert vol["attached_to"] == "web-1"

    def test_floating_ip_attached_server_resolved(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_full_mock(mock_client)

        result = invoke(["export", "-r", "floating_ips", "-f", "json"])
        output = result.output
        start = output.index("{")
        end = output.rindex("}") + 1
        data = json.loads(output[start:end])
        fip = data["floating_ips"][0]
        assert fip["attached_to"] == "web-1"


# ══════════════════════════════════════════════════════════════════════════
#  Edge cases
# ══════════════════════════════════════════════════════════════════════════


class TestExportEdgeCases:

    def test_empty_infrastructure(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        mock_client.compute_url = "https://nova.example.com/v2.1"
        mock_client.network_url = "https://neutron.example.com"
        mock_client.volume_url = "https://cinder.example.com/v3"
        mock_client.image_url = "https://glance.example.com"
        mock_client.get = lambda url, **kw: (
            {"images": []} if "/v2/images" in url else
            {"servers": []} if "servers/detail" in url else
            {"volumes": []} if "volumes/detail" in url else
            {"networks": []} if "/networks" in url else
            {"subnets": []} if "/subnets" in url else
            {"ports": []} if "/ports" in url else
            {"routers": []} if "/routers" in url else
            {"floatingips": []} if "/floatingips" in url else
            {"security_groups": []} if "/security-groups" in url else
            {"keypairs": []} if "/os-keypairs" in url else
            {}
        )

        result = invoke(["export", "-f", "json"])
        assert result.exit_code == 0
        output = result.output
        start = output.index("{")
        end = output.rindex("}") + 1
        data = json.loads(output[start:end])
        assert data["servers"] == []
        assert data["volumes"] == []

    def test_server_with_floating_ip_via_port(self, invoke, config_dir, mock_client, sample_profile):
        """Floating IP associated via port should appear in server network info."""
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_full_mock(mock_client)

        result = invoke(["export", "-r", "servers", "-f", "json"])
        output = result.output
        start = output.index("{")
        end = output.rindex("}") + 1
        data = json.loads(output[start:end])
        srv = data["servers"][0]
        net_entry = srv["networks"][0]
        assert net_entry.get("floating_ip") == "203.0.113.10"

    def test_volume_detached(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        mock_client.compute_url = "https://nova.example.com/v2.1"
        mock_client.network_url = "https://neutron.example.com"
        mock_client.volume_url = "https://cinder.example.com/v3"
        mock_client.image_url = "https://glance.example.com"

        def _get(url, **kwargs):
            if "/v2/images" in url:
                return {"images": []}
            if "servers/detail" in url:
                return {"servers": []}
            if "volumes/detail" in url:
                return {"volumes": [_volume(attached_srv=None, status="available")]}
            if "/subnets" in url:
                return {"subnets": []}
            if "/networks" in url:
                return {"networks": []}
            if "/ports" in url:
                return {"ports": []}
            if "/routers" in url:
                return {"routers": []}
            if "/floatingips" in url:
                return {"floatingips": []}
            if "/security-groups" in url:
                return {"security_groups": []}
            if "/os-keypairs" in url:
                return {"keypairs": []}
            return {}

        mock_client.get = _get

        result = invoke(["export", "-r", "volumes", "-f", "json"])
        output = result.output
        start = output.index("{")
        end = output.rindex("}") + 1
        data = json.loads(output[start:end])
        vol = data["volumes"][0]
        assert vol["attached_to"] is None

    def test_security_group_rule_all_ports(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        mock_client.compute_url = "https://nova.example.com/v2.1"
        mock_client.network_url = "https://neutron.example.com"
        mock_client.volume_url = "https://cinder.example.com/v3"
        mock_client.image_url = "https://glance.example.com"

        sg = {
            "id": "sg-1",
            "name": "wide-open",
            "security_group_rules": [
                {"direction": "ingress", "protocol": None,
                 "port_range_min": None, "port_range_max": None,
                 "remote_ip_prefix": None},
            ],
        }

        def _get(url, **kwargs):
            if "/v2/images" in url:
                return {"images": []}
            if "servers/detail" in url:
                return {"servers": []}
            if "volumes/detail" in url:
                return {"volumes": []}
            if "/subnets" in url:
                return {"subnets": []}
            if "/networks" in url:
                return {"networks": []}
            if "/ports" in url:
                return {"ports": []}
            if "/routers" in url:
                return {"routers": []}
            if "/floatingips" in url:
                return {"floatingips": []}
            if "/security-groups" in url:
                return {"security_groups": [sg]}
            if "/os-keypairs" in url:
                return {"keypairs": []}
            return {}

        mock_client.get = _get

        result = invoke(["export", "-r", "security_groups", "-f", "json"])
        output = result.output
        start = output.index("{")
        end = output.rindex("}") + 1
        data = json.loads(output[start:end])
        rule = data["security_groups"][0]["rules"][0]
        assert rule["port_range"] == "all"
        assert rule["protocol"] == "any"


# ══════════════════════════════════════════════════════════════════════════
#  Help
# ══════════════════════════════════════════════════════════════════════════


class TestExportHelp:

    def test_export_help(self, invoke):
        result = invoke(["export", "--help"])
        assert result.exit_code == 0
        assert "--output" in result.output
        assert "--resources" in result.output
        assert "--format" in result.output
        assert "yaml" in result.output
        assert "json" in result.output
