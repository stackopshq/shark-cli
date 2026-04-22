"""``orca availability-zone`` — manage availability zones (Nova)."""

from __future__ import annotations

import click

from orca_cli.core.context import OrcaContext
from orca_cli.core.output import output_options, print_list
from orca_cli.services.compute import ComputeService


@click.group(name="availability-zone")
@click.pass_context
def availability_zone(ctx: click.Context) -> None:
    """Manage availability zones (Nova)."""
    pass


@availability_zone.command("list")
@click.option("--long", "long_format", is_flag=True, help="Show hosts and services.")
@output_options
@click.pass_context
def az_list(ctx, long_format, output_format, columns, fit_width, max_width, noindent):
    """List availability zones."""
    svc = ComputeService(ctx.find_object(OrcaContext).ensure_client())
    zones = svc.find_availability_zones(detail=long_format)
    print_list(
        zones,
        [
            ("Zone", "zoneName", {"style": "bold"}),
            ("State", lambda z: "[green]available[/green]"
             if z.get("zoneState", {}).get("available") else "[red]unavailable[/red]"),
            ("Hosts", lambda z: str(len(z.get("hosts") or {}))),
        ],
        title="Availability Zones",
        output_format=output_format, columns=columns,
        fit_width=fit_width, max_width=max_width, noindent=noindent,
        empty_msg="No availability zones found.",
    )
