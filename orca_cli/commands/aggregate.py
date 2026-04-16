"""``orca aggregate`` — manage host aggregates (Nova)."""

from __future__ import annotations

import click

from orca_cli.core.context import OrcaContext
from orca_cli.core.output import output_options, print_list, print_detail, console


def _nova(client) -> str:
    return client.compute_url


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
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_nova(client)}/os-aggregates")
    print_list(
        data.get("aggregates", []),
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
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_nova(client)}/os-aggregates/{aggregate_id}")
    a = data.get("aggregate", data)
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
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {"name": name}
    if availability_zone:
        body["availability_zone"] = availability_zone
    data = client.post(f"{_nova(client)}/os-aggregates", json={"aggregate": body})
    a = data.get("aggregate", data)
    console.print(f"[green]Aggregate '{a.get('name')}' ({a.get('id')}) created.[/green]")


@aggregate.command("delete")
@click.argument("aggregate_id")
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def aggregate_delete(ctx, aggregate_id, yes):
    """Delete a host aggregate."""
    if not yes:
        click.confirm(f"Delete aggregate {aggregate_id}?", abort=True)
    client = ctx.find_object(OrcaContext).ensure_client()
    client.delete(f"{_nova(client)}/os-aggregates/{aggregate_id}")
    console.print(f"[green]Aggregate {aggregate_id} deleted.[/green]")


@aggregate.command("add-host")
@click.argument("aggregate_id")
@click.argument("host")
@click.pass_context
def aggregate_add_host(ctx, aggregate_id, host):
    """Add a host to an aggregate."""
    client = ctx.find_object(OrcaContext).ensure_client()
    client.post(f"{_nova(client)}/os-aggregates/{aggregate_id}/action",
                json={"add_host": {"host": host}})
    console.print(f"[green]Host '{host}' added to aggregate {aggregate_id}.[/green]")


@aggregate.command("remove-host")
@click.argument("aggregate_id")
@click.argument("host")
@click.pass_context
def aggregate_remove_host(ctx, aggregate_id, host):
    """Remove a host from an aggregate."""
    client = ctx.find_object(OrcaContext).ensure_client()
    client.post(f"{_nova(client)}/os-aggregates/{aggregate_id}/action",
                json={"remove_host": {"host": host}})
    console.print(f"[green]Host '{host}' removed from aggregate {aggregate_id}.[/green]")


@aggregate.command("set")
@click.argument("aggregate_id")
@click.option("--name", default=None, help="New name.")
@click.option("--zone", "availability_zone", default=None, help="New availability zone.")
@click.option("--property", "properties", multiple=True, metavar="KEY=VALUE",
              help="Metadata key=value (repeatable).")
@click.pass_context
def aggregate_set(ctx, aggregate_id, name, availability_zone, properties):
    """Update an aggregate's name, AZ, or metadata."""
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {}
    if name:
        body["name"] = name
    if availability_zone:
        body["availability_zone"] = availability_zone

    if body:
        client.put(f"{_nova(client)}/os-aggregates/{aggregate_id}",
                   json={"aggregate": body})

    if properties:
        meta = {}
        for prop in properties:
            if "=" not in prop:
                raise click.UsageError(f"Invalid format '{prop}', expected KEY=VALUE.")
            k, v = prop.split("=", 1)
            meta[k] = v
        client.post(f"{_nova(client)}/os-aggregates/{aggregate_id}/action",
                    json={"set_metadata": {"metadata": meta}})

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
    client = ctx.find_object(OrcaContext).ensure_client()
    # Setting a key to None removes it from the aggregate metadata
    meta = {k: None for k in properties}
    client.post(f"{_nova(client)}/os-aggregates/{aggregate_id}/action",
                json={"set_metadata": {"metadata": meta}})
    console.print(f"[green]Aggregate {aggregate_id} properties removed.[/green]")


@aggregate.command("cache-image")
@click.argument("aggregate_id")
@click.argument("image_ids", nargs=-1, required=True)
@click.pass_context
def aggregate_cache_image(ctx, aggregate_id, image_ids):
    """Request that images be cached on hosts in an aggregate.

    \b
    Examples:
      orca aggregate cache-image <agg-id> <image-id>
      orca aggregate cache-image <agg-id> <img1> <img2>
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    client.post(f"{_nova(client)}/os-aggregates/{aggregate_id}/images",
                json={"cache": [{"id": iid} for iid in image_ids]})
    console.print(f"[green]Image caching requested on aggregate {aggregate_id}.[/green]")
