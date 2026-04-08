"""``shark network`` — manage networks, subnets, ports & routers (Neutron v2)."""

from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from shark_cli.core.context import SharkContext
from shark_cli.core.validators import validate_id

console = Console()


def _net_base(client) -> str:
    return f"{client.network_url}/v2.0"


# ══════════════════════════════════════════════════════════════════════════
#  Networks
# ══════════════════════════════════════════════════════════════════════════

@click.group()
@click.pass_context
def network(ctx: click.Context) -> None:
    """Manage networks, subnets, ports & routers."""
    pass


@network.command("list")
@click.pass_context
def network_list(ctx: click.Context) -> None:
    """List networks."""
    client = ctx.find_object(SharkContext).ensure_client()
    data = client.get(f"{_net_base(client)}/networks")
    networks = data.get("networks", [])
    if not networks:
        console.print("[yellow]No networks found.[/yellow]")
        return

    table = Table(title="Networks", show_lines=True)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="bold")
    table.add_column("Subnets")
    table.add_column("Status", style="green")
    table.add_column("External")
    table.add_column("Shared")

    for net in networks:
        subnets = ", ".join(net.get("subnets", [])) or "—"
        table.add_row(
            str(net.get("id", "")),
            net.get("name", ""),
            subnets,
            net.get("status", ""),
            str(net.get("router:external", "")),
            str(net.get("shared", "")),
        )
    console.print(table)


@network.command("show")
@click.argument("network_id", callback=validate_id)
@click.pass_context
def network_show(ctx: click.Context, network_id: str) -> None:
    """Show network details."""
    client = ctx.find_object(SharkContext).ensure_client()
    data = client.get(f"{_net_base(client)}/networks/{network_id}")
    net = data.get("network", data)

    table = Table(title=f"Network {net.get('name', network_id)}", show_lines=True)
    table.add_column("Property", style="bold cyan")
    table.add_column("Value")

    for key in ["id", "name", "status", "admin_state_up", "shared",
                "router:external", "mtu", "subnets", "availability_zones",
                "created_at", "updated_at"]:
        val = net.get(key, "")
        table.add_row(key, str(val) if val is not None else "")
    console.print(table)


@network.command("create")
@click.argument("name")
@click.option("--admin-state/--no-admin-state", default=True, show_default=True, help="Admin state up.")
@click.option("--shared", is_flag=True, help="Shared across projects.")
@click.pass_context
def network_create(ctx: click.Context, name: str, admin_state: bool, shared: bool) -> None:
    """Create a network."""
    client = ctx.find_object(SharkContext).ensure_client()
    body = {"name": name, "admin_state_up": admin_state, "shared": shared}
    data = client.post(f"{_net_base(client)}/networks", json={"network": body})
    net = data.get("network", data)
    console.print(f"[green]Network '{net.get('name')}' ({net.get('id')}) created.[/green]")


@network.command("update")
@click.argument("network_id", callback=validate_id)
@click.option("--name", default=None, help="New name.")
@click.option("--admin-state/--no-admin-state", default=None, help="Admin state.")
@click.pass_context
def network_update(ctx: click.Context, network_id: str, name: str | None, admin_state: bool | None) -> None:
    """Update a network."""
    body: dict = {}
    if name is not None:
        body["name"] = name
    if admin_state is not None:
        body["admin_state_up"] = admin_state
    if not body:
        console.print("[yellow]Nothing to update.[/yellow]")
        return
    client = ctx.find_object(SharkContext).ensure_client()
    client.put(f"{_net_base(client)}/networks/{network_id}", json={"network": body})
    console.print(f"[green]Network {network_id} updated.[/green]")


@network.command("delete")
@click.argument("network_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def network_delete(ctx: click.Context, network_id: str, yes: bool) -> None:
    """Delete a network."""
    if not yes:
        click.confirm(f"Delete network {network_id}?", abort=True)
    client = ctx.find_object(SharkContext).ensure_client()
    client.delete(f"{_net_base(client)}/networks/{network_id}")
    console.print(f"[green]Network {network_id} deleted.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  Subnets
# ══════════════════════════════════════════════════════════════════════════

@network.command("subnet-list")
@click.pass_context
def subnet_list(ctx: click.Context) -> None:
    """List subnets."""
    client = ctx.find_object(SharkContext).ensure_client()
    data = client.get(f"{_net_base(client)}/subnets")
    subnets = data.get("subnets", [])
    if not subnets:
        console.print("[yellow]No subnets found.[/yellow]")
        return

    table = Table(title="Subnets", show_lines=True)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="bold")
    table.add_column("CIDR")
    table.add_column("Gateway")
    table.add_column("Network ID")
    table.add_column("IP Ver.", justify="right")

    for s in subnets:
        table.add_row(
            s.get("id", ""),
            s.get("name", "") or "—",
            s.get("cidr", ""),
            s.get("gateway_ip", "") or "—",
            s.get("network_id", ""),
            str(s.get("ip_version", "")),
        )
    console.print(table)


@network.command("subnet-show")
@click.argument("subnet_id", callback=validate_id)
@click.pass_context
def subnet_show(ctx: click.Context, subnet_id: str) -> None:
    """Show subnet details."""
    client = ctx.find_object(SharkContext).ensure_client()
    data = client.get(f"{_net_base(client)}/subnets/{subnet_id}")
    sub = data.get("subnet", data)

    table = Table(title=f"Subnet {sub.get('name') or subnet_id}", show_lines=True)
    table.add_column("Property", style="bold cyan")
    table.add_column("Value")

    for key in ["id", "name", "cidr", "ip_version", "gateway_ip", "enable_dhcp",
                "dns_nameservers", "allocation_pools", "network_id", "created_at"]:
        table.add_row(key, str(sub.get(key, "")))
    console.print(table)


@network.command("subnet-create")
@click.argument("name")
@click.option("--network-id", required=True, help="Parent network ID.")
@click.option("--cidr", required=True, help="CIDR (e.g. 10.0.0.0/24).")
@click.option("--ip-version", type=click.Choice(["4", "6"]), default="4", show_default=True)
@click.option("--gateway", default=None, help="Gateway IP. Auto if omitted.")
@click.option("--dhcp/--no-dhcp", default=True, show_default=True, help="Enable DHCP.")
@click.option("--dns", multiple=True, help="DNS nameserver (repeatable).")
@click.pass_context
def subnet_create(ctx: click.Context, name: str, network_id: str, cidr: str,
                  ip_version: str, gateway: str | None, dhcp: bool, dns: tuple) -> None:
    """Create a subnet."""
    client = ctx.find_object(SharkContext).ensure_client()
    body: dict = {
        "name": name,
        "network_id": network_id,
        "cidr": cidr,
        "ip_version": int(ip_version),
        "enable_dhcp": dhcp,
    }
    if gateway:
        body["gateway_ip"] = gateway
    if dns:
        body["dns_nameservers"] = list(dns)

    data = client.post(f"{_net_base(client)}/subnets", json={"subnet": body})
    sub = data.get("subnet", data)
    console.print(f"[green]Subnet '{sub.get('name')}' ({sub.get('id')}) created — {cidr}.[/green]")


@network.command("subnet-delete")
@click.argument("subnet_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def subnet_delete(ctx: click.Context, subnet_id: str, yes: bool) -> None:
    """Delete a subnet."""
    if not yes:
        click.confirm(f"Delete subnet {subnet_id}?", abort=True)
    client = ctx.find_object(SharkContext).ensure_client()
    client.delete(f"{_net_base(client)}/subnets/{subnet_id}")
    console.print(f"[green]Subnet {subnet_id} deleted.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  Ports
# ══════════════════════════════════════════════════════════════════════════

@network.command("port-list")
@click.option("--network-id", default=None, help="Filter by network ID.")
@click.pass_context
def port_list(ctx: click.Context, network_id: str | None) -> None:
    """List ports."""
    client = ctx.find_object(SharkContext).ensure_client()
    params = {}
    if network_id:
        params["network_id"] = network_id
    data = client.get(f"{_net_base(client)}/ports", params=params)
    ports = data.get("ports", [])
    if not ports:
        console.print("[yellow]No ports found.[/yellow]")
        return

    table = Table(title="Ports", show_lines=True)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="bold")
    table.add_column("MAC")
    table.add_column("Fixed IPs")
    table.add_column("Status", style="green")
    table.add_column("Device Owner")

    for p in ports:
        fixed = ", ".join(f"{ip.get('ip_address', '')}" for ip in p.get("fixed_ips", [])) or "—"
        table.add_row(
            p.get("id", ""),
            p.get("name", "") or "—",
            p.get("mac_address", ""),
            fixed,
            p.get("status", ""),
            p.get("device_owner", "") or "—",
        )
    console.print(table)


@network.command("port-show")
@click.argument("port_id", callback=validate_id)
@click.pass_context
def port_show(ctx: click.Context, port_id: str) -> None:
    """Show port details."""
    client = ctx.find_object(SharkContext).ensure_client()
    data = client.get(f"{_net_base(client)}/ports/{port_id}")
    port = data.get("port", data)

    table = Table(title=f"Port {port.get('name') or port_id}", show_lines=True)
    table.add_column("Property", style="bold cyan")
    table.add_column("Value")

    for key in ["id", "name", "mac_address", "fixed_ips", "status",
                "admin_state_up", "network_id", "device_id", "device_owner",
                "security_groups", "created_at"]:
        table.add_row(key, str(port.get(key, "")))
    console.print(table)


@network.command("port-create")
@click.option("--network-id", required=True, help="Network ID.")
@click.option("--name", default=None, help="Port name.")
@click.option("--fixed-ip", default=None, help="Fixed IP address.")
@click.pass_context
def port_create(ctx: click.Context, network_id: str, name: str | None, fixed_ip: str | None) -> None:
    """Create a port."""
    client = ctx.find_object(SharkContext).ensure_client()
    body: dict = {"network_id": network_id}
    if name:
        body["name"] = name
    if fixed_ip:
        body["fixed_ips"] = [{"ip_address": fixed_ip}]

    data = client.post(f"{_net_base(client)}/ports", json={"port": body})
    port = data.get("port", data)
    ips = ", ".join(ip.get("ip_address", "") for ip in port.get("fixed_ips", []))
    console.print(f"[green]Port {port.get('id')} created — {ips}.[/green]")


@network.command("port-update")
@click.argument("port_id", callback=validate_id)
@click.option("--name", default=None, help="New name.")
@click.option("--admin-state/--no-admin-state", default=None, help="Admin state.")
@click.pass_context
def port_update(ctx: click.Context, port_id: str, name: str | None, admin_state: bool | None) -> None:
    """Update a port."""
    body: dict = {}
    if name is not None:
        body["name"] = name
    if admin_state is not None:
        body["admin_state_up"] = admin_state
    if not body:
        console.print("[yellow]Nothing to update.[/yellow]")
        return
    client = ctx.find_object(SharkContext).ensure_client()
    client.put(f"{_net_base(client)}/ports/{port_id}", json={"port": body})
    console.print(f"[green]Port {port_id} updated.[/green]")


@network.command("port-delete")
@click.argument("port_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def port_delete(ctx: click.Context, port_id: str, yes: bool) -> None:
    """Delete a port."""
    if not yes:
        click.confirm(f"Delete port {port_id}?", abort=True)
    client = ctx.find_object(SharkContext).ensure_client()
    client.delete(f"{_net_base(client)}/ports/{port_id}")
    console.print(f"[green]Port {port_id} deleted.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  Routers
# ══════════════════════════════════════════════════════════════════════════

@network.command("router-list")
@click.pass_context
def router_list(ctx: click.Context) -> None:
    """List routers."""
    client = ctx.find_object(SharkContext).ensure_client()
    data = client.get(f"{_net_base(client)}/routers")
    routers = data.get("routers", [])
    if not routers:
        console.print("[yellow]No routers found.[/yellow]")
        return

    table = Table(title="Routers", show_lines=True)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="bold")
    table.add_column("Status", style="green")
    table.add_column("External GW")
    table.add_column("Admin Up")

    for r in routers:
        gw = r.get("external_gateway_info") or {}
        gw_net = gw.get("network_id", "—") if gw else "—"
        table.add_row(
            r.get("id", ""),
            r.get("name", "") or "—",
            r.get("status", ""),
            gw_net,
            str(r.get("admin_state_up", "")),
        )
    console.print(table)


@network.command("router-show")
@click.argument("router_id", callback=validate_id)
@click.pass_context
def router_show(ctx: click.Context, router_id: str) -> None:
    """Show router details."""
    client = ctx.find_object(SharkContext).ensure_client()
    data = client.get(f"{_net_base(client)}/routers/{router_id}")
    r = data.get("router", data)

    table = Table(title=f"Router {r.get('name') or router_id}", show_lines=True)
    table.add_column("Property", style="bold cyan")
    table.add_column("Value")

    for key in ["id", "name", "status", "admin_state_up",
                "external_gateway_info", "routes", "created_at"]:
        table.add_row(key, str(r.get(key, "")))
    console.print(table)


@network.command("router-create")
@click.argument("name")
@click.option("--external-network", default=None, help="External network ID for gateway.")
@click.pass_context
def router_create(ctx: click.Context, name: str, external_network: str | None) -> None:
    """Create a router."""
    client = ctx.find_object(SharkContext).ensure_client()
    body: dict = {"name": name, "admin_state_up": True}
    if external_network:
        body["external_gateway_info"] = {"network_id": external_network}

    data = client.post(f"{_net_base(client)}/routers", json={"router": body})
    r = data.get("router", data)
    console.print(f"[green]Router '{r.get('name')}' ({r.get('id')}) created.[/green]")


@network.command("router-update")
@click.argument("router_id", callback=validate_id)
@click.option("--name", default=None, help="New name.")
@click.option("--external-network", default=None, help="New external gateway network ID.")
@click.pass_context
def router_update(ctx: click.Context, router_id: str, name: str | None, external_network: str | None) -> None:
    """Update a router."""
    body: dict = {}
    if name is not None:
        body["name"] = name
    if external_network is not None:
        body["external_gateway_info"] = {"network_id": external_network}
    if not body:
        console.print("[yellow]Nothing to update.[/yellow]")
        return
    client = ctx.find_object(SharkContext).ensure_client()
    client.put(f"{_net_base(client)}/routers/{router_id}", json={"router": body})
    console.print(f"[green]Router {router_id} updated.[/green]")


@network.command("router-delete")
@click.argument("router_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def router_delete(ctx: click.Context, router_id: str, yes: bool) -> None:
    """Delete a router."""
    if not yes:
        click.confirm(f"Delete router {router_id}?", abort=True)
    client = ctx.find_object(SharkContext).ensure_client()
    client.delete(f"{_net_base(client)}/routers/{router_id}")
    console.print(f"[green]Router {router_id} deleted.[/green]")


@network.command("router-add-interface")
@click.argument("router_id", callback=validate_id)
@click.option("--subnet-id", required=True, help="Subnet to attach.")
@click.pass_context
def router_add_interface(ctx: click.Context, router_id: str, subnet_id: str) -> None:
    """Add a subnet interface to a router."""
    client = ctx.find_object(SharkContext).ensure_client()
    url = f"{_net_base(client)}/routers/{router_id}/add_router_interface"
    data = client.put(url, json={"subnet_id": subnet_id})
    console.print(f"[green]Subnet {subnet_id} added to router {router_id}.[/green]")


@network.command("router-remove-interface")
@click.argument("router_id", callback=validate_id)
@click.option("--subnet-id", required=True, help="Subnet to detach.")
@click.pass_context
def router_remove_interface(ctx: click.Context, router_id: str, subnet_id: str) -> None:
    """Remove a subnet interface from a router."""
    client = ctx.find_object(SharkContext).ensure_client()
    url = f"{_net_base(client)}/routers/{router_id}/remove_router_interface"
    data = client.put(url, json={"subnet_id": subnet_id})
    console.print(f"[green]Subnet {subnet_id} removed from router {router_id}.[/green]")
