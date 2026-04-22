"""``orca region`` — manage Keystone regions."""

from __future__ import annotations

import click

from orca_cli.core.context import OrcaContext
from orca_cli.core.output import console, output_options, print_detail, print_list
from orca_cli.services.identity import IdentityService


@click.group()
def region() -> None:
    """Manage Keystone regions."""
    pass


@region.command("list")
@click.option("--parent", default=None, help="Filter by parent region ID.")
@output_options
@click.pass_context
def region_list(ctx, parent, output_format, columns, fit_width, max_width, noindent):
    """List regions."""
    svc = IdentityService(ctx.find_object(OrcaContext).ensure_client())
    params = {}
    if parent:
        params["parent_region_id"] = parent

    regions = svc.find_regions(params=params or None)

    print_list(
        regions,
        [
            ("ID", "id", {"style": "bold cyan"}),
            ("Description", lambda r: (r.get("description") or "")[:60]),
            ("Parent Region", lambda r: r.get("parent_region_id") or "—"),
        ],
        title="Regions",
        output_format=output_format, fit_width=fit_width, max_width=max_width,
        noindent=noindent, columns=columns,
        empty_msg="No regions found.",
    )


@region.command("show")
@click.argument("region_id")
@output_options
@click.pass_context
def region_show(ctx, region_id, output_format, columns, fit_width, max_width, noindent):
    """Show region details."""
    svc = IdentityService(ctx.find_object(OrcaContext).ensure_client())
    reg = svc.get_region(region_id)

    print_detail(
        [(k, str(reg.get(k, "") or "")) for k in
         ["id", "description", "parent_region_id"]],
        output_format=output_format, fit_width=fit_width, max_width=max_width,
        noindent=noindent, columns=columns,
    )


@region.command("create")
@click.argument("region_id", metavar="ID")
@click.option("--description", default=None, help="Region description.")
@click.option("--parent", default=None, help="Parent region ID.")
@click.pass_context
def region_create(ctx, region_id, description, parent):
    """Create a region.

    \b
    The ID is the region name (e.g. RegionOne, dc3-a).
    """
    svc = IdentityService(ctx.find_object(OrcaContext).ensure_client())
    body: dict = {"id": region_id}
    if description:
        body["description"] = description
    if parent:
        body["parent_region_id"] = parent

    svc.create_region(body)
    console.print(f"[green]Region '{region_id}' created.[/green]")


@region.command("set")
@click.argument("region_id")
@click.option("--description", default=None, help="New description.")
@click.pass_context
def region_set(ctx, region_id, description):
    """Update a region's description."""
    if description is None:
        console.print("[yellow]Nothing to update. Use --description.[/yellow]")
        return
    svc = IdentityService(ctx.find_object(OrcaContext).ensure_client())
    svc.update_region(region_id, {"description": description})
    console.print(f"[green]Region '{region_id}' updated.[/green]")


@region.command("delete")
@click.argument("region_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def region_delete(ctx, region_id, yes):
    """Delete a region."""
    svc = IdentityService(ctx.find_object(OrcaContext).ensure_client())
    if not yes:
        click.confirm(f"Delete region '{region_id}'?", abort=True)
    svc.delete_region(region_id)
    console.print(f"[green]Region '{region_id}' deleted.[/green]")
