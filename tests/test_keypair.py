"""Tests for ``orca keypair`` commands."""

from __future__ import annotations

from orca_cli.core.config import save_profile, set_active_profile

# ── Helpers ────────────────────────────────────────────────────────────────


def _keypair(name="mykey", ktype="ssh", fingerprint="aa:bb:cc:dd"):
    return {
        "keypair": {
            "name": name,
            "type": ktype,
            "fingerprint": fingerprint,
            "public_key": "ssh-ed25519 AAAA... orca:mykey",
            "created_at": "2025-01-01T00:00:00Z",
        }
    }


def _setup_mock(mock_client, keypairs=None, kp_detail=None):
    keypairs = keypairs if keypairs is not None else []
    mock_client.compute_url = "https://nova.example.com/v2.1"

    posted = {}
    deleted = []

    def _get(url, **kwargs):
        # Detail URL has a name after /os-keypairs/
        if "/os-keypairs/" in url:
            if kp_detail:
                return kp_detail
            if keypairs:
                return {"keypair": keypairs[0]["keypair"]}
            return {}
        if "/os-keypairs" in url:
            return {"keypairs": keypairs}
        return {}

    def _post(url, **kwargs):
        body = kwargs.get("json", {})
        posted.update(body)
        kp = body.get("keypair", {})
        return {"keypair": {
            "name": kp.get("name", "new"),
            "fingerprint": "ff:ee:dd:cc",
            "private_key": "-----BEGIN PRIVATE KEY-----\nfake\n-----END PRIVATE KEY-----\n",
        }}

    def _delete(url, **kwargs):
        deleted.append(url)

    mock_client.get = _get
    mock_client.post = _post
    mock_client.delete = _delete

    return {"posted": posted, "deleted": deleted}


# ══════════════════════════════════════════════════════════════════════════
#  keypair list
# ══════════════════════════════════════════════════════════════════════════


class TestKeypairList:

    def test_list_keypairs(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client, keypairs=[
            _keypair(name="key-a"),
            _keypair(name="key-b", fingerprint="11:22:33:44"),
        ])

        result = invoke(["keypair", "list"])
        assert result.exit_code == 0
        assert "key-a" in result.output
        assert "key-b" in result.output

    def test_list_empty(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client, keypairs=[])

        result = invoke(["keypair", "list"])
        assert result.exit_code == 0
        assert "No key pairs found" in result.output

    def test_list_shows_type(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client, keypairs=[_keypair()])

        result = invoke(["keypair", "list"])
        assert "ssh" in result.output

    def test_list_shows_fingerprint(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client, keypairs=[_keypair(fingerprint="aa:bb:cc:dd")])

        result = invoke(["keypair", "list"])
        assert "aa:bb" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  keypair show
# ══════════════════════════════════════════════════════════════════════════


class TestKeypairShow:

    def test_show_keypair(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client, kp_detail={"keypair": {
            "name": "mykey",
            "type": "ssh",
            "fingerprint": "aa:bb:cc:dd",
            "public_key": "ssh-ed25519 AAAA...",
            "created_at": "2025-01-01T00:00:00Z",
        }})

        result = invoke(["keypair", "show", "mykey"])
        assert result.exit_code == 0
        assert "mykey" in result.output
        assert "aa:bb" in result.output

    def test_show_displays_public_key(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client, kp_detail={"keypair": {
            "name": "mykey",
            "type": "ssh",
            "fingerprint": "aa:bb:cc:dd",
            "public_key": "ssh-ed25519 AAAA...",
            "created_at": "2025-01-01T00:00:00Z",
        }})

        result = invoke(["keypair", "show", "mykey"])
        assert "ssh-ed25519" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  keypair create
# ══════════════════════════════════════════════════════════════════════════


class TestKeypairCreate:

    def test_create_keypair(self, invoke, config_dir, mock_client, sample_profile, tmp_path):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        save_path = tmp_path / "test.pem"
        result = invoke(["keypair", "create", "new-key", "--save-to", str(save_path)])
        assert result.exit_code == 0
        assert "created" in result.output.lower()
        assert state["posted"]["keypair"]["name"] == "new-key"
        assert save_path.exists()
        assert "PRIVATE KEY" in save_path.read_text()

    def test_create_default_save_path(self, invoke, config_dir, mock_client, sample_profile, monkeypatch, tmp_path):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        # Override the default key dir to tmp_path
        monkeypatch.setattr("orca_cli.commands.keypair._DEFAULT_KEY_DIR", tmp_path)

        result = invoke(["keypair", "create", "mykey2"])
        assert result.exit_code == 0
        pem = tmp_path / "mykey2.pem"
        assert pem.exists()


# ══════════════════════════════════════════════════════════════════════════
#  keypair upload
# ══════════════════════════════════════════════════════════════════════════


class TestKeypairUpload:

    def test_upload_from_file(self, invoke, config_dir, mock_client, sample_profile, tmp_path):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        pub_file = tmp_path / "id_ed25519.pub"
        pub_file.write_text("ssh-ed25519 AAAA... user@host\n")

        result = invoke(["keypair", "upload", "imported-key",
                         "--public-key-file", str(pub_file)])
        assert result.exit_code == 0
        assert "uploaded" in result.output.lower()
        assert state["posted"]["keypair"]["public_key"] == "ssh-ed25519 AAAA... user@host"

    def test_upload_from_string(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["keypair", "upload", "str-key",
                         "--public-key", "ssh-rsa BBBB..."])
        assert result.exit_code == 0
        assert state["posted"]["keypair"]["public_key"] == "ssh-rsa BBBB..."

    def test_upload_no_key_no_default(self, invoke, config_dir, mock_client, sample_profile, monkeypatch, tmp_path):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        # Point default key dir to empty tmp_path
        monkeypatch.setattr("orca_cli.commands.keypair._DEFAULT_KEY_DIR", tmp_path)

        result = invoke(["keypair", "upload", "nokey"])
        assert result.exit_code != 0


# ══════════════════════════════════════════════════════════════════════════
#  keypair delete
# ══════════════════════════════════════════════════════════════════════════


class TestKeypairDelete:

    def test_delete_keypair(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["keypair", "delete", "old-key", "-y"])
        assert result.exit_code == 0
        assert "deleted" in result.output.lower()
        assert any("old-key" in u for u in state["deleted"])

    def test_delete_aborts_without_confirm(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        _ = invoke(["keypair", "delete", "old-key"], input="n\n")
        assert len(state["deleted"]) == 0


# ══════════════════════════════════════════════════════════════════════════
#  Help
# ═══════��══════════════════════════════════════════════════════════════════


class TestKeypairHelp:

    def test_keypair_help(self, invoke):
        result = invoke(["keypair", "--help"])
        assert result.exit_code == 0
        for cmd in ("list", "show", "create", "generate", "upload", "delete"):
            assert cmd in result.output

    def test_keypair_list_help(self, invoke):
        result = invoke(["keypair", "list", "--help"])
        assert result.exit_code == 0

    def test_keypair_generate_help(self, invoke):
        result = invoke(["keypair", "generate", "--help"])
        assert result.exit_code == 0
        assert "--type" in result.output
