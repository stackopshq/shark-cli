"""``orca limit / registered-limit`` — manage Keystone resource limits."""

from __future__ import annotations

import click

from orca_cli.core.context import OrcaContext
from orca_cli.core.output import console, output_options, print_detail, print_list
from orca_cli.core.validators import validate_id


def _iam(client) -> str:
    return client.identity_url


# ══════════════════════════════════════════════════════════════════════════════
#  Registered Limits
# ══════════════════════════════════════════════════════════════════════════════

@click.group("registered-limit")
@click.pass_context
def registered_limit(ctx: click.Context) -> None:
    """Manage Keystone registered limits (defaults per service/resource)."""


@registered_limit.command("list")
@click.option("--service-id", default=None, help="Filter by service ID.")
@click.option("--region-id", default=None, help="Filter by region ID.")
@click.option("--resource-name", default=None, help="Filter by resource name.")
@output_options
@click.pass_context
def rl_list(ctx, service_id, region_id, resource_name,
            output_format, columns, fit_width, max_width, noindent):
    """List registered limits."""
    client = ctx.find_object(OrcaContext).ensure_client()
    params = {}
    if service_id:
        params["service_id"] = service_id
    if region_id:
        params["region_id"] = region_id
    if resource_name:
        params["resource_name"] = resource_name
    data = client.get(f"{_iam(client)}/v3/registered_limits", params=params)
    items = data.get("registered_limits", [])
    if not items:
        console.print("No registered limits found.")
        return
    col_defs = [
        ("ID", "id"),
        ("Service ID", "service_id"),
        ("Resource Name", "resource_name"),
        ("Default Limit", "default_limit"),
        ("Region ID", "region_id"),
        ("Description", "description"),
    ]
    print_list(items, col_defs, title="Registered Limits",
               output_format=output_format, columns=columns,
               fit_width=fit_width, max_width=max_width, noindent=noindent)


@registered_limit.command("show")
@click.argument("registered_limit_id", callback=validate_id)
@output_options
@click.pass_context
def rl_show(ctx, registered_limit_id, output_format, columns, fit_width, max_width, noindent):
    """Show a registered limit."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_iam(client)}/v3/registered_limits/{registered_limit_id}")
    rl = data.get("registered_limit", data)
    fields = [
        ("ID", rl.get("id", "")),
        ("Service ID", rl.get("service_id", "")),
        ("Resource Name", rl.get("resource_name", "")),
        ("Default Limit", rl.get("default_limit", "")),
        ("Region ID", rl.get("region_id", "")),
        ("Description", rl.get("description", "")),
    ]
    print_detail(fields,
                 output_format=output_format, columns=columns,
                 fit_width=fit_width, max_width=max_width, noindent=noindent)


@registered_limit.command("create")
@click.option("--service-id", required=True, help="Service ID.")
@click.option("--resource-name", required=True, help="Resource name (e.g. server).")
@click.option("--default-limit", required=True, type=int, help="Default limit value.")
@click.option("--region-id", default=None, help="Region ID.")
@click.option("--description", default="", help="Description.")
@output_options
@click.pass_context
def rl_create(ctx, service_id, resource_name, default_limit, region_id, description,
              output_format, columns, fit_width, max_width, noindent):
    """Create a registered limit."""
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {
        "service_id": service_id,
        "resource_name": resource_name,
        "default_limit": default_limit,
        "description": description,
    }
    if region_id:
        body["region_id"] = region_id
    data = client.post(f"{_iam(client)}/v3/registered_limits",
                       json={"registered_limits": [body]})
    items = data.get("registered_limits", [data])
    rl = items[0] if items else {}
    fields = [
        ("ID", rl.get("id", "")),
        ("Service ID", rl.get("service_id", "")),
        ("Resource Name", rl.get("resource_name", "")),
        ("Default Limit", rl.get("default_limit", "")),
    ]
    print_detail(fields,
                 output_format=output_format, columns=columns,
                 fit_width=fit_width, max_width=max_width, noindent=noindent)


@registered_limit.command("set")
@click.argument("registered_limit_id", callback=validate_id)
@click.option("--service-id", default=None)
@click.option("--resource-name", default=None)
@click.option("--default-limit", type=int, default=None)
@click.option("--region-id", default=None)
@click.option("--description", default=None)
@click.pass_context
def rl_set(ctx, registered_limit_id, service_id, resource_name, default_limit,
           region_id, description):
    """Update a registered limit."""
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {}
    if service_id is not None:
        body["service_id"] = service_id
    if resource_name is not None:
        body["resource_name"] = resource_name
    if default_limit is not None:
        body["default_limit"] = default_limit
    if region_id is not None:
        body["region_id"] = region_id
    if description is not None:
        body["description"] = description
    if not body:
        console.print("Nothing to update.")
        return
    client.patch(f"{_iam(client)}/v3/registered_limits/{registered_limit_id}",
                 json={"registered_limit": body})
    console.print(f"Registered limit [bold]{registered_limit_id}[/bold] updated.")


@registered_limit.command("delete")
@click.argument("registered_limit_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def rl_delete(ctx, registered_limit_id, yes):
    """Delete a registered limit."""
    client = ctx.find_object(OrcaContext).ensure_client()
    if not yes:
        click.confirm(f"Delete registered limit {registered_limit_id}?", abort=True)
    client.delete(f"{_iam(client)}/v3/registered_limits/{registered_limit_id}")
    console.print(f"Registered limit [bold]{registered_limit_id}[/bold] deleted.")


# ══════════════════════════════════════════════════════════════════════════════
#  Limits (project-level overrides)
# ══════════════════════════════════════════════════════════════════════════════

@click.group("limit")
@click.pass_context
def limit(ctx: click.Context) -> None:
    """Manage Keystone project-level resource limits."""


@limit.command("list")
@click.option("--service-id", default=None, help="Filter by service ID.")
@click.option("--region-id", default=None, help="Filter by region ID.")
@click.option("--resource-name", default=None, help="Filter by resource name.")
@click.option("--project-id", default=None, help="Filter by project ID.")
@output_options
@click.pass_context
def limit_list(ctx, service_id, region_id, resource_name, project_id,
               output_format, columns, fit_width, max_width, noindent):
    """List limits."""
    client = ctx.find_object(OrcaContext).ensure_client()
    params = {}
    if service_id:
        params["service_id"] = service_id
    if region_id:
        params["region_id"] = region_id
    if resource_name:
        params["resource_name"] = resource_name
    if project_id:
        params["project_id"] = project_id
    data = client.get(f"{_iam(client)}/v3/limits", params=params)
    items = data.get("limits", [])
    if not items:
        console.print("No limits found.")
        return
    col_defs = [
        ("ID", "id"),
        ("Project ID", "project_id"),
        ("Service ID", "service_id"),
        ("Resource Name", "resource_name"),
        ("Resource Limit", "resource_limit"),
        ("Region ID", "region_id"),
    ]
    print_list(items, col_defs, title="Limits",
               output_format=output_format, columns=columns,
               fit_width=fit_width, max_width=max_width, noindent=noindent)


@limit.command("show")
@click.argument("limit_id", callback=validate_id)
@output_options
@click.pass_context
def limit_show(ctx, limit_id, output_format, columns, fit_width, max_width, noindent):
    """Show a limit."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_iam(client)}/v3/limits/{limit_id}")
    lim = data.get("limit", data)
    fields = [
        ("ID", lim.get("id", "")),
        ("Project ID", lim.get("project_id", "")),
        ("Service ID", lim.get("service_id", "")),
        ("Resource Name", lim.get("resource_name", "")),
        ("Resource Limit", lim.get("resource_limit", "")),
        ("Region ID", lim.get("region_id", "")),
        ("Description", lim.get("description", "")),
    ]
    print_detail(fields,
                 output_format=output_format, columns=columns,
                 fit_width=fit_width, max_width=max_width, noindent=noindent)


@limit.command("create")
@click.option("--project-id", required=True, callback=validate_id, help="Project ID.")
@click.option("--service-id", required=True, help="Service ID.")
@click.option("--resource-name", required=True, help="Resource name.")
@click.option("--resource-limit", required=True, type=int, help="Limit value.")
@click.option("--region-id", default=None, help="Region ID.")
@click.option("--description", default="", help="Description.")
@output_options
@click.pass_context
def limit_create(ctx, project_id, service_id, resource_name, resource_limit,
                 region_id, description,
                 output_format, columns, fit_width, max_width, noindent):
    """Create a project-level limit."""
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {
        "project_id": project_id,
        "service_id": service_id,
        "resource_name": resource_name,
        "resource_limit": resource_limit,
        "description": description,
    }
    if region_id:
        body["region_id"] = region_id
    data = client.post(f"{_iam(client)}/v3/limits",
                       json={"limits": [body]})
    items = data.get("limits", [data])
    lim = items[0] if items else {}
    fields = [
        ("ID", lim.get("id", "")),
        ("Project ID", lim.get("project_id", "")),
        ("Resource Name", lim.get("resource_name", "")),
        ("Resource Limit", lim.get("resource_limit", "")),
    ]
    print_detail(fields,
                 output_format=output_format, columns=columns,
                 fit_width=fit_width, max_width=max_width, noindent=noindent)


@limit.command("set")
@click.argument("limit_id", callback=validate_id)
@click.option("--resource-limit", type=int, default=None, help="New limit value.")
@click.option("--description", default=None)
@click.pass_context
def limit_set(ctx, limit_id, resource_limit, description):
    """Update a project-level limit."""
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {}
    if resource_limit is not None:
        body["resource_limit"] = resource_limit
    if description is not None:
        body["description"] = description
    if not body:
        console.print("Nothing to update.")
        return
    client.patch(f"{_iam(client)}/v3/limits/{limit_id}", json={"limit": body})
    console.print(f"Limit [bold]{limit_id}[/bold] updated.")


@limit.command("delete")
@click.argument("limit_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def limit_delete(ctx, limit_id, yes):
    """Delete a project-level limit."""
    client = ctx.find_object(OrcaContext).ensure_client()
    if not yes:
        click.confirm(f"Delete limit {limit_id}?", abort=True)
    client.delete(f"{_iam(client)}/v3/limits/{limit_id}")
    console.print(f"Limit [bold]{limit_id}[/bold] deleted.")
