"""``orca subnet-pool`` — manage Neutron subnet pools (IPAM)."""

from __future__ import annotations

import click

from orca_cli.core.context import OrcaContext
from orca_cli.core.output import console, output_options, print_detail, print_list
from orca_cli.core.validators import validate_id


@click.group("subnet-pool")
def subnet_pool() -> None:
    """Manage Neutron subnet pools for automatic IP allocation."""
    pass


@subnet_pool.command("list")
@click.option("--shared", is_flag=True, default=False, help="Show only shared pools.")
@click.option("--default", "is_default", is_flag=True, default=False,
              help="Show only the default pool.")
@output_options
@click.pass_context
def subnet_pool_list(ctx, shared, is_default,
                     output_format, columns, fit_width, max_width, noindent):
    """List subnet pools."""
    client = ctx.find_object(OrcaContext).ensure_client()
    params = {}
    if shared:
        params["shared"] = True
    if is_default:
        params["is_default"] = True
    pools = client.get(f"{client.network_url}/v2.0/subnetpools",
                       params=params).get("subnetpools", [])
    print_list(
        pools,
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Name", "name", {"style": "bold"}),
            ("Prefixes", lambda p: ", ".join(p.get("prefixes", []))[:40]),
            ("Default PL", "default_prefixlen"),
            ("Min PL", "min_prefixlen"),
            ("Max PL", "max_prefixlen"),
            ("Shared", lambda p: "Yes" if p.get("shared") else "No"),
            ("Default", lambda p: "Yes" if p.get("is_default") else "No"),
        ],
        title="Subnet Pools",
        output_format=output_format, fit_width=fit_width, max_width=max_width,
        noindent=noindent, columns=columns,
        empty_msg="No subnet pools found.",
    )


@subnet_pool.command("show")
@click.argument("pool_id", callback=validate_id)
@output_options
@click.pass_context
def subnet_pool_show(ctx, pool_id,
                     output_format, columns, fit_width, max_width, noindent):
    """Show subnet pool details."""
    client = ctx.find_object(OrcaContext).ensure_client()
    p = client.get(f"{client.network_url}/v2.0/subnetpools/{pool_id}").get("subnetpool", {})
    fields = [(k, str(p.get(k, "") or "")) for k in
              ["id", "name", "default_prefixlen", "min_prefixlen", "max_prefixlen",
               "shared", "is_default", "ip_version", "description"]]
    fields.append(("prefixes", ", ".join(p.get("prefixes", []))))
    print_detail(fields, output_format=output_format, fit_width=fit_width,
                 max_width=max_width, noindent=noindent, columns=columns)


@subnet_pool.command("create")
@click.option("--name", required=True, help="Pool name.")
@click.option("--pool-prefix", "prefixes", required=True, multiple=True,
              help="CIDR prefix for the pool (repeatable).")
@click.option("--default-prefix-length", "default_prefixlen", type=int, default=None,
              help="Default prefix length for subnets from this pool.")
@click.option("--min-prefix-length", "min_prefixlen", type=int, default=None,
              help="Minimum prefix length.")
@click.option("--max-prefix-length", "max_prefixlen", type=int, default=None,
              help="Maximum prefix length.")
@click.option("--shared", is_flag=True, default=False, help="Make the pool shared.")
@click.option("--default", "is_default", is_flag=True, default=False,
              help="Set as the default pool.")
@click.option("--description", default=None, help="Description.")
@click.pass_context
def subnet_pool_create(ctx, name, prefixes, default_prefixlen, min_prefixlen,
                       max_prefixlen, shared, is_default, description):
    """Create a subnet pool.

    \b
    Example:
      orca subnet-pool create \\
        --name my-pool \\
        --pool-prefix 10.0.0.0/8 \\
        --default-prefix-length 24
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {"name": name, "prefixes": list(prefixes), "shared": shared,
                  "is_default": is_default}
    if default_prefixlen is not None:
        body["default_prefixlen"] = default_prefixlen
    if min_prefixlen is not None:
        body["min_prefixlen"] = min_prefixlen
    if max_prefixlen is not None:
        body["max_prefixlen"] = max_prefixlen
    if description:
        body["description"] = description
    p = client.post(f"{client.network_url}/v2.0/subnetpools",
                    json={"subnetpool": body}).get("subnetpool", {})
    console.print(f"[green]Subnet pool '{name}' created: {p.get('id', '?')}[/green]")


@subnet_pool.command("set")
@click.argument("pool_id", callback=validate_id)
@click.option("--name", default=None, help="New name.")
@click.option("--description", default=None, help="New description.")
@click.option("--default-prefix-length", "default_prefixlen", type=int, default=None,
              help="New default prefix length.")
@click.option("--pool-prefix", "prefixes", multiple=True,
              help="Add a prefix to the pool (repeatable).")
@click.option("--default/--no-default", "is_default", default=None,
              help="Set or unset as the default pool.")
@click.pass_context
def subnet_pool_set(ctx, pool_id, name, description, default_prefixlen,
                    prefixes, is_default):
    """Update a subnet pool."""
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {}
    if name is not None:
        body["name"] = name
    if description is not None:
        body["description"] = description
    if default_prefixlen is not None:
        body["default_prefixlen"] = default_prefixlen
    if prefixes:
        # Fetch existing and merge
        existing = client.get(
            f"{client.network_url}/v2.0/subnetpools/{pool_id}"
        ).get("subnetpool", {}).get("prefixes", [])
        body["prefixes"] = list(set(existing) | set(prefixes))
    if is_default is not None:
        body["is_default"] = is_default
    if not body:
        console.print("[yellow]Nothing to update.[/yellow]")
        return
    client.put(f"{client.network_url}/v2.0/subnetpools/{pool_id}",
               json={"subnetpool": body})
    console.print(f"[green]Subnet pool {pool_id} updated.[/green]")


@subnet_pool.command("delete")
@click.argument("pool_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def subnet_pool_delete(ctx, pool_id, yes):
    """Delete a subnet pool."""
    client = ctx.find_object(OrcaContext).ensure_client()
    if not yes:
        click.confirm(f"Delete subnet pool {pool_id}?", abort=True)
    client.delete(f"{client.network_url}/v2.0/subnetpools/{pool_id}")
    console.print(f"[green]Subnet pool {pool_id} deleted.[/green]")
