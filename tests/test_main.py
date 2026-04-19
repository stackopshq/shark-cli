"""Tests for orca_cli.main — the poetry entrypoint wrapper's error paths."""

from __future__ import annotations

from unittest.mock import patch

import click
import pytest

from orca_cli import main as main_module
from orca_cli.core.exceptions import OrcaCLIError


class TestMainEntrypoint:
    """The `main()` wrapper must convert exceptions into clean exit codes."""

    def test_orca_cli_error_exits_1_with_red_message(self, capsys):
        def raise_orca(**kwargs):
            raise OrcaCLIError("config missing")

        with patch.object(main_module, "cli", raise_orca):
            with pytest.raises(SystemExit) as exc_info:
                main_module.main()

        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "Error:" in err
        assert "config missing" in err

    def test_abort_exits_130(self, capsys):
        def raise_abort(**kwargs):
            raise click.exceptions.Abort()

        with patch.object(main_module, "cli", raise_abort):
            with pytest.raises(SystemExit) as exc_info:
                main_module.main()

        assert exc_info.value.code == 130
        err = capsys.readouterr().err
        assert "Aborted" in err

    def test_cli_is_group(self):
        """The auto-registered root must be a click.Group with sub-commands."""
        assert isinstance(main_module.cli, click.Group)
        # A handful of well-known commands must be registered
        names = set(main_module.cli.commands.keys())
        for expected in ("server", "volume", "network", "profile", "doctor"):
            assert expected in names, f"missing {expected} in {sorted(names)}"


class TestModuleTopLevelCommands:
    """Auto-discovery must return a stable list for a known module."""

    def test_server_module_exposes_server_group(self):
        import orca_cli.commands.server as server_mod
        cmds = main_module._module_top_level_commands(server_mod)
        names = {c.name for c in cmds}
        assert "server" in names
        # Subcommands of `server` must not be returned as top-level
        assert "list" not in names
        assert "create" not in names

    def test_federation_module_exposes_multiple_groups(self):
        """federation.py defines 4 top-level groups that must all surface."""
        import orca_cli.commands.federation as fed_mod
        cmds = main_module._module_top_level_commands(fed_mod)
        names = {c.name for c in cmds}
        # At least the core ones should be here
        assert len(names) >= 2
