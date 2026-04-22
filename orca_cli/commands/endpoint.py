"""``orca endpoint`` — manage Keystone service endpoints."""

from __future__ import annotations

import click

from orca_cli.core.context import OrcaContext
from orca_cli.core.output import console, output_options, print_detail, print_list
from orca_cli.core.validators import validate_id
from orca_cli.services.identity import IdentityService


@click.group()
def endpoint() -> None:
    """Manage Keystone service endpoints."""
    pass


@endpoint.command("list")
@click.option("--service", default=None, help="Filter by service ID or name.")
@click.option("--interface", default=None,
              type=click.Choice(["public", "internal", "admin"]),
              help="Filter by interface type.")
@click.option("--region", default=None, help="Filter by region ID.")
@output_options
@click.pass_context
def endpoint_list(ctx, service, interface, region,
                  output_format, columns, fit_width, max_width, noindent):
    """List endpoints."""
    client = ctx.find_object(OrcaContext).ensure_client()
    svc = IdentityService(client)
    params = {}
    if interface:
        params["interface"] = interface
    if region:
        params["region_id"] = region

    endpoints = svc.find_endpoints(params=params or None)

    # Resolve service_id → name using the in-memory catalog
    svc_names = {
        svc_entry["id"]: svc_entry.get("name", svc_entry["id"])
        for svc_entry in client._catalog
    } if hasattr(client, "_catalog") else {}

    if service:
        service_lower = service.lower()
        endpoints = [
            e for e in endpoints
            if e.get("service_id") == service
            or svc_names.get(e.get("service_id"), "").lower() == service_lower
        ]

    print_list(
        endpoints,
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Service", lambda e: svc_names.get(e.get("service_id", ""), e.get("service_id", "—")),
             {"style": "bold"}),
            ("Interface", "interface"),
            ("Region", lambda e: e.get("region_id") or e.get("region") or "—"),
            ("URL", "url"),
            ("Enabled", lambda e: "Yes" if e.get("enabled", True) else "No"),
        ],
        title="Endpoints",
        output_format=output_format, fit_width=fit_width, max_width=max_width,
        noindent=noindent, columns=columns,
        empty_msg="No endpoints found.",
    )


@endpoint.command("show")
@click.argument("endpoint_id", callback=validate_id)
@output_options
@click.pass_context
def endpoint_show(ctx, endpoint_id, output_format, columns, fit_width, max_width, noindent):
    """Show endpoint details."""
    svc = IdentityService(ctx.find_object(OrcaContext).ensure_client())
    ep = svc.get_endpoint(endpoint_id)

    print_detail(
        [(k, str(ep.get(k, "") or "")) for k in
         ["id", "service_id", "interface", "region_id", "url", "enabled"]],
        output_format=output_format, fit_width=fit_width, max_width=max_width,
        noindent=noindent, columns=columns,
    )


@endpoint.command("create")
@click.option("--service", required=True, help="Service ID.")
@click.option("--interface", required=True,
              type=click.Choice(["public", "internal", "admin"]),
              help="Endpoint interface.")
@click.option("--url", required=True, help="Endpoint URL.")
@click.option("--region", default=None, help="Region ID.")
@click.option("--enable/--disable", default=True, help="Enable or disable the endpoint.")
@click.pass_context
def endpoint_create(ctx, service, interface, url, region, enable):
    """Create an endpoint."""
    svc = IdentityService(ctx.find_object(OrcaContext).ensure_client())
    body: dict = {
        "service_id": service,
        "interface": interface,
        "url": url,
        "enabled": enable,
    }
    if region:
        body["region_id"] = region

    ep = svc.create_endpoint(body)
    console.print(f"[green]Endpoint created: {ep.get('id', '?')} ({interface} {url})[/green]")


@endpoint.command("set")
@click.argument("endpoint_id", callback=validate_id)
@click.option("--url", default=None, help="New URL.")
@click.option("--interface", default=None,
              type=click.Choice(["public", "internal", "admin"]),
              help="New interface type.")
@click.option("--region", default=None, help="New region ID.")
@click.option("--enable/--disable", default=None, help="Enable or disable.")
@click.pass_context
def endpoint_set(ctx, endpoint_id, url, interface, region, enable):
    """Update an endpoint."""
    body: dict = {}
    if url is not None:
        body["url"] = url
    if interface is not None:
        body["interface"] = interface
    if region is not None:
        body["region_id"] = region
    if enable is not None:
        body["enabled"] = enable
    if not body:
        console.print("[yellow]Nothing to update.[/yellow]")
        return
    svc = IdentityService(ctx.find_object(OrcaContext).ensure_client())
    svc.update_endpoint(endpoint_id, body)
    console.print(f"[green]Endpoint {endpoint_id} updated.[/green]")


@endpoint.command("delete")
@click.argument("endpoint_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def endpoint_delete(ctx, endpoint_id, yes):
    """Delete an endpoint."""
    svc = IdentityService(ctx.find_object(OrcaContext).ensure_client())
    if not yes:
        click.confirm(f"Delete endpoint {endpoint_id}?", abort=True)
    svc.delete_endpoint(endpoint_id)
    console.print(f"[green]Endpoint {endpoint_id} deleted.[/green]")
