"""Tests for ``orca completion`` command."""

from __future__ import annotations

# ══════════════════════════════════════════════════════════════════════════
#  completion
# ══════════════════════════════════════════════════════════════════════════


class TestCompletion:

    def test_bash(self, invoke):
        result = invoke(["completion", "bash"])
        assert result.exit_code == 0
        assert "bashrc" in result.output
        assert "_ORCA_COMPLETE" in result.output

    def test_zsh(self, invoke):
        result = invoke(["completion", "zsh"])
        assert result.exit_code == 0
        assert "zshrc" in result.output
        assert "_ORCA_COMPLETE" in result.output

    def test_fish(self, invoke):
        result = invoke(["completion", "fish"])
        assert result.exit_code == 0
        assert "fish" in result.output
        assert "_ORCA_COMPLETE" in result.output

    def test_invalid_shell(self, invoke):
        result = invoke(["completion", "powershell"])
        assert result.exit_code != 0


# ══════════════════════════════════════════════════════════════════════════
#  Help
# ══════════════════════════════════════════════════════════════════════════


class TestCompletionHelp:

    def test_completion_help(self, invoke):
        result = invoke(["completion", "--help"])
        assert result.exit_code == 0
        assert "bash" in result.output.lower()
        assert "zsh" in result.output.lower()
        assert "fish" in result.output.lower()
