"""Tests for ``orca overview`` command."""

from __future__ import annotations

from orca_cli.core.config import save_profile, set_active_profile


# ── Helpers ────────────────────────────────────────────────────────────────


def _setup_mock(mock_client, servers=None, volumes=None, fips=None,
                nets=None, subnets=None, routers=None, sgs=None,
                kps=None, images=None):
    mock_client.compute_url = "https://nova.example.com/v2.1"
    mock_client.volume_url = "https://cinder.example.com/v3"
    mock_client.network_url = "https://neutron.example.com"
    mock_client.image_url = "https://glance.example.com"

    servers = servers or []
    volumes = volumes or []
    fips = fips or []
    nets = nets or []
    subnets = subnets or []
    routers = routers or []
    sgs = sgs or []
    kps = kps or []
    images = images or []

    def _get(url, **kwargs):
        if "servers/detail" in url:
            return {"servers": servers}
        if "volumes/detail" in url:
            return {"volumes": volumes}
        if "/floatingips" in url:
            return {"floatingips": fips}
        if "/networks" in url:
            return {"networks": nets}
        if "/subnets" in url:
            return {"subnets": subnets}
        if "/routers" in url:
            return {"routers": routers}
        if "/security-groups" in url:
            return {"security_groups": sgs}
        if "/os-keypairs" in url:
            return {"keypairs": kps}
        if "/v2/images" in url:
            return {"images": images}
        return {}

    mock_client.get = _get


# ══════════════════════════════════════════════════════════════════════════
#  overview
# ══════════════════════════════════════════════════════════════════════════


class TestOverview:

    def test_overview_basic(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client,
                    servers=[
                        {"id": "s1", "status": "ACTIVE", "flavor": {"vcpus": 2, "ram": 4096}},
                        {"id": "s2", "status": "ACTIVE", "flavor": {"vcpus": 4, "ram": 8192}},
                        {"id": "s3", "status": "SHUTOFF", "flavor": {"vcpus": 1, "ram": 1024}},
                    ],
                    volumes=[
                        {"id": "v1", "size": 50, "status": "in-use"},
                        {"id": "v2", "size": 100, "status": "available"},
                    ],
                    fips=[
                        {"id": "f1", "port_id": "p1"},
                        {"id": "f2", "port_id": None},
                    ],
                    nets=[{"id": "n1"}],
                    subnets=[{"id": "sub1"}],
                    routers=[{"id": "r1"}],
                    sgs=[{"id": "sg1"}],
                    kps=[{"keypair": {"name": "k1"}}],
                    images=[{"id": "i1"}])

        result = invoke(["overview"])
        assert result.exit_code == 0
        assert "Servers" in result.output
        assert "ACTIVE" in result.output
        assert "Resource" in result.output
        assert "Network" in result.output

    def test_overview_empty(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["overview"])
        assert result.exit_code == 0
        assert "Total" in result.output
        assert "0" in result.output

    def test_overview_shows_vcpus(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client,
                    servers=[
                        {"id": "s1", "status": "ACTIVE", "flavor": {"vcpus": 8, "ram": 2048}},
                    ])

        result = invoke(["overview"])
        assert "8" in result.output
        assert "vCPUs" in result.output

    def test_overview_fips_count(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client,
                    fips=[
                        {"id": "f1", "port_id": "p1"},
                        {"id": "f2", "port_id": "p2"},
                        {"id": "f3", "port_id": None},
                    ])

        result = invoke(["overview"])
        assert "2 in use" in result.output
        assert "1 free" in result.output

    def test_overview_volume_size(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client,
                    volumes=[
                        {"id": "v1", "size": 200, "status": "in-use"},
                    ])

        result = invoke(["overview"])
        assert "200 GB" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  Help
# ══════════════════════════════════════════════════════════════════════════


class TestOverviewHelp:

    def test_overview_help(self, invoke):
        result = invoke(["overview", "--help"])
        assert result.exit_code == 0
        assert "dashboard" in result.output.lower()
