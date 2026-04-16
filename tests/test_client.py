"""Tests for orca_cli.core.client — OrcaClient init, auth payload, endpoints."""

from __future__ import annotations

import stat
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest
import yaml

from orca_cli.core.client import OrcaClient, TOKEN_EXPIRY_BUFFER, TOKEN_CACHE_PATH
from orca_cli.core.exceptions import AuthenticationError, APIError


@pytest.fixture(autouse=True)
def _no_real_cache(tmp_path):
    """Redirect TOKEN_CACHE_PATH to a temp dir for every test in this module."""
    with patch("orca_cli.core.client.TOKEN_CACHE_PATH", tmp_path / "token_cache.yaml"):
        yield


FAKE_CATALOG = [
    {
        "type": "compute",
        "name": "nova",
        "endpoints": [
            {"interface": "public", "url": "https://nova.example.com/v2.1", "region_id": "RegionOne"},
            {"interface": "internal", "url": "https://nova-int.example.com/v2.1", "region_id": "RegionOne"},
        ],
    },
    {
        "type": "network",
        "name": "neutron",
        "endpoints": [
            {"interface": "public", "url": "https://neutron.example.com", "region_id": "RegionOne"},
            {"interface": "public", "url": "https://neutron-r2.example.com", "region_id": "RegionTwo"},
        ],
    },
]

FAKE_TOKEN_RESPONSE = {
    "token": {
        "methods": ["password"],
        "user": {"id": "uid", "name": "admin", "domain": {"id": "did", "name": "Default"}},
        "project": {"id": "pid", "name": "demo", "domain": {"id": "did", "name": "Default"}},
        "roles": [{"id": "r1", "name": "admin"}],
        "catalog": FAKE_CATALOG,
        "expires_at": "2099-12-31T23:59:59Z",
        "issued_at": "2099-12-31T22:00:00Z",
    }
}


def _make_auth_response(status_code=201, token="fake-token"):
    """Build a mock httpx response for Keystone auth."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.is_success = 200 <= status_code < 300
    resp.headers = {"X-Subject-Token": token}
    resp.json.return_value = FAKE_TOKEN_RESPONSE
    resp.text = ""
    return resp


class TestOrcaClientInit:

    @patch("orca_cli.core.client.httpx.Client")
    def test_name_based_auth(self, mock_httpx_cls):
        """Config with user_domain_name + project_name → auth uses names."""
        http = MagicMock()
        http.post.return_value = _make_auth_response()
        mock_httpx_cls.return_value = http

        cfg = {
            "auth_url": "https://ks:5000",
            "username": "admin",
            "password": "secret",
            "user_domain_name": "Default",
            "project_name": "demo",
        }
        client = OrcaClient(cfg)

        call_args = http.post.call_args
        payload = call_args.kwargs["json"]
        user = payload["auth"]["identity"]["password"]["user"]
        assert user["name"] == "admin"
        assert user["domain"] == {"name": "Default"}

        scope = payload["auth"]["scope"]["project"]
        assert scope["name"] == "demo"
        assert "id" not in scope

    @patch("orca_cli.core.client.httpx.Client")
    def test_id_based_auth(self, mock_httpx_cls):
        """Config with user_domain_id + project_id → auth uses IDs."""
        http = MagicMock()
        http.post.return_value = _make_auth_response()
        mock_httpx_cls.return_value = http

        cfg = {
            "auth_url": "https://ks:5000",
            "username": "admin",
            "password": "secret",
            "user_domain_id": "domain-uuid",
            "project_id": "project-uuid",
        }
        client = OrcaClient(cfg)

        call_args = http.post.call_args
        payload = call_args.kwargs["json"]
        user = payload["auth"]["identity"]["password"]["user"]
        assert user["domain"] == {"id": "domain-uuid"}

        scope = payload["auth"]["scope"]["project"]
        assert scope == {"id": "project-uuid"}

    @patch("orca_cli.core.client.httpx.Client")
    def test_auth_failure_raises(self, mock_httpx_cls):
        http = MagicMock()
        http.post.return_value = _make_auth_response(status_code=401)
        mock_httpx_cls.return_value = http

        cfg = {
            "auth_url": "https://ks:5000",
            "username": "admin",
            "password": "wrong",
            "user_domain_name": "Default",
            "project_name": "demo",
        }
        with pytest.raises(AuthenticationError):
            OrcaClient(cfg)

    @patch("orca_cli.core.client.httpx.Client")
    def test_token_stored(self, mock_httpx_cls):
        http = MagicMock()
        http.post.return_value = _make_auth_response(token="my-token-123")
        mock_httpx_cls.return_value = http

        cfg = {
            "auth_url": "https://ks:5000",
            "username": "admin",
            "password": "secret",
            "user_domain_name": "Default",
            "project_name": "demo",
        }
        client = OrcaClient(cfg)
        assert client._token == "my-token-123"
        assert client._token_data["user"]["name"] == "admin"

    @patch("orca_cli.core.client.httpx.Client")
    def test_insecure_disables_verify(self, mock_httpx_cls):
        http = MagicMock()
        http.post.return_value = _make_auth_response()
        mock_httpx_cls.return_value = http

        cfg = {
            "auth_url": "https://ks:5000",
            "username": "admin",
            "password": "secret",
            "user_domain_name": "Default",
            "project_name": "demo",
            "insecure": "true",
        }
        OrcaClient(cfg)
        # httpx.Client should be called with verify=False
        call_kwargs = mock_httpx_cls.call_args.kwargs
        assert call_kwargs["verify"] is False

    @patch("orca_cli.core.client.httpx.Client")
    def test_cacert_passed_to_verify(self, mock_httpx_cls):
        http = MagicMock()
        http.post.return_value = _make_auth_response()
        mock_httpx_cls.return_value = http

        cfg = {
            "auth_url": "https://ks:5000",
            "username": "admin",
            "password": "secret",
            "user_domain_name": "Default",
            "project_name": "demo",
            "cacert": "/path/to/ca.pem",
        }
        OrcaClient(cfg)
        call_kwargs = mock_httpx_cls.call_args.kwargs
        assert call_kwargs["verify"] == "/path/to/ca.pem"


class TestEndpointResolution:

    @patch("orca_cli.core.client.httpx.Client")
    def _make_client(self, mock_httpx_cls, interface="public", region=None):
        http = MagicMock()
        http.post.return_value = _make_auth_response()
        mock_httpx_cls.return_value = http

        cfg = {
            "auth_url": "https://ks:5000",
            "username": "admin",
            "password": "secret",
            "user_domain_name": "Default",
            "project_name": "demo",
            "interface": interface,
        }
        if region:
            cfg["region_name"] = region
        return OrcaClient(cfg)

    def test_public_endpoint(self):
        client = self._make_client(interface="public")
        assert client.compute_url == "https://nova.example.com/v2.1"

    def test_internal_endpoint(self):
        client = self._make_client(interface="internal")
        assert client.compute_url == "https://nova-int.example.com/v2.1"

    def test_region_filter(self):
        client = self._make_client(interface="public", region="RegionTwo")
        assert client.network_url == "https://neutron-r2.example.com"

    def test_missing_service_raises(self):
        client = self._make_client()
        with pytest.raises(APIError, match="object-store.*not found"):
            client.object_store_url

    def test_domain_ref_name(self):
        assert OrcaClient._domain_ref("Default", None) == {"name": "Default"}

    def test_domain_ref_id(self):
        assert OrcaClient._domain_ref(None, "uuid-123") == {"id": "uuid-123"}

    def test_domain_ref_fallback(self):
        assert OrcaClient._domain_ref(None, None) == {"name": "Default"}


# ── Token caching ─────────────────────────────────────────────────────────────

BASE_CFG = {
    "auth_url": "https://ks:5000",
    "username": "admin",
    "password": "secret",
    "user_domain_name": "Default",
    "project_name": "demo",
}

FUTURE_EXPIRY = (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat()
PAST_EXPIRY = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
NEAR_EXPIRY = (datetime.now(timezone.utc) + timedelta(seconds=TOKEN_EXPIRY_BUFFER - 1)).isoformat()


def _make_client_with_http(mock_httpx_cls, cfg=None, token="tok"):
    http = MagicMock()
    http.post.return_value = _make_auth_response(token=token)
    mock_httpx_cls.return_value = http
    client = OrcaClient(cfg or BASE_CFG)
    return client, http


class TestTokenCaching:
    """Disk-based token cache: write on auth, read on next init, invalidate on expiry/401."""

    def setup_method(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._cache_path = Path(self._tmp.name) / "token_cache.yaml"

    def teardown_method(self):
        self._tmp.cleanup()

    def _patch_cache_path(self):
        return patch("orca_cli.core.client.TOKEN_CACHE_PATH", self._cache_path)

    @patch("orca_cli.core.client.httpx.Client")
    def test_auth_writes_cache(self, mock_httpx_cls):
        """After a fresh authentication the cache file is written."""
        with self._patch_cache_path():
            client, _ = _make_client_with_http(mock_httpx_cls, token="fresh-token")

        assert self._cache_path.exists()
        data = yaml.safe_load(self._cache_path.read_text())
        assert data["token"] == "fresh-token"
        assert data["cache_key"] == client._cache_key

    @patch("orca_cli.core.client.httpx.Client")
    def test_cache_file_permissions(self, mock_httpx_cls):
        """Cache file must be mode 0600."""
        with self._patch_cache_path():
            _make_client_with_http(mock_httpx_cls)

        mode = self._cache_path.stat().st_mode & 0o777
        assert mode == 0o600

    @patch("orca_cli.core.client.httpx.Client")
    def test_valid_cache_skips_auth(self, mock_httpx_cls):
        """A valid cached token is loaded without calling Keystone."""
        http = MagicMock()
        mock_httpx_cls.return_value = http

        # Pre-write a valid cache
        import hashlib
        parts = "|".join(["https://ks:5000", "admin", "Default", "demo", ""])
        cache_key = hashlib.sha256(parts.encode()).hexdigest()
        cache_data = {
            "cache_key": cache_key,
            "token": "cached-token",
            "expires_at": FUTURE_EXPIRY,
            "catalog": FAKE_CATALOG,
            "token_data": FAKE_TOKEN_RESPONSE["token"],
        }
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._cache_path.write_text(yaml.dump(cache_data))

        with self._patch_cache_path():
            client = OrcaClient(BASE_CFG)

        # Keystone should NOT have been called
        http.post.assert_not_called()
        assert client._token == "cached-token"
        assert client._token_from_cache is True

    @patch("orca_cli.core.client.httpx.Client")
    def test_expired_cache_triggers_auth(self, mock_httpx_cls):
        """An expired cached token causes re-authentication."""
        http = MagicMock()
        http.post.return_value = _make_auth_response(token="new-token")
        mock_httpx_cls.return_value = http

        import hashlib
        parts = "|".join(["https://ks:5000", "admin", "Default", "demo", ""])
        cache_key = hashlib.sha256(parts.encode()).hexdigest()
        cache_data = {
            "cache_key": cache_key,
            "token": "old-token",
            "expires_at": PAST_EXPIRY,
            "catalog": FAKE_CATALOG,
            "token_data": FAKE_TOKEN_RESPONSE["token"],
        }
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._cache_path.write_text(yaml.dump(cache_data))

        with self._patch_cache_path():
            client = OrcaClient(BASE_CFG)

        http.post.assert_called_once()
        assert client._token == "new-token"
        assert client._token_from_cache is False

    @patch("orca_cli.core.client.httpx.Client")
    def test_near_expiry_cache_triggers_auth(self, mock_httpx_cls):
        """A token expiring within TOKEN_EXPIRY_BUFFER seconds is treated as expired."""
        http = MagicMock()
        http.post.return_value = _make_auth_response(token="refreshed-token")
        mock_httpx_cls.return_value = http

        import hashlib
        parts = "|".join(["https://ks:5000", "admin", "Default", "demo", ""])
        cache_key = hashlib.sha256(parts.encode()).hexdigest()
        cache_data = {
            "cache_key": cache_key,
            "token": "near-expiry-token",
            "expires_at": NEAR_EXPIRY,
            "catalog": FAKE_CATALOG,
            "token_data": FAKE_TOKEN_RESPONSE["token"],
        }
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._cache_path.write_text(yaml.dump(cache_data))

        with self._patch_cache_path():
            client = OrcaClient(BASE_CFG)

        http.post.assert_called_once()

    @patch("orca_cli.core.client.httpx.Client")
    def test_different_profile_skips_cache(self, mock_httpx_cls):
        """A cache from a different cluster/project is ignored."""
        http = MagicMock()
        http.post.return_value = _make_auth_response(token="new-token")
        mock_httpx_cls.return_value = http

        # Write a cache with a different (wrong) cache key
        cache_data = {
            "cache_key": "totally-wrong-key",
            "token": "other-token",
            "expires_at": FUTURE_EXPIRY,
            "catalog": FAKE_CATALOG,
            "token_data": FAKE_TOKEN_RESPONSE["token"],
        }
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._cache_path.write_text(yaml.dump(cache_data))

        with self._patch_cache_path():
            client = OrcaClient(BASE_CFG)

        # Should have re-authenticated
        http.post.assert_called_once()
        assert client._token == "new-token"

    @patch("orca_cli.core.client.httpx.Client")
    def test_cache_key_differs_by_region(self, mock_httpx_cls):
        """Two clients with different regions produce different cache keys."""
        http = MagicMock()
        http.post.return_value = _make_auth_response()
        mock_httpx_cls.return_value = http

        cfg_r1 = {**BASE_CFG, "region_name": "RegionOne"}
        cfg_r2 = {**BASE_CFG, "region_name": "RegionTwo"}

        with self._patch_cache_path():
            c1 = OrcaClient(cfg_r1)
        with self._patch_cache_path():
            c2 = OrcaClient(cfg_r2)

        assert c1._cache_key != c2._cache_key

    @patch("orca_cli.core.client.httpx.Client")
    def test_cache_key_differs_by_project(self, mock_httpx_cls):
        """Two clients scoped to different projects produce different cache keys."""
        http = MagicMock()
        http.post.return_value = _make_auth_response()
        mock_httpx_cls.return_value = http

        cfg_a = {**BASE_CFG, "project_name": "project-a"}
        cfg_b = {**BASE_CFG, "project_name": "project-b"}

        with self._patch_cache_path():
            ca = OrcaClient(cfg_a)
        with self._patch_cache_path():
            cb = OrcaClient(cfg_b)

        assert ca._cache_key != cb._cache_key


class TestRequestRetryOn401:
    """_request() clears cache and re-auths transparently on 401 with cached token."""

    def setup_method(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._cache_path = Path(self._tmp.name) / "token_cache.yaml"

    def teardown_method(self):
        self._tmp.cleanup()

    def _patch_cache_path(self):
        return patch("orca_cli.core.client.TOKEN_CACHE_PATH", self._cache_path)

    def _write_valid_cache(self, token="cached-tok"):
        import hashlib
        parts = "|".join(["https://ks:5000", "admin", "Default", "demo", ""])
        cache_key = hashlib.sha256(parts.encode()).hexdigest()
        data = {
            "cache_key": cache_key,
            "token": token,
            "expires_at": FUTURE_EXPIRY,
            "catalog": FAKE_CATALOG,
            "token_data": FAKE_TOKEN_RESPONSE["token"],
        }
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._cache_path.write_text(yaml.dump(data))

    @patch("orca_cli.core.client.httpx.Client")
    def test_cached_token_401_retries_with_fresh_token(self, mock_httpx_cls):
        """When cached token gets 401, re-auth and retry succeed."""
        self._write_valid_cache(token="stale-token")

        http = MagicMock()
        mock_httpx_cls.return_value = http

        # First GET returns 401, second returns 200
        ok_resp = MagicMock()
        ok_resp.status_code = 200
        ok_resp.is_success = True
        ok_resp.content = b'{"servers": []}'
        ok_resp.json.return_value = {"servers": []}

        unauthorized = MagicMock()
        unauthorized.status_code = 401
        unauthorized.is_success = False

        fresh_auth = _make_auth_response(token="fresh-token")
        http.post.return_value = fresh_auth
        http.get.side_effect = [unauthorized, ok_resp]

        with self._patch_cache_path():
            client = OrcaClient(BASE_CFG)

        assert client._token_from_cache is True
        assert client._token == "stale-token"

        result = client.get("https://nova.example.com/servers")

        assert result == {"servers": []}
        # Should have re-authenticated once
        http.post.assert_called_once()
        assert client._token == "fresh-token"
        assert client._token_from_cache is False

    @patch("orca_cli.core.client.httpx.Client")
    def test_non_cached_401_does_not_retry(self, mock_httpx_cls):
        """When a fresh token gets 401, no retry occurs — raises AuthenticationError."""
        http = MagicMock()
        http.post.return_value = _make_auth_response(token="live-token")
        mock_httpx_cls.return_value = http

        unauthorized = MagicMock()
        unauthorized.status_code = 401
        unauthorized.is_success = False
        http.get.return_value = unauthorized

        with self._patch_cache_path():
            client = OrcaClient(BASE_CFG)

        assert client._token_from_cache is False

        with pytest.raises(AuthenticationError):
            client.get("https://nova.example.com/servers")

        # Should NOT have re-authenticated (no second post)
        http.post.assert_called_once()

    @patch("orca_cli.core.client.httpx.Client")
    def test_cache_cleared_on_401(self, mock_httpx_cls):
        """After a 401 on a cached token, the cache file is removed."""
        self._write_valid_cache(token="stale-token")
        assert self._cache_path.exists()

        http = MagicMock()
        mock_httpx_cls.return_value = http

        ok_resp = MagicMock()
        ok_resp.status_code = 200
        ok_resp.is_success = True
        ok_resp.content = b"{}"
        ok_resp.json.return_value = {}

        unauthorized = MagicMock()
        unauthorized.status_code = 401
        unauthorized.is_success = False

        http.post.return_value = _make_auth_response(token="new-token")
        http.get.side_effect = [unauthorized, ok_resp]

        with self._patch_cache_path():
            client = OrcaClient(BASE_CFG)
            client.get("https://nova.example.com/servers")
            # After retry, a new cache should have been written
            assert self._cache_path.exists()

        new_data = yaml.safe_load(self._cache_path.read_text())
        assert new_data["token"] == "new-token"
