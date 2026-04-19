"""Tests for Keystone v3 application-credential auth across the stack:
client payload, config loading, completeness checks, profile import/export."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import yaml

from orca_cli.core.client import OrcaClient
from orca_cli.core.config import (
    _is_app_cred,
    _normalise_clouds_yaml,
    config_is_complete,
    load_config,
)
from orca_cli.core.exceptions import AuthenticationError

# ── Helpers ─────────────────────────────────────────────────────────────

FAKE_CATALOG = [
    {"type": "compute", "name": "nova",
     "endpoints": [{"interface": "public", "url": "https://nova/", "region_id": "RegionOne"}]},
]

FAKE_TOKEN_RESPONSE = {
    "token": {
        "methods": ["application_credential"],
        "user": {"id": "uid", "name": "appcred-user", "domain": {"id": "did", "name": "Default"}},
        "project": {"id": "pid", "name": "demo", "domain": {"id": "did", "name": "Default"}},
        "roles": [{"id": "r1", "name": "member"}],
        "catalog": FAKE_CATALOG,
        "expires_at": "2099-12-31T23:59:59Z",
        "issued_at": "2099-12-31T22:00:00Z",
    }
}


def _auth_response(status=201, token="fake-token"):
    resp = MagicMock()
    resp.status_code = status
    resp.is_success = 200 <= status < 300
    resp.headers = {"X-Subject-Token": token}
    resp.json.return_value = FAKE_TOKEN_RESPONSE
    resp.text = ""
    return resp


@pytest.fixture(autouse=True)
def _no_real_cache(tmp_path):
    """Redirect on-disk token cache to a temp dir."""
    with patch("orca_cli.core.client.TOKEN_CACHE_PATH", tmp_path / "token_cache.yaml"):
        yield


# ── Client: auth payload ────────────────────────────────────────────────

class TestAppCredAuthPayload:

    @patch("orca_cli.core.client.httpx.Client")
    def test_id_based_payload(self, mock_httpx_cls):
        """app cred id+secret → correct payload, no scope, no password."""
        http = MagicMock()
        http.post.return_value = _auth_response()
        mock_httpx_cls.return_value = http

        OrcaClient({
            "auth_url": "https://ks:5000",
            "application_credential_id": "ac-1234",
            "application_credential_secret": "topsecret",
        })

        payload = http.post.call_args.kwargs["json"]
        identity = payload["auth"]["identity"]
        assert identity["methods"] == ["application_credential"]
        assert identity["application_credential"] == {
            "id": "ac-1234",
            "secret": "topsecret",
        }
        # App credentials are pre-scoped — no scope block at all.
        assert "scope" not in payload["auth"]
        # No password should leak in either.
        assert "password" not in identity

    @patch("orca_cli.core.client.httpx.Client")
    def test_name_based_payload(self, mock_httpx_cls):
        """app cred name + username → user reference required."""
        http = MagicMock()
        http.post.return_value = _auth_response()
        mock_httpx_cls.return_value = http

        OrcaClient({
            "auth_url": "https://ks:5000",
            "auth_type": "v3applicationcredential",
            "application_credential_name": "my-cred",
            "application_credential_secret": "topsecret",
            "username": "kevin",
            "user_domain_name": "Default",
        })

        ac = http.post.call_args.kwargs["json"]["auth"]["identity"]["application_credential"]
        assert ac["name"] == "my-cred"
        assert ac["secret"] == "topsecret"
        assert ac["user"] == {"name": "kevin", "domain": {"name": "Default"}}

    @patch("orca_cli.core.client.httpx.Client")
    def test_explicit_auth_type_v3applicationcredential(self, mock_httpx_cls):
        """auth_type='v3applicationcredential' is the canonical OpenStack form."""
        http = MagicMock()
        http.post.return_value = _auth_response()
        mock_httpx_cls.return_value = http

        OrcaClient({
            "auth_url": "https://ks:5000",
            "auth_type": "v3applicationcredential",
            "application_credential_id": "ac-1234",
            "application_credential_secret": "topsecret",
        })
        payload = http.post.call_args.kwargs["json"]
        assert payload["auth"]["identity"]["methods"] == ["application_credential"]

    @patch("orca_cli.core.client.httpx.Client")
    def test_password_auth_type_overrides_implicit_detection(self, mock_httpx_cls):
        """Explicit auth_type=password forces password flow even if app cred
        fields are present (let the server reject the empty password)."""
        http = MagicMock()
        http.post.return_value = _auth_response()
        mock_httpx_cls.return_value = http

        OrcaClient({
            "auth_url": "https://ks:5000",
            "auth_type": "password",
            "username": "admin",
            "password": "secret",
            "user_domain_name": "Default",
            "project_name": "demo",
            # Stray AC field — should be ignored because auth_type is explicit.
            "application_credential_id": "leftover-from-old-profile",
        })
        payload = http.post.call_args.kwargs["json"]
        assert payload["auth"]["identity"]["methods"] == ["password"]

    @patch("orca_cli.core.client.httpx.Client")
    def test_missing_secret_raises(self, mock_httpx_cls):
        http = MagicMock()
        mock_httpx_cls.return_value = http
        with pytest.raises(AuthenticationError, match="secret is missing"):
            OrcaClient({
                "auth_url": "https://ks:5000",
                "application_credential_id": "ac-1234",
                # secret missing
            })

    @patch("orca_cli.core.client.httpx.Client")
    def test_name_without_username_raises(self, mock_httpx_cls):
        """AC by name needs a user reference — the username field."""
        http = MagicMock()
        mock_httpx_cls.return_value = http
        with pytest.raises(AuthenticationError, match="application_credential_name"):
            OrcaClient({
                "auth_url": "https://ks:5000",
                "auth_type": "v3applicationcredential",
                "application_credential_name": "my-cred",
                "application_credential_secret": "topsecret",
                # username missing
            })


# ── Client: cache key isolation ─────────────────────────────────────────

class TestAppCredCacheKey:

    @patch("orca_cli.core.client.httpx.Client")
    def test_app_cred_key_differs_from_password_key(self, mock_httpx_cls):
        """Switching between password and app cred for the same user must
        produce different cache keys (so cached tokens don't cross-pollute)."""
        http = MagicMock()
        http.post.return_value = _auth_response()
        mock_httpx_cls.return_value = http

        password_client = OrcaClient({
            "auth_url": "https://ks:5000",
            "username": "kevin",
            "password": "secret",
            "user_domain_name": "Default",
            "project_name": "demo",
        })
        app_cred_client = OrcaClient({
            "auth_url": "https://ks:5000",
            "application_credential_id": "ac-1234",
            "application_credential_secret": "topsecret",
        })
        assert password_client._cache_key != app_cred_client._cache_key

    @patch("orca_cli.core.client.httpx.Client")
    def test_two_different_app_creds_get_different_keys(self, mock_httpx_cls):
        http = MagicMock()
        http.post.return_value = _auth_response()
        mock_httpx_cls.return_value = http

        c1 = OrcaClient({"auth_url": "https://ks:5000",
                         "application_credential_id": "ac-1",
                         "application_credential_secret": "s"})
        c2 = OrcaClient({"auth_url": "https://ks:5000",
                         "application_credential_id": "ac-2",
                         "application_credential_secret": "s"})
        assert c1._cache_key != c2._cache_key


# ── config.py ───────────────────────────────────────────────────────────

class TestConfigIsComplete:

    def test_app_cred_with_id_is_complete(self):
        cfg = {
            "auth_url": "https://ks:5000",
            "application_credential_id": "ac-1",
            "application_credential_secret": "s",
        }
        assert config_is_complete(cfg) is True

    def test_app_cred_with_name_and_user_is_complete(self):
        cfg = {
            "auth_url": "https://ks:5000",
            "auth_type": "v3applicationcredential",
            "application_credential_name": "my-cred",
            "application_credential_secret": "s",
            "username": "kevin",
        }
        assert config_is_complete(cfg) is True

    def test_app_cred_missing_secret_is_incomplete(self):
        cfg = {
            "auth_url": "https://ks:5000",
            "application_credential_id": "ac-1",
        }
        assert config_is_complete(cfg) is False

    def test_app_cred_name_without_username_is_incomplete(self):
        cfg = {
            "auth_url": "https://ks:5000",
            "auth_type": "v3applicationcredential",
            "application_credential_name": "my-cred",
            "application_credential_secret": "s",
            # username missing
        }
        assert config_is_complete(cfg) is False

    def test_app_cred_does_not_require_project(self):
        """Regression: password flow needs project, app cred does not."""
        cfg = {
            "auth_url": "https://ks:5000",
            "application_credential_id": "ac-1",
            "application_credential_secret": "s",
        }
        assert "project_name" not in cfg
        assert config_is_complete(cfg) is True


class TestIsAppCred:

    def test_explicit_v3applicationcredential(self):
        assert _is_app_cred({"auth_type": "v3applicationcredential"}) is True

    def test_explicit_application_credential(self):
        assert _is_app_cred({"auth_type": "application_credential"}) is True

    def test_implicit_via_id(self):
        assert _is_app_cred({"application_credential_id": "ac"}) is True

    def test_implicit_via_secret(self):
        assert _is_app_cred({"application_credential_secret": "s"}) is True

    def test_password_flow(self):
        assert _is_app_cred({"username": "admin", "password": "x"}) is False


class TestCloudsYamlNormalisation:

    def test_app_cred_in_clouds_yaml(self):
        cloud = {
            "auth_type": "v3applicationcredential",
            "auth": {
                "auth_url": "https://ks:5000",
                "application_credential_id": "ac-1",
                "application_credential_secret": "topsecret",
            },
            "region_name": "RegionOne",
            "interface": "public",
        }
        cfg = _normalise_clouds_yaml(cloud)
        assert cfg["auth_type"] == "v3applicationcredential"
        assert cfg["application_credential_id"] == "ac-1"
        assert cfg["application_credential_secret"] == "topsecret"
        assert cfg["auth_url"] == "https://ks:5000"
        assert cfg["region_name"] == "RegionOne"
        # No password / username / project should be invented.
        assert "password" not in cfg
        assert "project_name" not in cfg


class TestOSEnvVarsLoaded:

    def test_app_cred_env_vars(self, monkeypatch, config_dir):
        monkeypatch.setenv("OS_AUTH_URL", "https://ks:5000")
        monkeypatch.setenv("OS_AUTH_TYPE", "v3applicationcredential")
        monkeypatch.setenv("OS_APPLICATION_CREDENTIAL_ID", "ac-1")
        monkeypatch.setenv("OS_APPLICATION_CREDENTIAL_SECRET", "topsecret")
        cfg = load_config()
        assert cfg["auth_type"] == "v3applicationcredential"
        assert cfg["application_credential_id"] == "ac-1"
        assert cfg["application_credential_secret"] == "topsecret"
        assert config_is_complete(cfg) is True


# ── Profile import/export ───────────────────────────────────────────────

class TestProfileFromClouds:

    def test_imports_app_cred_cloud(self, invoke, config_dir, tmp_path):
        clouds_path = tmp_path / "clouds.yaml"
        clouds_path.write_text(yaml.dump({
            "clouds": {
                "myapp": {
                    "auth_type": "v3applicationcredential",
                    "auth": {
                        "auth_url": "https://ks:5000",
                        "application_credential_id": "ac-1",
                        "application_credential_secret": "topsecret",
                    },
                }
            }
        }))
        result = invoke(["profile", "from-clouds", "myapp", "-f", str(clouds_path)])
        assert result.exit_code == 0, result.output
        # Check the saved profile
        from orca_cli.core.config import get_profile
        cfg = get_profile("myapp")
        assert cfg["auth_type"] == "v3applicationcredential"
        assert cfg["application_credential_id"] == "ac-1"
        assert cfg["application_credential_secret"] == "topsecret"


class TestProfileFromOpenrc:

    def test_imports_app_cred_openrc(self, invoke, config_dir, tmp_path):
        openrc_path = tmp_path / "appcred-openrc.sh"
        openrc_path.write_text(
            "export OS_AUTH_URL=https://ks:5000\n"
            "export OS_AUTH_TYPE=v3applicationcredential\n"
            "export OS_APPLICATION_CREDENTIAL_ID=ac-1\n"
            'export OS_APPLICATION_CREDENTIAL_SECRET="topsecret"\n'
            "export OS_IDENTITY_API_VERSION=3\n"
        )
        result = invoke(["profile", "from-openrc", str(openrc_path), "-n", "appcred-prof"])
        assert result.exit_code == 0, result.output
        from orca_cli.core.config import get_profile
        cfg = get_profile("appcred-prof")
        assert cfg["auth_type"] == "v3applicationcredential"
        assert cfg["application_credential_id"] == "ac-1"
        assert cfg["application_credential_secret"] == "topsecret"


class TestProfileToOpenrc:

    def test_emits_app_cred_env_vars(self, invoke, config_dir, write_config):
        write_config({
            "active_profile": "ap",
            "profiles": {"ap": {
                "auth_url": "https://ks:5000",
                "auth_type": "v3applicationcredential",
                "application_credential_id": "ac-1",
                "application_credential_secret": "topsecret",
            }},
        })
        result = invoke(["profile", "to-openrc", "ap"])
        assert result.exit_code == 0, result.output
        out = result.output
        assert "OS_AUTH_TYPE=v3applicationcredential" in out
        assert "OS_APPLICATION_CREDENTIAL_ID=ac-1" in out
        assert "OS_APPLICATION_CREDENTIAL_SECRET=topsecret" in out
        # Must NOT emit password/project for app cred
        assert "OS_PASSWORD" not in out
        assert "OS_PROJECT_NAME" not in out


class TestProfileToClouds:

    def test_emits_app_cred_section(self, invoke, config_dir, write_config):
        write_config({
            "active_profile": "ap",
            "profiles": {"ap": {
                "auth_url": "https://ks:5000",
                "auth_type": "v3applicationcredential",
                "application_credential_id": "ac-1",
                "application_credential_secret": "topsecret",
            }},
        })
        result = invoke(["profile", "to-clouds", "ap"])
        assert result.exit_code == 0, result.output
        data = yaml.safe_load(result.output)
        cloud = data["clouds"]["ap"]
        assert cloud["auth_type"] == "v3applicationcredential"
        assert cloud["auth"]["application_credential_id"] == "ac-1"
        assert cloud["auth"]["application_credential_secret"] == "topsecret"
        assert "password" not in cloud["auth"]
        assert "project_name" not in cloud["auth"]


class TestRoundTrip:

    def test_clouds_to_profile_to_clouds(self, invoke, config_dir, tmp_path):
        """clouds.yaml → orca profile → clouds.yaml preserves app cred fields."""
        original = tmp_path / "clouds.yaml"
        original.write_text(yaml.dump({
            "clouds": {
                "src": {
                    "auth_type": "v3applicationcredential",
                    "auth": {
                        "auth_url": "https://ks:5000",
                        "application_credential_id": "ac-roundtrip",
                        "application_credential_secret": "rtsecret",
                    },
                    "region_name": "dc3-a",
                }
            }
        }))
        r1 = invoke(["profile", "from-clouds", "src", "-f", str(original)])
        assert r1.exit_code == 0, r1.output
        r2 = invoke(["profile", "to-clouds", "src"])
        assert r2.exit_code == 0, r2.output

        out = yaml.safe_load(r2.output)["clouds"]["src"]
        assert out["auth_type"] == "v3applicationcredential"
        assert out["auth"]["application_credential_id"] == "ac-roundtrip"
        assert out["auth"]["application_credential_secret"] == "rtsecret"
        assert out["region_name"] == "dc3-a"
