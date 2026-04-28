"""``orca endpoint-group`` — manage Keystone endpoint groups."""

from __future__ import annotations

import click

from orca_cli.core.context import OrcaContext
from orca_cli.core.output import console, output_options, print_detail, print_list
from orca_cli.core.validators import validate_id
from orca_cli.services.identity import IdentityService


@click.group("endpoint-group")
@click.pass_context
def endpoint_group(ctx: click.Context) -> None:
    """Manage Keystone endpoint groups."""


@endpoint_group.command("list")
@output_options
@click.pass_context
def eg_list(ctx, output_format, columns, fit_width, max_width, noindent):
    """List endpoint groups."""
    svc = IdentityService(ctx.find_object(OrcaContext).ensure_client())
    items = svc.find_endpoint_groups()
    if not items:
        console.print("No endpoint groups found.")
        return
    col_defs = [
        ("ID", "id"),
        ("Name", "name"),
        ("Description", "description"),
        ("Filters", lambda eg: str(eg.get("filters", {}))),
    ]
    print_list(items, col_defs, title="Endpoint Groups",
               output_format=output_format, columns=columns,
               fit_width=fit_width, max_width=max_width, noindent=noindent)


@endpoint_group.command("show")
@click.argument("endpoint_group_id", callback=validate_id)
@output_options
@click.pass_context
def eg_show(ctx, endpoint_group_id, output_format, columns, fit_width, max_width, noindent):
    """Show an endpoint group."""
    svc = IdentityService(ctx.find_object(OrcaContext).ensure_client())
    eg = svc.get_endpoint_group(endpoint_group_id)
    fields = [
        ("ID", eg.get("id", "")),
        ("Name", eg.get("name", "")),
        ("Description", eg.get("description", "")),
        ("Filters", str(eg.get("filters", {}))),
    ]
    print_detail(fields,
                 output_format=output_format, columns=columns,
                 fit_width=fit_width, max_width=max_width, noindent=noindent)


@endpoint_group.command("create")
@click.option("--name", required=True, help="Endpoint group name.")
@click.option("--filter", "filters", multiple=True, metavar="KEY=VALUE",
              help="Filter criterion (e.g. service_id=xxx). Repeatable.")
@click.option("--description", default="", help="Description.")
@output_options
@click.pass_context
def eg_create(ctx, name, filters, description,
              output_format, columns, fit_width, max_width, noindent):
    """Create an endpoint group."""
    svc = IdentityService(ctx.find_object(OrcaContext).ensure_client())
    filter_dict: dict = {}
    for f in filters:
        if "=" not in f:
            raise click.BadParameter(f"Expected KEY=VALUE, got '{f}'.", param_hint="--filter")
        k, _, v = f.partition("=")
        filter_dict[k.strip()] = v.strip()
    body = {"name": name, "description": description, "filters": filter_dict}
    eg = svc.create_endpoint_group(body)
    fields = [
        ("ID", eg.get("id", "")),
        ("Name", eg.get("name", "")),
        ("Filters", str(eg.get("filters", {}))),
    ]
    print_detail(fields,
                 output_format=output_format, columns=columns,
                 fit_width=fit_width, max_width=max_width, noindent=noindent)


@endpoint_group.command("set")
@click.argument("endpoint_group_id", callback=validate_id)
@click.option("--name", default=None)
@click.option("--description", default=None)
@click.option("--filter", "filters", multiple=True, metavar="KEY=VALUE")
@click.pass_context
def eg_set(ctx, endpoint_group_id, name, description, filters):
    """Update an endpoint group."""
    body: dict = {}
    if name is not None:
        body["name"] = name
    if description is not None:
        body["description"] = description
    if filters:
        filter_dict: dict = {}
        for f in filters:
            if "=" not in f:
                raise click.BadParameter(f"Expected KEY=VALUE, got '{f}'.", param_hint="--filter")
            k, _, v = f.partition("=")
            filter_dict[k.strip()] = v.strip()
        body["filters"] = filter_dict
    if not body:
        console.print("Nothing to update.")
        return
    svc = IdentityService(ctx.find_object(OrcaContext).ensure_client())
    svc.update_endpoint_group(endpoint_group_id, body)
    console.print(f"Endpoint group [bold]{endpoint_group_id}[/bold] updated.")


@endpoint_group.command("delete")
@click.argument("endpoint_group_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def eg_delete(ctx, endpoint_group_id, yes):
    """Delete an endpoint group."""
    svc = IdentityService(ctx.find_object(OrcaContext).ensure_client())
    if not yes:
        click.confirm(f"Delete endpoint group {endpoint_group_id}?", abort=True)
    svc.delete_endpoint_group(endpoint_group_id)
    console.print(f"Endpoint group [bold]{endpoint_group_id}[/bold] deleted.")


@endpoint_group.group("project")
def endpoint_group_project() -> None:
    """Manage project membership of an endpoint group."""


@endpoint_group_project.command("add")
@click.argument("endpoint_group_id", callback=validate_id)
@click.argument("project_id", callback=validate_id)
@click.pass_context
def eg_project_add(ctx, endpoint_group_id, project_id):
    """Associate a project with an endpoint group."""
    svc = IdentityService(ctx.find_object(OrcaContext).ensure_client())
    svc.add_endpoint_group_project(endpoint_group_id, project_id)
    console.print(
        f"Project [bold]{project_id}[/bold] added to endpoint group [bold]{endpoint_group_id}[/bold]."
    )


@endpoint_group_project.command("remove")
@click.argument("endpoint_group_id", callback=validate_id)
@click.argument("project_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def eg_project_remove(ctx, endpoint_group_id, project_id, yes):
    """Remove a project from an endpoint group."""
    svc = IdentityService(ctx.find_object(OrcaContext).ensure_client())
    if not yes:
        click.confirm(
            f"Remove project {project_id} from endpoint group {endpoint_group_id}?", abort=True
        )
    svc.remove_endpoint_group_project(endpoint_group_id, project_id)
    console.print(
        f"Project [bold]{project_id}[/bold] removed from endpoint group [bold]{endpoint_group_id}[/bold]."
    )
