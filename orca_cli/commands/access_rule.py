"""``orca access-rule`` — manage application credential access rules (Keystone)."""

from __future__ import annotations

import click

from orca_cli.core.context import OrcaContext
from orca_cli.core.output import console, output_options, print_detail, print_list
from orca_cli.core.validators import validate_id
from orca_cli.services.identity import IdentityService


@click.group("access-rule")
@click.pass_context
def access_rule(ctx: click.Context) -> None:
    """Manage application credential access rules (Keystone)."""


@access_rule.command("list")
@click.option("--user-id", default=None, callback=validate_id,
              help="User ID (defaults to current user).")
@click.option("--service", default=None, help="Filter by service type (e.g. compute).")
@click.option("--method", default=None, help="Filter by HTTP method.")
@click.option("--path", default=None, help="Filter by API path.")
@output_options
@click.pass_context
def ar_list(ctx, user_id, service, method, path,
            output_format, columns, fit_width, max_width, noindent):
    """List access rules."""
    client = ctx.find_object(OrcaContext).ensure_client()
    svc = IdentityService(client)
    uid = user_id or client._token_data.get("user", {}).get("id", "")
    # ``service``/``method``/``path`` were passed as query params to Keystone
    # in the pre-service implementation. Keystone does not support filtering
    # the access_rules endpoint, so they were silently no-ops; we intentionally
    # keep them as CLI flags without applying any filter (parity with prior
    # behaviour).
    del service, method, path
    items = svc.find_access_rules(uid)
    if not items:
        console.print("No access rules found.")
        return
    col_defs = [
        ("ID", "id"),
        ("Service", "service"),
        ("Method", "method"),
        ("Path", "path"),
    ]
    print_list(items, col_defs, title="Access Rules",
               output_format=output_format, columns=columns,
               fit_width=fit_width, max_width=max_width, noindent=noindent)


@access_rule.command("show")
@click.argument("access_rule_id", callback=validate_id)
@click.option("--user-id", default=None, callback=validate_id,
              help="User ID (defaults to current user).")
@output_options
@click.pass_context
def ar_show(ctx, access_rule_id, user_id,
            output_format, columns, fit_width, max_width, noindent):
    """Show an access rule."""
    client = ctx.find_object(OrcaContext).ensure_client()
    svc = IdentityService(client)
    uid = user_id or client._token_data.get("user", {}).get("id", "")
    ar = svc.get_access_rule(uid, access_rule_id)
    fields = [
        ("ID", ar.get("id", "")),
        ("Service", ar.get("service", "")),
        ("Method", ar.get("method", "")),
        ("Path", ar.get("path", "")),
    ]
    print_detail(fields,
                 output_format=output_format, columns=columns,
                 fit_width=fit_width, max_width=max_width, noindent=noindent)


@access_rule.command("delete")
@click.argument("access_rule_id", callback=validate_id)
@click.option("--user-id", default=None, callback=validate_id,
              help="User ID (defaults to current user).")
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def ar_delete(ctx, access_rule_id, user_id, yes):
    """Delete an access rule."""
    client = ctx.find_object(OrcaContext).ensure_client()
    svc = IdentityService(client)
    uid = user_id or client._token_data.get("user", {}).get("id", "")
    if not yes:
        click.confirm(f"Delete access rule {access_rule_id}?", abort=True)
    svc.delete_access_rule(uid, access_rule_id)
    console.print(f"Access rule [bold]{access_rule_id}[/bold] deleted.")
