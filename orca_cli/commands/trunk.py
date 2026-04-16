"""``orca trunk`` — manage Neutron trunks (VLAN sub-interfaces)."""

from __future__ import annotations

import click

from orca_cli.core.context import OrcaContext
from orca_cli.core.output import console, output_options, print_detail, print_list
from orca_cli.core.validators import validate_id

_TRUNK_BASE = "/v2.0/trunks"


@click.group("trunk")
def trunk() -> None:
    """Manage Neutron trunks (VLAN trunk ports)."""
    pass


@trunk.command("list")
@output_options
@click.pass_context
def trunk_list(ctx, output_format, columns, fit_width, max_width, noindent):
    """List trunks."""
    client = ctx.find_object(OrcaContext).ensure_client()
    trunks = client.get(f"{client.network_url}{_TRUNK_BASE}").get("trunks", [])
    print_list(
        trunks,
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Name", "name", {"style": "bold"}),
            ("Port ID", "port_id"),
            ("Status", "status"),
            ("Admin State", lambda t: "UP" if t.get("admin_state_up") else "DOWN"),
        ],
        title="Trunks",
        output_format=output_format, fit_width=fit_width, max_width=max_width,
        noindent=noindent, columns=columns,
        empty_msg="No trunks found.",
    )


@trunk.command("show")
@click.argument("trunk_id", callback=validate_id)
@output_options
@click.pass_context
def trunk_show(ctx, trunk_id, output_format, columns, fit_width, max_width, noindent):
    """Show trunk details."""
    client = ctx.find_object(OrcaContext).ensure_client()
    t = client.get(f"{client.network_url}{_TRUNK_BASE}/{trunk_id}").get("trunk", {})
    fields = [(k, str(t.get(k, "") or "")) for k in
              ["id", "name", "port_id", "status", "admin_state_up",
               "description", "project_id"]]
    sub_ports = t.get("sub_ports", [])
    fields.append(("sub_ports", str(len(sub_ports))))
    print_detail(fields, output_format=output_format, fit_width=fit_width,
                 max_width=max_width, noindent=noindent, columns=columns)


@trunk.command("create")
@click.option("--port", "port_id", required=True, callback=validate_id,
              help="Parent port ID (the trunk port).")
@click.option("--name", default=None, help="Trunk name.")
@click.option("--description", default=None, help="Description.")
@click.option("--disable", "admin_state_up", is_flag=True, default=False,
              help="Create trunk in administratively down state.")
@click.pass_context
def trunk_create(ctx, port_id, name, description, admin_state_up):
    """Create a trunk."""
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {"port_id": port_id, "admin_state_up": not admin_state_up}
    if name:
        body["name"] = name
    if description:
        body["description"] = description
    t = client.post(f"{client.network_url}{_TRUNK_BASE}",
                    json={"trunk": body}).get("trunk", {})
    console.print(f"[green]Trunk created: {t.get('id', '?')}[/green]")


@trunk.command("set")
@click.argument("trunk_id", callback=validate_id)
@click.option("--name", default=None, help="New name.")
@click.option("--description", default=None, help="New description.")
@click.option("--enable/--disable", "admin_state_up", default=None,
              help="Enable or disable the trunk.")
@click.pass_context
def trunk_set(ctx, trunk_id, name, description, admin_state_up):
    """Update a trunk."""
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {}
    if name is not None:
        body["name"] = name
    if description is not None:
        body["description"] = description
    if admin_state_up is not None:
        body["admin_state_up"] = admin_state_up
    if not body:
        console.print("[yellow]Nothing to update.[/yellow]")
        return
    client.put(f"{client.network_url}{_TRUNK_BASE}/{trunk_id}", json={"trunk": body})
    console.print(f"[green]Trunk {trunk_id} updated.[/green]")


@trunk.command("delete")
@click.argument("trunk_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def trunk_delete(ctx, trunk_id, yes):
    """Delete a trunk."""
    client = ctx.find_object(OrcaContext).ensure_client()
    if not yes:
        click.confirm(f"Delete trunk {trunk_id}?", abort=True)
    client.delete(f"{client.network_url}{_TRUNK_BASE}/{trunk_id}")
    console.print(f"[green]Trunk {trunk_id} deleted.[/green]")


# ── Sub-ports ──────────────────────────────────────────────────────────────

@trunk.command("subport-list")
@click.argument("trunk_id", callback=validate_id)
@output_options
@click.pass_context
def trunk_subport_list(ctx, trunk_id, output_format, columns, fit_width, max_width, noindent):
    """List sub-ports on a trunk."""
    client = ctx.find_object(OrcaContext).ensure_client()
    sub_ports = client.get(
        f"{client.network_url}{_TRUNK_BASE}/{trunk_id}/get_subports"
    ).get("sub_ports", [])
    print_list(
        sub_ports,
        [
            ("Port ID", "port_id", {"style": "cyan", "no_wrap": True}),
            ("Seg Type", "segmentation_type"),
            ("Seg ID", "segmentation_id", {"justify": "right"}),
        ],
        title=f"Sub-ports for trunk {trunk_id}",
        output_format=output_format, fit_width=fit_width, max_width=max_width,
        noindent=noindent, columns=columns,
        empty_msg="No sub-ports.",
    )


@trunk.command("add-subport")
@click.argument("trunk_id", callback=validate_id)
@click.option("--port", "port_id", required=True, callback=validate_id,
              help="Sub-port port ID.")
@click.option("--segmentation-type", default="vlan", show_default=True,
              type=click.Choice(["vlan", "inherit"]),
              help="Segmentation type.")
@click.option("--segmentation-id", type=int, required=True,
              help="VLAN ID (1–4094).")
@click.pass_context
def trunk_add_subport(ctx, trunk_id, port_id, segmentation_type, segmentation_id):
    """Add a sub-port to a trunk."""
    client = ctx.find_object(OrcaContext).ensure_client()
    client.put(
        f"{client.network_url}{_TRUNK_BASE}/{trunk_id}/add_subports",
        json={"sub_ports": [{"port_id": port_id,
                              "segmentation_type": segmentation_type,
                              "segmentation_id": segmentation_id}]},
    )
    console.print(f"[green]Sub-port {port_id} added to trunk {trunk_id}.[/green]")


@trunk.command("remove-subport")
@click.argument("trunk_id", callback=validate_id)
@click.option("--port", "port_id", required=True, callback=validate_id,
              help="Sub-port port ID to remove.")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def trunk_remove_subport(ctx, trunk_id, port_id, yes):
    """Remove a sub-port from a trunk."""
    client = ctx.find_object(OrcaContext).ensure_client()
    if not yes:
        click.confirm(f"Remove sub-port {port_id} from trunk {trunk_id}?", abort=True)
    client.put(
        f"{client.network_url}{_TRUNK_BASE}/{trunk_id}/remove_subports",
        json={"sub_ports": [{"port_id": port_id}]},
    )
    console.print(f"[green]Sub-port {port_id} removed from trunk {trunk_id}.[/green]")
