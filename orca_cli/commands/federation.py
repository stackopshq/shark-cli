"""``orca identity-provider / federation-protocol / mapping / service-provider`` — Keystone federation."""

from __future__ import annotations

import json

import click

from orca_cli.core.context import OrcaContext
from orca_cli.core.output import console, output_options, print_detail, print_list
from orca_cli.core.validators import validate_id


def _iam(client) -> str:
    return client.identity_url


# ══════════════════════════════════════════════════════════════════════════════
#  Identity Providers
# ══════════════════════════════════════════════════════════════════════════════

@click.group("identity-provider")
@click.pass_context
def identity_provider(ctx: click.Context) -> None:
    """Manage Keystone identity providers (federation)."""


@identity_provider.command("list")
@output_options
@click.pass_context
def idp_list(ctx, output_format, columns, fit_width, max_width, noindent):
    """List identity providers."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_iam(client)}/v3/identity_providers")
    items = data.get("identity_providers", [])
    if not items:
        console.print("No identity providers found.")
        return
    col_defs = [
        ("ID", "id"),
        ("Enabled", "enabled"),
        ("Description", "description"),
        ("Domain ID", "domain_id"),
    ]
    print_list(items, col_defs, title="Identity Providers",
               output_format=output_format, columns=columns,
               fit_width=fit_width, max_width=max_width, noindent=noindent)


@identity_provider.command("show")
@click.argument("idp_id")
@output_options
@click.pass_context
def idp_show(ctx, idp_id, output_format, columns, fit_width, max_width, noindent):
    """Show an identity provider."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_iam(client)}/v3/identity_providers/{idp_id}")
    idp = data.get("identity_provider", data)
    fields = [
        ("ID", idp.get("id", "")),
        ("Enabled", idp.get("enabled", "")),
        ("Description", idp.get("description", "")),
        ("Domain ID", idp.get("domain_id", "")),
        ("Remote IDs", ", ".join(idp.get("remote_ids", []))),
    ]
    print_detail(fields,
                 output_format=output_format, columns=columns,
                 fit_width=fit_width, max_width=max_width, noindent=noindent)


@identity_provider.command("create")
@click.argument("idp_id")
@click.option("--remote-id", "remote_ids", multiple=True, metavar="REMOTE_ID",
              help="Remote entity ID. Repeatable.")
@click.option("--description", default="", help="Description.")
@click.option("--domain-id", default=None, help="Domain to associate.")
@click.option("--enable/--disable", default=True)
@output_options
@click.pass_context
def idp_create(ctx, idp_id, remote_ids, description, domain_id, enable,
               output_format, columns, fit_width, max_width, noindent):
    """Create an identity provider."""
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {"enabled": enable, "description": description,
                  "remote_ids": list(remote_ids)}
    if domain_id:
        body["domain_id"] = domain_id
    data = client.put(f"{_iam(client)}/v3/identity_providers/{idp_id}",
                      json={"identity_provider": body})
    idp = data.get("identity_provider", data)
    fields = [("ID", idp.get("id", "")), ("Enabled", idp.get("enabled", ""))]
    print_detail(fields,
                 output_format=output_format, columns=columns,
                 fit_width=fit_width, max_width=max_width, noindent=noindent)


@identity_provider.command("set")
@click.argument("idp_id")
@click.option("--description", default=None)
@click.option("--enable/--disable", default=None)
@click.option("--remote-id", "remote_ids", multiple=True)
@click.pass_context
def idp_set(ctx, idp_id, description, enable, remote_ids):
    """Update an identity provider."""
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {}
    if description is not None:
        body["description"] = description
    if enable is not None:
        body["enabled"] = enable
    if remote_ids:
        body["remote_ids"] = list(remote_ids)
    if not body:
        console.print("Nothing to update.")
        return
    client.patch(f"{_iam(client)}/v3/identity_providers/{idp_id}",
                 json={"identity_provider": body})
    console.print(f"Identity provider [bold]{idp_id}[/bold] updated.")


@identity_provider.command("delete")
@click.argument("idp_id")
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def idp_delete(ctx, idp_id, yes):
    """Delete an identity provider."""
    client = ctx.find_object(OrcaContext).ensure_client()
    if not yes:
        click.confirm(f"Delete identity provider {idp_id}?", abort=True)
    client.delete(f"{_iam(client)}/v3/identity_providers/{idp_id}")
    console.print(f"Identity provider [bold]{idp_id}[/bold] deleted.")


# ══════════════════════════════════════════════════════════════════════════════
#  Federation Protocols
# ══════════════════════════════════════════════════════════════════════════════

@click.group("federation-protocol")
@click.pass_context
def federation_protocol(ctx: click.Context) -> None:
    """Manage Keystone federation protocols."""


@federation_protocol.command("list")
@click.argument("idp_id")
@output_options
@click.pass_context
def fp_list(ctx, idp_id, output_format, columns, fit_width, max_width, noindent):
    """List federation protocols for an identity provider."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_iam(client)}/v3/identity_providers/{idp_id}/protocols")
    items = data.get("protocols", [])
    if not items:
        console.print("No protocols found.")
        return
    col_defs = [("ID", "id"), ("Mapping ID", "mapping_id")]
    print_list(items, col_defs, title=f"Protocols for {idp_id}",
               output_format=output_format, columns=columns,
               fit_width=fit_width, max_width=max_width, noindent=noindent)


@federation_protocol.command("show")
@click.argument("idp_id")
@click.argument("protocol_id")
@output_options
@click.pass_context
def fp_show(ctx, idp_id, protocol_id, output_format, columns, fit_width, max_width, noindent):
    """Show a federation protocol."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(
        f"{_iam(client)}/v3/identity_providers/{idp_id}/protocols/{protocol_id}")
    p = data.get("protocol", data)
    fields = [("ID", p.get("id", "")), ("Mapping ID", p.get("mapping_id", ""))]
    print_detail(fields,
                 output_format=output_format, columns=columns,
                 fit_width=fit_width, max_width=max_width, noindent=noindent)


@federation_protocol.command("create")
@click.argument("idp_id")
@click.argument("protocol_id")
@click.option("--mapping-id", required=True, help="Mapping ID to associate.")
@output_options
@click.pass_context
def fp_create(ctx, idp_id, protocol_id, mapping_id,
              output_format, columns, fit_width, max_width, noindent):
    """Create a federation protocol."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.put(
        f"{_iam(client)}/v3/identity_providers/{idp_id}/protocols/{protocol_id}",
        json={"protocol": {"mapping_id": mapping_id}})
    p = data.get("protocol", data)
    fields = [("ID", p.get("id", "")), ("Mapping ID", p.get("mapping_id", ""))]
    print_detail(fields,
                 output_format=output_format, columns=columns,
                 fit_width=fit_width, max_width=max_width, noindent=noindent)


@federation_protocol.command("set")
@click.argument("idp_id")
@click.argument("protocol_id")
@click.option("--mapping-id", required=True, help="New mapping ID.")
@click.pass_context
def fp_set(ctx, idp_id, protocol_id, mapping_id):
    """Update a federation protocol."""
    client = ctx.find_object(OrcaContext).ensure_client()
    client.patch(
        f"{_iam(client)}/v3/identity_providers/{idp_id}/protocols/{protocol_id}",
        json={"protocol": {"mapping_id": mapping_id}})
    console.print(f"Protocol [bold]{protocol_id}[/bold] updated.")


@federation_protocol.command("delete")
@click.argument("idp_id")
@click.argument("protocol_id")
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def fp_delete(ctx, idp_id, protocol_id, yes):
    """Delete a federation protocol."""
    client = ctx.find_object(OrcaContext).ensure_client()
    if not yes:
        click.confirm(f"Delete protocol {protocol_id}?", abort=True)
    client.delete(
        f"{_iam(client)}/v3/identity_providers/{idp_id}/protocols/{protocol_id}")
    console.print(f"Protocol [bold]{protocol_id}[/bold] deleted.")


# ══════════════════════════════════════════════════════════════════════════════
#  Mappings
# ══════════════════════════════════════════════════════════════════════════════

@click.group("mapping")
@click.pass_context
def mapping(ctx: click.Context) -> None:
    """Manage Keystone federation attribute mappings."""


@mapping.command("list")
@output_options
@click.pass_context
def mapping_list(ctx, output_format, columns, fit_width, max_width, noindent):
    """List mappings."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_iam(client)}/v3/mappings")
    items = data.get("mappings", [])
    if not items:
        console.print("No mappings found.")
        return
    col_defs = [("ID", "id"), ("Schema Version", "schema_version")]
    print_list(items, col_defs, title="Mappings",
               output_format=output_format, columns=columns,
               fit_width=fit_width, max_width=max_width, noindent=noindent)


@mapping.command("show")
@click.argument("mapping_id")
@click.pass_context
def mapping_show(ctx, mapping_id):
    """Show a mapping (prints JSON rules)."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_iam(client)}/v3/mappings/{mapping_id}")
    m = data.get("mapping", data)
    console.print_json(json.dumps(m, indent=2))


@mapping.command("create")
@click.argument("mapping_id")
@click.option("--rules", required=True, metavar="JSON",
              help="Mapping rules as a JSON string.")
@click.pass_context
def mapping_create(ctx, mapping_id, rules):
    """Create a mapping."""
    client = ctx.find_object(OrcaContext).ensure_client()
    try:
        rules_obj = json.loads(rules)
    except json.JSONDecodeError as exc:
        raise click.BadParameter(f"Invalid JSON: {exc}", param_hint="--rules")
    data = client.put(f"{_iam(client)}/v3/mappings/{mapping_id}",
                      json={"mapping": {"rules": rules_obj}})
    m = data.get("mapping", data)
    console.print(f"Mapping [bold]{m.get('id', mapping_id)}[/bold] created.")


@mapping.command("set")
@click.argument("mapping_id")
@click.option("--rules", required=True, metavar="JSON", help="New rules as JSON.")
@click.pass_context
def mapping_set(ctx, mapping_id, rules):
    """Update a mapping."""
    client = ctx.find_object(OrcaContext).ensure_client()
    try:
        rules_obj = json.loads(rules)
    except json.JSONDecodeError as exc:
        raise click.BadParameter(f"Invalid JSON: {exc}", param_hint="--rules")
    client.patch(f"{_iam(client)}/v3/mappings/{mapping_id}",
                 json={"mapping": {"rules": rules_obj}})
    console.print(f"Mapping [bold]{mapping_id}[/bold] updated.")


@mapping.command("delete")
@click.argument("mapping_id")
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def mapping_delete(ctx, mapping_id, yes):
    """Delete a mapping."""
    client = ctx.find_object(OrcaContext).ensure_client()
    if not yes:
        click.confirm(f"Delete mapping {mapping_id}?", abort=True)
    client.delete(f"{_iam(client)}/v3/mappings/{mapping_id}")
    console.print(f"Mapping [bold]{mapping_id}[/bold] deleted.")


# ══════════════════════════════════════════════════════════════════════════════
#  Service Providers
# ══════════════════════════════════════════════════════════════════════════════

@click.group("service-provider")
@click.pass_context
def service_provider(ctx: click.Context) -> None:
    """Manage Keystone service providers (federation)."""


@service_provider.command("list")
@output_options
@click.pass_context
def sp_list(ctx, output_format, columns, fit_width, max_width, noindent):
    """List service providers."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_iam(client)}/v3/service_providers")
    items = data.get("service_providers", [])
    if not items:
        console.print("No service providers found.")
        return
    col_defs = [
        ("ID", "id"),
        ("Enabled", "enabled"),
        ("Auth URL", "auth_url"),
        ("SP URL", "sp_url"),
        ("Description", "description"),
    ]
    print_list(items, col_defs, title="Service Providers",
               output_format=output_format, columns=columns,
               fit_width=fit_width, max_width=max_width, noindent=noindent)


@service_provider.command("show")
@click.argument("sp_id")
@output_options
@click.pass_context
def sp_show(ctx, sp_id, output_format, columns, fit_width, max_width, noindent):
    """Show a service provider."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_iam(client)}/v3/service_providers/{sp_id}")
    sp = data.get("service_provider", data)
    fields = [
        ("ID", sp.get("id", "")),
        ("Enabled", sp.get("enabled", "")),
        ("Auth URL", sp.get("auth_url", "")),
        ("SP URL", sp.get("sp_url", "")),
        ("Description", sp.get("description", "")),
        ("Relay State Prefix", sp.get("relay_state_prefix", "")),
    ]
    print_detail(fields,
                 output_format=output_format, columns=columns,
                 fit_width=fit_width, max_width=max_width, noindent=noindent)


@service_provider.command("create")
@click.argument("sp_id")
@click.option("--auth-url", required=True, help="Remote Keystone auth URL.")
@click.option("--sp-url", required=True, help="Service provider SAML2 endpoint.")
@click.option("--description", default="")
@click.option("--enable/--disable", default=True)
@output_options
@click.pass_context
def sp_create(ctx, sp_id, auth_url, sp_url, description, enable,
              output_format, columns, fit_width, max_width, noindent):
    """Create a service provider."""
    client = ctx.find_object(OrcaContext).ensure_client()
    body = {"auth_url": auth_url, "sp_url": sp_url,
            "description": description, "enabled": enable}
    data = client.put(f"{_iam(client)}/v3/service_providers/{sp_id}",
                      json={"service_provider": body})
    sp = data.get("service_provider", data)
    fields = [("ID", sp.get("id", "")), ("Auth URL", sp.get("auth_url", ""))]
    print_detail(fields,
                 output_format=output_format, columns=columns,
                 fit_width=fit_width, max_width=max_width, noindent=noindent)


@service_provider.command("set")
@click.argument("sp_id")
@click.option("--auth-url", default=None)
@click.option("--sp-url", default=None)
@click.option("--description", default=None)
@click.option("--enable/--disable", default=None)
@click.pass_context
def sp_set(ctx, sp_id, auth_url, sp_url, description, enable):
    """Update a service provider."""
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {}
    if auth_url is not None:
        body["auth_url"] = auth_url
    if sp_url is not None:
        body["sp_url"] = sp_url
    if description is not None:
        body["description"] = description
    if enable is not None:
        body["enabled"] = enable
    if not body:
        console.print("Nothing to update.")
        return
    client.patch(f"{_iam(client)}/v3/service_providers/{sp_id}",
                 json={"service_provider": body})
    console.print(f"Service provider [bold]{sp_id}[/bold] updated.")


@service_provider.command("delete")
@click.argument("sp_id")
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def sp_delete(ctx, sp_id, yes):
    """Delete a service provider."""
    client = ctx.find_object(OrcaContext).ensure_client()
    if not yes:
        click.confirm(f"Delete service provider {sp_id}?", abort=True)
    client.delete(f"{_iam(client)}/v3/service_providers/{sp_id}")
    console.print(f"Service provider [bold]{sp_id}[/bold] deleted.")
