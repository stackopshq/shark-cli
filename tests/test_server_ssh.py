"""Tests for ``orca server ssh`` — distro detection, IP picking, key lookup."""

from __future__ import annotations

from pathlib import Path

import pytest

from orca_cli.commands import server as server_mod
from orca_cli.core.config import save_profile, set_active_profile

# ── Fixtures ──────────────────────────────────────────────────────────────

SRV_ID = "11112222-3333-4444-5555-666677778888"
IMG_ID = "aaaabbbb-cccc-dddd-eeee-ffffffffffff"


def _srv(**overrides):
    base = {
        "id": SRV_ID,
        "name": "web-1",
        "status": "ACTIVE",
        "key_name": "my-key",
        "image": {"id": IMG_ID},
        "addresses": {"my-net": [
            {"addr": "10.0.0.5", "OS-EXT-IPS:type": "fixed"},
            {"addr": "203.0.113.10", "OS-EXT-IPS:type": "floating"},
        ]},
    }
    base.update(overrides)
    return base


def _setup_profile(mock_client, sample_profile):
    """Wire mock_client into a saved+active profile so ensure_client works."""
    save_profile("test", sample_profile)
    set_active_profile("test")
    mock_client.compute_url = "https://nova.example.com/v2.1"
    mock_client.image_url = "https://glance.example.com"


# ══════════════════════════════════════════════════════════════════════════
#  _pick_ssh_ip
# ══════════════════════════════════════════════════════════════════════════


class TestPickSshIp:

    def test_prefers_floating_by_default(self):
        assert server_mod._pick_ssh_ip(_srv()) == "203.0.113.10"

    def test_prefer_fixed_flag(self):
        assert server_mod._pick_ssh_ip(_srv(), prefer_fixed=True) == "10.0.0.5"

    def test_fixed_fallback_when_no_floating(self):
        srv = _srv(addresses={"net": [{"addr": "10.0.0.5", "OS-EXT-IPS:type": "fixed"}]})
        assert server_mod._pick_ssh_ip(srv) == "10.0.0.5"

    def test_floating_fallback_when_prefer_fixed_but_no_fixed(self):
        srv = _srv(addresses={"net": [{"addr": "1.2.3.4", "OS-EXT-IPS:type": "floating"}]})
        assert server_mod._pick_ssh_ip(srv, prefer_fixed=True) == "1.2.3.4"

    def test_none_when_empty(self):
        assert server_mod._pick_ssh_ip(_srv(addresses={})) is None


# ══════════════════════════════════════════════════════════════════════════
#  _detect_ssh_user
# ══════════════════════════════════════════════════════════════════════════


class TestDetectSshUser:

    def test_ubuntu(self, mock_client):
        mock_client.image_url = "https://glance.example.com"
        mock_client.get.return_value = {"os_distro": "ubuntu"}
        assert server_mod._detect_ssh_user(mock_client, _srv()) == "ubuntu"

    def test_rhel_maps_to_cloud_user(self, mock_client):
        mock_client.image_url = "https://glance.example.com"
        mock_client.get.return_value = {"os_distro": "rhel"}
        assert server_mod._detect_ssh_user(mock_client, _srv()) == "cloud-user"

    def test_amazon_maps_to_ec2_user(self, mock_client):
        mock_client.image_url = "https://glance.example.com"
        mock_client.get.return_value = {"os_distro": "amazon"}
        assert server_mod._detect_ssh_user(mock_client, _srv()) == "ec2-user"

    def test_case_insensitive(self, mock_client):
        mock_client.image_url = "https://glance.example.com"
        mock_client.get.return_value = {"os_distro": "DEBIAN"}
        assert server_mod._detect_ssh_user(mock_client, _srv()) == "debian"

    def test_unknown_distro_returns_none(self, mock_client):
        mock_client.image_url = "https://glance.example.com"
        mock_client.get.return_value = {"os_distro": "plan9"}
        assert server_mod._detect_ssh_user(mock_client, _srv()) is None

    def test_no_image_id_returns_none(self, mock_client):
        assert server_mod._detect_ssh_user(mock_client, _srv(image={})) is None

    def test_image_not_dict_returns_none(self, mock_client):
        """Nova sometimes returns "" (empty string) for image on volume-backed servers."""
        assert server_mod._detect_ssh_user(mock_client, _srv(image="")) is None

    def test_glance_error_swallowed(self, mock_client):
        mock_client.image_url = "https://glance.example.com"
        mock_client.get.side_effect = RuntimeError("glance down")
        assert server_mod._detect_ssh_user(mock_client, _srv()) is None

    def test_boot_from_volume_uses_volume_image_metadata(self, mock_client):
        """Boot-from-volume servers carry an empty image ref; read os_distro from
        the attached boot volume's ``volume_image_metadata`` instead.

        Regression: on Infomaniak (Debian 12 boot-from-volume) the detector
        returned None and SSH fell back to root@ even though the image was
        clearly labelled os_distro=debian."""
        mock_client.image_url = "https://glance.example.com"
        mock_client.volume_url = "https://cinder.example.com/v3/proj"
        mock_client.get.return_value = {
            "volume": {"volume_image_metadata": {"os_distro": "debian"}}
        }
        srv = _srv(image="", **{
            "os-extended-volumes:volumes_attached": [{"id": "vol-1"}],
        })
        assert server_mod._detect_ssh_user(mock_client, srv) == "debian"

    def test_boot_from_volume_no_metadata_returns_none(self, mock_client):
        mock_client.image_url = "https://glance.example.com"
        mock_client.volume_url = "https://cinder.example.com/v3/proj"
        mock_client.get.return_value = {"volume": {}}
        srv = _srv(image="", **{
            "os-extended-volumes:volumes_attached": [{"id": "vol-1"}],
        })
        assert server_mod._detect_ssh_user(mock_client, srv) is None


# ══════════════════════════════════════════════════════════════════════════
#  _find_ssh_key
# ══════════════════════════════════════════════════════════════════════════


class TestFindSshKey:

    @pytest.fixture
    def fake_ssh(self, tmp_path, monkeypatch):
        """Redirect ~ to tmp_path and create a fake ~/.ssh."""
        monkeypatch.setenv("HOME", str(tmp_path))
        # Also patch Path.home() for Pathlib (it caches env lookups in some versions)
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
        ssh = tmp_path / ".ssh"
        ssh.mkdir()
        return ssh

    def test_matches_orca_prefix(self, fake_ssh):
        key = fake_ssh / "orca-my-key"
        key.write_text("PRIVATE")
        assert server_mod._find_ssh_key("my-key") == str(key)

    def test_matches_exact_name(self, fake_ssh):
        key = fake_ssh / "my-key"
        key.write_text("PRIVATE")
        assert server_mod._find_ssh_key("my-key") == str(key)

    def test_matches_pem_suffix(self, fake_ssh):
        key = fake_ssh / "my-key.pem"
        key.write_text("PRIVATE")
        assert server_mod._find_ssh_key("my-key") == str(key)

    def test_matches_orca_prefix_pem(self, fake_ssh):
        """orca keypair create saves to ~/.ssh/orca-<name>.pem when name already has orca- prefix."""
        key = fake_ssh / "orca-my-key.pem"
        key.write_text("PRIVATE")
        assert server_mod._find_ssh_key("my-key") == str(key)

    def test_does_not_match_unrelated_orca_key(self, fake_ssh):
        """Regression: fallback must not pick an unrelated orca-* key.

        Previously _find_ssh_key used glob("orca-*") as a wildcard fallback,
        so a leftover ~/.ssh/orca-other-project.pem would match a server whose
        key_name was 'lifecycle-test' — a silent auth failure.
        """
        (fake_ssh / "orca-other-project.pem").write_text("UNRELATED")
        assert server_mod._find_ssh_key("lifecycle-test") is None

    def test_falls_back_to_id_ed25519(self, fake_ssh):
        key = fake_ssh / "id_ed25519"
        key.write_text("PRIVATE")
        assert server_mod._find_ssh_key("nonexistent") == str(key)

    def test_skips_pub_files(self, fake_ssh):
        (fake_ssh / "id_rsa.pub").write_text("PUBLIC")
        # No private key exists
        assert server_mod._find_ssh_key(None) is None

    def test_no_ssh_dir_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
        assert server_mod._find_ssh_key("any") is None


# ══════════════════════════════════════════════════════════════════════════
#  Integration — orca server ssh --dry-run
# ══════════════════════════════════════════════════════════════════════════


class TestServerSshIntegration:

    def test_dry_run_by_id_auto_user_and_key(
        self, invoke, mock_client, config_dir, sample_profile, tmp_path, monkeypatch
    ):
        _setup_profile(mock_client, sample_profile)
        # Fake ~/.ssh with a matching key
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
        (tmp_path / ".ssh").mkdir()
        key = tmp_path / ".ssh" / "orca-my-key"
        key.write_text("PRIVATE")

        # First GET: server by ID; second GET: image for os_distro
        mock_client.get.side_effect = [
            {"server": _srv()},
            {"os_distro": "ubuntu"},
        ]

        result = invoke(["server", "ssh", SRV_ID, "--dry-run"])
        assert result.exit_code == 0, result.output
        assert "ubuntu@203.0.113.10" in result.output
        # Rich may wrap the long tmp path across lines — just check the filename
        normalised = result.output.replace("\n", "")
        assert str(key) in normalised

    def test_dry_run_fallback_user_root_when_unknown_distro(
        self, invoke, mock_client, config_dir, sample_profile, tmp_path, monkeypatch
    ):
        _setup_profile(mock_client, sample_profile)
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
        (tmp_path / ".ssh").mkdir()
        mock_client.get.side_effect = [
            {"server": _srv()},
            {"os_distro": "haiku-os"},  # unknown
        ]
        result = invoke(["server", "ssh", SRV_ID, "--dry-run"])
        assert result.exit_code == 0
        assert "root@203.0.113.10" in result.output

    def test_user_override_skips_detection(
        self, invoke, mock_client, config_dir, sample_profile, tmp_path, monkeypatch
    ):
        _setup_profile(mock_client, sample_profile)
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
        (tmp_path / ".ssh").mkdir()
        # Only ONE GET expected: no image fetch when user provided
        mock_client.get.return_value = {"server": _srv()}

        result = invoke(["server", "ssh", SRV_ID, "-u", "admin", "--dry-run"])
        assert result.exit_code == 0
        assert "admin@203.0.113.10" in result.output
        # Image endpoint must not have been called
        calls = [c.args[0] for c in mock_client.get.call_args_list]
        assert not any("glance" in c or "images/" in c for c in calls)

    def test_fixed_flag_uses_fixed_ip(
        self, invoke, mock_client, config_dir, sample_profile, tmp_path, monkeypatch
    ):
        _setup_profile(mock_client, sample_profile)
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
        (tmp_path / ".ssh").mkdir()
        mock_client.get.side_effect = [
            {"server": _srv()},
            {"os_distro": "ubuntu"},
        ]
        result = invoke(["server", "ssh", SRV_ID, "--fixed", "--dry-run"])
        assert result.exit_code == 0
        assert "ubuntu@10.0.0.5" in result.output

    def test_remote_args_passthrough(
        self, invoke, mock_client, config_dir, sample_profile, tmp_path, monkeypatch
    ):
        _setup_profile(mock_client, sample_profile)
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
        (tmp_path / ".ssh").mkdir()
        mock_client.get.side_effect = [
            {"server": _srv()},
            {"os_distro": "ubuntu"},
        ]
        result = invoke(["server", "ssh", SRV_ID, "--dry-run", "ls", "/var/log"])
        assert result.exit_code == 0
        assert "ls /var/log" in result.output

    def test_name_search_fallback(
        self, invoke, mock_client, config_dir, sample_profile, tmp_path, monkeypatch
    ):
        _setup_profile(mock_client, sample_profile)
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
        (tmp_path / ".ssh").mkdir()
        # ID lookup fails → name search succeeds with one match → image lookup
        mock_client.get.side_effect = [
            RuntimeError("not a uuid"),
            {"servers": [_srv()]},
            {"os_distro": "ubuntu"},
        ]
        result = invoke(["server", "ssh", "web-1", "--dry-run"])
        assert result.exit_code == 0
        assert "ubuntu@203.0.113.10" in result.output

    def test_name_search_multiple_matches_errors(
        self, invoke, mock_client, config_dir, sample_profile
    ):
        _setup_profile(mock_client, sample_profile)
        mock_client.get.side_effect = [
            RuntimeError("not a uuid"),
            {"servers": [_srv(), _srv(id="other-id", name="web-1")]},
        ]
        result = invoke(["server", "ssh", "web-1", "--dry-run"])
        assert result.exit_code != 0
        assert "Multiple servers match" in result.output or "more specific" in result.output.lower()

    def test_name_search_not_found_errors(
        self, invoke, mock_client, config_dir, sample_profile
    ):
        _setup_profile(mock_client, sample_profile)
        mock_client.get.side_effect = [
            RuntimeError("not a uuid"),
            {"servers": []},
        ]
        result = invoke(["server", "ssh", "ghost", "--dry-run"])
        assert result.exit_code != 0
        assert "not found" in result.output.lower()

    def test_no_ip_errors(
        self, invoke, mock_client, config_dir, sample_profile
    ):
        _setup_profile(mock_client, sample_profile)
        srv = _srv(addresses={})  # no IPs at all
        mock_client.get.return_value = {"server": srv}
        result = invoke(["server", "ssh", SRV_ID, "--dry-run"])
        assert result.exit_code != 0
        assert "No IP" in result.output
