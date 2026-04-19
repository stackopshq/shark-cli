"""Tests for orca_cli.core.completions — shell completion callbacks."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import click
import pytest

from orca_cli.core import completions


@pytest.fixture
def fake_ctx():
    """A Click context with no --profile set."""
    ctx = MagicMock(spec=click.Context)
    ctx.params = {}
    ctx.parent = None
    return ctx


@pytest.fixture
def fake_ctx_with_profile():
    ctx = MagicMock(spec=click.Context)
    ctx.params = {"profile": "prod"}
    ctx.parent = None
    return ctx


class TestBuildClient:

    def test_walks_parent_for_profile(self):
        """_build_client finds --profile from an ancestor context."""
        parent = MagicMock(spec=click.Context)
        parent.params = {"profile": "staging"}
        parent.parent = None
        child = MagicMock(spec=click.Context)
        child.params = {}
        child.parent = parent

        with patch("orca_cli.core.config.load_config") as load, \
             patch("orca_cli.core.config.config_is_complete", return_value=False):
            load.return_value = {}
            client, profile = completions._build_client(child)

        assert profile == "staging"
        assert client is None

    def test_returns_none_when_config_incomplete(self, fake_ctx):
        with patch("orca_cli.core.config.load_config", return_value={}), \
             patch("orca_cli.core.config.config_is_complete", return_value=False):
            client, profile = completions._build_client(fake_ctx)
        assert client is None

    def test_swallows_exceptions(self, fake_ctx):
        """Imports or load failures must return (None, None) — never crash the shell."""
        with patch("orca_cli.core.config.load_config", side_effect=RuntimeError("boom")):
            client, profile = completions._build_client(fake_ctx)
        assert client is None
        assert profile is None

    def test_builds_client_when_config_ok(self, fake_ctx):
        with patch("orca_cli.core.config.load_config", return_value={"x": 1}), \
             patch("orca_cli.core.config.config_is_complete", return_value=True), \
             patch("orca_cli.core.client.OrcaClient") as OC:
            OC.return_value = MagicMock()
            client, profile = completions._build_client(fake_ctx)
        assert client is not None


class TestMatches:

    def test_match_on_id(self):
        assert completions._matches({"id": "abc-123", "name": ""}, "abc") is True

    def test_match_on_name(self):
        assert completions._matches({"id": "xxx", "name": "prod-web"}, "web") is True

    def test_no_match(self):
        assert completions._matches({"id": "xxx", "name": "yyy"}, "zzz") is False

    def test_case_insensitive(self):
        assert completions._matches({"id": "ABC", "name": ""}, "abc") is True


class TestCompleteFromCache:
    """When cache is fresh, no client is built."""

    def test_cache_hit_filters_items(self, fake_ctx):
        items = [
            {"id": "s1", "name": "web"},
            {"id": "s2", "name": "db"},
            {"id": "s3", "name": "cache"},
        ]
        with patch("orca_cli.core.cache.load", return_value=items), \
             patch.object(completions, "_build_client") as bc:
            out = completions.complete_servers(fake_ctx, None, "we")

        # Cache hit → no client built
        bc.assert_not_called()
        assert len(out) == 1
        assert out[0].value == "s1"

    def test_empty_when_client_build_fails(self, fake_ctx):
        with patch("orca_cli.core.cache.load", return_value=None), \
             patch.object(completions, "_build_client", return_value=(None, None)):
            out = completions.complete_servers(fake_ctx, None, "")
        assert out == []

    def test_fetch_saves_to_cache(self, fake_ctx):
        """Cache miss → fetch → save → return filtered."""
        client = MagicMock()
        client.compute_url = "https://nova.example.com"
        client.get.return_value = {
            "servers": [{"id": "s1", "name": "web-1"}, {"id": "s2", "name": "db-1"}],
        }
        with patch("orca_cli.core.cache.load", return_value=None), \
             patch("orca_cli.core.cache.save") as save, \
             patch.object(completions, "_build_client", return_value=(client, "prod")):
            out = completions.complete_servers(fake_ctx, None, "web")

        save.assert_called_once()
        assert [c.value for c in out] == ["s1"]

    def test_fetch_failure_returns_empty(self, fake_ctx):
        client = MagicMock()
        client.get.side_effect = RuntimeError("api down")
        client.compute_url = "https://nova.example.com"
        with patch("orca_cli.core.cache.load", return_value=None), \
             patch.object(completions, "_build_client", return_value=(client, "p")):
            out = completions.complete_servers(fake_ctx, None, "")
        assert out == []


class TestAllCompletionFunctions:
    """Exercise every completion callback once with a cache hit."""

    @pytest.mark.parametrize("fn,items", [
        (completions.complete_volumes, [{"id": "v1", "name": "vol"}]),
        (completions.complete_images, [{"id": "i1", "name": "img"}]),
        (completions.complete_networks, [{"id": "n1", "name": "net"}]),
        (completions.complete_flavors, [{"id": "f1", "name": "flav"}]),
        (completions.complete_keypairs, [{"id": "key1", "name": ""}]),
        (completions.complete_security_groups, [{"id": "sg1", "name": "default"}]),
    ])
    def test_cache_hit_path(self, fake_ctx, fn, items):
        with patch("orca_cli.core.cache.load", return_value=items):
            out = fn(fake_ctx, None, "")
        assert len(out) >= 1


class TestFetchPathsPerFunction:
    """Cache miss → fetch → different URLs/payloads per resource type."""

    def _client(self):
        c = MagicMock()
        c.compute_url = "https://nova"
        c.volume_url = "https://cinder"
        c.image_url = "https://glance"
        c.network_url = "https://neutron"
        return c

    def test_volumes_fetch(self, fake_ctx):
        client = self._client()
        client.get.return_value = {"volumes": [{"id": "v1", "name": "disk"}]}
        with patch("orca_cli.core.cache.load", return_value=None), \
             patch("orca_cli.core.cache.save"), \
             patch.object(completions, "_build_client", return_value=(client, "p")):
            out = completions.complete_volumes(fake_ctx, None, "")
        assert out[0].value == "v1"

    def test_images_fetch(self, fake_ctx):
        client = self._client()
        client.get.return_value = {"images": [{"id": "i1", "name": "ubuntu"}]}
        with patch("orca_cli.core.cache.load", return_value=None), \
             patch("orca_cli.core.cache.save"), \
             patch.object(completions, "_build_client", return_value=(client, "p")):
            out = completions.complete_images(fake_ctx, None, "")
        assert out[0].value == "i1"

    def test_networks_fetch(self, fake_ctx):
        client = self._client()
        client.get.return_value = {"networks": [{"id": "n1", "name": "priv"}]}
        with patch("orca_cli.core.cache.load", return_value=None), \
             patch("orca_cli.core.cache.save"), \
             patch.object(completions, "_build_client", return_value=(client, "p")):
            out = completions.complete_networks(fake_ctx, None, "")
        assert out[0].value == "n1"

    def test_flavors_fetch(self, fake_ctx):
        client = self._client()
        client.get.return_value = {"flavors": [{"id": "f1", "name": "m1.tiny"}]}
        with patch("orca_cli.core.cache.load", return_value=None), \
             patch("orca_cli.core.cache.save"), \
             patch.object(completions, "_build_client", return_value=(client, "p")):
            out = completions.complete_flavors(fake_ctx, None, "")
        assert out[0].value == "f1"

    def test_keypairs_fetch(self, fake_ctx):
        client = self._client()
        client.get.return_value = {"keypairs": [{"keypair": {"name": "key-1"}}]}
        with patch("orca_cli.core.cache.load", return_value=None), \
             patch("orca_cli.core.cache.save"), \
             patch.object(completions, "_build_client", return_value=(client, "p")):
            out = completions.complete_keypairs(fake_ctx, None, "")
        assert out[0].value == "key-1"

    def test_security_groups_fetch(self, fake_ctx):
        client = self._client()
        client.get.return_value = {
            "security_groups": [{"id": "sg1", "name": "default"}]
        }
        with patch("orca_cli.core.cache.load", return_value=None), \
             patch("orca_cli.core.cache.save"), \
             patch.object(completions, "_build_client", return_value=(client, "p")):
            out = completions.complete_security_groups(fake_ctx, None, "")
        assert out[0].value == "default"  # name used, not id


class TestClientCloseFailureSwallowed:
    """client.close() exceptions in the finally branch must not propagate."""

    def test_close_failure_swallowed(self, fake_ctx):
        client = MagicMock()
        client.compute_url = "https://nova"
        client.get.return_value = {"servers": [{"id": "s1", "name": "x"}]}
        client.close.side_effect = RuntimeError("close boom")
        with patch("orca_cli.core.cache.load", return_value=None), \
             patch("orca_cli.core.cache.save"), \
             patch.object(completions, "_build_client", return_value=(client, "p")):
            out = completions.complete_servers(fake_ctx, None, "")
        assert len(out) == 1
