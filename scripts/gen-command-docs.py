"""Regenerate ``docs/commands/<name>.md`` as ``mkdocs-click`` wrappers.

Each top-level CLI command yields a one-page wrapper that defers to the
``mkdocs-click`` extension at build time. The page therefore always
reflects the live ``--help`` of the installed CLI — no manual sync.

Run from the repo root::

    .venv/bin/python scripts/gen-command-docs.py

Re-run after adding/removing/renaming a top-level command. The resulting
files are versioned, so a clean build is reproducible without rerunning
this script in CI.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

# Make the in-tree package importable when running the script directly.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import click  # noqa: E402

from orca_cli.main import cli  # noqa: E402

DOCS_DIR = Path(__file__).resolve().parents[1] / "docs" / "commands"

# Short, hand-curated tagline for each top-level command. Falls back to
# the first paragraph of the Click ``help`` when missing.
TAGLINES: dict[str, str] = {
    "access-rule": "Restrict application credentials to specific endpoints.",
    "aggregate": "Manage Nova host aggregates (compute admin).",
    "alarm": "Manage Aodh alarms.",
    "application-credential": "Manage Keystone application credentials.",
    "audit": "Cross-project audit reports (orca-exclusive).",
    "auth": "Inspect tokens and authentication details.",
    "availability-zone": "List availability zones across services.",
    "backup": "Trilio Freezer backup management.",
    "catalog": "Print the Keystone service catalog.",
    "cleanup": "Delete unused / dangling resources (orca-exclusive).",
    "cluster": "Manage Magnum (Kubernetes) clusters.",
    "completion": "Install or print shell completion scripts.",
    "compute-service": "Manage Nova compute services (admin).",
    "container": "Manage Swift containers.",
    "credential": "Manage Keystone non-application credentials.",
    "doctor": "Diagnose orca configuration and connectivity.",
    "domain": "Manage Keystone domains.",
    "endpoint": "Manage Keystone endpoints.",
    "endpoint-group": "Manage Keystone endpoint groups.",
    "event": "Inspect Nova instance events.",
    "export": "Export resources for backup / migration.",
    "federation-protocol": "Manage Keystone federation protocols.",
    "find": "Locate a resource by partial ID or name.",
    "flavor": "Manage Nova flavors.",
    "floating-ip": "Allocate and associate floating IPs.",
    "group": "Manage Keystone groups.",
    "hypervisor": "Inspect Nova hypervisors (admin).",
    "identity-provider": "Manage Keystone identity providers.",
    "image": "Manage Glance images.",
    "ip": "Resolve / inspect IP addresses (orca-exclusive).",
    "keypair": "Manage SSH key pairs.",
    "limit": "Manage Keystone project limits (admin).",
    "limits": "Show absolute / rate quota limits.",
    "loadbalancer": "Manage Octavia load balancers.",
    "mapping": "Manage Keystone federation mappings.",
    "metric": "Manage Gnocchi metrics, measures and resources.",
    "network": "Manage Neutron networks, subnets, ports and routers.",
    "object": "Manage Swift objects.",
    "overview": "Render a single-screen account overview (orca-exclusive).",
    "placement": "Manage Placement resources, traits and inventories.",
    "policy": "Manage Keystone policies.",
    "profile": "Manage orca configuration profiles.",
    "project": "Manage Keystone projects.",
    "qos": "Manage Neutron QoS policies and rules.",
    "quota": "Inspect and update project quotas.",
    "rating": "Manage CloudKitty rating modules.",
    "recordset": "Manage Designate recordsets.",
    "region": "Manage Keystone regions.",
    "registered-limit": "Manage Keystone registered limits (admin).",
    "role": "Manage Keystone roles and assignments.",
    "secret": "Manage Barbican secrets and containers.",
    "security-group": "Manage Neutron security groups.",
    "server": "Manage Nova compute instances.",
    "server-group": "Manage Nova server groups.",
    "service": "Manage Keystone services.",
    "service-provider": "Manage Keystone federation service providers.",
    "setup": "Interactive credential setup wizard.",
    "stack": "Manage Heat orchestration stacks.",
    "subnet-pool": "Manage Neutron subnet pools.",
    "token": "Inspect and revoke Keystone tokens.",
    "trunk": "Manage Neutron trunk ports.",
    "trust": "Manage Keystone trusts.",
    "usage": "Show Nova tenant usage.",
    "user": "Manage Keystone users.",
    "volume": "Manage block storage volumes & snapshots (Cinder).",
    "watch": "Live tail Nova/Neutron events (orca-exclusive).",
    "zone": "Manage Designate zones.",
}


WRAPPER = """# `orca {cmd}`

{tagline}

The reference below is generated from the live CLI by `mkdocs-click`. It
always reflects the version installed.

::: mkdocs-click
    :module: {module}
    :command: {variable}
    :prog_name: orca {cmd}
    :depth: 2
    :style: table
    :list_subcommands: true
"""


def _resolve_variable_name(module_name: str, command: click.Command) -> str:
    """Return the Python variable in *module_name* that holds *command*."""
    mod = importlib.import_module(module_name)
    for name, value in vars(mod).items():
        if value is command:
            return name
    raise RuntimeError(
        f"could not find the variable holding {command.name!r} "
        f"in {module_name}; check the module exports it at top-level."
    )


def _tagline(cmd_name: str, command: click.Command) -> str:
    if cmd_name in TAGLINES:
        return TAGLINES[cmd_name]
    short = (command.help or "").splitlines()[0].strip() if command.help else ""
    return short or f"`{cmd_name}` commands."


def main() -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    written: list[str] = []
    for cmd_name in cli.list_commands(None):
        command = cli.get_command(None, cmd_name)
        if command is None:
            continue
        module = command.callback.__module__ if command.callback else None
        if module is None:
            # Pure groups (no callback) — pull from the registered command's
            # __module__ via one of its sub-commands, falling back to the
            # group itself.
            module = command.__class__.__module__
        # When the callback lives in main.py (root group), fall back to the
        # commands package via the lazy index.
        if not module.startswith("orca_cli.commands."):
            module = f"orca_cli.commands.{cli._cmd_to_module[cmd_name]}"

        variable = _resolve_variable_name(module, command)
        path = DOCS_DIR / f"{cmd_name}.md"
        path.write_text(WRAPPER.format(
            cmd=cmd_name,
            tagline=_tagline(cmd_name, command),
            module=module,
            variable=variable,
        ))
        written.append(cmd_name)

    print(f"Wrote {len(written)} command pages to {DOCS_DIR}.")


if __name__ == "__main__":
    main()
