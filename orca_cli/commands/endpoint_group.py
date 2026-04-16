"""``orca endpoint-group`` — manage Keystone endpoint groups."""

from __future__ import annotations

import click

from orca_cli.core.context import OrcaContext
from orca_cli.core.output import console, output_options, print_detail, print_list
from orca_cli.core.validators import validate_id


def _iam(client) -> str:
    return client.identity_url


@click.group("endpoint-group")
@click.pass_context
def endpoint_group(ctx: click.Context) -> None:
    """Manage Keystone endpoint groups."""


@endpoint_group.command("list")
@output_options
@click.pass_context
def eg_list(ctx, output_format, columns, fit_width, max_width, noindent):
    """List endpoint groups."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_iam(client)}/v3/endpoint_groups")
    items = data.get("endpoint_groups", [])
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
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_iam(client)}/v3/endpoint_groups/{endpoint_group_id}")
    eg = data.get("endpoint_group", data)
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
    client = ctx.find_object(OrcaContext).ensure_client()
    filter_dict: dict = {}
    for f in filters:
        if "=" not in f:
            raise click.BadParameter(f"Expected KEY=VALUE, got '{f}'.", param_hint="--filter")
        k, _, v = f.partition("=")
        filter_dict[k.strip()] = v.strip()
    body = {"name": name, "description": description, "filters": filter_dict}
    data = client.post(f"{_iam(client)}/v3/endpoint_groups",
                       json={"endpoint_group": body})
    eg = data.get("endpoint_group", data)
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
    client = ctx.find_object(OrcaContext).ensure_client()
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
    client.patch(f"{_iam(client)}/v3/endpoint_groups/{endpoint_group_id}",
                 json={"endpoint_group": body})
    console.print(f"Endpoint group [bold]{endpoint_group_id}[/bold] updated.")


@endpoint_group.command("delete")
@click.argument("endpoint_group_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def eg_delete(ctx, endpoint_group_id, yes):
    """Delete an endpoint group."""
    client = ctx.find_object(OrcaContext).ensure_client()
    if not yes:
        click.confirm(f"Delete endpoint group {endpoint_group_id}?", abort=True)
    client.delete(f"{_iam(client)}/v3/endpoint_groups/{endpoint_group_id}")
    console.print(f"Endpoint group [bold]{endpoint_group_id}[/bold] deleted.")


@endpoint_group.command("add-project")
@click.argument("endpoint_group_id", callback=validate_id)
@click.argument("project_id", callback=validate_id)
@click.pass_context
def eg_add_project(ctx, endpoint_group_id, project_id):
    """Associate a project with an endpoint group."""
    client = ctx.find_object(OrcaContext).ensure_client()
    client.put(
        f"{_iam(client)}/v3/endpoint_groups/{endpoint_group_id}/projects/{project_id}",
        json={},
    )
    console.print(
        f"Project [bold]{project_id}[/bold] added to endpoint group [bold]{endpoint_group_id}[/bold]."
    )


@endpoint_group.command("remove-project")
@click.argument("endpoint_group_id", callback=validate_id)
@click.argument("project_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def eg_remove_project(ctx, endpoint_group_id, project_id, yes):
    """Remove a project from an endpoint group."""
    client = ctx.find_object(OrcaContext).ensure_client()
    if not yes:
        click.confirm(
            f"Remove project {project_id} from endpoint group {endpoint_group_id}?", abort=True
        )
    client.delete(
        f"{_iam(client)}/v3/endpoint_groups/{endpoint_group_id}/projects/{project_id}"
    )
    console.print(
        f"Project [bold]{project_id}[/bold] removed from endpoint group [bold]{endpoint_group_id}[/bold]."
    )
