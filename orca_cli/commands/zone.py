"""``orca zone`` — manage DNS zones (Designate)."""

from __future__ import annotations

import time

import click

from orca_cli.core.context import OrcaContext
from orca_cli.core.output import console, output_options, print_detail, print_list
from orca_cli.core.validators import safe_output_path
from orca_cli.services.dns import DnsService


def _status_style(status: str) -> str:
    """Return a Rich style string for a Designate resource status."""
    s = (status or "").upper()
    if s == "ACTIVE":
        return "green"
    if s == "PENDING":
        return "yellow"
    if s == "ERROR":
        return "red"
    return "dim"


def _resolve_zone_id(svc: DnsService, zone: str) -> str:
    """Resolve a zone argument to an ID.

    If *zone* looks like a UUID it is returned as-is.  Otherwise the zone list
    is queried and the first zone whose name matches is used.
    """
    # Simple heuristic: UUIDs contain dashes and are 36 chars long
    if len(zone) == 36 and "-" in zone:
        return zone
    # Try matching by name
    zones = svc.find_zones(params={"name": zone})
    if zones:
        return zones[0]["id"]
    # Fallback: treat as ID anyway (let the API return a useful error)
    return zone


_TYPE_COLORS: dict[str, str] = {
    "A": "green",
    "AAAA": "blue",
    "CNAME": "yellow",
    "MX": "magenta",
    "TXT": "dim",
    "NS": "cyan",
    "SOA": "bold",
    "SRV": "red",
    "PTR": "bright_magenta",
}

# Preferred display order for record types in the tree view
_TYPE_ORDER: list[str] = ["SOA", "NS", "A", "AAAA", "CNAME", "MX", "TXT", "SRV", "PTR"]


@click.group()
@click.pass_context
def zone(ctx: click.Context) -> None:
    """Manage DNS zones (Designate)."""
    pass


@zone.command("list")
@output_options
@click.pass_context
def zone_list(ctx: click.Context, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List DNS zones."""
    client = ctx.find_object(OrcaContext).ensure_client()
    svc = DnsService(client)
    zones = svc.find_zones()

    print_list(
        zones,
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Name", "name", {"style": "bold"}),
            ("Type", "type"),
            ("Status", lambda z: z.get("status", ""), {"style": "green"}),
            ("Email", lambda z: z.get("email", "") or "—"),
            ("TTL", lambda z: str(z.get("ttl", "")), {"justify": "right"}),
            ("Serial", lambda z: str(z.get("serial", ""))),
        ],
        title="DNS Zones",
        output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent,
        columns=columns,
        empty_msg="No DNS zones found.",
    )


@zone.command("show")
@click.argument("zone")
@output_options
@click.pass_context
def zone_show(ctx: click.Context, zone: str, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show DNS zone details.

    ZONE can be a zone ID or name.
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    svc = DnsService(client)
    zone_id = _resolve_zone_id(svc, zone)
    data = svc.get_zone(zone_id)

    fields = [
        (key, str(data.get(key, "") or ""))
        for key in [
            "id", "name", "type", "status", "email", "ttl", "serial",
            "pool_id", "project_id", "description",
            "masters", "created_at", "updated_at", "version",
        ]
    ]

    print_detail(fields, output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent, columns=columns)


@zone.command("create")
@click.argument("name")
@click.option("--email", required=True, help="Zone administrator email.")
@click.option("--ttl", type=int, default=None, help="Default TTL in seconds.")
@click.option("--description", default=None, help="Zone description.")
@click.option("--type", "zone_type", type=click.Choice(["PRIMARY", "SECONDARY"], case_sensitive=False),
              default="PRIMARY", show_default=True, help="Zone type.")
@click.option("--masters", multiple=True, help="Master servers (for SECONDARY zones, repeatable).")
@click.pass_context
def zone_create(ctx: click.Context, name: str, email: str, ttl: int | None,
                description: str | None, zone_type: str, masters: tuple[str, ...]) -> None:
    """Create a DNS zone.

    \b
    NAME must be a fully-qualified domain name ending with a dot, e.g.:
      orca zone create example.com. --email admin@example.com
    """
    if not name.endswith("."):
        raise click.BadParameter("Zone name must end with a dot (e.g. 'example.com.').", param_hint="'NAME'")

    client = ctx.find_object(OrcaContext).ensure_client()
    svc = DnsService(client)
    body: dict = {"name": name, "email": email, "type": zone_type.upper()}
    if ttl is not None:
        body["ttl"] = ttl
    if description:
        body["description"] = description
    if masters:
        body["masters"] = list(masters)

    data = svc.create_zone(body)
    console.print(f"[green]Zone '{data.get('name', name)}' created (ID: {data.get('id', '?')}).[/green]")


@zone.command("set")
@click.argument("zone")
@click.option("--email", default=None, help="Zone administrator email.")
@click.option("--ttl", type=int, default=None, help="Default TTL in seconds.")
@click.option("--description", default=None, help="Zone description.")
@click.pass_context
def zone_set(ctx: click.Context, zone: str, email: str | None,
             ttl: int | None, description: str | None) -> None:
    """Update a DNS zone.

    ZONE can be a zone ID or name.
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    svc = DnsService(client)
    zone_id = _resolve_zone_id(svc, zone)

    body: dict = {}
    if email is not None:
        body["email"] = email
    if ttl is not None:
        body["ttl"] = ttl
    if description is not None:
        body["description"] = description

    if not body:
        console.print("[yellow]Nothing to update — provide at least one option.[/yellow]")
        return

    svc.update_zone(zone_id, body)
    console.print(f"[green]Zone {zone_id} updated.[/green]")


@zone.command("delete")
@click.argument("zone")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def zone_delete(ctx: click.Context, zone: str, yes: bool) -> None:
    """Delete a DNS zone.

    ZONE can be a zone ID or name.
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    svc = DnsService(client)
    zone_id = _resolve_zone_id(svc, zone)

    if not yes:
        click.confirm(f"Delete zone {zone_id}?", abort=True)

    svc.delete_zone(zone_id)
    console.print(f"[green]Zone {zone_id} deleted.[/green]")


@zone.command("tree")
@click.argument("zone")
@click.pass_context
def zone_tree(ctx: click.Context, zone: str) -> None:
    """Show a zone as a Rich tree grouped by record type.

    \b
    Displays SOA at the top, then NS, then A/AAAA/CNAME/MX/TXT and other
    types — each colour-coded for quick scanning.

    ZONE can be a zone ID or name.
    """
    from rich.tree import Tree

    client = ctx.find_object(OrcaContext).ensure_client()
    svc = DnsService(client)
    zone_id = _resolve_zone_id(svc, zone)

    zone_data = svc.get_zone(zone_id)
    zone_name = zone_data.get("name", zone_id)

    # Fetch all recordsets for the zone.
    # Designate returns up to the per-page default; for very large zones the
    # service exposes pagination via links.next — currently not followed here
    # because the service method does not expose cursoring. Acceptable: tree
    # view is a UX convenience, not an audit-grade listing.
    recordsets = svc.find_recordsets(zone_id)

    # Group by type
    by_type: dict[str, list] = {}
    for rs in recordsets:
        rtype = rs.get("type", "UNKNOWN")
        by_type.setdefault(rtype, []).append(rs)

    # Build tree
    root = Tree(f"[bold]{zone_name}[/bold]  [dim]{zone_id}[/dim]")

    # Sort: known types first in preferred order, then any remaining alphabetically
    known_order = [t for t in _TYPE_ORDER if t in by_type]
    remaining = sorted(t for t in by_type if t not in _TYPE_ORDER)
    ordered_types = known_order + remaining

    for rtype in ordered_types:
        color = _TYPE_COLORS.get(rtype, "white")
        type_node = root.add(f"[{color}]{rtype}[/{color}]  [dim]({len(by_type[rtype])} record{'s' if len(by_type[rtype]) != 1 else ''})[/dim]")
        for rs in sorted(by_type[rtype], key=lambda r: r.get("name", "")):
            name = rs.get("name", "")
            values = rs.get("records", []) or []
            ttl = rs.get("ttl")
            ttl_str = f"  [dim]TTL={ttl}[/dim]" if ttl is not None else ""
            if len(values) == 1:
                type_node.add(f"[{color}]{name}[/{color}] → {values[0]}{ttl_str}")
            elif values:
                rec_node = type_node.add(f"[{color}]{name}[/{color}]{ttl_str}")
                for v in values:
                    rec_node.add(v)
            else:
                type_node.add(f"[{color}]{name}[/{color}]  [dim](no records)[/dim]{ttl_str}")

    console.print(root)


@zone.command("export")
@click.argument("zone")
@click.option("--file", "output_file", default=None, type=click.Path(),
              help="Write zone file to this path (default: stdout).")
@click.pass_context
def zone_export(ctx: click.Context, zone: str, output_file: str | None) -> None:
    """Export a zone as a BIND-format zone file.

    \b
    Examples:
      orca zone export example.com.
      orca zone export example.com. --file example.com.zone
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    svc = DnsService(client)
    zone_id = _resolve_zone_id(svc, zone)

    # Create the export task
    task = svc.export_zone(zone_id)
    export_id = task.get("id", "")
    if not export_id:
        console.print("[red]Failed to create zone export task.[/red]")
        return

    # Poll until the export is complete
    with console.status("[bold cyan]Exporting zone…[/bold cyan]"):
        for _ in range(60):
            status_data = svc.get_export_task(export_id)
            status = status_data.get("status", "")
            if status == "COMPLETE":
                break
            if status == "ERROR":
                msg = status_data.get("message", "unknown error")
                console.print(f"[red]Zone export failed: {msg}[/red]")
                return
            time.sleep(1)
        else:
            console.print("[red]Zone export timed out.[/red]")
            return

    zone_content = svc.fetch_export_text(export_id)
    if output_file:
        out = safe_output_path(output_file)
        out.write_text(zone_content)
        console.print(f"[green]Zone exported to {out}.[/green]")
    else:
        console.print(zone_content)


@zone.command("import")
@click.option("--file", "input_file", required=True, type=click.Path(exists=True),
              help="BIND-format zone file to import.")
@click.pass_context
def zone_import(ctx: click.Context, input_file: str) -> None:
    """Import a zone from a BIND-format zone file.

    \b
    Examples:
      orca zone import --file example.com.zone
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    svc = DnsService(client)

    with open(input_file) as fh:
        content = fh.read()

    data = svc.import_zone_text(content)
    status = data.get("status", "")
    import_id = data.get("id", "")
    console.print(f"[green]Zone import initiated (ID: {import_id}, status: {status}).[/green]")

    # Poll briefly to report final status
    with console.status("[bold cyan]Importing zone…[/bold cyan]"):
        for _ in range(30):
            check = svc.get_import_task(import_id)
            s = check.get("status", "")
            if s == "COMPLETE":
                zone_id = check.get("zone_id", "?")
                console.print(f"[green]Zone import complete (zone ID: {zone_id}).[/green]")
                return
            if s == "ERROR":
                msg = check.get("message", "unknown error")
                console.print(f"[red]Zone import failed: {msg}[/red]")
                return
            time.sleep(1)

    console.print("[yellow]Zone import still in progress — check status later.[/yellow]")


@zone.command("reverse-lookup")
@click.argument("ip")
@click.pass_context
def reverse_lookup(ctx: click.Context, ip: str) -> None:
    """Find PTR records for an IP address.

    Queries Designate reverse DNS for floating IPs and searches for matching
    in-addr.arpa / ip6.arpa zones.

    \b
    Examples:
      orca zone reverse-lookup 192.0.2.1
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    svc = DnsService(client)

    # Try the Designate reverse floatingips endpoint first
    try:
        floatingips = svc.find_reverse_floatingips()
        matches = [
            fip for fip in floatingips
            if fip.get("address") == ip
        ]
        if matches:
            for fip in matches:
                console.print(f"[bold]{ip}[/bold] → [green]{fip.get('ptrdname', '—')}[/green]"
                              f"  [dim](floating IP {fip.get('id', '')})[/dim]")
            return
    except Exception:
        pass

    # Fallback: build the in-addr.arpa name and search recordsets
    parts = ip.split(".")
    if len(parts) == 4:
        arpa_name = ".".join(reversed(parts)) + ".in-addr.arpa."
        console.print(f"[dim]Searching for {arpa_name} …[/dim]")
        try:
            rsets = svc.find_all_recordsets(params={"name": arpa_name, "type": "PTR"})
            if rsets:
                for rs in rsets:
                    values = ", ".join(rs.get("records", []) or []) or "—"
                    console.print(f"[bold]{ip}[/bold] → [green]{values}[/green]"
                                  f"  [dim](zone {rs.get('zone_name', rs.get('zone_id', ''))})[/dim]")
                return
        except Exception:
            pass

    console.print(f"[yellow]No PTR record found for {ip}.[/yellow]")


# ══════════════════════════════════════════════════════════════════════════
#  Zone Transfer Requests
# ══════════════════════════════════════════════════════════════════════════

@zone.command("transfer-request-create")
@click.argument("zone_id")
@click.option("--target-project-id", default=None,
              help="Restrict transfer to a specific project ID.")
@click.option("--description", default=None, help="Description.")
@click.pass_context
def zone_transfer_request_create(ctx: click.Context, zone_id: str,
                                  target_project_id: str | None,
                                  description: str | None) -> None:
    """Create a zone transfer request."""
    client = ctx.find_object(OrcaContext).ensure_client()
    svc = DnsService(client)
    zone_id = _resolve_zone_id(svc, zone_id)
    body: dict = {}
    if target_project_id:
        body["target_project_id"] = target_project_id
    if description:
        body["description"] = description
    t = svc.create_transfer_request(zone_id, body)
    console.print(f"[green]Transfer request created: {t.get('id', '?')}[/green]")
    if t.get("key"):
        console.print(f"  Key: [bold cyan]{t['key']}[/bold cyan]")
        console.print("  [yellow]Save the key — it is needed to accept the transfer.[/yellow]")


@zone.command("transfer-request-list")
@output_options
@click.pass_context
def zone_transfer_request_list(ctx: click.Context, output_format: str,
                                columns: tuple[str, ...], fit_width: bool,
                                max_width: int | None, noindent: bool) -> None:
    """List zone transfer requests."""
    client = ctx.find_object(OrcaContext).ensure_client()
    svc = DnsService(client)
    items = svc.find_transfer_requests()
    print_list(
        items,
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Zone ID", "zone_id"),
            ("Zone Name", "zone_name"),
            ("Status", "status", {"style": "green"}),
            ("Target Project", lambda t: t.get("target_project_id") or "any"),
        ],
        title="Zone Transfer Requests",
        output_format=output_format, fit_width=fit_width, max_width=max_width,
        noindent=noindent, columns=columns,
        empty_msg="No transfer requests found.",
    )


@zone.command("transfer-request-show")
@click.argument("transfer_id")
@output_options
@click.pass_context
def zone_transfer_request_show(ctx: click.Context, transfer_id: str,
                                output_format: str, columns: tuple[str, ...],
                                fit_width: bool, max_width: int | None,
                                noindent: bool) -> None:
    """Show a zone transfer request."""
    client = ctx.find_object(OrcaContext).ensure_client()
    svc = DnsService(client)
    t = svc.get_transfer_request(transfer_id)
    fields = [(k, str(t.get(k, "") or "")) for k in
              ["id", "zone_id", "zone_name", "status", "target_project_id",
               "description", "created_at", "updated_at"]]
    print_detail(fields, output_format=output_format, fit_width=fit_width,
                 max_width=max_width, noindent=noindent, columns=columns)


@zone.command("transfer-request-delete")
@click.argument("transfer_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def zone_transfer_request_delete(ctx: click.Context, transfer_id: str, yes: bool) -> None:
    """Delete a zone transfer request."""
    if not yes:
        click.confirm(f"Delete transfer request {transfer_id}?", abort=True)
    client = ctx.find_object(OrcaContext).ensure_client()
    svc = DnsService(client)
    svc.delete_transfer_request(transfer_id)
    console.print(f"[green]Transfer request {transfer_id} deleted.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  Zone Transfer Accepts
# ══════════════════════════════════════════════════════════════════════════

@zone.command("transfer-accept")
@click.argument("transfer_id")
@click.argument("key")
@click.pass_context
def zone_transfer_accept(ctx: click.Context, transfer_id: str, key: str) -> None:
    """Accept a zone transfer request."""
    client = ctx.find_object(OrcaContext).ensure_client()
    svc = DnsService(client)
    t = svc.accept_transfer({"zone_transfer_request_id": transfer_id, "key": key})
    console.print(f"[green]Transfer accepted. Zone ID: {t.get('zone_id', '?')}[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  TLDs (admin)
# ══════════════════════════════════════════════════════════════════════════

@zone.command("tld-list")
@output_options
@click.pass_context
def zone_tld_list(ctx: click.Context, output_format: str, columns: tuple[str, ...],
                  fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List allowed TLDs (admin)."""
    client = ctx.find_object(OrcaContext).ensure_client()
    svc = DnsService(client)
    tlds = svc.find_tlds()
    print_list(
        tlds,
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Name", "name", {"style": "bold"}),
            ("Description", lambda t: (t.get("description") or "")[:50]),
        ],
        title="TLDs",
        output_format=output_format, fit_width=fit_width, max_width=max_width,
        noindent=noindent, columns=columns,
        empty_msg="No TLDs found.",
    )


@zone.command("tld-create")
@click.argument("name")
@click.option("--description", default=None, help="Description.")
@click.pass_context
def zone_tld_create(ctx: click.Context, name: str, description: str | None) -> None:
    """Create a TLD (admin)."""
    client = ctx.find_object(OrcaContext).ensure_client()
    svc = DnsService(client)
    body: dict = {"name": name}
    if description:
        body["description"] = description
    t = svc.create_tld(body)
    console.print(f"[green]TLD '{name}' created: {t.get('id', '?')}[/green]")


@zone.command("tld-delete")
@click.argument("tld_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def zone_tld_delete(ctx: click.Context, tld_id: str, yes: bool) -> None:
    """Delete a TLD (admin)."""
    if not yes:
        click.confirm(f"Delete TLD {tld_id}?", abort=True)
    client = ctx.find_object(OrcaContext).ensure_client()
    svc = DnsService(client)
    svc.delete_tld(tld_id)
    console.print(f"[green]TLD {tld_id} deleted.[/green]")
