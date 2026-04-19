"""Tests for the interactive wizard — wizard.py helpers and -i flag on commands."""

from __future__ import annotations

from unittest.mock import MagicMock

import click
from click.testing import CliRunner

from orca_cli.core import wizard as wiz

# ── Reusable UUIDs ────────────────────────────────────────────────────────

IMG  = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
FLV  = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
NET  = "cccccccc-cccc-cccc-cccc-cccccccccccc"
SRV  = "dddddddd-dddd-dddd-dddd-dddddddddddd"
VOL  = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"
PRJ  = "ffffffff-ffff-ffff-ffff-ffffffffffff"

# ── Fixture helpers ────────────────────────────────────────────────────────

def _images():
    return [{"id": IMG, "name": "Ubuntu 22.04", "status": "active",
             "os_distro": "ubuntu", "size": 2_000_000_000}]


def _flavors():
    return [{"id": FLV, "name": "m1.small", "vcpus": 2, "ram": 2048, "disk": 20}]


def _networks():
    return [{"id": NET, "name": "private", "status": "ACTIVE", "shared": False}]


def _keypairs():
    return [{"keypair": {"name": "my-key", "type": "ssh",
                         "fingerprint": "aa:bb:cc:dd:ee:ff:00:11:22:33"}}]


def _sgs():
    return [{"id": "sg-1", "name": "default", "description": "Default SG"}]


def _vtypes():
    return [{"id": "vt-1", "name": "ceph-ssd", "description": "Fast SSD"}]


def _limits():
    return {"limits": {"absolute": {
        "totalInstancesUsed": 2, "maxTotalInstances": 10,
        "totalCoresUsed": 4, "maxTotalCores": 20,
        "totalRAMUsed": 4096, "maxTotalRAMSize": 51200,
    }}}


def _mock_client_for_server():
    mc = MagicMock()
    mc.compute_url = "https://nova.example.com/v2.1"
    mc.network_url = "https://neutron.example.com"
    mc.image_url   = "https://glance.example.com"
    mc.volume_url  = "https://cinder.example.com/v3"

    def _get(url, **kw):
        if "images" in url:
            return {"images": _images()}
        if "flavors/detail" in url:
            return {"flavors": _flavors()}
        if "v2.0/networks" in url:
            return {"networks": _networks()}
        if "os-keypairs" in url:
            return {"keypairs": _keypairs()}
        if "security-groups" in url:
            return {"security_groups": _sgs()}
        if "limits" in url:
            return _limits()
        return {}

    mc.get.side_effect = _get
    mc.post.return_value = {"server": {"id": SRV, "adminPass": ""}}
    return mc


def _mock_client_for_volume():
    mc = MagicMock()
    mc.compute_url = "https://nova.example.com/v2.1"
    mc.volume_url  = "https://cinder.example.com/v3"

    def _get(url, **kw):
        if "types" in url:
            return {"volume_types": _vtypes()}
        if "limits" in url:
            return _limits()
        return {}

    mc.get.side_effect = _get
    mc.post.return_value = {"volume": {"id": VOL, "name": "my-vol", "size": 50}}
    return mc


# ══════════════════════════════════════════════════════════════════════════
#  Unit tests — wizard helpers
# ══════════════════════════════════════════════════════════════════════════

class TestWizardSelect:
    """Tests for wizard_select() generic selector."""

    def _run(self, items, user_input, **kwargs):
        """Run wizard_select inside a CliRunner to capture output."""
        @click.command()
        def cmd():
            idx = wiz.wizard_select(
                items, "Item",
                ["Name", "Extra"],
                lambda x: (x["name"], x.get("extra", "—")),
                **kwargs,
            )
            click.echo(f"RESULT:{idx}")

        runner = CliRunner()
        return runner.invoke(cmd, input=user_input)

    def test_single_item_select(self):
        items = [{"name": "alpha", "extra": "A"}]
        r = self._run(items, "1\n")
        assert r.exit_code == 0
        assert "RESULT:0" in r.output

    def test_second_item(self):
        items = [{"name": "alpha"}, {"name": "beta"}]
        r = self._run(items, "2\n")
        assert "RESULT:1" in r.output

    def test_allow_none_returns_none(self):
        items = [{"name": "alpha"}]
        r = self._run(items, "0\n", allow_none=True)
        assert "RESULT:None" in r.output

    def test_headers_shown(self):
        items = [{"name": "alpha", "extra": "X"}]
        r = self._run(items, "1\n")
        assert "Name" in r.output
        assert "Extra" in r.output

    def test_item_names_shown(self):
        items = [{"name": "ubuntu-22"}, {"name": "debian-12"}]
        r = self._run(items, "1\n")
        assert "ubuntu-22" in r.output
        assert "debian-12" in r.output

    def test_empty_list_aborts(self):
        @click.command()
        def cmd():
            wiz.wizard_select([], "Item", ["Name"], lambda x: (x["name"],))

        r = CliRunner().invoke(cmd, input="")
        # Should abort (Abort exception or non-zero exit)
        assert r.exit_code != 0 or "No item" in r.output


class TestWizardFormatHelpers:

    def test_fmt_bytes_gb(self):
        assert "GB" in wiz._fmt_bytes(2_000_000_000)

    def test_fmt_bytes_mb(self):
        assert "MB" in wiz._fmt_bytes(500_000_000)

    def test_fmt_bytes_small(self):
        assert "B" in wiz._fmt_bytes(500)

    def test_fmt_ram_gb(self):
        assert "GB" in wiz._fmt_ram(2048)

    def test_fmt_ram_mb(self):
        assert "MB" in wiz._fmt_ram(512)


class TestBuildServerCommand:

    def test_basic(self):
        cmd = wiz.build_server_command("vm1", IMG, FLV, 20, None, None, [])
        assert "--name vm1" in cmd
        assert f"--image {IMG}" in cmd
        assert f"--flavor {FLV}" in cmd

    def test_includes_network(self):
        cmd = wiz.build_server_command("vm1", IMG, FLV, 20, NET, None, [])
        assert f"--network {NET}" in cmd

    def test_includes_key(self):
        cmd = wiz.build_server_command("vm1", IMG, FLV, 20, None, "my-key", [])
        assert "--key-name my-key" in cmd

    def test_includes_sg(self):
        cmd = wiz.build_server_command("vm1", IMG, FLV, 20, None, None, ["default"])
        assert "--security-group default" in cmd

    def test_multiple_sgs(self):
        cmd = wiz.build_server_command("vm1", IMG, FLV, 20, None, None, ["sg1", "sg2"])
        assert "sg1" in cmd
        assert "sg2" in cmd


class TestSelectSecurityGroups:
    """Multi-select parser for SGs: comma-separated indices, skip blank, skip bad ints."""

    def _client(self, sgs):
        c = MagicMock()
        c.network_url = "https://neutron.example.com"
        c.get.return_value = {"security_groups": sgs}
        return c

    def test_blank_returns_empty(self):
        c = self._client([{"name": "default", "description": ""}])
        @click.command()
        def cmd():
            result = wiz.select_security_groups(c)
            click.echo(f"SGS:{result}")
        r = CliRunner().invoke(cmd, input="\n")
        assert "SGS:[]" in r.output

    def test_single_selection(self):
        sgs = [{"name": "web", "description": "Web SG"},
               {"name": "db", "description": "DB SG"}]
        c = self._client(sgs)
        @click.command()
        def cmd():
            result = wiz.select_security_groups(c)
            click.echo(f"SGS:{result}")
        r = CliRunner().invoke(cmd, input="1\n")
        assert "SGS:['web']" in r.output

    def test_multi_selection_with_comma(self):
        sgs = [{"name": "a"}, {"name": "b"}, {"name": "c"}]
        c = self._client(sgs)
        @click.command()
        def cmd():
            result = wiz.select_security_groups(c)
            click.echo(f"SGS:{result}")
        r = CliRunner().invoke(cmd, input="1,3\n")
        assert "SGS:['a', 'c']" in r.output

    def test_ignores_bad_int_and_out_of_range(self):
        """'foo' should be skipped silently; '99' out of range; '1' kept."""
        sgs = [{"name": "only"}]
        c = self._client(sgs)
        @click.command()
        def cmd():
            result = wiz.select_security_groups(c)
            click.echo(f"SGS:{result}")
        r = CliRunner().invoke(cmd, input="1,foo,99\n")
        assert "SGS:['only']" in r.output


class TestSelectCidr:

    def test_option_1_returns_open(self):
        runner = CliRunner()
        @click.command()
        def cmd():
            result = wiz.select_cidr()
            click.echo(f"CIDR:{result}")
        r = runner.invoke(cmd, input="1\n")
        assert "CIDR:0.0.0.0/0" in r.output

    def test_option_2_returns_custom(self):
        runner = CliRunner()
        @click.command()
        def cmd():
            result = wiz.select_cidr()
            click.echo(f"CIDR:{result}")
        r = runner.invoke(cmd, input="2\n192.168.1.0/24\n")
        assert "CIDR:192.168.1.0/24" in r.output


# ══════════════════════════════════════════════════════════════════════════
#  Integration tests — server create -i
# ══════════════════════════════════════════════════════════════════════════

class TestServerCreateInteractive:

    def _full_input(self, name="my-vm", image=1, flavor=1, network=1,
                    keypair=1, sgs="", confirm="y"):
        """Simulate wizard stdin for server create -i (all prompts)."""
        return f"{name}\n{image}\n{flavor}\n{network}\n{keypair}\n{sgs}\n{confirm}\n"

    def test_creates_server(self, invoke, mock_client):
        _setup(mock_client)
        result = invoke(
            ["server", "create", "-i"],
            input=self._full_input(),
        )
        assert result.exit_code == 0
        assert mock_client.post.called
        assert "Server created" in result.output

    def test_posts_correct_name(self, invoke, mock_client):
        _setup(mock_client)
        invoke(["server", "create", "-i"], input=self._full_input(name="prod-web"))
        body = mock_client.post.call_args[1]["json"]["server"]
        assert body["name"] == "prod-web"

    def test_posts_selected_image(self, invoke, mock_client):
        _setup(mock_client)
        invoke(["server", "create", "-i"], input=self._full_input())
        body = mock_client.post.call_args[1]["json"]["server"]
        bdm = body["block_device_mapping_v2"][0]
        assert bdm["uuid"] == IMG

    def test_posts_selected_flavor(self, invoke, mock_client):
        _setup(mock_client)
        invoke(["server", "create", "-i"], input=self._full_input())
        body = mock_client.post.call_args[1]["json"]["server"]
        assert body["flavorRef"] == FLV

    def test_posts_selected_network(self, invoke, mock_client):
        _setup(mock_client)
        invoke(["server", "create", "-i"], input=self._full_input())
        body = mock_client.post.call_args[1]["json"]["server"]
        assert body["networks"][0]["uuid"] == NET

    def test_posts_selected_keypair(self, invoke, mock_client):
        _setup(mock_client)
        invoke(["server", "create", "-i"], input=self._full_input())
        body = mock_client.post.call_args[1]["json"]["server"]
        assert body["key_name"] == "my-key"

    def test_skip_network_sends_none(self, invoke, mock_client):
        _setup(mock_client)
        # Choose 0 for network (skip)
        invoke(["server", "create", "-i"],
               input=self._full_input(network=0))
        body = mock_client.post.call_args[1]["json"]["server"]
        assert "networks" not in body

    def test_skip_keypair_sends_none(self, invoke, mock_client):
        _setup(mock_client)
        invoke(["server", "create", "-i"],
               input=self._full_input(keypair=0))
        body = mock_client.post.call_args[1]["json"]["server"]
        assert "key_name" not in body

    def test_abort_on_no_confirm(self, invoke, mock_client):
        _setup(mock_client)
        result = invoke(["server", "create", "-i"],
                        input=self._full_input(confirm="n"))
        assert result.exit_code == 0
        mock_client.post.assert_not_called()

    def test_shows_quota_preview(self, invoke, mock_client):
        _setup(mock_client)
        result = invoke(["server", "create", "-i"], input=self._full_input())
        assert "Quota" in result.output or "vCPU" in result.output or "Instance" in result.output

    def test_shows_cli_equivalent(self, invoke, mock_client):
        _setup(mock_client)
        result = invoke(["server", "create", "-i"], input=self._full_input())
        assert "orca server create" in result.output

    def test_prefilled_name_skips_name_prompt(self, invoke, mock_client):
        """If --name is given, wizard should skip name prompt."""
        _setup(mock_client)
        # No name in stdin (only image, flavor, network, keypair, sg, confirm)
        result = invoke(
            ["server", "create", "-i", "--name", "pre-filled"],
            input="1\n1\n1\n1\n\ny\n",
        )
        assert result.exit_code == 0
        body = mock_client.post.call_args[1]["json"]["server"]
        assert body["name"] == "pre-filled"

    def test_prefilled_image_skips_image_prompt(self, invoke, mock_client):
        """If --image is given, wizard should skip image selection."""
        _setup(mock_client)
        # No image selection needed: name, flavor, network, keypair, sg, confirm
        result = invoke(
            ["server", "create", "-i", "--image", IMG],
            input="my-vm\n1\n1\n1\n\ny\n",
        )
        assert result.exit_code == 0
        body = mock_client.post.call_args[1]["json"]["server"]
        assert body["block_device_mapping_v2"][0]["uuid"] == IMG

    def test_wizard_help(self, invoke):
        result = invoke(["server", "create", "--help"])
        assert result.exit_code == 0
        assert "interactive" in result.output.lower() or "-i" in result.output

    def test_missing_required_without_interactive(self, invoke, mock_client):
        _setup(mock_client)
        result = invoke(["server", "create"])
        assert result.exit_code != 0
        assert "--name" in result.output or "Missing" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  Integration tests — volume create -i
# ══════════════════════════════════════════════════════════════════════════

class TestVolumeCreateInteractive:

    def test_creates_volume(self, invoke, mock_client):
        _setup_vol(mock_client)
        result = invoke(
            ["volume", "create", "-i"],
            input="my-vol\n50\n1\n\ny\n",
        )
        assert result.exit_code == 0
        assert mock_client.post.called

    def test_posts_correct_name_and_size(self, invoke, mock_client):
        _setup_vol(mock_client)
        invoke(["volume", "create", "-i"], input="data-vol\n100\n0\n\ny\n")
        body = mock_client.post.call_args[1]["json"]["volume"]
        assert body["name"] == "data-vol"
        assert body["size"] == 100

    def test_posts_selected_type(self, invoke, mock_client):
        _setup_vol(mock_client)
        invoke(["volume", "create", "-i"], input="v\n10\n1\n\ny\n")
        body = mock_client.post.call_args[1]["json"]["volume"]
        assert body.get("volume_type") == "ceph-ssd"

    def test_abort_on_no_confirm(self, invoke, mock_client):
        _setup_vol(mock_client)
        result = invoke(["volume", "create", "-i"], input="v\n10\n0\n\nn\n")
        assert result.exit_code == 0
        mock_client.post.assert_not_called()

    def test_prefilled_name_skips_name_prompt(self, invoke, mock_client):
        _setup_vol(mock_client)
        result = invoke(["volume", "create", "-i", "--name", "pre"], input="50\n0\n\ny\n")
        assert result.exit_code == 0
        body = mock_client.post.call_args[1]["json"]["volume"]
        assert body["name"] == "pre"

    def test_missing_required_without_interactive(self, invoke, mock_client):
        _setup_vol(mock_client)
        result = invoke(["volume", "create"])
        assert result.exit_code != 0

    def test_wizard_help(self, invoke):
        result = invoke(["volume", "create", "--help"])
        assert result.exit_code == 0
        assert "interactive" in result.output.lower() or "-i" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  Integration tests — doctor --fix --cidr
# ══════════════════════════════════════════════════════════════════════════

PRJ_ID = "proj-1111-1111-1111-111111111111"


def _sg(has_ssh=True, has_icmp=True):
    rules = []
    if has_ssh:
        rules.append({"direction": "ingress", "protocol": "tcp",
                      "port_range_min": 22, "port_range_max": 22})
    if has_icmp:
        rules.append({"direction": "ingress", "protocol": "icmp"})
    return {"security_groups": [{"id": "sg-default", "name": "default",
                                  "security_group_rules": rules}]}


def _setup_doctor(mock_client, sg_data=None):
    mock_client.compute_url = "https://nova.example.com/v2.1"
    mock_client.network_url = "https://neutron.example.com"
    mock_client.volume_url  = "https://cinder.example.com/v3"
    mock_client.image_url   = "https://glance.example.com"
    mock_client._token_data = {
        "user": {"name": "admin"},
        "project": {"name": "demo", "id": PRJ_ID},
    }
    mock_client.post.return_value = {}

    def _get(url, **kw):
        if "nova" in url and "limits" in url:
            return {"limits": {"absolute": {
                "totalInstancesUsed": 2, "maxTotalInstances": 10,
                "totalCoresUsed": 4, "maxTotalCores": 20,
                "totalRAMUsed": 4096, "maxTotalRAMSize": 51200,
            }}}
        if "cinder" in url and "limits" in url:
            return {"limits": {"absolute": {
                "totalVolumesUsed": 1, "maxTotalVolumes": 10,
                "totalGigabytesUsed": 50, "maxTotalVolumeGigabytes": 1000,
            }}}
        if "quotas" in url and PRJ_ID in url:
            return {"quota": {
                "floatingip":     {"used": 2,  "limit": 10},
                "security_group": {"used": 3,  "limit": 20},
            }}
        if "quotas/defaults" in url:
            return {}
        if "security-groups" in url:
            return sg_data or _sg()
        if "images" in url:
            return {"images": []}
        return {}

    mock_client.get.side_effect = _get


class TestDoctorFixCidr:

    def test_fix_uses_cidr_option(self, invoke, mock_client):
        _setup_doctor(mock_client, sg_data=_sg(has_ssh=False, has_icmp=False))
        result = invoke(["doctor", "--fix", "--cidr", "10.0.0.0/8"])
        assert result.exit_code == 0
        assert mock_client.post.called
        # Both posted rules should contain the specified CIDR
        for call in mock_client.post.call_args_list:
            body = call[1]["json"]["security_group_rule"]
            assert body["remote_ip_prefix"] == "10.0.0.0/8"

    def test_fix_defaults_to_open_when_no_tty(self, invoke, mock_client):
        """Non-TTY (CliRunner) without --cidr → 0.0.0.0/0."""
        _setup_doctor(mock_client, sg_data=_sg(has_ssh=False, has_icmp=False))
        result = invoke(["doctor", "--fix"])
        assert result.exit_code == 0
        for call in mock_client.post.call_args_list:
            body = call[1]["json"]["security_group_rule"]
            assert body["remote_ip_prefix"] == "0.0.0.0/0"

    def test_fix_cidr_shown_in_output(self, invoke, mock_client):
        _setup_doctor(mock_client, sg_data=_sg(has_ssh=False, has_icmp=False))
        result = invoke(["doctor", "--fix", "--cidr", "172.16.0.0/12"])
        assert "172.16.0.0/12" in result.output

    def test_doctor_help_shows_cidr_option(self, invoke):
        result = invoke(["doctor", "--help"])
        assert result.exit_code == 0
        assert "cidr" in result.output.lower()

    def test_no_post_when_rules_present_with_cidr(self, invoke, mock_client):
        """Even with --cidr, no POST if rules already exist."""
        _setup_doctor(mock_client, sg_data=_sg(has_ssh=True, has_icmp=True))
        invoke(["doctor", "--fix", "--cidr", "10.0.0.0/8"])
        mock_client.post.assert_not_called()


# ══════════════════════════════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════════════════════════════

def _setup(mock_client):
    """Configure mock_client for server create -i tests."""
    mock_client.compute_url = "https://nova.example.com/v2.1"
    mock_client.network_url = "https://neutron.example.com"
    mock_client.image_url   = "https://glance.example.com"
    mock_client.volume_url  = "https://cinder.example.com/v3"

    def _get(url, **kw):
        if "images" in url:
            return {"images": _images()}
        if "flavors/detail" in url:
            return {"flavors": _flavors()}
        if "v2.0/networks" in url:
            return {"networks": _networks()}
        if "os-keypairs" in url:
            return {"keypairs": _keypairs()}
        if "security-groups" in url:
            return {"security_groups": _sgs()}
        if "limits" in url:
            return _limits()
        return {}

    mock_client.get.side_effect = _get
    mock_client.post.return_value = {"server": {"id": SRV, "adminPass": ""}}


def _setup_vol(mock_client):
    """Configure mock_client for volume create -i tests."""
    mock_client.compute_url = "https://nova.example.com/v2.1"
    mock_client.volume_url  = "https://cinder.example.com/v3"

    def _get(url, **kw):
        if "types" in url:
            return {"volume_types": _vtypes()}
        if "limits" in url:
            return _limits()
        return {}

    mock_client.get.side_effect = _get
    mock_client.post.return_value = {"volume": {"id": VOL, "name": "my-vol", "size": 50}}
