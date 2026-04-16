"""``orca token`` — issue and revoke Keystone tokens."""

from __future__ import annotations

import click

from orca_cli.core.context import OrcaContext
from orca_cli.core.output import console, output_options, print_detail


def _iam(client) -> str:
    return client.identity_url


@click.group("token")
@click.pass_context
def token(ctx: click.Context) -> None:
    """Manage Keystone tokens."""


@token.command("issue")
@output_options
@click.pass_context
def token_issue(ctx, output_format, columns, fit_width, max_width, noindent):
    """Issue a token for the current credentials (show token details)."""
    client = ctx.find_object(OrcaContext).ensure_client()
    # Token is already acquired during client init; expose it
    tok = client._token or ""  # type: ignore[attr-defined]
    token_data = client._token_data or {}  # type: ignore[attr-defined]
    user = token_data.get("user", {})
    catalog = token_data.get("catalog", [])
    expires = token_data.get("expires_at", "")
    issued = token_data.get("issued_at", "")
    fields = [
        ("Token", tok),
        ("User ID", user.get("id", "")),
        ("User Name", user.get("name", "")),
        ("Project ID", token_data.get("project", {}).get("id", "")),
        ("Project Name", token_data.get("project", {}).get("name", "")),
        ("Domain ID", token_data.get("domain", {}).get("id", "")),
        ("Issued At", issued),
        ("Expires At", expires),
        ("Service Catalog Entries", str(len(catalog))),
    ]
    print_detail(fields,
                 output_format=output_format, columns=columns,
                 fit_width=fit_width, max_width=max_width, noindent=noindent)


@token.command("revoke")
@click.argument("token_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def token_revoke(ctx, token_id, yes):
    """Revoke a token."""
    client = ctx.find_object(OrcaContext).ensure_client()
    if not yes:
        click.confirm(f"Revoke token {token_id[:16]}…?", abort=True)
    client.delete(f"{_iam(client)}/v3/auth/tokens",
                  headers={"X-Subject-Token": token_id})
    console.print("Token revoked.")
