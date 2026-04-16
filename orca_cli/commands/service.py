"""``orca service`` — manage Keystone services (service catalog CRUD)."""

from __future__ import annotations

import click

from orca_cli.core.context import OrcaContext
from orca_cli.core.output import console, output_options, print_detail, print_list
from orca_cli.core.validators import validate_id


@click.group()
def service() -> None:
    """Manage Keystone services (service catalog)."""
    pass


@service.command("list")
@click.option("--type", "service_type", default=None, help="Filter by service type.")
@output_options
@click.pass_context
def service_list(ctx, service_type, output_format, columns, fit_width, max_width, noindent):
    """List Keystone services."""
    client = ctx.find_object(OrcaContext).ensure_client()
    params = {}
    if service_type:
        params["type"] = service_type

    services = client.get(f"{client.identity_url}/services",
                          params=params).get("services", [])

    print_list(
        services,
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Name", "name", {"style": "bold"}),
            ("Type", "type"),
            ("Description", lambda s: (s.get("description") or "")[:60]),
            ("Enabled", lambda s: "Yes" if s.get("enabled", True) else "No"),
        ],
        title="Services",
        output_format=output_format, fit_width=fit_width, max_width=max_width,
        noindent=noindent, columns=columns,
        empty_msg="No services found.",
    )


@service.command("show")
@click.argument("service_id", callback=validate_id)
@output_options
@click.pass_context
def service_show(ctx, service_id, output_format, columns, fit_width, max_width, noindent):
    """Show service details."""
    client = ctx.find_object(OrcaContext).ensure_client()
    svc = client.get(f"{client.identity_url}/services/{service_id}").get("service", {})

    print_detail(
        [(k, str(svc.get(k, "") or "")) for k in
         ["id", "name", "type", "description", "enabled"]],
        output_format=output_format, fit_width=fit_width, max_width=max_width,
        noindent=noindent, columns=columns,
    )


@service.command("create")
@click.option("--name", required=True, help="Service name.")
@click.option("--type", "service_type", required=True, help="Service type (e.g. identity, compute).")
@click.option("--description", default=None, help="Service description.")
@click.option("--enable/--disable", default=True, help="Enable or disable the service.")
@click.pass_context
def service_create(ctx, name, service_type, description, enable):
    """Create a Keystone service."""
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {"name": name, "type": service_type, "enabled": enable}
    if description:
        body["description"] = description

    svc = client.post(f"{client.identity_url}/services",
                      json={"service": body}).get("service", {})
    console.print(f"[green]Service '{name}' created: {svc.get('id', '?')}[/green]")


@service.command("set")
@click.argument("service_id", callback=validate_id)
@click.option("--name", default=None, help="New name.")
@click.option("--type", "service_type", default=None, help="New type.")
@click.option("--description", default=None, help="New description.")
@click.option("--enable/--disable", default=None, help="Enable or disable.")
@click.pass_context
def service_set(ctx, service_id, name, service_type, description, enable):
    """Update a Keystone service."""
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {}
    if name is not None:
        body["name"] = name
    if service_type is not None:
        body["type"] = service_type
    if description is not None:
        body["description"] = description
    if enable is not None:
        body["enabled"] = enable
    if not body:
        console.print("[yellow]Nothing to update.[/yellow]")
        return
    client.patch(f"{client.identity_url}/services/{service_id}",
                 json={"service": body})
    console.print(f"[green]Service {service_id} updated.[/green]")


@service.command("delete")
@click.argument("service_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def service_delete(ctx, service_id, yes):
    """Delete a Keystone service."""
    client = ctx.find_object(OrcaContext).ensure_client()
    if not yes:
        click.confirm(f"Delete service {service_id}?", abort=True)
    client.delete(f"{client.identity_url}/services/{service_id}")
    console.print(f"[green]Service {service_id} deleted.[/green]")
