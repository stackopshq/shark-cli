"""``orca ip`` — IP address lookup utilities."""

from __future__ import annotations

import click

from orca_cli.core.context import OrcaContext
from orca_cli.core.output import console


@click.group("ip")
@click.pass_context
def ip_cmd(ctx: click.Context) -> None:
    """IP address utilities."""
    pass


@ip_cmd.command("whois")
@click.argument("address")
@click.pass_context
def ip_whois(ctx: click.Context, address: str) -> None:
    """Find which resource owns a given IP address.

    Searches across floating IPs, ports, subnets, routers, servers
    and load-balancers to resolve who is using the address.

    \b
    Examples:
      orca ip whois 10.0.0.15
      orca ip whois 203.0.113.42
    """
    from rich.table import Table

    client = ctx.find_object(OrcaContext).ensure_client()
    results: list[tuple[str, str, str, str]] = []  # (type, id, name, detail)

    with console.status(f"[bold cyan]Looking up {address}…[/bold cyan]"):
        # ── Floating IPs ─────────────────────────────────────────────
        fips = client.get(f"{client.network_url}/v2.0/floatingips").get("floatingips", [])
        for f in fips:
            if f.get("floating_ip_address") == address:
                port_id = f.get("port_id", "") or "—"
                results.append(("floating-ip", f["id"], f["floating_ip_address"],
                                f"port: {port_id}, status: {f.get('status', '')}"))
            if f.get("fixed_ip_address") == address:
                results.append(("floating-ip (fixed side)", f["id"], f["floating_ip_address"],
                                f"fixed: {address}, port: {f.get('port_id', '')}"))

        # ── Ports ────────────────────────────────────────────────────
        ports = client.get(f"{client.network_url}/v2.0/ports").get("ports", [])
        for p in ports:
            for ip in p.get("fixed_ips", []):
                if ip.get("ip_address") == address:
                    owner = p.get("device_owner", "") or "unbound"
                    dev_id = p.get("device_id", "") or "—"
                    mac = p.get("mac_address", "")
                    results.append(("port", p["id"], f"{owner}",
                                    f"device: {dev_id}, mac: {mac}, net: {p.get('network_id', '')}"))

        # ── Servers ──────────────────────────────────────────────────
        servers = client.get(f"{client.compute_url}/servers/detail", params={"limit": 1000}).get("servers", [])
        for srv in servers:
            for net_name, addrs in srv.get("addresses", {}).items():
                for a in addrs:
                    if a.get("addr") == address:
                        ip_type = a.get("OS-EXT-IPS:type", "fixed")
                        results.append(("server", srv["id"], srv.get("name", ""),
                                        f"{net_name}, {ip_type}, status: {srv.get('status', '')}"))

        # ── Routers (gateway IPs) ────────────────────────────────────
        routers = client.get(f"{client.network_url}/v2.0/routers").get("routers", [])
        for r in routers:
            gw = r.get("external_gateway_info", {})
            if gw:
                for eip in gw.get("external_fixed_ips", []):
                    if eip.get("ip_address") == address:
                        results.append(("router (gateway)", r["id"], r.get("name", ""),
                                        f"external gateway on subnet {eip.get('subnet_id', '')}"))

        # ── Subnets (gateway) ────────────────────────────────────────
        subnets = client.get(f"{client.network_url}/v2.0/subnets").get("subnets", [])
        for s in subnets:
            if s.get("gateway_ip") == address:
                results.append(("subnet (gateway)", s["id"], s.get("name", ""),
                                f"CIDR: {s.get('cidr', '')}, net: {s.get('network_id', '')}"))

        # Check if the address falls within any allocation pool
        for s in subnets:
            for pool in s.get("allocation_pools", []):
                # Simple check — not full IP math but works for most cases
                if _ip_in_range(address, pool.get("start", ""), pool.get("end", "")):
                    results.append(("subnet (pool)", s["id"], s.get("name", ""),
                                    f"CIDR: {s.get('cidr', '')}, pool: {pool['start']}-{pool['end']}"))

        # ── Load Balancers ───────────────────────────────────────────
        try:
            lbs = client.get(f"{client.load_balancer_url}/v2/lbaas/loadbalancers").get("loadbalancers", [])
            for lb in lbs:
                if lb.get("vip_address") == address:
                    results.append(("load-balancer", lb["id"], lb.get("name", ""),
                                    f"VIP, status: {lb.get('provisioning_status', '')}"))
        except Exception:
            pass

    # ── Display ───────────────────────────────────────────────────────
    if not results:
        console.print(f"[yellow]No resource found for {address}.[/yellow]")
        return

    console.print(f"\n[bold]Results for {address}:[/bold]\n")

    table = Table(show_lines=False)
    table.add_column("Type", style="bold")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name")
    table.add_column("Details", style="dim")

    for rtype, rid, rname, detail in results:
        table.add_row(rtype, rid, rname, detail)

    console.print(table)
    console.print()


def _ip_in_range(ip: str, start: str, end: str) -> bool:
    """Check if an IPv4 address falls within a range (simple numeric comparison)."""
    try:
        ip_parts = tuple(int(x) for x in ip.split("."))
        start_parts = tuple(int(x) for x in start.split("."))
        end_parts = tuple(int(x) for x in end.split("."))
        return start_parts <= ip_parts <= end_parts
    except (ValueError, AttributeError):
        return False
