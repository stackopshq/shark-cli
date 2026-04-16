"""``orca credential`` — manage Keystone credentials (EC2, TOTP, etc.)."""

from __future__ import annotations

import click

from orca_cli.core.context import OrcaContext
from orca_cli.core.output import console, output_options, print_detail, print_list
from orca_cli.core.validators import validate_id


@click.group()
def credential() -> None:
    """Manage Keystone credentials."""
    pass


@credential.command("list")
@click.option("--user", default=None, help="Filter by user ID.")
@click.option("--type", "cred_type", default=None, help="Filter by type (ec2, totp, cert…).")
@output_options
@click.pass_context
def credential_list(ctx, user, cred_type, output_format, columns, fit_width, max_width, noindent):
    """List credentials."""
    client = ctx.find_object(OrcaContext).ensure_client()
    params = {}
    if user:
        params["user_id"] = user
    if cred_type:
        params["type"] = cred_type

    creds = client.get(f"{client.identity_url}/credentials",
                       params=params).get("credentials", [])

    print_list(
        creds,
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Type", "type"),
            ("User ID", "user_id"),
            ("Project ID", lambda c: c.get("project_id") or "—"),
            ("Blob", lambda c: (c.get("blob") or "")[:40] + ("…" if len(c.get("blob") or "") > 40 else "")),
        ],
        title="Credentials",
        output_format=output_format, fit_width=fit_width, max_width=max_width,
        noindent=noindent, columns=columns,
        empty_msg="No credentials found.",
    )


@credential.command("show")
@click.argument("credential_id", callback=validate_id)
@output_options
@click.pass_context
def credential_show(ctx, credential_id, output_format, columns, fit_width, max_width, noindent):
    """Show credential details."""
    client = ctx.find_object(OrcaContext).ensure_client()
    cred = client.get(f"{client.identity_url}/credentials/{credential_id}").get("credential", {})

    print_detail(
        [(k, str(cred.get(k, "") or "")) for k in
         ["id", "type", "user_id", "project_id", "blob"]],
        output_format=output_format, fit_width=fit_width, max_width=max_width,
        noindent=noindent, columns=columns,
    )


@credential.command("create")
@click.option("--user", required=True, help="User ID who owns this credential.")
@click.option("--type", "cred_type", required=True,
              help="Credential type (ec2, totp, cert, etc.).")
@click.option("--blob", required=True, help="Credential data (JSON string or raw value).")
@click.option("--project", default=None, help="Project ID (required for EC2 credentials).")
@click.pass_context
def credential_create(ctx, user, cred_type, blob, project):
    """Create a credential."""
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {"user_id": user, "type": cred_type, "blob": blob}
    if project:
        body["project_id"] = project

    cred = client.post(f"{client.identity_url}/credentials",
                       json={"credential": body}).get("credential", {})
    console.print(f"[green]Credential created: {cred.get('id', '?')} (type: {cred_type})[/green]")


@credential.command("set")
@click.argument("credential_id", callback=validate_id)
@click.option("--blob", default=None, help="New credential data.")
@click.option("--project", default=None, help="New project ID.")
@click.pass_context
def credential_set(ctx, credential_id, blob, project):
    """Update a credential."""
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {}
    if blob is not None:
        body["blob"] = blob
    if project is not None:
        body["project_id"] = project
    if not body:
        console.print("[yellow]Nothing to update.[/yellow]")
        return
    client.patch(f"{client.identity_url}/credentials/{credential_id}",
                 json={"credential": body})
    console.print(f"[green]Credential {credential_id} updated.[/green]")


@credential.command("delete")
@click.argument("credential_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def credential_delete(ctx, credential_id, yes):
    """Delete a credential."""
    client = ctx.find_object(OrcaContext).ensure_client()
    if not yes:
        click.confirm(f"Delete credential {credential_id}?", abort=True)
    client.delete(f"{client.identity_url}/credentials/{credential_id}")
    console.print(f"[green]Credential {credential_id} deleted.[/green]")
