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
