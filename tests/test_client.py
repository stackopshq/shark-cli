"""Tests for orca_cli.core.client — OrcaClient init, auth payload, endpoints."""

from __future__ import annotations

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest
import yaml

from orca_cli.core.client import MAX_RETRIES, TOKEN_EXPIRY_BUFFER, OrcaClient
from orca_cli.core.exceptions import APIError, AuthenticationError, PermissionDeniedError


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
        _ = OrcaClient(cfg)

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
        _ = OrcaClient(cfg)

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
            _ = OrcaClient(BASE_CFG)

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


# ── Transient-error retry ─────────────────────────────────────────────────────

def _resp(status_code: int, body: Any = None) -> MagicMock:
    """Build a mock httpx.Response with the given status code."""
    r = MagicMock()
    r.status_code = status_code
    r.is_success = 200 <= status_code < 300
    r.content = b"" if body is None else str(body).encode()
    r.json.return_value = body if body is not None else {}
    r.text = "" if body is None else str(body)
    return r


class TestRequestRetryOnTransient:
    """_request() retries idempotent methods on 5xx and network errors."""

    @pytest.fixture(autouse=True)
    def _no_sleep(self):
        """Don't actually sleep during retry backoff."""
        with patch("orca_cli.core.client.time.sleep") as sleep_mock:
            yield sleep_mock

    @patch("orca_cli.core.client.httpx.Client")
    def test_get_retries_on_503_then_succeeds(self, mock_httpx_cls, _no_sleep):
        http = MagicMock()
        http.post.return_value = _make_auth_response()
        http.get.side_effect = [_resp(503), _resp(503), _resp(200, {"ok": True})]
        mock_httpx_cls.return_value = http

        client = OrcaClient(BASE_CFG)
        result = client.get("https://nova.example.com/servers")

        assert result == {"ok": True}
        assert http.get.call_count == 3  # initial + 2 retries
        assert _no_sleep.call_count == 2
        # Exponential backoff: 0.5, 1.0
        assert _no_sleep.call_args_list[0].args[0] == 0.5
        assert _no_sleep.call_args_list[1].args[0] == 1.0

    @patch("orca_cli.core.client.httpx.Client")
    def test_retries_exhausted_raises_apierror(self, mock_httpx_cls, _no_sleep):
        http = MagicMock()
        http.post.return_value = _make_auth_response()
        # All three attempts return 502.
        err_body = {"error": "bad gateway"}
        http.get.side_effect = [_resp(502, err_body)] * (MAX_RETRIES + 1)
        mock_httpx_cls.return_value = http

        client = OrcaClient(BASE_CFG)
        with pytest.raises(APIError) as exc_info:
            client.get("https://nova.example.com/servers")

        assert exc_info.value.status_code == 502
        assert http.get.call_count == MAX_RETRIES + 1

    @patch("orca_cli.core.client.httpx.Client")
    def test_post_does_not_retry_on_503(self, mock_httpx_cls, _no_sleep):
        """POST is not idempotent — must fail fast without retry."""
        http = MagicMock()
        http.post.side_effect = [_make_auth_response(), _resp(503, {"error": "x"})]
        mock_httpx_cls.return_value = http

        client = OrcaClient(BASE_CFG)
        with pytest.raises(APIError) as exc_info:
            client.post("https://nova.example.com/servers", json={"x": 1})

        assert exc_info.value.status_code == 503
        # Only the auth POST and the one user POST — no retry
        assert http.post.call_count == 2
        _no_sleep.assert_not_called()

    @patch("orca_cli.core.client.httpx.Client")
    def test_patch_does_not_retry_on_503(self, mock_httpx_cls, _no_sleep):
        """PATCH is not idempotent by convention — no retry."""
        http = MagicMock()
        http.post.return_value = _make_auth_response()
        http.patch.return_value = _resp(503, {"error": "x"})
        mock_httpx_cls.return_value = http

        client = OrcaClient(BASE_CFG)
        with pytest.raises(APIError):
            client.patch("https://nova.example.com/servers/1", json={"x": 1})

        assert http.patch.call_count == 1

    @patch("orca_cli.core.client.httpx.Client")
    def test_delete_retries_on_503(self, mock_httpx_cls, _no_sleep):
        """DELETE is idempotent — retried."""
        http = MagicMock()
        http.post.return_value = _make_auth_response()
        http.delete.side_effect = [_resp(503), _resp(204)]
        mock_httpx_cls.return_value = http

        client = OrcaClient(BASE_CFG)
        result = client.delete("https://nova.example.com/servers/1")

        assert result is None
        assert http.delete.call_count == 2

    @patch("orca_cli.core.client.httpx.Client")
    def test_4xx_not_retried(self, mock_httpx_cls, _no_sleep):
        """404 / 400 / 409 are client errors — never retried."""
        http = MagicMock()
        http.post.return_value = _make_auth_response()
        http.get.return_value = _resp(404, {"error": "not found"})
        mock_httpx_cls.return_value = http

        client = OrcaClient(BASE_CFG)
        with pytest.raises(APIError) as exc_info:
            client.get("https://nova.example.com/servers/missing")

        assert exc_info.value.status_code == 404
        assert http.get.call_count == 1
        _no_sleep.assert_not_called()

    @patch("orca_cli.core.client.httpx.Client")
    def test_connect_error_retries_then_succeeds(self, mock_httpx_cls, _no_sleep):
        http = MagicMock()
        http.post.return_value = _make_auth_response()
        http.get.side_effect = [
            httpx.ConnectError("boom"),
            _resp(200, {"ok": True}),
        ]
        mock_httpx_cls.return_value = http

        client = OrcaClient(BASE_CFG)
        result = client.get("https://nova.example.com/servers")

        assert result == {"ok": True}
        assert http.get.call_count == 2

    @patch("orca_cli.core.client.httpx.Client")
    def test_connect_error_exhausted_raises_apierror_zero(self, mock_httpx_cls, _no_sleep):
        http = MagicMock()
        http.post.return_value = _make_auth_response()
        http.get.side_effect = httpx.ReadTimeout("too slow")
        mock_httpx_cls.return_value = http

        client = OrcaClient(BASE_CFG)
        with pytest.raises(APIError) as exc_info:
            client.get("https://nova.example.com/servers")

        # status_code 0 = sentinel for network-level error
        assert exc_info.value.status_code == 0
        assert "Network error" in str(exc_info.value)
        assert http.get.call_count == MAX_RETRIES + 1

    @patch("orca_cli.core.client.httpx.Client")
    def test_post_network_error_not_retried(self, mock_httpx_cls, _no_sleep):
        """Network errors on POST must fail fast (no retry)."""
        http = MagicMock()
        http.post.side_effect = [
            _make_auth_response(),
            httpx.ConnectError("boom"),
        ]
        mock_httpx_cls.return_value = http

        client = OrcaClient(BASE_CFG)
        with pytest.raises(APIError) as exc_info:
            client.post("https://nova.example.com/servers", json={"x": 1})

        assert exc_info.value.status_code == 0
        # Auth POST + one user POST, no retry
        assert http.post.call_count == 2
        _no_sleep.assert_not_called()


# ── Nova microversion header scoping ─────────────────────────────────────────

class TestNovaMicroversionHeader:
    """The X-OpenStack-Nova-API-Version header must ONLY be sent to Nova."""

    @patch("orca_cli.core.client.httpx.Client")
    def test_header_present_on_compute_call(self, mock_httpx_cls):
        http = MagicMock()
        http.post.return_value = _make_auth_response()
        http.get.return_value = _resp(200, {"servers": []})
        mock_httpx_cls.return_value = http

        client = OrcaClient(BASE_CFG)
        client.get(f"{client.compute_url}/servers")

        headers = http.get.call_args.kwargs["headers"]
        assert headers.get("X-OpenStack-Nova-API-Version") == "2.79"

    @patch("orca_cli.core.client.httpx.Client")
    def test_header_absent_on_neutron_call(self, mock_httpx_cls):
        http = MagicMock()
        http.post.return_value = _make_auth_response()
        http.get.return_value = _resp(200, {"networks": []})
        mock_httpx_cls.return_value = http

        client = OrcaClient(BASE_CFG)
        client.get(f"{client.network_url}/v2.0/networks")

        headers = http.get.call_args.kwargs["headers"]
        assert "X-OpenStack-Nova-API-Version" not in headers

    @patch("orca_cli.core.client.httpx.Client")
    def test_header_absent_on_stream(self, mock_httpx_cls):
        """get_stream() also respects the scoping."""
        http = MagicMock()
        http.post.return_value = _make_auth_response()
        mock_httpx_cls.return_value = http

        client = OrcaClient(BASE_CFG)
        client.get_stream(f"{client.network_url}/v2.0/networks")

        headers = http.stream.call_args.kwargs["headers"]
        assert "X-OpenStack-Nova-API-Version" not in headers


# ── Typed endpoint URL properties ─────────────────────────────────────────────

RICH_CATALOG = [
    {"type": t, "name": t, "endpoints": [
        {"interface": "public", "url": f"https://{t.replace('-', '')}.example.com", "region_id": "RegionOne"},
    ]}
    for t in (
        "compute", "network", "identity", "image", "volumev3",
        "container-infra", "metric", "key-manager", "load-balancer",
        "backup", "object-store", "orchestration", "dns",
        "placement", "alarming",
    )
]

RICH_TOKEN_RESPONSE = {
    "token": {
        "methods": ["password"],
        "user": {"id": "u", "name": "u", "domain": {"id": "d", "name": "d"}},
        "project": {"id": "p", "name": "p", "domain": {"id": "d", "name": "d"}},
        "roles": [{"id": "r", "name": "r"}],
        "catalog": RICH_CATALOG,
        "expires_at": "2099-12-31T23:59:59Z",
        "issued_at": "2099-12-31T22:00:00Z",
    }
}


def _rich_auth_response():
    resp = MagicMock()
    resp.status_code = 201
    resp.is_success = True
    resp.headers = {"X-Subject-Token": "tok"}
    resp.json.return_value = RICH_TOKEN_RESPONSE
    resp.text = ""
    return resp


class TestTypedEndpointURLs:
    """Every typed URL property must resolve via _endpoint_for against the catalogue."""

    @patch("orca_cli.core.client.httpx.Client")
    def test_all_service_urls(self, mock_httpx_cls):
        http = MagicMock()
        http.post.return_value = _rich_auth_response()
        mock_httpx_cls.return_value = http

        client = OrcaClient(BASE_CFG)

        assert client.compute_url == "https://compute.example.com"
        assert client.network_url == "https://network.example.com"
        assert client.identity_url == "https://identity.example.com"
        assert client.image_url == "https://image.example.com"
        assert client.volume_url == "https://volumev3.example.com"
        assert client.container_infra_url == "https://containerinfra.example.com"
        assert client.metric_url == "https://metric.example.com"
        assert client.key_manager_url == "https://keymanager.example.com"
        assert client.load_balancer_url == "https://loadbalancer.example.com"
        assert client.backup_url == "https://backup.example.com"
        assert client.object_store_url == "https://objectstore.example.com"
        assert client.orchestration_url == "https://orchestration.example.com"
        assert client.dns_url == "https://dns.example.com"
        assert client.placement_url == "https://placement.example.com"
        assert client.alarming_url == "https://alarming.example.com"


class TestIsComputeUrlHandlesMissingNova:
    """_is_compute_url() must return False when Nova isn't in the catalog."""

    @patch("orca_cli.core.client.httpx.Client")
    def test_returns_false_without_nova(self, mock_httpx_cls):
        # Catalog without compute service
        catalog_no_nova = [c for c in RICH_CATALOG if c["type"] != "compute"]
        resp = MagicMock()
        resp.status_code = 201
        resp.is_success = True
        resp.headers = {"X-Subject-Token": "tok"}
        resp.json.return_value = {
            "token": {**RICH_TOKEN_RESPONSE["token"], "catalog": catalog_no_nova}
        }
        resp.text = ""
        http = MagicMock()
        http.post.return_value = resp
        http.get.return_value = _resp(200, {"x": 1})
        mock_httpx_cls.return_value = http

        client = OrcaClient(BASE_CFG)
        client.get("https://network.example.com/v2.0/x")

        headers = http.get.call_args.kwargs["headers"]
        assert "X-OpenStack-Nova-API-Version" not in headers


class TestExtractErrorMessage:
    """_extract_error_message unwraps OpenStack's inconsistent error shapes."""

    def test_top_level_message(self):
        assert OrcaClient._extract_error_message({"message": "bad"}) == "bad"

    def test_top_level_error_string(self):
        assert OrcaClient._extract_error_message({"error": "boom"}) == "boom"

    def test_top_level_error_dict_with_message(self):
        body = {"error": {"message": "wrong", "code": 400}}
        assert OrcaClient._extract_error_message(body) == "wrong"

    def test_top_level_error_dict_without_message(self):
        body = {"error": {"code": 400}}
        result = OrcaClient._extract_error_message(body)
        assert "400" in result

    def test_nested_resource_error(self):
        body = {"badRequest": {"message": "invalid param"}}
        assert OrcaClient._extract_error_message(body) == "invalid param"

    def test_unknown_shape_stringified(self):
        body = {"random": "data"}
        result = OrcaClient._extract_error_message(body)
        assert "random" in result


class TestForbiddenAndHtmlResponses:
    """403 must surface as PermissionDeniedError (not AuthenticationError) so users
    aren't told to re-run `orca setup` for a permissions issue. HTML error bodies
    (load-balancer 404 pages) must be replaced by a readable message."""

    @patch("orca_cli.core.client.httpx.Client")
    def test_403_raises_permission_denied_not_auth(self, mock_httpx_cls):
        http = MagicMock()
        http.post.return_value = _make_auth_response()
        forbidden = MagicMock()
        forbidden.status_code = 403
        forbidden.is_success = False
        forbidden.json.return_value = {"forbidden": {"message": "admin role required"}}
        forbidden.headers = {"content-type": "application/json"}
        forbidden.text = ""
        forbidden.content = b"{}"
        http.get.return_value = forbidden
        mock_httpx_cls.return_value = http

        client = OrcaClient(BASE_CFG)
        with pytest.raises(PermissionDeniedError) as exc_info:
            client.get("https://nova.example.com/os-hypervisors")
        assert "Permission denied" in str(exc_info.value)
        assert "admin role required" in str(exc_info.value)

    @patch("orca_cli.core.client.httpx.Client")
    def test_html_error_body_shows_clean_message(self, mock_httpx_cls):
        """Regression: endpoint advertised in catalogue but not exposed returns HTML."""
        http = MagicMock()
        http.post.return_value = _make_auth_response()
        bad = MagicMock()
        bad.status_code = 404
        bad.is_success = False
        bad.headers = {"content-type": "text/html; charset=utf-8"}
        bad.text = "<!DOCTYPE HTML PUBLIC ...><html>404 Not Found</html>"
        bad.content = bad.text.encode()
        bad.json.side_effect = ValueError("not json")
        http.get.side_effect = [bad] * 3
        mock_httpx_cls.return_value = http

        with patch("orca_cli.core.client.time.sleep"):
            client = OrcaClient(BASE_CFG)
            with pytest.raises(APIError) as exc_info:
                client.get("https://nova.example.com/servers")
        msg = str(exc_info.value)
        assert "HTML" in msg
        assert "not actually exposed" in msg
        assert "<!DOCTYPE" not in msg  # raw HTML should NOT leak through

    def test_html_sniffed_without_content_type(self):
        """Even without a Content-Type header, HTML body is detected from prefix."""
        resp = MagicMock()
        resp.headers = {}
        resp.text = "<!doctype html><html>boom</html>"
        assert OrcaClient._is_html_response(resp) is True


class TestHandleResponseNonJson:
    """When the error body isn't JSON, fall back to raw text (truncated)."""

    @patch("orca_cli.core.client.httpx.Client")
    def test_non_json_error_body_uses_text(self, mock_httpx_cls):
        http = MagicMock()
        http.post.return_value = _make_auth_response()
        bad = MagicMock()
        bad.status_code = 500
        bad.is_success = False
        bad.json.side_effect = ValueError("not json")
        bad.text = "Internal Server Error: details here"
        bad.content = b"Internal Server Error: details here"
        http.get.side_effect = [bad] * 3  # exhaust retries
        mock_httpx_cls.return_value = http

        with patch("orca_cli.core.client.time.sleep"):
            client = OrcaClient(BASE_CFG)
            with pytest.raises(APIError) as exc_info:
                client.get("https://nova.example.com/servers")

        assert "Internal" in str(exc_info.value) or "Internal" in exc_info.value.message


class TestPatchWithContent:
    """PATCH with content + content_type takes the content branch."""

    @patch("orca_cli.core.client.httpx.Client")
    def test_patch_with_raw_content(self, mock_httpx_cls):
        http = MagicMock()
        http.post.return_value = _make_auth_response()
        http.patch.return_value = _resp(200, {"ok": True})
        mock_httpx_cls.return_value = http

        client = OrcaClient(BASE_CFG)
        client.patch(
            "https://nova.example.com/servers/1",
            content=b"binary",
            content_type="application/octet-stream",
        )
        kwargs = http.patch.call_args.kwargs
        assert kwargs["content"] == b"binary"
        assert kwargs["headers"]["Content-Type"] == "application/octet-stream"


class TestPutStream:

    @patch("orca_cli.core.client.httpx.Client")
    def test_put_stream_sets_content_type(self, mock_httpx_cls):
        http = MagicMock()
        http.post.return_value = _make_auth_response()
        http.put.return_value = _resp(204)
        mock_httpx_cls.return_value = http

        client = OrcaClient(BASE_CFG)
        client.put_stream(
            "https://glance.example.com/v2/images/x/file",
            stream=iter([b"a", b"b"]),
            content_type="application/octet-stream",
        )
        kwargs = http.put.call_args.kwargs
        assert kwargs["headers"]["Content-Type"] == "application/octet-stream"


class TestClose:

    @patch("orca_cli.core.client.httpx.Client")
    def test_close_delegates_to_http(self, mock_httpx_cls):
        http = MagicMock()
        http.post.return_value = _make_auth_response()
        mock_httpx_cls.return_value = http

        client = OrcaClient(BASE_CFG)
        client.close()
        http.close.assert_called_once()
