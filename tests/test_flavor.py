"""Tests for ``orca flavor`` commands."""

from __future__ import annotations

from orca_cli.core.config import save_profile, set_active_profile


# ── Helpers ────────────────────────────────────────────────────────────────


def _flavor(fid="flv-1", name="m1.small", vcpus=2, ram=2048, disk=20):
    return {"id": fid, "name": name, "vcpus": vcpus, "ram": ram, "disk": disk}


def _setup_mock(mock_client, flavors=None):
    flavors = flavors if flavors is not None else []
    mock_client.compute_url = "https://nova.example.com/v2.1"
    mock_client.get = lambda url, **kw: {"flavors": flavors}


# ══════════════════════════════════════════════════════════════════════════
#  flavor list
# ══════════════════════════════════════════════════════════════════════════


class TestFlavorList:

    def test_list_flavors(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client, flavors=[
            _flavor(name="m1.small", vcpus=1, ram=1024, disk=10),
            _flavor(fid="flv-2", name="m1.large", vcpus=4, ram=8192, disk=80),
        ])

        result = invoke(["flavor", "list"])
        assert result.exit_code == 0
        assert "m1.small" in result.output
        assert "m1.large" in result.output

    def test_list_empty(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client, flavors=[])

        result = invoke(["flavor", "list"])
        assert result.exit_code == 0
        assert "No flavors found" in result.output

    def test_list_sorted_by_vcpus_then_ram(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client, flavors=[
            _flavor(fid="f3", name="big", vcpus=8, ram=16384, disk=100),
            _flavor(fid="f1", name="tiny", vcpus=1, ram=512, disk=5),
            _flavor(fid="f2", name="mid", vcpus=2, ram=4096, disk=40),
        ])

        result = invoke(["flavor", "list"])
        assert result.exit_code == 0
        tiny_pos = result.output.index("tiny")
        mid_pos = result.output.index("mid")
        big_pos = result.output.index("big")
        assert tiny_pos < mid_pos < big_pos

    def test_list_shows_vcpus_ram_disk(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client, flavors=[_flavor(vcpus=4, ram=8192, disk=80)])

        result = invoke(["flavor", "list"])
        assert "4" in result.output
        assert "8192" in result.output
        assert "80" in result.output

    def test_list_many_flavors(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        flavors = [_flavor(fid=f"f-{i}", name=f"m1.x{i}", vcpus=i, ram=i*1024)
                   for i in range(1, 11)]
        _setup_mock(mock_client, flavors=flavors)

        result = invoke(["flavor", "list"])
        assert result.exit_code == 0
        assert "m1.x1" in result.output
        assert "m1.x10" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  Help
# ══════════════════════════════════════════════════════════════════════════


class TestFlavorHelp:

    def test_flavor_help(self, invoke):
        result = invoke(["flavor", "--help"])
        assert result.exit_code == 0
        assert "list" in result.output

    def test_flavor_list_help(self, invoke):
        result = invoke(["flavor", "list", "--help"])
        assert result.exit_code == 0
