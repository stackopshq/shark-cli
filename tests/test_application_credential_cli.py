"""Tests for ``orca application-credential`` CLI subcommands."""

from __future__ import annotations

import yaml

# ══════════════════════════════════════════════════════════════════════════
#  --user resolution: must use real token user id, never the literal "me"
# ══════════════════════════════════════════════════════════════════════════


class TestCurrentUserResolution:
    """Regression: --user default was always falling back to "me", which is
    not a valid Keystone user id. It now reads from the token data."""

    def test_list_uses_token_user_id_when_user_flag_omitted(
        self, invoke, mock_client, write_config, sample_profile
    ):
        write_config({"active_profile": "p", "profiles": {"p": sample_profile}})
        mock_client.get.return_value = {"application_credentials": []}

        result = invoke(["application-credential", "list", "-f", "json"])
        assert result.exit_code == 0, result.output

        url = mock_client.get.call_args[0][0]
        # Should use the FAKE_TOKEN_DATA user id, NOT the literal "me".
        assert "/v3/users/user-uuid-1234/application_credentials" in url
        assert "/users/me/" not in url

    def test_list_explicit_user_overrides_token(
        self, invoke, mock_client, write_config, sample_profile
    ):
        write_config({"active_profile": "p", "profiles": {"p": sample_profile}})
        mock_client.get.return_value = {"application_credentials": []}

        result = invoke([
            "application-credential", "list", "--user", "other-uid", "-f", "json"
        ])
        assert result.exit_code == 0, result.output
        url = mock_client.get.call_args[0][0]
        assert "/v3/users/other-uid/application_credentials" in url

    def test_show_uses_token_user_id(
        self, invoke, mock_client, write_config, sample_profile
    ):
        write_config({"active_profile": "p", "profiles": {"p": sample_profile}})
        mock_client.get.return_value = {"application_credential": {
            "id": "ac-1", "name": "demo", "project_id": "pid",
        }}
        result = invoke(["application-credential", "show", "ac-1", "-f", "json"])
        assert result.exit_code == 0, result.output
        url = mock_client.get.call_args[0][0]
        assert "/v3/users/user-uuid-1234/application_credentials/ac-1" in url

    def test_delete_uses_token_user_id(
        self, invoke, mock_client, write_config, sample_profile
    ):
        write_config({"active_profile": "p", "profiles": {"p": sample_profile}})
        mock_client.delete.return_value = None
        result = invoke([
            "application-credential", "delete", "ac-1", "-y",
        ])
        assert result.exit_code == 0, result.output
        url = mock_client.delete.call_args[0][0]
        assert "/v3/users/user-uuid-1234/application_credentials/ac-1" in url

    def test_no_user_id_in_token_raises_with_guidance(
        self, invoke, mock_client, write_config, sample_profile
    ):
        """If the token genuinely has no user, surface a clean error pointing
        at --user instead of silently sending an invalid 'me' to Keystone."""
        write_config({"active_profile": "p", "profiles": {"p": sample_profile}})
        mock_client._token_data = {}  # no "user" key
        mock_client.get.return_value = {"application_credentials": []}

        result = invoke(["application-credential", "list"])
        assert result.exit_code != 0
        assert "current user id" in result.output
        assert "--user" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  create
# ══════════════════════════════════════════════════════════════════════════


class TestCreate:

    def test_basic_create(self, invoke, mock_client, write_config, sample_profile):
        write_config({"active_profile": "p", "profiles": {"p": sample_profile}})
        mock_client.post.return_value = {"application_credential": {
            "id": "ac-new", "name": "ci", "secret": "s3cr3t",
        }}
        result = invoke(["application-credential", "create", "ci"])
        assert result.exit_code == 0, result.output
        url = mock_client.post.call_args[0][0]
        body = mock_client.post.call_args[1]["json"]["application_credential"]
        assert "/v3/users/user-uuid-1234/application_credentials" in url
        assert body == {"name": "ci", "unrestricted": False}
        assert "ac-new" in result.output
        assert "s3cr3t" in result.output

    def test_create_with_options(self, invoke, mock_client, write_config, sample_profile):
        write_config({"active_profile": "p", "profiles": {"p": sample_profile}})
        mock_client.post.return_value = {"application_credential": {
            "id": "ac-new", "name": "ci", "secret": "s3cr3t",
        }}
        result = invoke([
            "application-credential", "create", "ci",
            "--description", "for CI",
            "--secret", "my-own-secret",
            "--expires", "2027-01-01T00:00:00",
            "--unrestricted",
        ])
        assert result.exit_code == 0, result.output
        body = mock_client.post.call_args[1]["json"]["application_credential"]
        assert body["description"] == "for CI"
        assert body["secret"] == "my-own-secret"
        assert body["expires_at"] == "2027-01-01T00:00:00"
        assert body["unrestricted"] is True


# ══════════════════════════════════════════════════════════════════════════
#  --save-profile: chains AC creation into a ready-to-use orca profile
# ══════════════════════════════════════════════════════════════════════════


class TestCreateSaveProfile:

    def test_save_profile_writes_app_cred_profile(
        self, invoke, mock_client, write_config, sample_profile, config_dir
    ):
        write_config({"active_profile": "p", "profiles": {"p": sample_profile}})
        mock_client.post.return_value = {"application_credential": {
            "id": "ac-saved", "name": "ci", "secret": "topsecret",
        }}
        result = invoke([
            "application-credential", "create", "ci",
            "--save-profile", "ci-prof",
        ])
        assert result.exit_code == 0, result.output
        assert "ci-prof" in result.output

        with open(config_dir / "config.yaml") as fh:
            data = yaml.safe_load(fh)
        saved = data["profiles"]["ci-prof"]
        assert saved["auth_type"] == "v3applicationcredential"
        assert saved["application_credential_id"] == "ac-saved"
        assert saved["application_credential_secret"] == "topsecret"
        assert saved["auth_url"] == mock_client._auth_url
        # Must NOT inherit password / project from the current profile —
        # AC profiles are pre-scoped and don't use a password.
        assert "password" not in saved
        assert "project_name" not in saved

    def test_save_profile_carries_region(
        self, invoke, mock_client, write_config, sample_profile, config_dir
    ):
        write_config({"active_profile": "p", "profiles": {"p": sample_profile}})
        mock_client._region_name = "dc3-a"
        mock_client.post.return_value = {"application_credential": {
            "id": "ac-1", "name": "ci", "secret": "s",
        }}
        result = invoke([
            "application-credential", "create", "ci",
            "--save-profile", "regional",
        ])
        assert result.exit_code == 0, result.output
        with open(config_dir / "config.yaml") as fh:
            data = yaml.safe_load(fh)
        assert data["profiles"]["regional"]["region_name"] == "dc3-a"

    def test_save_profile_without_secret_fails_clean(
        self, invoke, mock_client, write_config, sample_profile
    ):
        """If Keystone doesn't return a secret (shouldn't happen on create,
        but defensive), refuse to write a useless profile."""
        write_config({"active_profile": "p", "profiles": {"p": sample_profile}})
        mock_client.post.return_value = {"application_credential": {
            "id": "ac-1", "name": "ci",  # secret missing
        }}
        result = invoke([
            "application-credential", "create", "ci",
            "--save-profile", "broken",
        ])
        assert result.exit_code != 0
        assert "secret" in result.output.lower()


# ══════════════════════════════════════════════════════════════════════════
#  list / show / delete smoke tests
# ══════════════════════════════════════════════════════════════════════════


class TestListShowDelete:

    def test_list_renders(self, invoke, mock_client, write_config, sample_profile):
        write_config({"active_profile": "p", "profiles": {"p": sample_profile}})
        mock_client.get.return_value = {"application_credentials": [
            {"id": "ac-1", "name": "demo", "expires_at": None, "unrestricted": False},
        ]}
        result = invoke(["application-credential", "list", "-f", "json"])
        assert result.exit_code == 0, result.output
        assert "ac-1" in result.output
        assert "demo" in result.output

    def test_show_renders(self, invoke, mock_client, write_config, sample_profile):
        write_config({"active_profile": "p", "profiles": {"p": sample_profile}})
        mock_client.get.return_value = {"application_credential": {
            "id": "ac-1", "name": "demo", "project_id": "pid",
            "expires_at": None, "unrestricted": False, "description": "x",
        }}
        result = invoke(["application-credential", "show", "ac-1", "-f", "json"])
        assert result.exit_code == 0, result.output
        assert "ac-1" in result.output

    def test_delete_requires_confirmation(
        self, invoke, mock_client, write_config, sample_profile
    ):
        write_config({"active_profile": "p", "profiles": {"p": sample_profile}})
        result = invoke(
            ["application-credential", "delete", "ac-1"],
            input="n\n",
        )
        assert result.exit_code != 0  # aborted
        mock_client.delete.assert_not_called()
