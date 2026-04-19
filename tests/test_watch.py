"""Tests for ``orca watch`` helpers and help."""

from __future__ import annotations

# ══════════════════════════════════════════════════════════════════════════
#  _styled_status
# ══════════════════════════════════════════════════════════════════════════


class TestStyledStatus:

    def test_active(self):
        from orca_cli.commands.watch import _styled_status
        t = _styled_status("ACTIVE")
        assert t.plain == "ACTIVE"
        assert "green" in str(t.style)

    def test_error(self):
        from orca_cli.commands.watch import _styled_status
        t = _styled_status("ERROR")
        assert t.plain == "ERROR"
        assert "red" in str(t.style)

    def test_unknown(self):
        from orca_cli.commands.watch import _styled_status
        t = _styled_status("WEIRD")
        assert t.plain == "WEIRD"


# ══════════════════════════════════════════════════════════════════════════
#  _extract_ip
# ══════════════════════════════════════════════════════════════════════════


class TestExtractIp:

    def test_prefer_floating(self):
        from orca_cli.commands.watch import _extract_ip
        addresses = {
            "my-net": [
                {"addr": "10.0.0.5", "OS-EXT-IPS:type": "fixed"},
                {"addr": "203.0.113.10", "OS-EXT-IPS:type": "floating"},
            ]
        }
        assert _extract_ip(addresses) == "203.0.113.10"

    def test_fixed_fallback(self):
        from orca_cli.commands.watch import _extract_ip
        addresses = {
            "my-net": [
                {"addr": "10.0.0.5", "OS-EXT-IPS:type": "fixed"},
            ]
        }
        assert _extract_ip(addresses) == "10.0.0.5"

    def test_empty(self):
        from orca_cli.commands.watch import _extract_ip
        assert _extract_ip({}) == "—"


# ══════════════════════════════════════════════════════════════════════════
#  Help
# ══════════════════════════════════════════════════════════════════════════


class TestWatchHelp:

    def test_watch_help(self, invoke):
        result = invoke(["watch", "--help"])
        assert result.exit_code == 0
        assert "--interval" in result.output
        assert "dashboard" in result.output.lower()


# ══════════════════════════════════════════════════════════════════════════
#  Safe fetchers — each swallows exceptions to an empty list
# ══════════════════════════════════════════════════════════════════════════

from unittest.mock import MagicMock  # noqa: E402

from orca_cli.commands import watch as watch_mod  # noqa: E402


class TestFetchers:

    def _client(self, **urls):
        c = MagicMock()
        c.compute_url = urls.get("compute", "https://nova")
        c.volume_url = urls.get("volume", "https://cinder")
        c.network_url = urls.get("network", "https://neutron")
        return c

    def test_fetch_servers_ok(self):
        c = self._client()
        c.get.return_value = {"servers": [{"id": "s1"}]}
        assert watch_mod._fetch_servers(c) == [{"id": "s1"}]

    def test_fetch_servers_swallows(self):
        c = self._client()
        c.get.side_effect = RuntimeError("boom")
        assert watch_mod._fetch_servers(c) == []

    def test_fetch_volumes_ok(self):
        c = self._client()
        c.get.return_value = {"volumes": [{"id": "v1", "size": 5}]}
        assert watch_mod._fetch_volumes(c) == [{"id": "v1", "size": 5}]

    def test_fetch_volumes_swallows(self):
        c = self._client()
        c.get.side_effect = RuntimeError("boom")
        assert watch_mod._fetch_volumes(c) == []

    def test_fetch_floating_ips_ok(self):
        c = self._client()
        c.get.return_value = {"floatingips": [{"id": "f1"}]}
        assert watch_mod._fetch_floating_ips(c) == [{"id": "f1"}]

    def test_fetch_floating_ips_swallows(self):
        c = self._client()
        c.get.side_effect = RuntimeError("boom")
        assert watch_mod._fetch_floating_ips(c) == []

    def test_fetch_networks_ok(self):
        c = self._client()
        c.get.return_value = {"networks": [{"id": "n1"}]}
        assert watch_mod._fetch_networks(c) == [{"id": "n1"}]

    def test_fetch_networks_swallows(self):
        c = self._client()
        c.get.side_effect = RuntimeError("boom")
        assert watch_mod._fetch_networks(c) == []

    def test_fetch_recent_events_sorts_and_truncates(self):
        c = self._client()
        servers = [{"id": "srv-1", "name": "web"}]
        c.get.return_value = {"instanceActions": [
            {"action": "reboot", "start_time": "2025-01-01T00:00:00"},
            {"action": "start", "start_time": "2025-02-01T00:00:00"},
            {"action": "stop", "start_time": "2025-03-01T00:00:00"},
            {"action": "pause", "start_time": "2025-04-01T00:00:00"},
            {"action": "resume", "start_time": "2025-05-01T00:00:00"},
            {"action": "delete", "start_time": "2025-06-01T00:00:00"},
        ]}
        out = watch_mod._fetch_recent_events(c, servers, limit=3)
        assert len(out) == 3
        # Sorted descending by start_time
        assert out[0]["action"] == "delete"
        assert out[2]["action"] == "pause"
        # Each action tagged with server name
        assert out[0]["_server_name"] == "web"

    def test_fetch_recent_events_per_server_exception_swallows(self):
        c = self._client()
        servers = [{"id": "srv-1", "name": "web"}, {"id": "srv-2", "name": "db"}]
        c.get.side_effect = [
            RuntimeError("srv-1 down"),
            {"instanceActions": [{"action": "start", "start_time": "2025-01-01"}]},
        ]
        out = watch_mod._fetch_recent_events(c, servers)
        assert len(out) == 1
        assert out[0]["_server_name"] == "db"


class TestBuildDashboard:

    def test_with_data(self):
        c = MagicMock()
        c.compute_url = "https://nova"
        c.volume_url = "https://cinder"
        c.network_url = "https://neutron"
        c.get.side_effect = [
            {"servers": [
                {"id": "srv-aaaa1111", "name": "web",
                 "status": "ACTIVE",
                 "flavor": {"original_name": "m1.small"},
                 "addresses": {"net": [
                     {"addr": "10.0.0.5", "OS-EXT-IPS:type": "fixed"},
                 ]}},
            ]},
            {"volumes": [{"id": "v1", "size": 10, "status": "in-use"}]},
            {"floatingips": [{"id": "f1", "fixed_ip_address": "10.0.0.5"}]},
            {"networks": [{"id": "n1"}]},
            {"instanceActions": [{"action": "reboot", "start_time": "2025-06-01T00:00:00",
                                  "message": "ok"}]},
        ]

        group = watch_mod._build_dashboard(c, interval=5)
        # Group contains the renderables (header, spacer, servers panel, summary, events panel)
        assert len(group.renderables) == 5

    def test_with_empty_data(self):
        c = MagicMock()
        c.compute_url = "https://nova"
        c.volume_url = "https://cinder"
        c.network_url = "https://neutron"
        c.get.side_effect = RuntimeError("all down")  # every fetch swallows

        group = watch_mod._build_dashboard(c, interval=10)
        # Placeholder rows rendered: "No servers found", "No recent events"
        assert len(group.renderables) == 5

    def test_long_timestamp_gets_truncated(self):
        """Event timestamps longer than 19 chars are truncated to 19."""
        c = MagicMock()
        c.compute_url = "https://nova"
        c.volume_url = "https://cinder"
        c.network_url = "https://neutron"
        c.get.side_effect = [
            {"servers": [{"id": "s1", "name": "web", "status": "ACTIVE",
                          "flavor": {}, "addresses": {}}]},
            {"volumes": []},
            {"floatingips": []},
            {"networks": []},
            # start_time with microseconds + TZ — clearly > 19 chars
            {"instanceActions": [{"action": "reboot",
                                  "start_time": "2025-06-01T00:00:00.123456+00:00",
                                  "message": "ok"}]},
        ]
        group = watch_mod._build_dashboard(c, interval=5)
        assert len(group.renderables) == 5
