"""``orca floating-ip`` — manage floating IPs (Neutron)."""

from __future__ import annotations

import click

from orca_cli.core.context import OrcaContext
from orca_cli.core.output import output_options, print_list, print_detail, console
from orca_cli.core.validators import validate_id


@click.group("floating-ip")
@click.pass_context
def floating_ip(ctx: click.Context) -> None:
    """Manage floating IPs."""
    pass


@floating_ip.command("list")
@output_options
@click.pass_context
def fip_list(ctx: click.Context, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List floating IPs."""
    client = ctx.find_object(OrcaContext).ensure_client()
    url = f"{client.network_url}/v2.0/floatingips"
    data = client.get(url)

    print_list(
        data.get("floatingips", []),
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Floating IP", "floating_ip_address", {"style": "bold"}),
            ("Fixed IP", lambda f: f.get("fixed_ip_address", "") or "—"),
            ("Port ID", lambda f: f.get("port_id", "") or "—"),
            ("Status", "status", {"style": "green"}),
        ],
        title="Floating IPs",
        output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent,
        columns=columns,
        empty_msg="No floating IPs found.",
    )


@floating_ip.command("create")
@click.option("--network", "network_id", required=True, help="External network ID.")
@click.pass_context
def fip_create(ctx: click.Context, network_id: str) -> None:
    """Allocate a floating IP from an external network."""
    client = ctx.find_object(OrcaContext).ensure_client()
    url = f"{client.network_url}/v2.0/floatingips"
    data = client.post(url, json={"floatingip": {"floating_network_id": network_id}})

    fip = data.get("floatingip", data)
    console.print(f"[green]Floating IP {fip.get('floating_ip_address')} allocated ({fip.get('id')}).[/green]")


@floating_ip.command("delete")
@click.argument("floating_ip_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def fip_delete(ctx: click.Context, floating_ip_id: str, yes: bool) -> None:
    """Release a floating IP."""
    if not yes:
        click.confirm(f"Release floating IP {floating_ip_id}?", abort=True)

    client = ctx.find_object(OrcaContext).ensure_client()
    url = f"{client.network_url}/v2.0/floatingips/{floating_ip_id}"
    client.delete(url)
    console.print(f"[green]Floating IP {floating_ip_id} released.[/green]")


@floating_ip.command("show")
@click.argument("floating_ip_id", callback=validate_id)
@output_options
@click.pass_context
def fip_show(ctx: click.Context, floating_ip_id: str, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show floating IP details."""
    client = ctx.find_object(OrcaContext).ensure_client()
    url = f"{client.network_url}/v2.0/floatingips/{floating_ip_id}"
    data = client.get(url)
    fip = data.get("floatingip", data)

    fields = [(key, str(fip.get(key, "") or "")) for key in
              ["id", "floating_ip_address", "fixed_ip_address", "floating_network_id",
               "port_id", "router_id", "status", "created_at"]]

    print_detail(fields, output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent, columns=columns)


@floating_ip.command("associate")
@click.argument("floating_ip_id", callback=validate_id)
@click.option("--port-id", required=True, help="Port ID to associate with.")
@click.option("--fixed-ip", default=None, help="Fixed IP on the port (if multiple).")
@click.pass_context
def fip_associate(ctx: click.Context, floating_ip_id: str, port_id: str, fixed_ip: str | None) -> None:
    """Associate a floating IP with a port.

    \b
    Examples:
      orca floating-ip associate <fip-id> --port-id <port-id>
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {"port_id": port_id}
    if fixed_ip:
        body["fixed_ip_address"] = fixed_ip

    url = f"{client.network_url}/v2.0/floatingips/{floating_ip_id}"
    client.put(url, json={"floatingip": body})
    console.print(f"[green]Floating IP {floating_ip_id} associated with port {port_id}.[/green]")


@floating_ip.command("disassociate")
@click.argument("floating_ip_id", callback=validate_id)
@click.pass_context
def fip_disassociate(ctx: click.Context, floating_ip_id: str) -> None:
    """Disassociate a floating IP from its port."""
    client = ctx.find_object(OrcaContext).ensure_client()
    url = f"{client.network_url}/v2.0/floatingips/{floating_ip_id}"
    client.put(url, json={"floatingip": {"port_id": None}})
    console.print(f"[green]Floating IP {floating_ip_id} disassociated.[/green]")


# ── set ──────────────────────────────────────────────────────────────────

@floating_ip.command("set")
@click.argument("floating_ip_id", callback=validate_id)
@click.option("--port", "port_id", default=None, help="Associate with port ID.")
@click.option("--fixed-ip-address", default=None, help="Fixed IP on the port (if multiple).")
@click.option("--description", default=None, help="Set description.")
@click.option("--qos-policy", "qos_policy_id", default=None, help="Attach QoS policy ID.")
@click.option("--no-qos-policy", is_flag=True, default=False, help="Remove attached QoS policy.")
@click.pass_context
def fip_set(ctx: click.Context, floating_ip_id: str, port_id: str | None,
            fixed_ip_address: str | None, description: str | None,
            qos_policy_id: str | None, no_qos_policy: bool) -> None:
    """Set floating IP properties.

    \b
    Examples:
      orca floating-ip set <id> --port <port-id>
      orca floating-ip set <id> --description "my FIP"
      orca floating-ip set <id> --qos-policy <qos-id>
      orca floating-ip set <id> --no-qos-policy
    """
    if qos_policy_id and no_qos_policy:
        raise click.UsageError("--qos-policy and --no-qos-policy are mutually exclusive.")

    body: dict = {}
    if port_id is not None:
        body["port_id"] = port_id
    if fixed_ip_address is not None:
        body["fixed_ip_address"] = fixed_ip_address
    if description is not None:
        body["description"] = description
    if qos_policy_id is not None:
        body["qos_policy_id"] = qos_policy_id
    if no_qos_policy:
        body["qos_policy_id"] = None

    if not body:
        console.print("[yellow]Nothing to update.[/yellow]")
        return

    client = ctx.find_object(OrcaContext).ensure_client()
    client.put(f"{client.network_url}/v2.0/floatingips/{floating_ip_id}",
               json={"floatingip": body})
    console.print(f"[green]Floating IP {floating_ip_id} updated.[/green]")


# ── unset ─────────────────────────────────────────────────────────────────

@floating_ip.command("unset")
@click.argument("floating_ip_id", callback=validate_id)
@click.option("--port", is_flag=True, default=False, help="Disassociate port.")
@click.option("--qos-policy", is_flag=True, default=False, help="Remove QoS policy.")
@click.pass_context
def fip_unset(ctx: click.Context, floating_ip_id: str, port: bool, qos_policy: bool) -> None:
    """Unset floating IP properties.

    \b
    Examples:
      orca floating-ip unset <id> --port
      orca floating-ip unset <id> --qos-policy
    """
    body: dict = {}
    if port:
        body["port_id"] = None
    if qos_policy:
        body["qos_policy_id"] = None

    if not body:
        console.print("[yellow]Nothing to unset.[/yellow]")
        return

    client = ctx.find_object(OrcaContext).ensure_client()
    client.put(f"{client.network_url}/v2.0/floatingips/{floating_ip_id}",
               json={"floatingip": body})
    console.print(f"[green]Floating IP {floating_ip_id} updated.[/green]")


# ── bulk-release ─────────────────────────────────────────────────────────

@floating_ip.command("bulk-release")
@click.option("--status", "-s", "target_status", default="DOWN",
              show_default=True,
              help="Release floating IPs with this status (DOWN, ERROR, etc.).")
@click.option("--unassociated", "-u", is_flag=True, default=False,
              help="Release all unassociated floating IPs (no port_id), regardless of status.")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def fip_bulk_release(ctx: click.Context, target_status: str, unassociated: bool, yes: bool) -> None:
    """Bulk-release floating IPs to free up unused addresses.

    By default releases all IPs with status DOWN. Use --unassociated to
    release all IPs not attached to any port. Combine both for maximum
    cleanup.

    \b
    Examples:
      orca floating-ip bulk-release                 # release all DOWN
      orca floating-ip bulk-release --status ERROR  # release all ERROR
      orca floating-ip bulk-release -u              # release all unassociated
      orca floating-ip bulk-release -u -y           # auto-confirm
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    url = f"{client.network_url}/v2.0/floatingips"

    with console.status("[bold]Fetching floating IPs..."):
        fips = client.get(url).get("floatingips", [])

    # Filter targets
    targets = []
    for fip in fips:
        if unassociated and not fip.get("port_id"):
            targets.append(fip)
        elif not unassociated and fip.get("status", "").upper() == target_status.upper():
            targets.append(fip)

    if not targets:
        label = "unassociated" if unassociated else f"status={target_status}"
        console.print(f"[green]No floating IPs matching {label}.[/green]")
        return

    from rich.table import Table

    table = Table(title=f"Floating IPs to release ({len(targets)})", show_lines=False)
    table.add_column("Floating IP", style="bold")
    table.add_column("Status")
    table.add_column("Fixed IP")
    table.add_column("Port ID")
    table.add_column("ID", style="dim")

    for fip in targets:
        status = fip.get("status", "?")
        s_color = "green" if status == "ACTIVE" else "red" if status == "ERROR" else "yellow"
        table.add_row(
            fip.get("floating_ip_address", "?"),
            f"[{s_color}]{status}[/{s_color}]",
            fip.get("fixed_ip_address") or "—",
            (fip.get("port_id") or "—")[:12],
            fip.get("id", "?"),
        )

    console.print()
    console.print(table)

    if not yes:
        click.confirm(f"\nRelease {len(targets)} floating IP(s)?", abort=True)

    released = 0
    errors = 0
    for fip in targets:
        fip_id = fip.get("id", "?")
        fip_addr = fip.get("floating_ip_address", "?")
        try:
            client.delete(f"{url}/{fip_id}")
            console.print(f"  [green]Released[/green] {fip_addr} ({fip_id})")
            released += 1
        except Exception as exc:
            console.print(f"  [red]Failed[/red] {fip_addr}: {exc}")
            errors += 1

    console.print(f"\n[green]{released} released[/green]", end="")
    if errors:
        console.print(f", [red]{errors} failed[/red]")
    else:
        console.print()
    console.print()
