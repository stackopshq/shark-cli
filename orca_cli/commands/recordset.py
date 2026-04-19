"""``orca recordset`` — manage DNS recordsets (Designate)."""

from __future__ import annotations

import click

from orca_cli.core.context import OrcaContext
from orca_cli.core.output import console, output_options, print_detail, print_list


def _dns(client) -> str:
    return client.dns_url


def _resolve_zone_id(client, zone: str) -> str:
    """Resolve a zone argument to an ID.

    If *zone* looks like a UUID it is returned as-is.  Otherwise the zone list
    is queried and the first zone whose name matches is used.
    """
    # Simple heuristic: UUIDs contain dashes and are 36 chars long
    if len(zone) == 36 and "-" in zone:
        return zone
    # Try matching by name
    data = client.get(f"{_dns(client)}/v2/zones", params={"name": zone})
    zones = data.get("zones", [])
    if zones:
        return zones[0]["id"]
    # Fallback: treat as ID anyway (let the API return a useful error)
    return zone


@click.group()
@click.pass_context
def recordset(ctx: click.Context) -> None:
    """Manage DNS recordsets (Designate)."""
    pass


@recordset.command("list")
@click.argument("zone")
@click.option("--type", "record_type", default=None, help="Filter by record type (A, AAAA, CNAME, MX, …).")
@click.option("--name", "record_name", default=None, help="Filter by record name.")
@output_options
@click.pass_context
def recordset_list(ctx: click.Context, zone: str, record_type: str | None,
                   record_name: str | None, output_format: str,
                   columns: tuple[str, ...], fit_width: bool, max_width: int | None,
                   noindent: bool) -> None:
    """List recordsets in a zone.

    ZONE can be a zone ID or name.
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    zone_id = _resolve_zone_id(client, zone)

    params: dict = {}
    if record_type:
        params["type"] = record_type.upper()
    if record_name:
        params["name"] = record_name

    data = client.get(f"{_dns(client)}/v2/zones/{zone_id}/recordsets", params=params)

    def _format_records(r: dict) -> str:
        records = r.get("records", []) or []
        if not records:
            return "—"
        rtype = (r.get("type") or "").upper()
        # SOA records are a single whitespace-separated tuple — split on
        # whitespace and line-break for readability. NS/MX/TXT with multiple
        # values also render better one-per-line than comma-joined.
        if rtype == "SOA" and len(records) == 1:
            parts = records[0].split()
            return "\n".join(parts) if len(parts) > 1 else records[0]
        return "\n".join(records)

    print_list(
        data.get("recordsets", []),
        [
            ("ID", "id", {"style": "cyan", "overflow": "fold"}),
            ("Name", "name", {"style": "bold"}),
            ("Type", "type"),
            ("Records", _format_records),
            ("Status", lambda r: r.get("status", ""), {"style": "green"}),
            ("TTL", lambda r: str(r.get("ttl", "")) if r.get("ttl") is not None else "—", {"justify": "right"}),
        ],
        title="Recordsets",
        output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent,
        columns=columns,
        empty_msg="No recordsets found.",
    )


@recordset.command("show")
@click.argument("zone")
@click.argument("recordset_id")
@output_options
@click.pass_context
def recordset_show(ctx: click.Context, zone: str, recordset_id: str,
                   output_format: str, columns: tuple[str, ...], fit_width: bool,
                   max_width: int | None, noindent: bool) -> None:
    """Show recordset details.

    ZONE and RECORDSET can be IDs or names.
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    zone_id = _resolve_zone_id(client, zone)
    data = client.get(f"{_dns(client)}/v2/zones/{zone_id}/recordsets/{recordset_id}")

    fields = [
        (key, str(data.get(key, "") or ""))
        for key in [
            "id", "name", "type", "status", "ttl", "description",
            "records", "zone_id", "zone_name",
            "created_at", "updated_at", "version",
        ]
    ]

    print_detail(fields, output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent, columns=columns)


@recordset.command("create")
@click.argument("zone")
@click.argument("name")
@click.option("--type", "record_type", required=True, help="Record type (A, AAAA, CNAME, MX, TXT, …).")
@click.option("--record", "records", multiple=True, required=True,
              help="Record value (repeatable for multiple values).")
@click.option("--ttl", type=int, default=None, help="TTL in seconds.")
@click.option("--description", default=None, help="Recordset description.")
@click.pass_context
def recordset_create(ctx: click.Context, zone: str, name: str, record_type: str,
                     records: tuple[str, ...], ttl: int | None,
                     description: str | None) -> None:
    """Create a recordset in a zone.

    \b
    Examples:
      orca recordset create example.com. www.example.com. --type A --record 1.2.3.4
      orca recordset create example.com. example.com. --type MX --record "10 mail.example.com."
      orca recordset create example.com. example.com. --type A --record 1.2.3.4 --record 5.6.7.8
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    zone_id = _resolve_zone_id(client, zone)

    body: dict = {
        "name": name,
        "type": record_type.upper(),
        "records": list(records),
    }
    if ttl is not None:
        body["ttl"] = ttl
    if description:
        body["description"] = description

    data = client.post(f"{_dns(client)}/v2/zones/{zone_id}/recordsets", json=body)
    console.print(f"[green]Recordset '{data.get('name', name)}' ({record_type.upper()}) created "
                  f"(ID: {data.get('id', '?')}).[/green]")


@recordset.command("set")
@click.argument("zone")
@click.argument("recordset_id")
@click.option("--record", "records", multiple=True,
              help="Record value (repeatable — replaces all existing values).")
@click.option("--ttl", type=int, default=None, help="TTL in seconds.")
@click.option("--description", default=None, help="Recordset description.")
@click.pass_context
def recordset_set(ctx: click.Context, zone: str, recordset_id: str,
                  records: tuple[str, ...], ttl: int | None,
                  description: str | None) -> None:
    """Update a recordset in a zone.

    ZONE and RECORDSET can be IDs or names.  The ``--record`` option replaces
    all existing record values.
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    zone_id = _resolve_zone_id(client, zone)

    body: dict = {}
    if records:
        body["records"] = list(records)
    if ttl is not None:
        body["ttl"] = ttl
    if description is not None:
        body["description"] = description

    if not body:
        console.print("[yellow]Nothing to update — provide at least one option.[/yellow]")
        return

    client.put(f"{_dns(client)}/v2/zones/{zone_id}/recordsets/{recordset_id}", json=body)
    console.print(f"[green]Recordset {recordset_id} updated.[/green]")


@recordset.command("delete")
@click.argument("zone")
@click.argument("recordset_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def recordset_delete(ctx: click.Context, zone: str, recordset_id: str, yes: bool) -> None:
    """Delete a recordset.

    ZONE and RECORDSET can be IDs or names.
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    zone_id = _resolve_zone_id(client, zone)

    if not yes:
        click.confirm(f"Delete recordset {recordset_id}?", abort=True)

    client.delete(f"{_dns(client)}/v2/zones/{zone_id}/recordsets/{recordset_id}")
    console.print(f"[green]Recordset {recordset_id} deleted.[/green]")
