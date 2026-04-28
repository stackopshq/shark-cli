"""Shared fixtures for orca tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml
from click.testing import CliRunner

from orca_cli.main import cli


@pytest.fixture
def runner():
    """Click CLI test runner."""
    return CliRunner()

@pytest.fixture
def invoke(runner):
    """Shortcut: runner.invoke bound to the orca CLI group."""
    def _invoke(*args, **kwargs):
        return runner.invoke(cli, *args, catch_exceptions=False, **kwargs)
    return _invoke

# ── Fake config directory ───────────────────────────────────────────────

@pytest.fixture
def config_dir(tmp_path, monkeypatch):
    """Redirect orca config to a temp directory."""
    cfg_dir = tmp_path / ".orca"
    cfg_dir.mkdir()
    monkeypatch.setattr("orca_cli.core.config.CONFIG_DIR", cfg_dir)
    monkeypatch.setattr("orca_cli.core.config.CONFIG_FILE", cfg_dir / "config.yaml")
    return cfg_dir

@pytest.fixture
def sample_profile():
    """A complete orca profile dict (new canonical keys)."""
    return {
        "auth_url": "https://keystone.example.com:5000",
        "username": "admin",
        "password": "secret",
        "user_domain_name": "Default",
        "project_name": "my-project",
        "insecure": "true",
    }

@pytest.fixture
def legacy_profile():
    """A legacy orca profile dict (old domain_id / project_id keys)."""
    return {
        "auth_url": "https://keystone.example.com:5000",
        "username": "admin",
        "password": "secret",
        "domain_id": "Default",
        "project_id": "my-project",
        "insecure": "true",
    }

@pytest.fixture
def write_config(config_dir):
    """Helper to write an orca config.yaml."""
    def _write(data: dict):
        path = config_dir / "config.yaml"
        with open(path, "w") as fh:
            yaml.dump(data, fh)
        return path
    return _write

@pytest.fixture
def clouds_yaml(tmp_path):
    """Write a clouds.yaml and return its path."""
    def _write(data: dict) -> Path:
        path = tmp_path / "clouds.yaml"
        with open(path, "w") as fh:
            yaml.dump(data, fh)
        return path
    return _write

# ── Mock OrcaClient ─────────────────────────────────────────────────────

FAKE_TOKEN_DATA = {
    "methods": ["password"],
    "user": {
        "id": "user-uuid-1234",
        "name": "admin",
        "domain": {"id": "domain-uuid", "name": "Default"},
    },
    "project": {
        "id": "project-uuid-5678",
        "name": "my-project",
        "domain": {"id": "domain-uuid", "name": "Default"},
    },
    "roles": [
        {"id": "role-1", "name": "admin"},
        {"id": "role-2", "name": "member"},
    ],
    "catalog": [
        {
            "type": "compute",
            "name": "nova",
            "endpoints": [
                {"interface": "public", "url": "https://nova.example.com/v2.1", "region_id": "RegionOne"},
            ],
        },
        {
            "type": "identity",
            "name": "keystone",
            "endpoints": [
                {"interface": "public", "url": "https://keystone.example.com:5000", "region_id": "RegionOne"},
            ],
        },
        {
            "type": "network",
            "name": "neutron",
            "endpoints": [
                {"interface": "public", "url": "https://neutron.example.com", "region_id": "RegionOne"},
            ],
        },
    ],
    "expires_at": "2099-12-31T23:59:59Z",
    "issued_at": "2099-12-31T22:59:59Z",
}

def make_mock_client():
    """Build a mock OrcaClient with realistic token data."""
    client = MagicMock()
    # Private fields (kept for legacy tests that still poke them) and the
    # public properties the production code reads.
    fake_token = "fake-token-abcdef1234567890abcdef1234567890"
    fake_token_data = FAKE_TOKEN_DATA.copy()
    client._token = fake_token
    client._token_data = fake_token_data
    client._catalog = FAKE_TOKEN_DATA["catalog"]
    client._auth_url = "https://keystone.example.com:5000"
    client._interface = "public"
    client._region_name = None
    client._project_id = "project-uuid-5678"
    client.token = fake_token
    client.token_data = fake_token_data
    client.catalog = list(FAKE_TOKEN_DATA["catalog"])
    client.auth_url = "https://keystone.example.com:5000"
    client.interface = "public"
    client.region_name = None
    client.project_id = "project-uuid-5678"
    client.authenticate = MagicMock()
    client.compute_url = "https://nova.example.com/v2.1"
    client.network_url = "https://neutron.example.com"
    client.identity_url = "https://keystone.example.com:5000"

    # paginate() on the real client issues one or more GETs and concatenates
    # the pages. Tests rarely simulate multiple pages, so the default mock
    # fetches the first page through whatever `client.get` returns and extracts
    # `key` — matching single-page behaviour of the real helper.
    def _paginate(url, key, *, page_size=1000, params=None, max_items=None):
        merged = dict(params or {})
        merged["limit"] = page_size
        page = client.get(url, params=merged) or {}
        items = page.get(key, []) if isinstance(page, dict) else []
        if max_items is not None:
            return items[:max_items]
        return items
    client.paginate = _paginate

    # Streaming helpers — the real client builds headers from ``_headers()`` and
    # forwards to ``self._http.<verb>``. Tests mock ``_http`` and ``_headers``,
    # so the mock's public streaming helpers must delegate to those for the
    # mocking to behave as before.
    def _put_stream(url, *, content, content_type="application/octet-stream",
                    content_length=None, extra_headers=None):
        headers = dict(client._headers())
        headers["Content-Type"] = content_type
        if content_length is not None:
            headers["Content-Length"] = str(content_length)
        if extra_headers:
            headers.update(extra_headers)
        return client._http.put(url, headers=headers, content=content)
    client.put_stream = _put_stream

    def _post_no_body(url, *, extra_headers=None):
        headers = dict(client._headers())
        if extra_headers:
            headers.update(extra_headers)
        return client._http.post(url, headers=headers)
    client.post_no_body = _post_no_body

    def _post_stream(url, *, content, content_type="application/octet-stream",
                     content_length=None, extra_headers=None):
        headers = dict(client._headers())
        headers["Content-Type"] = content_type
        if content_length is not None:
            headers["Content-Length"] = str(content_length)
        if extra_headers:
            headers.update(extra_headers)
        return client._http.post(url, headers=headers, content=content)
    client.post_stream = _post_stream

    def _head_request(url, *, extra_headers=None):
        headers = dict(client._headers())
        if extra_headers:
            headers.update(extra_headers)
        return client._http.head(url, headers=headers)
    client.head_request = _head_request

    def _get_stream(url, *, extra_headers=None):
        headers = dict(client._headers())
        if extra_headers:
            headers.update(extra_headers)
        return client._http.stream("GET", url, headers=headers)
    client.get_stream = _get_stream

    return client

@pytest.fixture
def mock_client(monkeypatch):
    """Patch OrcaContext.ensure_client to return a mock client."""
    client = make_mock_client()

    def _ensure_client(self):
        self.client = client
        return client

    monkeypatch.setattr("orca_cli.core.context.OrcaContext.ensure_client", _ensure_client)
    return client

@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Remove OS_* and ORCA_* vars to avoid test pollution."""
    for key in list(dict(**__import__("os").environ)):
        if key.startswith("OS_") or key.startswith("ORCA_"):
            monkeypatch.delenv(key, raising=False)
