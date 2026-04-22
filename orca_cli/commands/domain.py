"""``orca domain`` — manage domains (Keystone v3)."""

from __future__ import annotations

import click

from orca_cli.core.context import OrcaContext
from orca_cli.core.output import console, output_options, print_detail, print_list
from orca_cli.services.identity import IdentityService


@click.group()
@click.pass_context
def domain(ctx: click.Context) -> None:
    """Manage domains (Keystone v3)."""
    pass


@domain.command("list")
@output_options
@click.pass_context
def domain_list(ctx, output_format, columns, fit_width, max_width, noindent):
    """List domains."""
    svc = IdentityService(ctx.find_object(OrcaContext).ensure_client())
    print_list(
        svc.find_domains(),
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Name", "name", {"style": "bold"}),
            ("Description", lambda d: (d.get("description") or "")[:50]),
            ("Enabled", lambda d: "[green]yes[/green]" if d.get("enabled") else "[red]no[/red]"),
        ],
        title="Domains",
        output_format=output_format, columns=columns,
        fit_width=fit_width, max_width=max_width, noindent=noindent,
        empty_msg="No domains found.",
    )


@domain.command("show")
@click.argument("domain_id")
@output_options
@click.pass_context
def domain_show(ctx, domain_id, output_format, columns, fit_width, max_width, noindent):
    """Show domain details."""
    svc = IdentityService(ctx.find_object(OrcaContext).ensure_client())
    d = svc.get_domain(domain_id)
    print_detail(
        [
            ("ID", d.get("id", "")),
            ("Name", d.get("name", "")),
            ("Description", d.get("description") or "—"),
            ("Enabled", "yes" if d.get("enabled") else "no"),
        ],
        output_format=output_format, columns=columns,
        fit_width=fit_width, max_width=max_width, noindent=noindent,
    )


@domain.command("create")
@click.argument("name")
@click.option("--description", default=None)
@click.option("--enable/--disable", "enabled", default=True)
@click.pass_context
def domain_create(ctx, name, description, enabled):
    """Create a domain."""
    svc = IdentityService(ctx.find_object(OrcaContext).ensure_client())
    body: dict = {"name": name, "enabled": enabled}
    if description:
        body["description"] = description
    d = svc.create_domain(body)
    console.print(f"[green]Domain '{d.get('name')}' ({d.get('id')}) created.[/green]")


@domain.command("set")
@click.argument("domain_id")
@click.option("--name", default=None)
@click.option("--description", default=None)
@click.option("--enable/--disable", "enabled", default=None)
@click.pass_context
def domain_set(ctx, domain_id, name, description, enabled):
    """Update a domain."""
    body = {}
    if name:
        body["name"] = name
    if description:
        body["description"] = description
    if enabled is not None:
        body["enabled"] = enabled
    if not body:
        console.print("[yellow]Nothing to update.[/yellow]")
        return
    svc = IdentityService(ctx.find_object(OrcaContext).ensure_client())
    svc.update_domain(domain_id, body)
    console.print(f"[green]Domain {domain_id} updated.[/green]")


@domain.command("delete")
@click.argument("domain_id")
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def domain_delete(ctx, domain_id, yes):
    """Delete a domain."""
    if not yes:
        click.confirm(f"Delete domain {domain_id}?", abort=True)
    svc = IdentityService(ctx.find_object(OrcaContext).ensure_client())
    svc.delete_domain(domain_id)
    console.print(f"[green]Domain {domain_id} deleted.[/green]")
