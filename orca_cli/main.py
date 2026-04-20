"""Entry point for orca — initialises the Click group and lazy-resolves sub-commands.

Commands live in ``orca_cli/commands/<name>.py``. The mapping
``command_name -> module_name`` follows the convention
``module_name.replace("_", "-")``, with a few explicit overrides for files
that expose either a different command name or several top-level commands
(e.g. ``federation.py`` publishes 4 groups).

Modules are imported lazily — only when their command is actually invoked —
so ``orca <cmd>`` startup pays for one module's import, not all 60+. The one
exception is ``orca --help``, which still walks every command to print its
short description.

Adding a new command: drop a file into ``orca_cli/commands/`` with a
``@click.group()`` (or ``@click.command()``) at module level. If the
command name doesn't match the filename or if the module exposes more than
one top-level command, add an entry to ``_COMMAND_OVERRIDES`` below.
"""

from __future__ import annotations

import importlib
import logging
import pkgutil
import sys
from pathlib import Path
from typing import Any

import click

from orca_cli import __version__
from orca_cli.core.context import OrcaContext
from orca_cli.core.exceptions import OrcaCLIError

# Modules whose published command name(s) don't follow the filename convention.
# Keys are module basenames (no .py); values are the list of command names the
# module exposes at root level.
_COMMAND_OVERRIDES: dict[str, list[str]] = {
    "federation": ["federation-protocol", "identity-provider", "mapping", "service-provider"],
    "limit": ["limit", "registered-limit"],
    "ip_whois": ["ip"],
    "object_store": ["object"],
    "qos_policy": ["qos"],
}


class LazyOrcaGroup(click.Group):
    """A click.Group that imports each command's module only on first use.

    The command-name → module-name index is built once at construction time
    by scanning ``orca_cli/commands/`` directory entries (no imports). Each
    ``get_command`` call then imports exactly one module.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._cmd_to_module: dict[str, str] = self._build_index()

    @staticmethod
    def _build_index() -> dict[str, str]:
        pkg = importlib.import_module("orca_cli.commands")
        pkg_path = Path(pkg.__file__).parent
        index: dict[str, str] = {}
        for mi in pkgutil.iter_modules([str(pkg_path)]):
            if mi.ispkg or mi.name.startswith("_"):
                continue
            names = _COMMAND_OVERRIDES.get(mi.name, [mi.name.replace("_", "-")])
            for name in names:
                index[name] = mi.name
        return index

    def list_commands(self, ctx: click.Context) -> list[str]:
        return sorted(self._cmd_to_module)

    def get_command(self, ctx: click.Context, name: str) -> click.Command | None:
        module_name = self._cmd_to_module.get(name)
        if module_name is None:
            return None
        mod = importlib.import_module(f"orca_cli.commands.{module_name}")
        for attr in dir(mod):
            if attr.startswith("_"):
                continue
            obj = getattr(mod, attr)
            if not isinstance(obj, click.Command) or obj.name != name:
                continue
            cb = getattr(obj, "callback", None)
            if cb is None or getattr(cb, "__module__", None) != mod.__name__:
                continue
            return obj
        return None


def _enable_debug_logging() -> None:
    """Configure root logger for --debug output on stderr.

    Keeps the format short so debug lines don't wreck terminal formatting
    when interleaved with rich table output. Level is applied to the
    ``orca_cli`` tree only — third-party libraries (httpx, urllib3) stay
    quiet unless the user explicitly wants them.
    """
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(logging.Formatter("[%(asctime)s %(levelname)s %(name)s] %(message)s",
                                           datefmt="%H:%M:%S"))
    orca_logger = logging.getLogger("orca_cli")
    orca_logger.setLevel(logging.DEBUG)
    orca_logger.addHandler(handler)
    # Don't propagate to the root logger; avoids duplicate lines if the
    # user has pre-configured logging in a wrapping script.
    orca_logger.propagate = False
    click.secho(
        "DEBUG mode enabled — request URLs and retry decisions will be logged to stderr. "
        "Credentials are redacted, but response bodies may contain sensitive data.",
        fg="yellow", err=True,
    )


def _complete_regions(ctx: click.Context, param: click.Parameter, incomplete: str) -> list:  # pragma: no cover
    """Shell completion for the global --region flag.

    Invoked by the shell, not exercised in pytest. Best-effort: all exceptions
    swallow to empty — never crash the user's tab key. Results are cached for
    30 seconds to avoid a Keystone round-trip on every Tab press.
    """
    try:
        from orca_cli.core import cache

        cached = cache.load(None, "regions")
        if cached is not None:
            return sorted(r["id"] for r in cached if r["id"].startswith(incomplete))

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
        cache.save(None, "regions", [{"id": r} for r in sorted(regions)])
        return sorted(r for r in regions if r.startswith(incomplete))
    except Exception:
        return []


@click.group(cls=LazyOrcaGroup)
@click.version_option(version=__version__, prog_name="orca")
@click.option("--profile", "-P", default=None, envvar="ORCA_PROFILE",
              help="Config profile to use (overrides active profile).")
@click.option("--region", "-R", default=None, envvar="ORCA_REGION",
              shell_complete=_complete_regions,
              help="Region to use (overrides profile region_name).")
@click.option("--debug", is_flag=True, envvar="ORCA_DEBUG",
              help="Log HTTP requests, retries, and auth decisions to stderr.")
@click.pass_context
def cli(ctx: click.Context, profile: str | None, region: str | None,
        debug: bool) -> None:
    """orca — OpenStack Rich Command-line Alternative."""
    if debug:
        _enable_debug_logging()
    orca_ctx = ctx.ensure_object(OrcaContext)
    orca_ctx.profile = profile
    orca_ctx.region = region


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
