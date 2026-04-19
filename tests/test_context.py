"""Tests for OrcaContext — the per-invocation bag attached to click.Context.obj.

Covers lazy client construction, profile/region propagation, and the
end-to-end path for the global ``--region`` flag.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from orca_cli.core.context import OrcaContext
from orca_cli.core.exceptions import OrcaCLIError

# ── Unit: OrcaContext.ensure_client ──────────────────────────────────────────

class TestOrcaContextEnsureClient:

    def test_raises_when_config_incomplete(self, monkeypatch):
        """Missing auth_url/username/password → clear OrcaCLIError pointing at setup."""
        monkeypatch.setattr(
            "orca_cli.core.context.load_config",
            lambda profile_name=None: {},
        )
        monkeypatch.setattr(
            "orca_cli.core.context.config_is_complete",
            lambda cfg: False,
        )
        ctx = OrcaContext()
        with pytest.raises(OrcaCLIError, match="orca setup"):
            ctx.ensure_client()

    def test_profile_is_passed_to_load_config(self, monkeypatch):
        """ctx.profile must flow through to load_config(profile_name=...)."""
        received = {}

        def fake_load(profile_name=None):
            received["profile"] = profile_name
            return {
                "auth_url": "https://ks:5000",
                "username": "u",
                "password": "p",
                "user_domain_name": "Default",
                "project_name": "demo",
            }

        monkeypatch.setattr("orca_cli.core.context.load_config", fake_load)
        monkeypatch.setattr("orca_cli.core.context.config_is_complete", lambda c: True)

        made = {}

        def fake_client(cfg):
            made["cfg"] = cfg
            return MagicMock()

        monkeypatch.setattr("orca_cli.core.context.OrcaClient", fake_client)

        ctx = OrcaContext()
        ctx.profile = "prod"
        ctx.ensure_client()

        assert received["profile"] == "prod"

    def test_region_override_is_applied_to_config(self, monkeypatch):
        """ctx.region overrides config['region_name'] before the client is built."""
        base_cfg = {
            "auth_url": "https://ks:5000",
            "username": "u",
            "password": "p",
            "user_domain_name": "Default",
            "project_name": "demo",
            "region_name": "RegionOne",  # should be replaced
        }
        monkeypatch.setattr("orca_cli.core.context.load_config", lambda profile_name=None: dict(base_cfg))
        monkeypatch.setattr("orca_cli.core.context.config_is_complete", lambda c: True)

        captured = {}

        def fake_client(cfg):
            captured["cfg"] = cfg
            return MagicMock()

        monkeypatch.setattr("orca_cli.core.context.OrcaClient", fake_client)

        ctx = OrcaContext()
        ctx.region = "RegionTwo"
        ctx.ensure_client()

        assert captured["cfg"]["region_name"] == "RegionTwo"

    def test_client_is_cached_across_calls(self, monkeypatch):
        """Second ensure_client() returns the same instance (no re-auth)."""
        monkeypatch.setattr("orca_cli.core.context.load_config", lambda profile_name=None: {
            "auth_url": "x", "username": "u", "password": "p",
            "user_domain_name": "Default", "project_name": "demo",
        })
        monkeypatch.setattr("orca_cli.core.context.config_is_complete", lambda c: True)

        calls = {"n": 0}

        def fake_client(cfg):
            calls["n"] += 1
            return MagicMock()

        monkeypatch.setattr("orca_cli.core.context.OrcaClient", fake_client)

        ctx = OrcaContext()
        c1 = ctx.ensure_client()
        c2 = ctx.ensure_client()

        assert c1 is c2
        assert calls["n"] == 1


# ── E2E: the global --region flag on the root CLI ───────────────────────────

class TestGlobalRegionFlag:
    """`orca --region X <cmd>` must thread X into the config the client sees."""

    def test_region_flag_reaches_orca_client(self, invoke, monkeypatch, write_config, sample_profile):
        """--region RegionTwo → OrcaClient is built with region_name='RegionTwo'."""
        write_config({"active_profile": "p", "profiles": {"p": sample_profile}})

        captured: dict = {}

        def fake_client_cls(cfg):
            captured["cfg"] = cfg
            client = MagicMock()
            client.get.return_value = {"servers": []}
            client.compute_url = "https://nova.example.com/v2.1"
            return client

        monkeypatch.setattr("orca_cli.core.context.OrcaClient", fake_client_cls)

        result = invoke(["--region", "RegionTwo", "server", "list"])

        assert result.exit_code == 0, result.output
        assert captured["cfg"]["region_name"] == "RegionTwo"

    def test_orca_region_env_var_is_read(self, invoke, monkeypatch, write_config, sample_profile):
        """ORCA_REGION env var is an alias for --region."""
        write_config({"active_profile": "p", "profiles": {"p": sample_profile}})

        captured: dict = {}

        def fake_client_cls(cfg):
            captured["cfg"] = cfg
            client = MagicMock()
            client.get.return_value = {"servers": []}
            client.compute_url = "https://nova.example.com/v2.1"
            return client

        monkeypatch.setattr("orca_cli.core.context.OrcaClient", fake_client_cls)
        monkeypatch.setenv("ORCA_REGION", "RegionThree")

        result = invoke(["server", "list"])

        assert result.exit_code == 0, result.output
        assert captured["cfg"]["region_name"] == "RegionThree"

    def test_no_region_flag_preserves_profile_region(self, invoke, monkeypatch,
                                                     write_config, sample_profile):
        """Without --region, the profile's region_name (if any) is used unchanged."""
        profile = dict(sample_profile, region_name="RegionOne")
        write_config({"active_profile": "p", "profiles": {"p": profile}})

        captured: dict = {}

        def fake_client_cls(cfg):
            captured["cfg"] = cfg
            client = MagicMock()
            client.get.return_value = {"servers": []}
            client.compute_url = "https://nova.example.com/v2.1"
            return client

        monkeypatch.setattr("orca_cli.core.context.OrcaClient", fake_client_cls)

        result = invoke(["server", "list"])

        assert result.exit_code == 0, result.output
        assert captured["cfg"]["region_name"] == "RegionOne"

    def test_region_flag_overrides_profile_region(self, invoke, monkeypatch,
                                                  write_config, sample_profile):
        """--region wins over any region_name stored in the profile."""
        profile = dict(sample_profile, region_name="RegionOne")
        write_config({"active_profile": "p", "profiles": {"p": profile}})

        captured: dict = {}

        def fake_client_cls(cfg):
            captured["cfg"] = cfg
            client = MagicMock()
            client.get.return_value = {"servers": []}
            client.compute_url = "https://nova.example.com/v2.1"
            return client

        monkeypatch.setattr("orca_cli.core.context.OrcaClient", fake_client_cls)

        result = invoke(["--region", "RegionTwo", "server", "list"])

        assert result.exit_code == 0, result.output
        assert captured["cfg"]["region_name"] == "RegionTwo"
