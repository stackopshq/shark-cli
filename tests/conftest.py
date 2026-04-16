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
    client._token = "fake-token-abcdef1234567890abcdef1234567890"
    client._token_data = FAKE_TOKEN_DATA.copy()
    client._catalog = FAKE_TOKEN_DATA["catalog"]
    client._auth_url = "https://keystone.example.com:5000"
    client._interface = "public"
    client._region_name = None
    client.compute_url = "https://nova.example.com/v2.1"
    client.network_url = "https://neutron.example.com"
    client.identity_url = "https://keystone.example.com:5000"
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
