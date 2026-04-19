"""Tests that all command groups are properly registered and loadable."""

from __future__ import annotations

import pytest

from orca_cli.main import cli

EXPECTED_COMMANDS = [
    "aggregate", "application-credential", "audit", "auth", "availability-zone",
    "backup", "catalog", "cleanup", "cluster", "completion", "compute-service", "credential",
    "container", "doctor", "domain", "endpoint", "event", "export", "find", "flavor", "floating-ip",
    "group", "hypervisor",
    "image", "ip", "keypair", "limits", "loadbalancer", "metric", "network", "object",
    "overview", "profile", "project", "qos", "quota", "recordset", "region", "role", "secret",
    "security-group", "server", "server-group", "service", "setup", "stack", "subnet-pool",
    "trust", "trunk", "usage",
    "user", "volume", "watch", "zone", "placement", "alarm",
    "policy", "identity-provider", "federation-protocol", "mapping", "service-provider",
    "limit", "registered-limit", "access-rule", "token", "endpoint-group",
]


class TestCLIRegistration:

    def test_all_commands_registered(self):
        """Every expected command should be in the CLI group."""
        registered = list(cli.commands.keys())
        for cmd in EXPECTED_COMMANDS:
            assert cmd in registered, f"Command '{cmd}' not registered in CLI"

    def test_no_unexpected_commands(self):
        """No stray commands should appear."""
        registered = set(cli.commands.keys())
        expected = set(EXPECTED_COMMANDS)
        extra = registered - expected
        assert not extra, f"Unexpected commands registered: {extra}"

    def test_main_help(self, invoke):
        result = invoke(["--help"])
        assert result.exit_code == 0
        assert "orca" in result.output
        for cmd in EXPECTED_COMMANDS:
            assert cmd in result.output, f"'{cmd}' missing from --help output"

    def test_version(self, invoke):
        result = invoke(["--version"])
        assert result.exit_code == 0
        assert "orca" in result.output


class TestSubcommandHelp:
    """Verify each command group shows --help without errors."""

    @pytest.mark.parametrize("cmd", EXPECTED_COMMANDS)
    def test_command_help(self, invoke, cmd):
        result = invoke([cmd, "--help"])
        assert result.exit_code == 0, f"'{cmd} --help' failed: {result.output}"


class TestServerSubcommands:
    """Verify key server subcommands including the new port-forward."""

    SERVER_SUBCMDS = [
        "list", "show", "create", "delete", "start", "stop", "reboot",
        "ssh", "snapshot", "wait", "bulk", "clone", "diff", "port-forward",
    ]

    @pytest.mark.parametrize("sub", SERVER_SUBCMDS)
    def test_server_subcommand_help(self, invoke, sub):
        result = invoke(["server", sub, "--help"])
        assert result.exit_code == 0, f"'server {sub} --help' failed"

    def test_port_forward_requires_args(self, invoke):
        result = invoke(["server", "port-forward"])
        # Should fail because SERVER_ID and PORT_MAPPING are required
        assert result.exit_code != 0


class TestProfileSubcommands:
    """Verify profile subcommands including conversions."""

    PROFILE_SUBCMDS = [
        "list", "show", "add", "edit", "switch", "remove", "rename",
        "set-color", "to-openrc", "to-clouds", "from-openrc", "from-clouds",
    ]

    @pytest.mark.parametrize("sub", PROFILE_SUBCMDS)
    def test_profile_subcommand_help(self, invoke, sub):
        result = invoke(["profile", sub, "--help"])
        assert result.exit_code == 0, f"'profile {sub} --help' failed"


class TestNewServiceCommands:
    """Verify the 3 new service command groups have their subcommands."""

    def test_object_subcommands(self, invoke):
        result = invoke(["object", "--help"])
        assert result.exit_code == 0
        for sub in ["list", "upload", "download", "delete", "tree"]:
            assert sub in result.output, f"'object {sub}' missing"

    def test_container_subcommands(self, invoke):
        result = invoke(["container", "--help"])
        assert result.exit_code == 0
        for sub in ["list", "show", "create", "delete", "set", "save", "stats"]:
            assert sub in result.output, f"'container {sub}' missing"

    def test_stack_subcommands(self, invoke):
        result = invoke(["stack", "--help"])
        assert result.exit_code == 0
        for sub in ["list", "show", "create", "delete", "event-list",
                     "resource-list", "output-list", "topology"]:
            assert sub in result.output, f"'stack {sub}' missing"

    def test_zone_subcommands(self, invoke):
        result = invoke(["zone", "--help"])
        assert result.exit_code == 0
        for sub in ["list", "show", "create", "set", "delete", "tree", "export", "import", "reverse-lookup"]:
            assert sub in result.output, f"'zone {sub}' missing"

    def test_recordset_subcommands(self, invoke):
        result = invoke(["recordset", "--help"])
        assert result.exit_code == 0
        for sub in ["list", "show", "create", "set", "delete"]:
            assert sub in result.output, f"'recordset {sub}' missing"

    def test_event_subcommands(self, invoke):
        result = invoke(["event", "--help"])
        assert result.exit_code == 0
        for sub in ["list", "show", "all", "timeline"]:
            assert sub in result.output, f"'event {sub}' missing"

    def test_auth_subcommands(self, invoke):
        result = invoke(["auth", "--help"])
        assert result.exit_code == 0
        for sub in ["whoami", "token-debug", "check"]:
            assert sub in result.output, f"'auth {sub}' missing"
