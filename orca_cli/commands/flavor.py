"""``orca flavor`` — manage flavors (Nova)."""

from __future__ import annotations

import click

from orca_cli.core.context import OrcaContext
from orca_cli.core.output import console, output_options, print_detail, print_list
from orca_cli.core.validators import validate_id


@click.group()
@click.pass_context
def flavor(ctx: click.Context) -> None:
    """Manage flavors."""
    pass


@flavor.command("list")
@output_options
@click.pass_context
def flavor_list(ctx: click.Context, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List available flavors."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{client.compute_url}/flavors/detail")

    flavors = sorted(data.get("flavors", []), key=lambda x: (x.get("vcpus", 0), x.get("ram", 0)))

    print_list(
        flavors,
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Name", "name", {"style": "bold"}),
            ("vCPUs", "vcpus", {"justify": "right"}),
            ("RAM (MB)", "ram", {"justify": "right"}),
            ("Disk (GB)", "disk", {"justify": "right"}),
            ("Public", lambda f: "yes" if f.get("os-flavor-access:is_public", True) else "no"),
        ],
        title="Flavors",
        output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent,
        columns=columns,
        empty_msg="No flavors found.",
    )


@flavor.command("show")
@click.argument("flavor_id")
@output_options
@click.pass_context
def flavor_show(ctx: click.Context, flavor_id: str, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show flavor details."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{client.compute_url}/flavors/{flavor_id}")
    f = data.get("flavor", data)

    extra = f.get("extra_specs") or {}
    fields = [
        ("ID", f.get("id", "")),
        ("Name", f.get("name", "")),
        ("vCPUs", str(f.get("vcpus", ""))),
        ("RAM (MB)", str(f.get("ram", ""))),
        ("Disk (GB)", str(f.get("disk", ""))),
        ("Ephemeral (GB)", str(f.get("OS-FLV-EXT-DATA:ephemeral", 0))),
        ("Swap (MB)", str(f.get("swap", "") or 0)),
        ("RX Factor", str(f.get("rxtx_factor", 1.0))),
        ("Public", "yes" if f.get("os-flavor-access:is_public", True) else "no"),
    ]
    if extra:
        for k, v in extra.items():
            fields.append((f"  {k}", str(v)))

    print_detail(fields, output_format=output_format, columns=columns,
                 fit_width=fit_width, max_width=max_width, noindent=noindent)


@flavor.command("create")
@click.argument("name")
@click.option("--vcpus", type=int, required=True, help="Number of vCPUs.")
@click.option("--ram", type=int, required=True, help="RAM in MB.")
@click.option("--disk", type=int, default=0, show_default=True, help="Root disk size in GB.")
@click.option("--ephemeral", type=int, default=0, show_default=True, help="Ephemeral disk in GB.")
@click.option("--swap", type=int, default=0, show_default=True, help="Swap disk in MB.")
@click.option("--rxtx-factor", type=float, default=1.0, show_default=True, help="RX/TX factor.")
@click.option("--public/--private", "is_public", default=True, show_default=True,
              help="Make flavor public or private.")
@click.option("--id", "flavor_id", default="auto", show_default=True,
              help="Flavor ID (auto-generated if 'auto').")
@click.pass_context
def flavor_create(ctx: click.Context, name: str, vcpus: int, ram: int, disk: int,
                  ephemeral: int, swap: int, rxtx_factor: float, is_public: bool,
                  flavor_id: str) -> None:
    """Create a flavor."""
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {
        "name": name, "vcpus": vcpus, "ram": ram, "disk": disk,
        "OS-FLV-EXT-DATA:ephemeral": ephemeral,
        "rxtx_factor": rxtx_factor,
        "os-flavor-access:is_public": is_public,
    }
    if swap:
        body["swap"] = swap
    if flavor_id != "auto":
        body["id"] = flavor_id

    data = client.post(f"{client.compute_url}/flavors", json={"flavor": body})
    f = data.get("flavor", data)
    console.print(f"[green]Flavor '{f.get('name')}' ({f.get('id')}) created.[/green]")


@flavor.command("delete")
@click.argument("flavor_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def flavor_delete(ctx: click.Context, flavor_id: str, yes: bool) -> None:
    """Delete a flavor."""
    if not yes:
        click.confirm(f"Delete flavor {flavor_id}?", abort=True)
    client = ctx.find_object(OrcaContext).ensure_client()
    client.delete(f"{client.compute_url}/flavors/{flavor_id}")
    console.print(f"[green]Flavor {flavor_id} deleted.[/green]")


@flavor.command("set")
@click.argument("flavor_id")
@click.option("--property", "properties", multiple=True, metavar="KEY=VALUE",
              help="Extra spec key=value (repeatable).")
@click.pass_context
def flavor_set(ctx: click.Context, flavor_id: str, properties: tuple[str, ...]) -> None:
    """Set extra specs on a flavor.

    \b
    Examples:
      orca flavor set <id> --property hw:cpu_policy=dedicated
      orca flavor set <id> --property hw:mem_page_size=large --property aggregate_instance_extra_specs:ssd=true
    """
    if not properties:
        console.print("[yellow]No properties specified.[/yellow]")
        return
    client = ctx.find_object(OrcaContext).ensure_client()
    specs = {}
    for prop in properties:
        if "=" not in prop:
            raise click.UsageError(f"Invalid property format '{prop}', expected KEY=VALUE.")
        k, v = prop.split("=", 1)
        specs[k] = v
    client.post(f"{client.compute_url}/flavors/{flavor_id}/os-extra-specs",
                json={"extra_specs": specs})
    console.print(f"[green]Extra specs updated on flavor {flavor_id}.[/green]")


@flavor.command("unset")
@click.argument("flavor_id")
@click.option("--property", "properties", multiple=True, metavar="KEY",
              help="Extra spec key to remove (repeatable).")
@click.pass_context
def flavor_unset(ctx: click.Context, flavor_id: str, properties: tuple[str, ...]) -> None:
    """Unset extra specs from a flavor."""
    if not properties:
        console.print("[yellow]No properties specified.[/yellow]")
        return
    client = ctx.find_object(OrcaContext).ensure_client()
    for key in properties:
        client.delete(f"{client.compute_url}/flavors/{flavor_id}/os-extra-specs/{key}")
    console.print(f"[green]Extra specs removed from flavor {flavor_id}.[/green]")


# ── flavor access (private flavors) ───────────────────────────────────────

@flavor.command("access-list")
@click.argument("flavor_id", callback=validate_id)
@output_options
@click.pass_context
def flavor_access_list(ctx: click.Context, flavor_id: str,
                       output_format: str, columns: tuple[str, ...],
                       fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List projects that have access to a private flavor."""
    client = ctx.find_object(OrcaContext).ensure_client()
    accesses = client.get(
        f"{client.compute_url}/flavors/{flavor_id}/os-flavor-access"
    ).get("flavor_access", [])

    print_list(
        accesses,
        [
            ("Flavor ID", "flavor_id", {"style": "cyan"}),
            ("Project ID", "tenant_id", {"style": "bold"}),
        ],
        title=f"Access list for flavor {flavor_id}",
        output_format=output_format, fit_width=fit_width, max_width=max_width,
        noindent=noindent, columns=columns,
        empty_msg="No access entries (flavor may be public).",
    )


@flavor.command("access-add")
@click.argument("flavor_id", callback=validate_id)
@click.argument("project_id", callback=validate_id)
@click.pass_context
def flavor_access_add(ctx: click.Context, flavor_id: str, project_id: str) -> None:
    """Grant a project access to a private flavor."""
    client = ctx.find_object(OrcaContext).ensure_client()
    client.post(
        f"{client.compute_url}/flavors/{flavor_id}/action",
        json={"addTenantAccess": {"tenant": project_id}},
    )
    console.print(f"[green]Project {project_id} now has access to flavor {flavor_id}.[/green]")


@flavor.command("access-remove")
@click.argument("flavor_id", callback=validate_id)
@click.argument("project_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def flavor_access_remove(ctx: click.Context, flavor_id: str, project_id: str, yes: bool) -> None:
    """Revoke a project's access to a private flavor."""
    client = ctx.find_object(OrcaContext).ensure_client()
    if not yes:
        click.confirm(f"Remove project {project_id} from flavor {flavor_id}?", abort=True)
    client.post(
        f"{client.compute_url}/flavors/{flavor_id}/action",
        json={"removeTenantAccess": {"tenant": project_id}},
    )
    console.print(f"[green]Project {project_id} access to flavor {flavor_id} revoked.[/green]")
