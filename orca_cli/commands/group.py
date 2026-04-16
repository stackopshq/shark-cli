"""``orca group`` — manage groups (Keystone v3)."""

from __future__ import annotations

import click

from orca_cli.core.context import OrcaContext
from orca_cli.core.output import console, output_options, print_detail, print_list


def _iam(client) -> str:
    return client.identity_url


@click.group()
@click.pass_context
def group(ctx: click.Context) -> None:
    """Manage groups (Keystone v3)."""
    pass


@group.command("list")
@click.option("--domain", default=None, help="Filter by domain ID.")
@output_options
@click.pass_context
def group_list(ctx, domain, output_format, columns, fit_width, max_width, noindent):
    """List groups."""
    client = ctx.find_object(OrcaContext).ensure_client()
    params = {}
    if domain:
        params["domain_id"] = domain
    data = client.get(f"{_iam(client)}/v3/groups", params=params)
    print_list(
        data.get("groups", []),
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Name", "name", {"style": "bold"}),
            ("Domain ID", "domain_id"),
            ("Description", lambda g: (g.get("description") or "")[:50]),
        ],
        title="Groups",
        output_format=output_format, columns=columns,
        fit_width=fit_width, max_width=max_width, noindent=noindent,
        empty_msg="No groups found.",
    )


@group.command("show")
@click.argument("group_id")
@output_options
@click.pass_context
def group_show(ctx, group_id, output_format, columns, fit_width, max_width, noindent):
    """Show group details."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_iam(client)}/v3/groups/{group_id}")
    g = data.get("group", data)
    print_detail(
        [
            ("ID", g.get("id", "")),
            ("Name", g.get("name", "")),
            ("Domain ID", g.get("domain_id", "")),
            ("Description", g.get("description") or "—"),
        ],
        output_format=output_format, columns=columns,
        fit_width=fit_width, max_width=max_width, noindent=noindent,
    )


@group.command("create")
@click.argument("name")
@click.option("--description", default=None)
@click.option("--domain", "domain_id", default=None)
@click.pass_context
def group_create(ctx, name, description, domain_id):
    """Create a group."""
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {"name": name}
    if description:
        body["description"] = description
    if domain_id:
        body["domain_id"] = domain_id
    data = client.post(f"{_iam(client)}/v3/groups", json={"group": body})
    g = data.get("group", data)
    console.print(f"[green]Group '{g.get('name')}' ({g.get('id')}) created.[/green]")


@group.command("set")
@click.argument("group_id")
@click.option("--name", default=None)
@click.option("--description", default=None)
@click.pass_context
def group_set(ctx, group_id, name, description):
    """Update a group."""
    client = ctx.find_object(OrcaContext).ensure_client()
    body = {}
    if name:
        body["name"] = name
    if description:
        body["description"] = description
    if not body:
        console.print("[yellow]Nothing to update.[/yellow]")
        return
    client.patch(f"{_iam(client)}/v3/groups/{group_id}", json={"group": body})
    console.print(f"[green]Group {group_id} updated.[/green]")


@group.command("delete")
@click.argument("group_id")
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def group_delete(ctx, group_id, yes):
    """Delete a group."""
    if not yes:
        click.confirm(f"Delete group {group_id}?", abort=True)
    client = ctx.find_object(OrcaContext).ensure_client()
    client.delete(f"{_iam(client)}/v3/groups/{group_id}")
    console.print(f"[green]Group {group_id} deleted.[/green]")


@group.command("add-user")
@click.argument("group_id")
@click.argument("user_id")
@click.pass_context
def group_add_user(ctx, group_id, user_id):
    """Add a user to a group."""
    client = ctx.find_object(OrcaContext).ensure_client()
    client.put(f"{_iam(client)}/v3/groups/{group_id}/users/{user_id}")
    console.print(f"[green]User {user_id} added to group {group_id}.[/green]")


@group.command("remove-user")
@click.argument("group_id")
@click.argument("user_id")
@click.pass_context
def group_remove_user(ctx, group_id, user_id):
    """Remove a user from a group."""
    client = ctx.find_object(OrcaContext).ensure_client()
    client.delete(f"{_iam(client)}/v3/groups/{group_id}/users/{user_id}")
    console.print(f"[green]User {user_id} removed from group {group_id}.[/green]")


@group.command("member-list")
@click.argument("group_id")
@output_options
@click.pass_context
def group_member_list(ctx, group_id, output_format, columns, fit_width, max_width, noindent):
    """List users in a group."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_iam(client)}/v3/groups/{group_id}/users")
    print_list(
        data.get("users", []),
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Name", "name", {"style": "bold"}),
            ("Email", lambda u: u.get("email") or "—"),
            ("Enabled", lambda u: "[green]yes[/green]" if u.get("enabled") else "[red]no[/red]"),
        ],
        title=f"Users in group {group_id}",
        output_format=output_format, columns=columns,
        fit_width=fit_width, max_width=max_width, noindent=noindent,
        empty_msg="No users in this group.",
    )
