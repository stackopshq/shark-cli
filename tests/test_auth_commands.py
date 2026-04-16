"""Tests for orca auth commands — whoami, token-debug, check."""

from __future__ import annotations

import json

from orca_cli.core.config import save_profile, set_active_profile

# ══════════════════════════════════════════════════════════════════════════
#  whoami
# ══════════════════════════════════════════════════════════════════════════


class TestWhoami:

    def test_whoami_displays_user_info(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        result = invoke(["auth", "whoami"])
        assert result.exit_code == 0
        output = result.output
        assert "admin" in output
        assert "my-project" in output
        assert "Default" in output

    def test_whoami_shows_roles(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        result = invoke(["auth", "whoami"])
        assert "admin" in result.output
        assert "member" in result.output

    def test_whoami_shows_services(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        result = invoke(["auth", "whoami"])
        assert "compute" in result.output
        assert "identity" in result.output
        assert "network" in result.output

    def test_whoami_shows_token_expiry(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        result = invoke(["auth", "whoami"])
        # Token expires in 2099, so should show remaining time
        assert "2099" in result.output

    def test_whoami_shows_auth_url(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        result = invoke(["auth", "whoami"])
        assert "keystone.example.com" in result.output

    def test_whoami_shows_interface(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        result = invoke(["auth", "whoami"])
        assert "public" in result.output

    def test_whoami_shows_region_when_set(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("prod", sample_profile)
        set_active_profile("prod")
        mock_client._region_name = "eu-west-1"

        result = invoke(["auth", "whoami"])
        assert "eu-west-1" in result.output

    def test_whoami_no_region_when_none(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("prod", sample_profile)
        set_active_profile("prod")
        mock_client._region_name = None

        result = invoke(["auth", "whoami"])
        # "Region" row should not appear
        # Just verify the command works without error
        assert result.exit_code == 0

    def test_whoami_expired_token(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("prod", sample_profile)
        set_active_profile("prod")
        mock_client._token_data = {
            **mock_client._token_data,
            "expires_at": "2020-01-01T00:00:00Z",
        }

        result = invoke(["auth", "whoami"])
        assert result.exit_code == 0
        assert "EXPIRED" in result.output

    def test_whoami_no_roles(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("prod", sample_profile)
        set_active_profile("prod")
        mock_client._token_data = {**mock_client._token_data, "roles": []}

        result = invoke(["auth", "whoami"])
        assert result.exit_code == 0
        assert "none" in result.output

    def test_whoami_empty_catalog(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("prod", sample_profile)
        set_active_profile("prod")
        mock_client._catalog = []

        result = invoke(["auth", "whoami"])
        assert result.exit_code == 0
        assert "none" in result.output

    def test_whoami_invalid_expires_at(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("prod", sample_profile)
        set_active_profile("prod")
        mock_client._token_data = {**mock_client._token_data, "expires_at": "not-a-date"}

        result = invoke(["auth", "whoami"])
        assert result.exit_code == 0
        # Should show "?" for remaining
        assert "?" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  token-debug
# ══════════════════════════════════════════════════════════════════════════


class TestTokenDebug:

    def test_token_debug_displays_summary(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        result = invoke(["auth", "token-debug"])
        assert result.exit_code == 0
        output = result.output
        assert "Token Debug" in output
        assert "password" in output  # auth method
        assert "admin" in output  # user
        assert "my-project" in output  # project

    def test_token_debug_shows_roles_table(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        result = invoke(["auth", "token-debug"])
        assert "Roles" in result.output
        assert "admin" in result.output
        assert "member" in result.output

    def test_token_debug_shows_catalog(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        result = invoke(["auth", "token-debug"])
        assert "Service Catalog" in result.output
        assert "compute" in result.output
        assert "nova" in result.output

    def test_token_debug_raw_json(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        result = invoke(["auth", "token-debug", "--raw"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["user"]["name"] == "admin"
        assert data["project"]["name"] == "my-project"
        assert len(data["roles"]) == 2
        assert len(data["catalog"]) == 3

    def test_token_debug_shows_truncated_token(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        result = invoke(["auth", "token-debug"])
        # Token should be truncated (first 32 chars + "…")
        assert "fake-token-abcdef1234567890abcde" in result.output

    def test_token_debug_shows_lifetime(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        result = invoke(["auth", "token-debug"])
        assert "Lifetime" in result.output
        assert "Remaining" in result.output
        # Token issued/expires in 2099 → remaining time should show "elapsed"
        assert "elapsed" in result.output

    def test_token_debug_shows_endpoints(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        result = invoke(["auth", "token-debug"])
        # Check service catalog endpoints
        assert "nova.example.com" in result.output
        assert "keystone.example.com" in result.output
        assert "neutron.example.com" in result.output
        assert "RegionOne" in result.output

    def test_token_debug_shows_domain_info(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        result = invoke(["auth", "token-debug"])
        assert "User Domain" in result.output
        assert "Project Domain" in result.output
        assert "Default" in result.output

    def test_token_debug_empty_roles(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("prod", sample_profile)
        set_active_profile("prod")
        mock_client._token_data = {**mock_client._token_data, "roles": []}

        result = invoke(["auth", "token-debug"])
        assert result.exit_code == 0
        assert "Roles" in result.output

    def test_token_debug_empty_catalog(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("prod", sample_profile)
        set_active_profile("prod")
        mock_client._catalog = []

        result = invoke(["auth", "token-debug"])
        assert result.exit_code == 0
        assert "Service Catalog" in result.output

    def test_token_debug_no_timestamps(self, invoke, config_dir, mock_client, sample_profile):
        """Missing issued_at/expires_at should not crash."""
        save_profile("prod", sample_profile)
        set_active_profile("prod")
        mock_client._token_data = {
            **mock_client._token_data,
            "issued_at": "",
            "expires_at": "",
        }

        result = invoke(["auth", "token-debug"])
        assert result.exit_code == 0


# ══════════════════════════════════════════════════════════════════════════
#  check
# ══════════════════════════════════════════════════════════════════════════


class TestCheck:

    def test_check_active_profile(self, invoke, config_dir, sample_profile, monkeypatch):
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        from unittest.mock import patch

        from tests.conftest import make_mock_client

        with patch("orca_cli.core.client.OrcaClient") as mock_cls:
            mock_cls.return_value = make_mock_client()
            result = invoke(["auth", "check"])

        assert result.exit_code == 0
        assert "OK" in result.output

    def test_check_all_profiles(self, invoke, config_dir, sample_profile, monkeypatch):
        save_profile("prod", sample_profile)
        save_profile("staging", {**sample_profile, "username": "stage-user"})
        set_active_profile("prod")

        from unittest.mock import patch

        from tests.conftest import make_mock_client

        with patch("orca_cli.core.client.OrcaClient") as mock_cls:
            mock_cls.return_value = make_mock_client()
            result = invoke(["auth", "check", "--all"])

        assert result.exit_code == 0
        assert "prod" in result.output
        # "staging" may be truncated by Rich in narrow terminals; check username instead
        assert "stage-user" in result.output

    def test_check_incomplete_profile_skipped(self, invoke, config_dir, monkeypatch):
        incomplete = {
            "auth_url": "https://ks:5000",
            "username": "u",
            # missing password, domain, project
        }
        save_profile("broken", incomplete)
        set_active_profile("broken")

        result = invoke(["auth", "check"])
        assert result.exit_code == 0
        assert "SKIP" in result.output

    def test_check_auth_failure(self, invoke, config_dir, sample_profile, monkeypatch):
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        from unittest.mock import patch

        from orca_cli.core.exceptions import AuthenticationError

        with patch("orca_cli.core.client.OrcaClient") as mock_cls:
            mock_cls.side_effect = AuthenticationError("bad creds")
            result = invoke(["auth", "check"])

        assert result.exit_code == 0
        assert "FAIL" in result.output

    def test_check_shows_roles_in_details(self, invoke, config_dir, sample_profile, monkeypatch):
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        from unittest.mock import patch

        from tests.conftest import make_mock_client

        with patch("orca_cli.core.client.OrcaClient") as mock_cls:
            mock_cls.return_value = make_mock_client()
            result = invoke(["auth", "check"])

        assert "roles:" in result.output
        assert "admin" in result.output
        assert "member" in result.output

    def test_check_shows_token_hours(self, invoke, config_dir, sample_profile, monkeypatch):
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        from unittest.mock import patch

        from tests.conftest import make_mock_client

        with patch("orca_cli.core.client.OrcaClient") as mock_cls:
            mock_cls.return_value = make_mock_client()
            result = invoke(["auth", "check"])

        # Token expires in 2099, should show remaining hours
        assert "token:" in result.output
        assert "h" in result.output

    def test_check_mixed_profiles(self, invoke, config_dir, sample_profile, monkeypatch):
        """One OK, one incomplete → both appear in output."""
        save_profile("good", sample_profile)
        save_profile("bad", {"auth_url": "https://ks:5000", "username": "u"})
        set_active_profile("good")

        from unittest.mock import patch

        from tests.conftest import make_mock_client

        with patch("orca_cli.core.client.OrcaClient") as mock_cls:
            mock_cls.return_value = make_mock_client()
            result = invoke(["auth", "check", "--all"])

        assert result.exit_code == 0
        assert "OK" in result.output
        assert "SKIP" in result.output

    def test_check_all_fail(self, invoke, config_dir, sample_profile, monkeypatch):
        """All profiles fail auth."""
        save_profile("p1", sample_profile)
        save_profile("p2", {**sample_profile, "username": "other"})
        set_active_profile("p1")

        from unittest.mock import patch

        from orca_cli.core.exceptions import AuthenticationError

        with patch("orca_cli.core.client.OrcaClient") as mock_cls:
            mock_cls.side_effect = AuthenticationError("nope")
            result = invoke(["auth", "check", "--all"])

        assert result.exit_code == 0
        assert result.output.count("FAIL") >= 2

    def test_check_clouds_flag_no_clouds_yaml(self, invoke, config_dir, sample_profile, monkeypatch):
        """--clouds with no clouds.yaml found → only orca profiles checked."""
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        from unittest.mock import patch

        from tests.conftest import make_mock_client

        with patch("orca_cli.core.client.OrcaClient") as mock_cls:
            mock_cls.return_value = make_mock_client()
            # Ensure no clouds.yaml is found
            with patch("orca_cli.commands.auth._find_clouds_yaml", return_value=None):
                result = invoke(["auth", "check", "--clouds"])

        assert result.exit_code == 0
        assert "OK" in result.output

    def test_check_clouds_flag_with_clouds_yaml(self, invoke, config_dir, sample_profile,
                                                  clouds_yaml, monkeypatch):
        """--clouds includes entries from clouds.yaml."""
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        path = clouds_yaml({
            "clouds": {
                "mycloud": {
                    "auth": {
                        "auth_url": "https://cloud-ks:5000",
                        "username": "cloud-user",
                        "password": "cloud-pass",
                        "user_domain_name": "Default",
                        "project_name": "cloud-proj",
                    }
                }
            }
        })

        from unittest.mock import patch

        from tests.conftest import make_mock_client

        with patch("orca_cli.core.client.OrcaClient") as mock_cls:
            mock_cls.return_value = make_mock_client()
            with patch("orca_cli.commands.auth._find_clouds_yaml", return_value=path):
                with patch("orca_cli.commands.auth._load_clouds_yaml") as mock_load:
                    mock_load.return_value = {
                        "auth_url": "https://cloud-ks:5000",
                        "username": "cloud-user",
                        "password": "cloud-pass",
                        "user_domain_name": "Default",
                        "project_name": "cloud-proj",
                    }
                    result = invoke(["auth", "check", "--clouds"])

        assert result.exit_code == 0
        # Should see both the orca profile and the cloud entry
        # Rich may truncate "cloud:mycloud" → "cloud:myclo…", check username instead
        assert "cloud-user" in result.output

    def test_check_generic_exception(self, invoke, config_dir, sample_profile, monkeypatch):
        """Non-auth exception (e.g. network error) → FAIL with message."""
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        from unittest.mock import patch

        with patch("orca_cli.core.client.OrcaClient") as mock_cls:
            mock_cls.side_effect = ConnectionError("Connection refused")
            result = invoke(["auth", "check"])

        assert result.exit_code == 0
        assert "FAIL" in result.output
        # Rich may wrap the message across lines; check both words independently
        assert "Connection" in result.output
        assert "refused" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  CLI Help
# ══════════════════════════════════════════════════════════════════════════


class TestCLIHelp:
    """Verify all commands are properly registered and show help."""

    def test_auth_help(self, invoke):
        result = invoke(["auth", "--help"])
        assert result.exit_code == 0
        assert "whoami" in result.output
        assert "token-debug" in result.output
        assert "check" in result.output

    def test_whoami_help(self, invoke):
        result = invoke(["auth", "whoami", "--help"])
        assert result.exit_code == 0
        assert "identity" in result.output.lower() or "user" in result.output.lower()

    def test_token_debug_help(self, invoke):
        result = invoke(["auth", "token-debug", "--help"])
        assert result.exit_code == 0
        assert "--raw" in result.output

    def test_check_help(self, invoke):
        result = invoke(["auth", "check", "--help"])
        assert result.exit_code == 0
        assert "--all" in result.output
        assert "--clouds" in result.output
