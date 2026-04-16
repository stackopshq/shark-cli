"""``orca user`` — manage users (Keystone v3)."""

from __future__ import annotations

import click

from orca_cli.core.context import OrcaContext
from orca_cli.core.output import output_options, print_list, print_detail, console


def _iam(client) -> str:
    return client.identity_url


@click.group()
@click.pass_context
def user(ctx: click.Context) -> None:
    """Manage users (Keystone v3)."""
    pass


@user.command("list")
@click.option("--domain", default=None, help="Filter by domain name or ID.")
@click.option("--project", default=None, help="Filter by project ID.")
@click.option("--enabled/--disabled", default=None, help="Filter by enabled state.")
@output_options
@click.pass_context
def user_list(ctx, domain, project, enabled,
              output_format, columns, fit_width, max_width, noindent):
    """List users."""
    client = ctx.find_object(OrcaContext).ensure_client()
    params = {}
    if domain:
        params["domain_id"] = domain
    if project:
        params["member_of"] = project
    if enabled is not None:
        params["enabled"] = str(enabled).lower()

    data = client.get(f"{_iam(client)}/v3/users", params=params)
    print_list(
        data.get("users", []),
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Name", "name", {"style": "bold"}),
            ("Domain ID", "domain_id"),
            ("Email", lambda u: u.get("email") or "—"),
            ("Enabled", lambda u: "[green]yes[/green]" if u.get("enabled") else "[red]no[/red]"),
        ],
        title="Users",
        output_format=output_format, columns=columns,
        fit_width=fit_width, max_width=max_width, noindent=noindent,
        empty_msg="No users found.",
    )


@user.command("show")
@click.argument("user_id")
@output_options
@click.pass_context
def user_show(ctx, user_id, output_format, columns, fit_width, max_width, noindent):
    """Show user details."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_iam(client)}/v3/users/{user_id}")
    u = data.get("user", data)
    print_detail(
        [
            ("ID", u.get("id", "")),
            ("Name", u.get("name", "")),
            ("Domain ID", u.get("domain_id", "")),
            ("Email", u.get("email") or "—"),
            ("Description", u.get("description") or "—"),
            ("Enabled", "yes" if u.get("enabled") else "no"),
            ("Default Project", u.get("default_project_id") or "—"),
            ("Password Expires", u.get("password_expires_at") or "never"),
            ("Created", u.get("created_at", "")),
            ("Updated", u.get("updated_at") or "—"),
        ],
        output_format=output_format, columns=columns,
        fit_width=fit_width, max_width=max_width, noindent=noindent,
    )


@user.command("create")
@click.argument("name")
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True,
              help="User password.")
@click.option("--email", default=None, help="Email address.")
@click.option("--description", default=None, help="Description.")
@click.option("--domain", "domain_id", default=None, help="Domain ID.")
@click.option("--project", "default_project_id", default=None, help="Default project ID.")
@click.option("--enable/--disable", "enabled", default=True, show_default=True,
              help="Enable or disable the user.")
@click.pass_context
def user_create(ctx, name, password, email, description, domain_id,
                default_project_id, enabled):
    """Create a user."""
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {"name": name, "password": password, "enabled": enabled}
    if email:
        body["email"] = email
    if description:
        body["description"] = description
    if domain_id:
        body["domain_id"] = domain_id
    if default_project_id:
        body["default_project_id"] = default_project_id

    data = client.post(f"{_iam(client)}/v3/users", json={"user": body})
    u = data.get("user", data)
    console.print(f"[green]User '{u.get('name')}' ({u.get('id')}) created.[/green]")


@user.command("set")
@click.argument("user_id")
@click.option("--name", default=None, help="New name.")
@click.option("--email", default=None, help="New email.")
@click.option("--description", default=None, help="New description.")
@click.option("--password", default=None, help="New password.")
@click.option("--enable/--disable", "enabled", default=None, help="Enable or disable.")
@click.pass_context
def user_set(ctx, user_id, name, email, description, password, enabled):
    """Update a user."""
    client = ctx.find_object(OrcaContext).ensure_client()
    body = {}
    if name:
        body["name"] = name
    if email:
        body["email"] = email
    if description:
        body["description"] = description
    if password:
        body["password"] = password
    if enabled is not None:
        body["enabled"] = enabled

    if not body:
        console.print("[yellow]Nothing to update.[/yellow]")
        return

    client.patch(f"{_iam(client)}/v3/users/{user_id}", json={"user": body})
    console.print(f"[green]User {user_id} updated.[/green]")


@user.command("delete")
@click.argument("user_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def user_delete(ctx, user_id, yes):
    """Delete a user."""
    if not yes:
        click.confirm(f"Delete user {user_id}?", abort=True)
    client = ctx.find_object(OrcaContext).ensure_client()
    client.delete(f"{_iam(client)}/v3/users/{user_id}")
    console.print(f"[green]User {user_id} deleted.[/green]")


@user.command("set-password")
@click.argument("user_id")
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True,
              help="New password.")
@click.pass_context
def user_set_password(ctx, user_id, password):
    """Set a user's password (admin)."""
    client = ctx.find_object(OrcaContext).ensure_client()
    client.patch(f"{_iam(client)}/v3/users/{user_id}",
                 json={"user": {"password": password}})
    console.print(f"[green]Password updated for user {user_id}.[/green]")
