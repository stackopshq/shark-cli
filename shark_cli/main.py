"""Entry point for the shark CLI — initialises the Click group and registers sub-commands."""

from __future__ import annotations

import sys

import click

from shark_cli import __version__
from shark_cli.core.context import SharkContext
from shark_cli.core.exceptions import SharkCLIError


@click.group()
@click.version_option(version=__version__, prog_name="shark-cli")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """shark-cli — Interact with the Sharktech Cloud API from your terminal."""
    ctx.ensure_object(SharkContext)


# ── Register sub-commands / groups ────────────────────────────────────────

from shark_cli.commands.setup import setup  # noqa: E402
from shark_cli.commands.server import server  # noqa: E402
from shark_cli.commands.flavor import flavor  # noqa: E402
from shark_cli.commands.image import image  # noqa: E402
from shark_cli.commands.network import network  # noqa: E402
from shark_cli.commands.keypair import keypair  # noqa: E402
from shark_cli.commands.volume import volume  # noqa: E402
from shark_cli.commands.security_group import security_group  # noqa: E402
from shark_cli.commands.floating_ip import floating_ip  # noqa: E402
from shark_cli.commands.completion import completion  # noqa: E402
from shark_cli.commands.catalog import catalog  # noqa: E402
from shark_cli.commands.cluster import cluster  # noqa: E402
from shark_cli.commands.metric import metric  # noqa: E402
from shark_cli.commands.secret import secret  # noqa: E402
from shark_cli.commands.loadbalancer import loadbalancer  # noqa: E402

cli.add_command(setup)
cli.add_command(server)
cli.add_command(flavor)
cli.add_command(image)
cli.add_command(network)
cli.add_command(keypair)
cli.add_command(volume)
cli.add_command(security_group)
cli.add_command(floating_ip)
cli.add_command(cluster)
cli.add_command(metric)
cli.add_command(secret)
cli.add_command(loadbalancer)
cli.add_command(catalog)
cli.add_command(completion)


def main() -> None:
    """Wrapper used by the ``[tool.poetry.scripts]`` entry-point."""
    try:
        cli(standalone_mode=False)
    except SharkCLIError as exc:
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
