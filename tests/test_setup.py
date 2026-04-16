"""Tests for ``orca setup`` command."""

from __future__ import annotations

# ══════════════════════════════════════════════════════════════════════════
#  Help
# ══════════════════════════════════════════════════════════════════════════


class TestSetupHelp:

    def test_setup_help(self, invoke):
        result = invoke(["setup", "--help"])
        assert result.exit_code == 0
        assert "--profile" in result.output
        assert "credentials" in result.output.lower()
