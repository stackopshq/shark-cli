"""Entry point for orca — initialises the Click group and registers sub-commands."""

from __future__ import annotations

import sys

import click

from orca_cli import __version__
from orca_cli.core.context import OrcaContext
from orca_cli.core.exceptions import OrcaCLIError


def _complete_regions(ctx: click.Context, param: click.Parameter, incomplete: str) -> list:
    """Shell completion for the global --region flag."""
    try:
        from orca_cli.core.config import load_config, config_is_complete
        from orca_cli.core.client import OrcaClient

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


# ── Register sub-commands / groups ────────────────────────────────────────

from orca_cli.commands.setup import setup  # noqa: E402
from orca_cli.commands.server import server  # noqa: E402
from orca_cli.commands.flavor import flavor  # noqa: E402
from orca_cli.commands.image import image  # noqa: E402
from orca_cli.commands.network import network  # noqa: E402
from orca_cli.commands.keypair import keypair  # noqa: E402
from orca_cli.commands.volume import volume  # noqa: E402
from orca_cli.commands.security_group import security_group  # noqa: E402
from orca_cli.commands.floating_ip import floating_ip  # noqa: E402
from orca_cli.commands.completion import completion  # noqa: E402
from orca_cli.commands.catalog import catalog  # noqa: E402
from orca_cli.commands.cluster import cluster  # noqa: E402
from orca_cli.commands.metric import metric  # noqa: E402
from orca_cli.commands.secret import secret  # noqa: E402
from orca_cli.commands.loadbalancer import loadbalancer  # noqa: E402
from orca_cli.commands.overview import overview  # noqa: E402
from orca_cli.commands.quota import quota  # noqa: E402
from orca_cli.commands.backup import backup  # noqa: E402
from orca_cli.commands.cleanup import cleanup  # noqa: E402
from orca_cli.commands.ip_whois import ip_cmd  # noqa: E402
from orca_cli.commands.audit import audit  # noqa: E402
from orca_cli.commands.usage import usage  # noqa: E402
from orca_cli.commands.profile import profile  # noqa: E402
from orca_cli.commands.object_store import object_store  # noqa: E402
from orca_cli.commands.stack import stack  # noqa: E402
from orca_cli.commands.auth import auth  # noqa: E402
from orca_cli.commands.event import event  # noqa: E402
from orca_cli.commands.watch import watch  # noqa: E402
from orca_cli.commands.export import export  # noqa: E402
from orca_cli.commands.user import user  # noqa: E402
from orca_cli.commands.project import project  # noqa: E402
from orca_cli.commands.group import group  # noqa: E402
from orca_cli.commands.role import role  # noqa: E402
from orca_cli.commands.domain import domain  # noqa: E402
from orca_cli.commands.application_credential import application_credential  # noqa: E402
from orca_cli.commands.aggregate import aggregate  # noqa: E402
from orca_cli.commands.hypervisor import hypervisor  # noqa: E402
from orca_cli.commands.availability_zone import availability_zone  # noqa: E402
from orca_cli.commands.server_group import server_group  # noqa: E402
from orca_cli.commands.limits import limits  # noqa: E402
from orca_cli.commands.zone import zone  # noqa: E402
from orca_cli.commands.placement import placement  # noqa: E402
from orca_cli.commands.alarm import alarm  # noqa: E402
from orca_cli.commands.policy import policy  # noqa: E402
from orca_cli.commands.federation import (  # noqa: E402
    identity_provider, federation_protocol, mapping, service_provider,
)
from orca_cli.commands.limit import limit, registered_limit  # noqa: E402
from orca_cli.commands.access_rule import access_rule  # noqa: E402
from orca_cli.commands.token import token  # noqa: E402
from orca_cli.commands.endpoint_group import endpoint_group  # noqa: E402
from orca_cli.commands.recordset import recordset  # noqa: E402
from orca_cli.commands.container import container  # noqa: E402
from orca_cli.commands.doctor import doctor  # noqa: E402
from orca_cli.commands.endpoint import endpoint  # noqa: E402
from orca_cli.commands.service import service  # noqa: E402
from orca_cli.commands.credential import credential  # noqa: E402
from orca_cli.commands.region import region  # noqa: E402
from orca_cli.commands.trust import trust  # noqa: E402
from orca_cli.commands.compute_service import compute_service  # noqa: E402
from orca_cli.commands.subnet_pool import subnet_pool  # noqa: E402
from orca_cli.commands.qos_policy import qos_policy  # noqa: E402
from orca_cli.commands.trunk import trunk  # noqa: E402

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
cli.add_command(overview)
cli.add_command(quota)
cli.add_command(backup)
cli.add_command(cleanup)
cli.add_command(ip_cmd)
cli.add_command(audit)
cli.add_command(usage)
cli.add_command(profile)
cli.add_command(object_store)
cli.add_command(stack)
cli.add_command(auth)
cli.add_command(event)
cli.add_command(watch)
cli.add_command(export)
cli.add_command(user)
cli.add_command(project)
cli.add_command(group)
cli.add_command(role)
cli.add_command(domain)
cli.add_command(application_credential)
cli.add_command(aggregate)
cli.add_command(hypervisor)
cli.add_command(availability_zone)
cli.add_command(server_group)
cli.add_command(limits)
cli.add_command(zone)
cli.add_command(placement)
cli.add_command(alarm)
cli.add_command(policy)
cli.add_command(identity_provider)
cli.add_command(federation_protocol)
cli.add_command(mapping)
cli.add_command(service_provider)
cli.add_command(limit)
cli.add_command(registered_limit)
cli.add_command(access_rule)
cli.add_command(token)
cli.add_command(endpoint_group)
cli.add_command(recordset)
cli.add_command(container)
cli.add_command(doctor)
cli.add_command(endpoint)
cli.add_command(service)
cli.add_command(credential)
cli.add_command(region)
cli.add_command(trust)
cli.add_command(compute_service)
cli.add_command(subnet_pool)
cli.add_command(qos_policy)
cli.add_command(trunk)
cli.add_command(completion)


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
