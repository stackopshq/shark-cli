"""``orca application-credential`` — manage application credentials (Keystone v3)."""

from __future__ import annotations

import click

from orca_cli.core.context import OrcaContext
from orca_cli.core.output import console, output_options, print_detail, print_list


def _iam(client) -> str:
    return client.identity_url


@click.group(name="application-credential")
@click.pass_context
def application_credential(ctx: click.Context) -> None:
    """Manage application credentials (Keystone v3)."""
    pass


@application_credential.command("list")
@click.option("--user", "user_id", default=None, help="User ID (default: current user).")
@output_options
@click.pass_context
def app_credential_list(ctx, user_id, output_format, columns, fit_width, max_width, noindent):
    """List application credentials."""
    client = ctx.find_object(OrcaContext).ensure_client()
    uid = user_id or client._token_data.get("token", {}).get("user", {}).get("id", "me")
    data = client.get(f"{_iam(client)}/v3/users/{uid}/application_credentials")
    print_list(
        data.get("application_credentials", []),
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Name", "name", {"style": "bold"}),
            ("Description", lambda a: (a.get("description") or "")[:40]),
            ("Expires", lambda a: a.get("expires_at") or "never"),
            ("Unrestricted", lambda a: "yes" if a.get("unrestricted") else "no"),
        ],
        title="Application Credentials",
        output_format=output_format, columns=columns,
        fit_width=fit_width, max_width=max_width, noindent=noindent,
        empty_msg="No application credentials found.",
    )


@application_credential.command("show")
@click.argument("credential_id")
@click.option("--user", "user_id", default=None)
@output_options
@click.pass_context
def app_credential_show(ctx, credential_id, user_id,
                        output_format, columns, fit_width, max_width, noindent):
    """Show application credential details."""
    client = ctx.find_object(OrcaContext).ensure_client()
    uid = user_id or client._token_data.get("token", {}).get("user", {}).get("id", "me")
    data = client.get(f"{_iam(client)}/v3/users/{uid}/application_credentials/{credential_id}")
    a = data.get("application_credential", data)
    print_detail(
        [
            ("ID", a.get("id", "")),
            ("Name", a.get("name", "")),
            ("Description", a.get("description") or "—"),
            ("Project ID", a.get("project_id", "")),
            ("Expires", a.get("expires_at") or "never"),
            ("Unrestricted", "yes" if a.get("unrestricted") else "no"),
        ],
        output_format=output_format, columns=columns,
        fit_width=fit_width, max_width=max_width, noindent=noindent,
    )


@application_credential.command("create")
@click.argument("name")
@click.option("--description", default=None)
@click.option("--secret", default=None, help="Secret (auto-generated if omitted).")
@click.option("--expires", "expires_at", default=None, help="Expiry (ISO 8601, e.g. 2026-12-31T00:00:00).")
@click.option("--unrestricted", is_flag=True, help="Allow creation of other credentials (dangerous).")
@click.option("--user", "user_id", default=None)
@click.pass_context
def app_credential_create(ctx, name, description, secret, expires_at, unrestricted, user_id):
    """Create an application credential."""
    client = ctx.find_object(OrcaContext).ensure_client()
    uid = user_id or client._token_data.get("token", {}).get("user", {}).get("id", "me")
    body: dict = {"name": name, "unrestricted": unrestricted}
    if description:
        body["description"] = description
    if secret:
        body["secret"] = secret
    if expires_at:
        body["expires_at"] = expires_at

    data = client.post(
        f"{_iam(client)}/v3/users/{uid}/application_credentials",
        json={"application_credential": body},
    )
    a = data.get("application_credential", data)
    console.print(f"[green]Application credential '{a.get('name')}' ({a.get('id')}) created.[/green]")
    if a.get("secret"):
        console.print(f"  [cyan]Secret:[/cyan] {a['secret']}")
        console.print("  [bold yellow]This secret will NOT be shown again.[/bold yellow]")


@application_credential.command("delete")
@click.argument("credential_id")
@click.option("--user", "user_id", default=None)
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def app_credential_delete(ctx, credential_id, user_id, yes):
    """Delete an application credential."""
    if not yes:
        click.confirm(f"Delete application credential {credential_id}?", abort=True)
    client = ctx.find_object(OrcaContext).ensure_client()
    uid = user_id or client._token_data.get("token", {}).get("user", {}).get("id", "me")
    client.delete(f"{_iam(client)}/v3/users/{uid}/application_credentials/{credential_id}")
    console.print(f"[green]Application credential {credential_id} deleted.[/green]")
