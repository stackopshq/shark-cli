"""Tests for ``orca completion`` command."""

from __future__ import annotations

from unittest.mock import patch

# ══════════════════════════════════════════════════════════════════════════
#  completion — print instructions (legacy behavior)
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

    def test_no_shell_autodetect(self, invoke, monkeypatch):
        """Bare `orca completion` auto-detects shell from $SHELL."""
        monkeypatch.setenv("SHELL", "/bin/zsh")
        result = invoke(["completion"])
        assert result.exit_code == 0
        assert "zshrc" in result.output

    def test_no_shell_no_env(self, invoke, monkeypatch):
        monkeypatch.delenv("SHELL", raising=False)
        result = invoke(["completion"])
        assert result.exit_code == 1
        assert "auto-detect" in result.output.lower()


# ══════════════════════════════════════════════════════════════════════════
#  completion install — auto-install
# ══════════════════════════════════════════════════════════════════════════


class TestCompletionInstall:

    def test_install_bash_explicit(self, invoke):
        with patch("orca_cli.commands.completion.install_completion",
                   return_value="Appended to ~/.bashrc") as mock_install:
            result = invoke(["completion", "install", "bash"])
        assert result.exit_code == 0, result.output
        mock_install.assert_called_once_with("bash")
        assert "Appended" in result.output

    def test_install_autodetect(self, invoke, monkeypatch):
        monkeypatch.setenv("SHELL", "/bin/zsh")
        with patch("orca_cli.commands.completion.install_completion",
                   return_value="ok") as mock_install:
            result = invoke(["completion", "install"])
        assert result.exit_code == 0
        mock_install.assert_called_once_with("zsh")

    def test_install_no_shell_no_env(self, invoke, monkeypatch):
        monkeypatch.delenv("SHELL", raising=False)
        result = invoke(["completion", "install"])
        assert result.exit_code == 1
        assert "auto-detect" in result.output.lower()

    def test_install_invalid_shell(self, invoke):
        result = invoke(["completion", "install", "powershell"])
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

    def test_install_help(self, invoke):
        result = invoke(["completion", "install", "--help"])
        assert result.exit_code == 0
        assert "install" in result.output.lower()
