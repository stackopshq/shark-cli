"""Entry point for orca — initialises the Click group and auto-registers sub-commands.

Commands are discovered by scanning ``orca_cli.commands``: every
``click.Command`` defined at module level is registered on the root group,
except for objects that are subcommands of another group in the same module.
A module may therefore expose multiple top-level groups (e.g. ``federation.py``
exports identity-provider, federation-protocol, mapping, service-provider)
without any bookkeeping in this file.

Adding a new command group: drop a file into ``orca_cli/commands/`` with a
``@click.group()`` (or ``@click.command()``) at module level. That's it.
"""

from __future__ import annotations

import importlib
import pkgutil
import sys
from pathlib import Path

import click

from orca_cli import __version__
from orca_cli.core.context import OrcaContext
from orca_cli.core.exceptions import OrcaCLIError


def _complete_regions(ctx: click.Context, param: click.Parameter, incomplete: str) -> list:  # pragma: no cover
    """Shell completion for the global --region flag.

    Invoked by the shell, not exercised in pytest. Best-effort: all exceptions
    swallow to empty — never crash the user's tab key.
    """
    try:
        from orca_cli.core.client import OrcaClient
        from orca_cli.core.config import config_is_complete, load_config

        config = load_config()
        if not config_is_complete(config):
            return []
        client = OrcaClient(config)
        regions: set[str] = set()
        for svc in client._catalog:
            for ep in svc.get("endpoints", []):
                region = ep.get("region_id") or ep.get("region")
                if region:
                    regions.add(region)
        client.close()
        return sorted(r for r in regions if r.startswith(incomplete))
    except Exception:
        return []


@click.group()
@click.version_option(version=__version__, prog_name="orca")
@click.option("--profile", "-P", default=None, envvar="ORCA_PROFILE",
              help="Config profile to use (overrides active profile).")
@click.option("--region", "-R", default=None, envvar="ORCA_REGION",
              shell_complete=_complete_regions,
              help="Region to use (overrides profile region_name).")
@click.pass_context
def cli(ctx: click.Context, profile: str | None, region: str | None) -> None:
    """orca — OpenStack Rich Command-line Alternative."""
    orca_ctx = ctx.ensure_object(OrcaContext)
    orca_ctx.profile = profile
    orca_ctx.region = region


# ── Auto-registration of sub-commands ─────────────────────────────────────

def _module_top_level_commands(mod) -> list[click.Command]:
    """Return every click command/group *defined* in ``mod`` that is not a
    subcommand of another group in the same module."""
    candidates: list[click.Command] = []
    for attr_name in dir(mod):
        if attr_name.startswith("_"):
            continue
        obj = getattr(mod, attr_name)
        if not isinstance(obj, click.Command):
            continue
        # Only keep objects whose callback was actually defined in this module —
        # filters out click commands re-imported from elsewhere.
        callback = getattr(obj, "callback", None)
        if callback is None or getattr(callback, "__module__", None) != mod.__name__:
            continue
        candidates.append(obj)

    # Drop anything that is attached as a subcommand of a group we found.
    subcommand_ids: set[int] = set()
    stack = [c for c in candidates if isinstance(c, click.Group)]
    while stack:
        grp = stack.pop()
        for sub in grp.commands.values():
            if id(sub) in subcommand_ids:
                continue
            subcommand_ids.add(id(sub))
            if isinstance(sub, click.Group):
                stack.append(sub)

    return [c for c in candidates if id(c) not in subcommand_ids]


def _register_all_commands() -> None:
    """Import every module under ``orca_cli.commands`` and register its
    top-level click commands on the root ``cli`` group."""
    pkg = importlib.import_module("orca_cli.commands")
    pkg_path = Path(pkg.__file__).parent

    for mod_info in sorted(pkgutil.iter_modules([str(pkg_path)]), key=lambda m: m.name):
        if mod_info.ispkg or mod_info.name.startswith("_"):
            continue
        mod = importlib.import_module(f"orca_cli.commands.{mod_info.name}")
        for cmd in _module_top_level_commands(mod):
            cli.add_command(cmd)


_register_all_commands()


def main() -> None:
    """Wrapper used by the ``[tool.poetry.scripts]`` entry-point."""
    try:
        cli(standalone_mode=False)
    except OrcaCLIError as exc:
        click.secho(f"Error: {exc.format_message()}", fg="red", err=True)
        sys.exit(1)
    except click.exceptions.Abort:
        click.echo("\nAborted.", err=True)
        sys.exit(130)
    except Exception as exc:  # pragma: no cover
        click.secho(f"Unexpected error: {exc}", fg="red", err=True)
        sys.exit(2)


if __name__ == "__main__":
    main()
