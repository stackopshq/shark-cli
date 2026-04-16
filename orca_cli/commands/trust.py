"""``orca trust`` — manage Keystone trusts (delegation)."""

from __future__ import annotations

import click

from orca_cli.core.context import OrcaContext
from orca_cli.core.output import console, output_options, print_detail, print_list
from orca_cli.core.validators import validate_id

_TRUST_URL = "/OS-TRUST/trusts"


@click.group()
def trust() -> None:
    """Manage Keystone trusts (token delegation)."""
    pass


@trust.command("list")
@click.option("--trustor", default=None, help="Filter by trustor user ID.")
@click.option("--trustee", default=None, help="Filter by trustee user ID.")
@output_options
@click.pass_context
def trust_list(ctx, trustor, trustee, output_format, columns, fit_width, max_width, noindent):
    """List trusts."""
    client = ctx.find_object(OrcaContext).ensure_client()
    params = {}
    if trustor:
        params["trustor_user_id"] = trustor
    if trustee:
        params["trustee_user_id"] = trustee

    trusts = client.get(f"{client.identity_url}{_TRUST_URL}",
                        params=params).get("trusts", [])

    print_list(
        trusts,
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Trustor", "trustor_user_id"),
            ("Trustee", "trustee_user_id"),
            ("Project", lambda t: t.get("project_id") or "—"),
            ("Expires", lambda t: t.get("expires_at") or "never"),
            ("Impersonation", lambda t: "Yes" if t.get("impersonation") else "No"),
        ],
        title="Trusts",
        output_format=output_format, fit_width=fit_width, max_width=max_width,
        noindent=noindent, columns=columns,
        empty_msg="No trusts found.",
    )


@trust.command("show")
@click.argument("trust_id", callback=validate_id)
@output_options
@click.pass_context
def trust_show(ctx, trust_id, output_format, columns, fit_width, max_width, noindent):
    """Show trust details."""
    client = ctx.find_object(OrcaContext).ensure_client()
    t = client.get(f"{client.identity_url}{_TRUST_URL}/{trust_id}").get("trust", {})

    fields = [(k, str(t.get(k, "") or "")) for k in
              ["id", "trustor_user_id", "trustee_user_id", "project_id",
               "impersonation", "expires_at", "remaining_uses"]]
    roles = t.get("roles", [])
    if roles:
        fields.append(("roles", ", ".join(r.get("name", r.get("id", "")) for r in roles)))

    print_detail(
        fields,
        output_format=output_format, fit_width=fit_width, max_width=max_width,
        noindent=noindent, columns=columns,
    )


@trust.command("create")
@click.option("--trustor", required=True, help="Trustor user ID (delegating identity).")
@click.option("--trustee", required=True, help="Trustee user ID (receiving delegation).")
@click.option("--project", default=None, help="Project ID for the trust scope.")
@click.option("--role", "roles", multiple=True, help="Role name to delegate (repeatable).")
@click.option("--impersonate/--no-impersonate", default=False,
              help="Allow trustee to impersonate trustor.")
@click.option("--expires-at", default=None,
              help="Expiry datetime in ISO 8601 (e.g. 2026-12-31T23:59:59Z).")
@click.option("--uses", default=None, type=int,
              help="Maximum number of times the trust can be used.")
@click.pass_context
def trust_create(ctx, trustor, trustee, project, roles, impersonate, expires_at, uses):
    """Create a trust (delegation from trustor to trustee).

    \b
    Example:
      orca trust create \\
        --trustor <user-id> \\
        --trustee <user-id> \\
        --project <project-id> \\
        --role member \\
        --impersonate
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {
        "trustor_user_id": trustor,
        "trustee_user_id": trustee,
        "impersonation": impersonate,
    }
    if project:
        body["project_id"] = project
    if roles:
        body["roles"] = [{"name": r} for r in roles]
    if expires_at:
        body["expires_at"] = expires_at
    if uses is not None:
        body["allow_redelegation"] = False
        body["remaining_uses"] = uses

    t = client.post(f"{client.identity_url}{_TRUST_URL}",
                    json={"trust": body}).get("trust", {})
    console.print(f"[green]Trust created: {t.get('id', '?')}[/green]")
    console.print(f"  Trustor: {trustor}  →  Trustee: {trustee}")
    if expires_at:
        console.print(f"  Expires: {expires_at}")


@trust.command("delete")
@click.argument("trust_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def trust_delete(ctx, trust_id, yes):
    """Delete a trust."""
    client = ctx.find_object(OrcaContext).ensure_client()
    if not yes:
        click.confirm(f"Delete trust {trust_id}?", abort=True)
    client.delete(f"{client.identity_url}{_TRUST_URL}/{trust_id}")
    console.print(f"[green]Trust {trust_id} deleted.[/green]")
