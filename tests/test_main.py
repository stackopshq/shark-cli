"""Tests for orca_cli.main — the poetry entrypoint wrapper's error paths."""

from __future__ import annotations

import logging
from unittest.mock import patch

import click
import pytest
from click.testing import CliRunner

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
        """The lazy root group must list well-known commands without importing them."""
        assert isinstance(main_module.cli, click.Group)
        names = set(main_module.cli.list_commands(None))
        for expected in ("server", "volume", "network", "profile", "doctor"):
            assert expected in names, f"missing {expected} in {sorted(names)}"


class TestLazyResolution:
    """The LazyOrcaGroup must resolve commands on demand without bulk-importing."""

    def test_get_command_resolves_simple_name(self):
        cmd = main_module.cli.get_command(None, "server")
        assert cmd is not None
        assert cmd.name == "server"
        assert isinstance(cmd, click.Group)

    def test_get_command_resolves_overridden_name(self):
        # ip_whois.py exposes a command named "ip", not "ip-whois"
        cmd = main_module.cli.get_command(None, "ip")
        assert cmd is not None
        assert cmd.name == "ip"

    def test_get_command_resolves_multi_command_module(self):
        # federation.py exposes 4 distinct top-level commands
        for name in ("federation-protocol", "identity-provider",
                     "mapping", "service-provider"):
            cmd = main_module.cli.get_command(None, name)
            assert cmd is not None, f"{name} did not resolve"
            assert cmd.name == name

    def test_get_command_returns_none_for_unknown(self):
        assert main_module.cli.get_command(None, "this-command-does-not-exist") is None


class TestDebugFlag:
    """--debug attaches a stderr handler to the orca_cli logger."""

    @pytest.fixture(autouse=True)
    def _reset_logger(self):
        """Strip handlers before and after to keep tests isolated."""
        orca_logger = logging.getLogger("orca_cli")
        saved = (orca_logger.handlers[:], orca_logger.level, orca_logger.propagate)
        orca_logger.handlers = []
        orca_logger.setLevel(logging.WARNING)
        yield
        orca_logger.handlers, orca_logger.level, orca_logger.propagate = saved

    def test_enable_debug_logging_configures_logger(self, capsys):
        main_module._enable_debug_logging()
        orca_logger = logging.getLogger("orca_cli")
        assert orca_logger.level == logging.DEBUG
        assert len(orca_logger.handlers) == 1
        # Handler writes to stderr, not stdout.
        handler = orca_logger.handlers[0]
        assert isinstance(handler, logging.StreamHandler)
        # User is warned about the implications on stderr.
        err = capsys.readouterr().err
        assert "DEBUG mode enabled" in err

    def test_debug_option_is_registered_on_root(self):
        names = [p.name for p in main_module.cli.params]
        assert "debug" in names

    def test_debug_flag_triggers_enable(self):
        """Invoking the root with --debug must call _enable_debug_logging."""
        runner = CliRunner()
        with patch.object(main_module, "_enable_debug_logging") as mock_enable:
            # catalog is a lightweight subcommand that needs config; it will
            # fail on missing creds, but the callback (and our flag handling)
            # runs before that.
            runner.invoke(main_module.cli, ["--debug", "catalog"])
        mock_enable.assert_called_once()
