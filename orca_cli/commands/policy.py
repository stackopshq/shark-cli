"""``orca policy`` — manage Keystone policies."""

from __future__ import annotations

import click

from orca_cli.core.context import OrcaContext
from orca_cli.core.output import console, output_options, print_detail, print_list
from orca_cli.core.validators import validate_id


def _iam(client) -> str:
    return client.identity_url


@click.group()
@click.pass_context
def policy(ctx: click.Context) -> None:
    """Manage Keystone policies."""


@policy.command("list")
@click.option("--type", "blob_type", default=None, help="Filter by policy type.")
@output_options
@click.pass_context
def policy_list(ctx, blob_type, output_format, columns, fit_width, max_width, noindent):
    """List policies."""
    client = ctx.find_object(OrcaContext).ensure_client()
    params = {}
    if blob_type:
        params["type"] = blob_type
    data = client.get(f"{_iam(client)}/v3/policies", params=params)
    items = data.get("policies", [])
    if not items:
        console.print("No policies found.")
        return
    col_defs = [
        ("ID", "id"),
        ("Type", "type"),
        ("Blob", lambda p: (p.get("blob", "")[:60] + "…" if len(p.get("blob", "")) > 60
                            else p.get("blob", ""))),
    ]
    print_list(items, col_defs, title="Policies",
               output_format=output_format, columns=columns,
               fit_width=fit_width, max_width=max_width, noindent=noindent)


@policy.command("show")
@click.argument("policy_id", callback=validate_id)
@output_options
@click.pass_context
def policy_show(ctx, policy_id, output_format, columns, fit_width, max_width, noindent):
    """Show a policy."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_iam(client)}/v3/policies/{policy_id}")
    p = data.get("policy", data)
    fields = [
        ("ID", p.get("id", "")),
        ("Type", p.get("type", "")),
        ("Blob", p.get("blob", "")),
        ("Project ID", p.get("project_id", "")),
        ("User ID", p.get("user_id", "")),
    ]
    print_detail(fields,
                 output_format=output_format, columns=columns,
                 fit_width=fit_width, max_width=max_width, noindent=noindent)


@policy.command("create")
@click.argument("blob")
@click.option("--type", "blob_type", default="application/json",
              show_default=True, help="MIME type of the policy blob.")
@output_options
@click.pass_context
def policy_create(ctx, blob, blob_type, output_format, columns, fit_width, max_width, noindent):
    """Create a policy."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.post(f"{_iam(client)}/v3/policies",
                       json={"policy": {"blob": blob, "type": blob_type}})
    p = data.get("policy", data)
    fields = [
        ("ID", p.get("id", "")),
        ("Type", p.get("type", "")),
        ("Blob", p.get("blob", "")),
    ]
    print_detail(fields,
                 output_format=output_format, columns=columns,
                 fit_width=fit_width, max_width=max_width, noindent=noindent)


@policy.command("set")
@click.argument("policy_id", callback=validate_id)
@click.option("--blob", default=None, help="New policy blob.")
@click.option("--type", "blob_type", default=None, help="New MIME type.")
@click.pass_context
def policy_set(ctx, policy_id, blob, blob_type):
    """Update a policy."""
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {}
    if blob is not None:
        body["blob"] = blob
    if blob_type is not None:
        body["type"] = blob_type
    if not body:
        console.print("Nothing to update.")
        return
    client.patch(f"{_iam(client)}/v3/policies/{policy_id}", json={"policy": body})
    console.print(f"Policy [bold]{policy_id}[/bold] updated.")


@policy.command("delete")
@click.argument("policy_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def policy_delete(ctx, policy_id, yes):
    """Delete a policy."""
    client = ctx.find_object(OrcaContext).ensure_client()
    if not yes:
        click.confirm(f"Delete policy {policy_id}?", abort=True)
    client.delete(f"{_iam(client)}/v3/policies/{policy_id}")
    console.print(f"Policy [bold]{policy_id}[/bold] deleted.")
