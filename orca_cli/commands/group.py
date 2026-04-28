"""``orca group`` — manage groups (Keystone v3)."""

from __future__ import annotations

import click

from orca_cli.core.aliases import add_command_with_alias
from orca_cli.core.context import OrcaContext
from orca_cli.core.output import console, output_options, print_detail, print_list
from orca_cli.services.identity import IdentityService


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
    svc = IdentityService(ctx.find_object(OrcaContext).ensure_client())
    params = {}
    if domain:
        params["domain_id"] = domain
    print_list(
        svc.find_groups(params=params or None),
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
    svc = IdentityService(ctx.find_object(OrcaContext).ensure_client())
    g = svc.get_group(group_id)
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
    svc = IdentityService(ctx.find_object(OrcaContext).ensure_client())
    body: dict = {"name": name}
    if description:
        body["description"] = description
    if domain_id:
        body["domain_id"] = domain_id
    g = svc.create_group(body)
    console.print(f"[green]Group '{g.get('name')}' ({g.get('id')}) created.[/green]")


@group.command("set")
@click.argument("group_id")
@click.option("--name", default=None)
@click.option("--description", default=None)
@click.pass_context
def group_set(ctx, group_id, name, description):
    """Update a group."""
    body = {}
    if name:
        body["name"] = name
    if description:
        body["description"] = description
    if not body:
        console.print("[yellow]Nothing to update.[/yellow]")
        return
    svc = IdentityService(ctx.find_object(OrcaContext).ensure_client())
    svc.update_group(group_id, body)
    console.print(f"[green]Group {group_id} updated.[/green]")


@group.command("delete")
@click.argument("group_id")
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def group_delete(ctx, group_id, yes):
    """Delete a group."""
    if not yes:
        click.confirm(f"Delete group {group_id}?", abort=True)
    svc = IdentityService(ctx.find_object(OrcaContext).ensure_client())
    svc.delete_group(group_id)
    console.print(f"[green]Group {group_id} deleted.[/green]")


@group.group("user")
def group_user() -> None:
    """Manage user membership of a group."""


@group_user.command("add")
@click.argument("group_id")
@click.argument("user_id")
@click.pass_context
def group_user_add(ctx, group_id, user_id):
    """Add a user to a group."""
    svc = IdentityService(ctx.find_object(OrcaContext).ensure_client())
    svc.add_group_user(group_id, user_id)
    console.print(f"[green]User {user_id} added to group {group_id}.[/green]")


@group_user.command("remove")
@click.argument("group_id")
@click.argument("user_id")
@click.pass_context
def group_user_remove(ctx, group_id, user_id):
    """Remove a user from a group."""
    svc = IdentityService(ctx.find_object(OrcaContext).ensure_client())
    svc.remove_group_user(group_id, user_id)
    console.print(f"[green]User {user_id} removed from group {group_id}.[/green]")


@group.group("member")
def group_member() -> None:
    """Inspect users belonging to a group."""


@group_member.command("list")
@click.argument("group_id")
@output_options
@click.pass_context
def group_member_list(ctx, group_id, output_format, columns, fit_width, max_width, noindent):
    """List users in a group."""
    svc = IdentityService(ctx.find_object(OrcaContext).ensure_client())
    print_list(
        svc.list_group_users(group_id),
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


add_command_with_alias(group, group_user_add,
                        legacy_name="add-user", primary_path="group user add")
add_command_with_alias(group, group_user_remove,
                        legacy_name="remove-user", primary_path="group user remove")
add_command_with_alias(group, group_member_list,
                        legacy_name="member-list", primary_path="group member list")
