"""``orca aggregate`` — manage host aggregates (Nova)."""

from __future__ import annotations

import click

from orca_cli.core.aliases import add_command_with_alias
from orca_cli.core.context import OrcaContext
from orca_cli.core.exceptions import OrcaCLIError
from orca_cli.core.output import console, output_options, print_detail, print_list
from orca_cli.services.compute import ComputeService


@click.group()
@click.pass_context
def aggregate(ctx: click.Context) -> None:
    """Manage host aggregates (Nova)."""
    pass


@aggregate.command("list")
@output_options
@click.pass_context
def aggregate_list(ctx, output_format, columns, fit_width, max_width, noindent):
    """List host aggregates."""
    svc = ComputeService(ctx.find_object(OrcaContext).ensure_client())
    print_list(
        svc.find_aggregates(),
        [
            ("ID", "id", {"style": "cyan"}),
            ("Name", "name", {"style": "bold"}),
            ("AZ", lambda a: a.get("availability_zone") or "—"),
            ("Hosts", lambda a: str(len(a.get("hosts", [])))),
            ("Metadata", lambda a: ", ".join(f"{k}={v}" for k, v in (a.get("metadata") or {}).items()) or "—"),
        ],
        title="Host Aggregates",
        output_format=output_format, columns=columns,
        fit_width=fit_width, max_width=max_width, noindent=noindent,
        empty_msg="No aggregates found.",
    )


@aggregate.command("show")
@click.argument("aggregate_id")
@output_options
@click.pass_context
def aggregate_show(ctx, aggregate_id, output_format, columns, fit_width, max_width, noindent):
    """Show aggregate details."""
    svc = ComputeService(ctx.find_object(OrcaContext).ensure_client())
    a = svc.get_aggregate(aggregate_id)
    print_detail(
        [
            ("ID", str(a.get("id", ""))),
            ("Name", a.get("name", "")),
            ("Availability Zone", a.get("availability_zone") or "—"),
            ("Hosts", ", ".join(a.get("hosts", [])) or "—"),
            ("Metadata", ", ".join(f"{k}={v}" for k, v in (a.get("metadata") or {}).items()) or "—"),
            ("Created", a.get("created_at", "")),
            ("Updated", a.get("updated_at") or "—"),
        ],
        output_format=output_format, columns=columns,
        fit_width=fit_width, max_width=max_width, noindent=noindent,
    )


@aggregate.command("create")
@click.argument("name")
@click.option("--zone", "availability_zone", default=None, help="Availability zone name.")
@click.pass_context
def aggregate_create(ctx, name, availability_zone):
    """Create a host aggregate."""
    svc = ComputeService(ctx.find_object(OrcaContext).ensure_client())
    body: dict = {"name": name}
    if availability_zone:
        body["availability_zone"] = availability_zone
    a = svc.create_aggregate(body)
    console.print(f"[green]Aggregate '{a.get('name')}' ({a.get('id')}) created.[/green]")


@aggregate.command("delete")
@click.argument("aggregate_id")
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def aggregate_delete(ctx, aggregate_id, yes):
    """Delete a host aggregate."""
    if not yes:
        click.confirm(f"Delete aggregate {aggregate_id}?", abort=True)
    svc = ComputeService(ctx.find_object(OrcaContext).ensure_client())
    svc.delete_aggregate(aggregate_id)
    console.print(f"[green]Aggregate {aggregate_id} deleted.[/green]")


@aggregate.group("host")
def aggregate_host() -> None:
    """Manage hosts inside an aggregate."""


@aggregate_host.command("add")
@click.argument("aggregate_id")
@click.argument("host")
@click.pass_context
def aggregate_host_add(ctx, aggregate_id, host):
    """Add a host to an aggregate."""
    svc = ComputeService(ctx.find_object(OrcaContext).ensure_client())
    svc.add_aggregate_host(aggregate_id, host)
    console.print(f"[green]Host '{host}' added to aggregate {aggregate_id}.[/green]")


@aggregate_host.command("remove")
@click.argument("aggregate_id")
@click.argument("host")
@click.pass_context
def aggregate_host_remove(ctx, aggregate_id, host):
    """Remove a host from an aggregate."""
    svc = ComputeService(ctx.find_object(OrcaContext).ensure_client())
    svc.remove_aggregate_host(aggregate_id, host)
    console.print(f"[green]Host '{host}' removed from aggregate {aggregate_id}.[/green]")


add_command_with_alias(aggregate, aggregate_host_add,
                        legacy_name="add-host", primary_path="aggregate host add")
add_command_with_alias(aggregate, aggregate_host_remove,
                        legacy_name="remove-host", primary_path="aggregate host remove")


@aggregate.command("set")
@click.argument("aggregate_id")
@click.option("--name", default=None, help="New name.")
@click.option("--zone", "availability_zone", default=None, help="New availability zone.")
@click.option("--property", "properties", multiple=True, metavar="KEY=VALUE",
              help="Metadata key=value (repeatable).")
@click.pass_context
def aggregate_set(ctx, aggregate_id, name, availability_zone, properties):
    """Update an aggregate's name, AZ, or metadata."""
    svc = ComputeService(ctx.find_object(OrcaContext).ensure_client())
    body: dict = {}
    if name:
        body["name"] = name
    if availability_zone:
        body["availability_zone"] = availability_zone

    if body:
        svc.update_aggregate(aggregate_id, body)

    if properties:
        meta = {}
        for prop in properties:
            if "=" not in prop:
                raise OrcaCLIError(f"Invalid format '{prop}', expected KEY=VALUE.")
            k, v = prop.split("=", 1)
            meta[k] = v
        svc.set_aggregate_metadata(aggregate_id, meta)

    if not body and not properties:
        console.print("[yellow]Nothing to update.[/yellow]")
        return
    console.print(f"[green]Aggregate {aggregate_id} updated.[/green]")


@aggregate.command("unset")
@click.argument("aggregate_id")
@click.option("--property", "properties", multiple=True, metavar="KEY",
              help="Metadata key to remove (repeatable).")
@click.pass_context
def aggregate_unset(ctx, aggregate_id, properties):
    """Unset metadata properties on an aggregate."""
    if not properties:
        console.print("[yellow]Nothing to unset.[/yellow]")
        return
    svc = ComputeService(ctx.find_object(OrcaContext).ensure_client())
    # Setting a key to None removes it from the aggregate metadata
    meta = {k: None for k in properties}
    svc.set_aggregate_metadata(aggregate_id, meta)
    console.print(f"[green]Aggregate {aggregate_id} properties removed.[/green]")


@aggregate.group("image")
def aggregate_image() -> None:
    """Manage image caching on aggregates."""


@aggregate_image.command("cache")
@click.argument("aggregate_id")
@click.argument("image_ids", nargs=-1, required=True)
@click.pass_context
def aggregate_image_cache(ctx, aggregate_id, image_ids):
    """Request that images be cached on hosts in an aggregate.

    \b
    Examples:
      orca aggregate image cache <agg-id> <image-id>
      orca aggregate image cache <agg-id> <img1> <img2>
    """
    svc = ComputeService(ctx.find_object(OrcaContext).ensure_client())
    svc.cache_aggregate_images(aggregate_id, [{"id": iid} for iid in image_ids])
    console.print(f"[green]Image caching requested on aggregate {aggregate_id}.[/green]")


add_command_with_alias(aggregate, aggregate_image_cache,
                        legacy_name="cache-image",
                        primary_path="aggregate image cache")
