"""``orca role`` — manage roles and assignments (Keystone v3)."""

from __future__ import annotations

import click

from orca_cli.core.context import OrcaContext
from orca_cli.core.output import console, output_options, print_detail, print_list
from orca_cli.core.validators import validate_id


def _iam(client) -> str:
    return client.identity_url


def _role_assignment_url(base, user_id, group_id, project_id, domain_id, role_id):
    """Build Keystone role assignment URL."""
    if not (user_id or group_id):
        raise click.UsageError("Specify --user or --group.")
    if not (project_id or domain_id):
        raise click.UsageError("Specify --project or --domain.")

    actor = f"users/{user_id}" if user_id else f"groups/{group_id}"
    scope = f"projects/{project_id}" if project_id else f"domains/{domain_id}"
    return f"{base}/v3/{scope}/{actor}/roles/{role_id}"


@click.group()
@click.pass_context
def role(ctx: click.Context) -> None:
    """Manage roles and assignments (Keystone v3)."""
    pass


@role.command("list")
@click.option("--domain", default=None, help="Filter by domain ID.")
@output_options
@click.pass_context
def role_list(ctx, domain, output_format, columns, fit_width, max_width, noindent):
    """List roles."""
    client = ctx.find_object(OrcaContext).ensure_client()
    params = {}
    if domain:
        params["domain_id"] = domain
    data = client.get(f"{_iam(client)}/v3/roles", params=params)
    print_list(
        data.get("roles", []),
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Name", "name", {"style": "bold"}),
            ("Domain ID", lambda r: r.get("domain_id") or "global"),
            ("Description", lambda r: (r.get("description") or "")[:50]),
        ],
        title="Roles",
        output_format=output_format, columns=columns,
        fit_width=fit_width, max_width=max_width, noindent=noindent,
        empty_msg="No roles found.",
    )


@role.command("show")
@click.argument("role_id")
@output_options
@click.pass_context
def role_show(ctx, role_id, output_format, columns, fit_width, max_width, noindent):
    """Show role details."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_iam(client)}/v3/roles/{role_id}")
    r = data.get("role", data)
    print_detail(
        [
            ("ID", r.get("id", "")),
            ("Name", r.get("name", "")),
            ("Domain ID", r.get("domain_id") or "global"),
            ("Description", r.get("description") or "—"),
        ],
        output_format=output_format, columns=columns,
        fit_width=fit_width, max_width=max_width, noindent=noindent,
    )


@role.command("create")
@click.argument("name")
@click.option("--description", default=None)
@click.option("--domain", "domain_id", default=None)
@click.pass_context
def role_create(ctx, name, description, domain_id):
    """Create a role."""
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {"name": name}
    if description:
        body["description"] = description
    if domain_id:
        body["domain_id"] = domain_id
    data = client.post(f"{_iam(client)}/v3/roles", json={"role": body})
    r = data.get("role", data)
    console.print(f"[green]Role '{r.get('name')}' ({r.get('id')}) created.[/green]")


@role.command("delete")
@click.argument("role_id")
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def role_delete(ctx, role_id, yes):
    """Delete a role."""
    if not yes:
        click.confirm(f"Delete role {role_id}?", abort=True)
    client = ctx.find_object(OrcaContext).ensure_client()
    client.delete(f"{_iam(client)}/v3/roles/{role_id}")
    console.print(f"[green]Role {role_id} deleted.[/green]")


@role.command("add")
@click.option("--user", "user_id", default=None, help="User ID.")
@click.option("--group", "group_id", default=None, help="Group ID.")
@click.option("--project", "project_id", default=None, help="Project ID.")
@click.option("--domain", "domain_id", default=None, help="Domain ID.")
@click.argument("role_id")
@click.pass_context
def role_add(ctx, user_id, group_id, project_id, domain_id, role_id):
    """Grant a role to a user or group on a project or domain.

    \b
    Examples:
      orca role add --user <uid> --project <pid> <role-id>
      orca role add --group <gid> --domain <did> <role-id>
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    url = _role_assignment_url(_iam(client), user_id, group_id, project_id, domain_id, role_id)
    client.put(url)
    console.print(f"[green]Role {role_id} granted.[/green]")


@role.command("remove")
@click.option("--user", "user_id", default=None, help="User ID.")
@click.option("--group", "group_id", default=None, help="Group ID.")
@click.option("--project", "project_id", default=None, help="Project ID.")
@click.option("--domain", "domain_id", default=None, help="Domain ID.")
@click.argument("role_id")
@click.pass_context
def role_remove(ctx, user_id, group_id, project_id, domain_id, role_id):
    """Revoke a role from a user or group."""
    client = ctx.find_object(OrcaContext).ensure_client()
    url = _role_assignment_url(_iam(client), user_id, group_id, project_id, domain_id, role_id)
    client.delete(url)
    console.print(f"[green]Role {role_id} revoked.[/green]")


@role.command("assignment-list")
@click.option("--user", "user_id", default=None)
@click.option("--group", "group_id", default=None)
@click.option("--project", "project_id", default=None)
@click.option("--domain", "domain_id", default=None)
@click.option("--role", "role_id", default=None)
@click.option("--effective", is_flag=True, help="Include inherited/effective assignments.")
@output_options
@click.pass_context
def role_assignment_list(ctx, user_id, group_id, project_id, domain_id, role_id, effective,
                         output_format, columns, fit_width, max_width, noindent):
    """List role assignments."""
    client = ctx.find_object(OrcaContext).ensure_client()
    params = {}
    if user_id:
        params["user.id"] = user_id
    if group_id:
        params["group.id"] = group_id
    if project_id:
        params["scope.project.id"] = project_id
    if domain_id:
        params["scope.domain.id"] = domain_id
    if role_id:
        params["role.id"] = role_id
    if effective:
        params["effective"] = ""

    data = client.get(f"{_iam(client)}/v3/role_assignments", params=params)
    assignments = data.get("role_assignments", [])

    rows = []
    for a in assignments:
        r = a.get("role", {})
        u = a.get("user", {})
        grp = a.get("group", {})
        scope = a.get("scope", {})
        rows.append({
            "role_id": r.get("id", ""),
            "user_id": u.get("id") or "—",
            "group_id": grp.get("id") or "—",
            "project_id": scope.get("project", {}).get("id") or "—",
            "domain_id": scope.get("domain", {}).get("id") or "—",
        })

    print_list(
        rows,
        [
            ("Role ID", "role_id", {"style": "cyan"}),
            ("User ID", "user_id"),
            ("Group ID", "group_id"),
            ("Project ID", "project_id"),
            ("Domain ID", "domain_id"),
        ],
        title="Role Assignments",
        output_format=output_format, columns=columns,
        fit_width=fit_width, max_width=max_width, noindent=noindent,
        empty_msg="No role assignments found.",
    )


# ══════════════════════════════════════════════════════════════════════════════
#  Implied Roles
# ══════════════════════════════════════════════════════════════════════════════

@role.command("implied-list")
@output_options
@click.pass_context
def role_implied_list(ctx, output_format, columns, fit_width, max_width, noindent):
    """List all implied role relationships."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_iam(client)}/v3/role_inferences")
    raw = data.get("role_inferences", [])
    items = []
    for entry in raw:
        prior = entry.get("prior_role", {})
        for implied in entry.get("implies", []):
            items.append({
                "prior_role_id": prior.get("id", ""),
                "prior_role_name": prior.get("name", ""),
                "implied_role_id": implied.get("id", ""),
                "implied_role_name": implied.get("name", ""),
            })
    if not items:
        console.print("No implied roles found.")
        return
    col_defs = [
        ("Prior Role ID", "prior_role_id"),
        ("Prior Role Name", "prior_role_name"),
        ("Implied Role ID", "implied_role_id"),
        ("Implied Role Name", "implied_role_name"),
    ]
    print_list(items, col_defs, title="Implied Roles",
               output_format=output_format, columns=columns,
               fit_width=fit_width, max_width=max_width, noindent=noindent)


@role.command("implied-create")
@click.argument("prior_role_id", callback=validate_id)
@click.argument("implied_role_id", callback=validate_id)
@click.pass_context
def role_implied_create(ctx, prior_role_id, implied_role_id):
    """Create an implied role (prior implies implied)."""
    client = ctx.find_object(OrcaContext).ensure_client()
    client.put(
        f"{_iam(client)}/v3/role_inferences/{prior_role_id}/implies/{implied_role_id}",
        json={},
    )
    console.print(
        f"Role [bold]{prior_role_id}[/bold] now implies [bold]{implied_role_id}[/bold]."
    )


@role.command("implied-delete")
@click.argument("prior_role_id", callback=validate_id)
@click.argument("implied_role_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def role_implied_delete(ctx, prior_role_id, implied_role_id, yes):
    """Delete an implied role relationship."""
    client = ctx.find_object(OrcaContext).ensure_client()
    if not yes:
        click.confirm(
            f"Remove implied role {implied_role_id} from {prior_role_id}?", abort=True
        )
    client.delete(
        f"{_iam(client)}/v3/role_inferences/{prior_role_id}/implies/{implied_role_id}"
    )
    console.print("Implied role relationship deleted.")


# ── set ───────────────────────────────────────────────────────────────────

@role.command("set")
@click.argument("role_id", callback=validate_id)
@click.option("--name", default=None, help="New role name.")
@click.option("--description", default=None, help="New description.")
@click.pass_context
def role_set(ctx: click.Context, role_id: str, name: str | None, description: str | None) -> None:
    """Set role properties (rename or update description).

    \b
    Examples:
      orca role set <id> --name new-name
      orca role set <id> --description "My role"
    """
    body: dict = {}
    if name is not None:
        body["name"] = name
    if description is not None:
        body["description"] = description

    if not body:
        console.print("[yellow]Nothing to update.[/yellow]")
        return

    client = ctx.find_object(OrcaContext).ensure_client()
    client.patch(f"{_iam(client)}/v3/roles/{role_id}", json={"role": body})
    console.print(f"[green]Role {role_id} updated.[/green]")
