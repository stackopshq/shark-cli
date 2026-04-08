"""``shark loadbalancer`` — manage load balancers (Octavia)."""

from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from shark_cli.core.context import SharkContext
from shark_cli.core.validators import validate_id

console = Console()


def _octavia(client) -> str:
    return client.load_balancer_url


# ══════════════════════════════════════════════════════════════════════════
#  Top-level group
# ══════════════════════════════════════════════════════════════════════════

@click.group("loadbalancer")
@click.pass_context
def loadbalancer(ctx: click.Context) -> None:
    """Manage load balancers, listeners, pools & members (Octavia)."""
    pass


# ══════════════════════════════════════════════════════════════════════════
#  Load Balancers
# ══════════════════════════════════════════════════════════════════════════

@loadbalancer.command("list")
@click.pass_context
def lb_list(ctx: click.Context) -> None:
    """List load balancers."""
    client = ctx.find_object(SharkContext).ensure_client()
    data = client.get(f"{_octavia(client)}/v2/lbaas/loadbalancers")
    lbs = data.get("loadbalancers", [])
    if not lbs:
        console.print("[yellow]No load balancers found.[/yellow]")
        return

    table = Table(title="Load Balancers", show_lines=True)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="bold")
    table.add_column("VIP Address")
    table.add_column("Prov. Status", style="green")
    table.add_column("Oper. Status")
    table.add_column("Provider")

    for lb in lbs:
        table.add_row(
            lb.get("id", ""),
            lb.get("name", "") or "—",
            lb.get("vip_address", ""),
            lb.get("provisioning_status", ""),
            lb.get("operating_status", ""),
            lb.get("provider", ""),
        )
    console.print(table)


@loadbalancer.command("show")
@click.argument("lb_id", callback=validate_id)
@click.pass_context
def lb_show(ctx: click.Context, lb_id: str) -> None:
    """Show load balancer details."""
    client = ctx.find_object(SharkContext).ensure_client()
    data = client.get(f"{_octavia(client)}/v2/lbaas/loadbalancers/{lb_id}")
    lb = data.get("loadbalancer", data)

    table = Table(title=f"LB {lb.get('name') or lb_id}", show_lines=True)
    table.add_column("Property", style="bold cyan")
    table.add_column("Value")

    for key in ["id", "name", "description", "vip_address", "vip_subnet_id",
                "vip_network_id", "vip_port_id", "provider",
                "provisioning_status", "operating_status",
                "admin_state_up", "listeners", "pools",
                "created_at", "updated_at"]:
        table.add_row(key, str(lb.get(key, "")))
    console.print(table)


@loadbalancer.command("create")
@click.argument("name")
@click.option("--subnet-id", "vip_subnet_id", required=True, help="VIP subnet ID.")
@click.option("--description", default="", help="Description.")
@click.option("--provider", default=None, help="Provider (e.g. amphora, ovn).")
@click.pass_context
def lb_create(ctx: click.Context, name: str, vip_subnet_id: str,
              description: str, provider: str | None) -> None:
    """Create a load balancer.

    \b
    Examples:
      shark loadbalancer create my-lb --subnet-id <subnet-id>
    """
    client = ctx.find_object(SharkContext).ensure_client()
    body: dict = {"name": name, "vip_subnet_id": vip_subnet_id, "description": description}
    if provider:
        body["provider"] = provider
    data = client.post(f"{_octavia(client)}/v2/lbaas/loadbalancers", json={"loadbalancer": body})
    lb = data.get("loadbalancer", data)
    console.print(f"[green]Load balancer '{lb.get('name')}' ({lb.get('id')}) created — VIP {lb.get('vip_address', 'pending')}.[/green]")


@loadbalancer.command("delete")
@click.argument("lb_id", callback=validate_id)
@click.option("--cascade", is_flag=True, help="Delete LB and all child resources.")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def lb_delete(ctx: click.Context, lb_id: str, cascade: bool, yes: bool) -> None:
    """Delete a load balancer."""
    if not yes:
        click.confirm(f"Delete load balancer {lb_id}?", abort=True)
    client = ctx.find_object(SharkContext).ensure_client()
    params = {"cascade": "true"} if cascade else {}
    client.delete(f"{_octavia(client)}/v2/lbaas/loadbalancers/{lb_id}", params=params)
    console.print(f"[green]Load balancer {lb_id} deletion started.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  Listeners
# ══════════════════════════════════════════════════════════════════════════

@loadbalancer.command("listener-list")
@click.pass_context
def listener_list(ctx: click.Context) -> None:
    """List listeners."""
    client = ctx.find_object(SharkContext).ensure_client()
    data = client.get(f"{_octavia(client)}/v2/lbaas/listeners")
    listeners = data.get("listeners", [])
    if not listeners:
        console.print("[yellow]No listeners found.[/yellow]")
        return

    table = Table(title="Listeners", show_lines=True)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="bold")
    table.add_column("Protocol")
    table.add_column("Port", justify="right")
    table.add_column("LB ID")
    table.add_column("Status", style="green")

    for l in listeners:
        lbs = l.get("loadbalancers", [])
        lb_id = lbs[0].get("id", "") if lbs else ""
        table.add_row(
            l.get("id", ""),
            l.get("name", "") or "—",
            l.get("protocol", ""),
            str(l.get("protocol_port", "")),
            lb_id,
            l.get("provisioning_status", ""),
        )
    console.print(table)


@loadbalancer.command("listener-create")
@click.argument("name")
@click.option("--lb-id", "loadbalancer_id", required=True, help="Load balancer ID.")
@click.option("--protocol", required=True, type=click.Choice(["HTTP", "HTTPS", "TCP", "UDP", "TERMINATED_HTTPS"]))
@click.option("--port", "protocol_port", required=True, type=int, help="Listen port.")
@click.option("--default-pool-id", default=None, help="Default pool ID.")
@click.pass_context
def listener_create(ctx: click.Context, name: str, loadbalancer_id: str,
                    protocol: str, protocol_port: int, default_pool_id: str | None) -> None:
    """Create a listener."""
    client = ctx.find_object(SharkContext).ensure_client()
    body: dict = {
        "name": name,
        "loadbalancer_id": loadbalancer_id,
        "protocol": protocol,
        "protocol_port": protocol_port,
    }
    if default_pool_id:
        body["default_pool_id"] = default_pool_id
    data = client.post(f"{_octavia(client)}/v2/lbaas/listeners", json={"listener": body})
    l = data.get("listener", data)
    console.print(f"[green]Listener '{l.get('name')}' ({l.get('id')}) created on port {protocol_port}.[/green]")


@loadbalancer.command("listener-show")
@click.argument("listener_id", callback=validate_id)
@click.pass_context
def listener_show(ctx: click.Context, listener_id: str) -> None:
    """Show listener details."""
    client = ctx.find_object(SharkContext).ensure_client()
    data = client.get(f"{_octavia(client)}/v2/lbaas/listeners/{listener_id}")
    l = data.get("listener", data)

    table = Table(title=f"Listener {l.get('name') or listener_id}", show_lines=True)
    table.add_column("Property", style="bold cyan")
    table.add_column("Value")
    for key in ["id", "name", "protocol", "protocol_port", "default_pool_id",
                "connection_limit", "provisioning_status", "operating_status",
                "admin_state_up", "created_at", "updated_at"]:
        table.add_row(key, str(l.get(key, "")))
    console.print(table)


@loadbalancer.command("listener-delete")
@click.argument("listener_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def listener_delete(ctx: click.Context, listener_id: str, yes: bool) -> None:
    """Delete a listener."""
    if not yes:
        click.confirm(f"Delete listener {listener_id}?", abort=True)
    client = ctx.find_object(SharkContext).ensure_client()
    client.delete(f"{_octavia(client)}/v2/lbaas/listeners/{listener_id}")
    console.print(f"[green]Listener {listener_id} deleted.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  Pools
# ══════════════════════════════════════════════════════════════════════════

@loadbalancer.command("pool-list")
@click.pass_context
def pool_list(ctx: click.Context) -> None:
    """List pools."""
    client = ctx.find_object(SharkContext).ensure_client()
    data = client.get(f"{_octavia(client)}/v2/lbaas/pools")
    pools = data.get("pools", [])
    if not pools:
        console.print("[yellow]No pools found.[/yellow]")
        return

    table = Table(title="Pools", show_lines=True)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="bold")
    table.add_column("Protocol")
    table.add_column("LB Algorithm")
    table.add_column("Members", justify="right")
    table.add_column("Status", style="green")

    for p in pools:
        table.add_row(
            p.get("id", ""),
            p.get("name", "") or "—",
            p.get("protocol", ""),
            p.get("lb_algorithm", ""),
            str(len(p.get("members", []))),
            p.get("provisioning_status", ""),
        )
    console.print(table)


@loadbalancer.command("pool-create")
@click.argument("name")
@click.option("--listener-id", default=None, help="Listener ID to attach to.")
@click.option("--lb-id", "loadbalancer_id", default=None, help="Load balancer ID (if no listener).")
@click.option("--protocol", required=True, type=click.Choice(["HTTP", "HTTPS", "PROXY", "TCP", "UDP"]))
@click.option("--algorithm", "lb_algorithm", required=True,
              type=click.Choice(["ROUND_ROBIN", "LEAST_CONNECTIONS", "SOURCE_IP"]),
              help="Load balancing algorithm.")
@click.pass_context
def pool_create(ctx: click.Context, name: str, listener_id: str | None,
                loadbalancer_id: str | None, protocol: str, lb_algorithm: str) -> None:
    """Create a pool."""
    client = ctx.find_object(SharkContext).ensure_client()
    body: dict = {"name": name, "protocol": protocol, "lb_algorithm": lb_algorithm}
    if listener_id:
        body["listener_id"] = listener_id
    elif loadbalancer_id:
        body["loadbalancer_id"] = loadbalancer_id
    data = client.post(f"{_octavia(client)}/v2/lbaas/pools", json={"pool": body})
    p = data.get("pool", data)
    console.print(f"[green]Pool '{p.get('name')}' ({p.get('id')}) created.[/green]")


@loadbalancer.command("pool-show")
@click.argument("pool_id", callback=validate_id)
@click.pass_context
def pool_show(ctx: click.Context, pool_id: str) -> None:
    """Show pool details."""
    client = ctx.find_object(SharkContext).ensure_client()
    data = client.get(f"{_octavia(client)}/v2/lbaas/pools/{pool_id}")
    p = data.get("pool", data)

    table = Table(title=f"Pool {p.get('name') or pool_id}", show_lines=True)
    table.add_column("Property", style="bold cyan")
    table.add_column("Value")
    for key in ["id", "name", "protocol", "lb_algorithm", "session_persistence",
                "healthmonitor_id", "provisioning_status", "operating_status",
                "admin_state_up", "created_at", "updated_at"]:
        table.add_row(key, str(p.get(key, "")))
    console.print(table)


@loadbalancer.command("pool-delete")
@click.argument("pool_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def pool_delete(ctx: click.Context, pool_id: str, yes: bool) -> None:
    """Delete a pool."""
    if not yes:
        click.confirm(f"Delete pool {pool_id}?", abort=True)
    client = ctx.find_object(SharkContext).ensure_client()
    client.delete(f"{_octavia(client)}/v2/lbaas/pools/{pool_id}")
    console.print(f"[green]Pool {pool_id} deleted.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  Members
# ══════════════════════════════════════════════════════════════════════════

@loadbalancer.command("member-list")
@click.argument("pool_id", callback=validate_id)
@click.pass_context
def member_list(ctx: click.Context, pool_id: str) -> None:
    """List members in a pool."""
    client = ctx.find_object(SharkContext).ensure_client()
    data = client.get(f"{_octavia(client)}/v2/lbaas/pools/{pool_id}/members")
    members = data.get("members", [])
    if not members:
        console.print("[yellow]No members found.[/yellow]")
        return

    table = Table(title=f"Members in pool {pool_id}", show_lines=True)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="bold")
    table.add_column("Address")
    table.add_column("Port", justify="right")
    table.add_column("Weight", justify="right")
    table.add_column("Status", style="green")

    for m in members:
        table.add_row(
            m.get("id", ""),
            m.get("name", "") or "—",
            m.get("address", ""),
            str(m.get("protocol_port", "")),
            str(m.get("weight", "")),
            m.get("operating_status", ""),
        )
    console.print(table)


@loadbalancer.command("member-add")
@click.argument("pool_id", callback=validate_id)
@click.option("--address", required=True, help="Member IP address.")
@click.option("--port", "protocol_port", required=True, type=int, help="Member port.")
@click.option("--subnet-id", default=None, help="Member subnet ID.")
@click.option("--weight", type=int, default=1, show_default=True, help="Weight (0-256).")
@click.option("--name", default=None, help="Member name.")
@click.pass_context
def member_add(ctx: click.Context, pool_id: str, address: str, protocol_port: int,
               subnet_id: str | None, weight: int, name: str | None) -> None:
    """Add a member to a pool."""
    client = ctx.find_object(SharkContext).ensure_client()
    body: dict = {"address": address, "protocol_port": protocol_port, "weight": weight}
    if subnet_id:
        body["subnet_id"] = subnet_id
    if name:
        body["name"] = name
    data = client.post(f"{_octavia(client)}/v2/lbaas/pools/{pool_id}/members",
                       json={"member": body})
    m = data.get("member", data)
    console.print(f"[green]Member {m.get('id')} added — {address}:{protocol_port}.[/green]")


@loadbalancer.command("member-remove")
@click.argument("pool_id", callback=validate_id)
@click.argument("member_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def member_remove(ctx: click.Context, pool_id: str, member_id: str, yes: bool) -> None:
    """Remove a member from a pool."""
    if not yes:
        click.confirm(f"Remove member {member_id}?", abort=True)
    client = ctx.find_object(SharkContext).ensure_client()
    client.delete(f"{_octavia(client)}/v2/lbaas/pools/{pool_id}/members/{member_id}")
    console.print(f"[green]Member {member_id} removed.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  Health Monitors
# ══════════════════════════════════════════════════════════════════════════

@loadbalancer.command("healthmonitor-list")
@click.pass_context
def hm_list(ctx: click.Context) -> None:
    """List health monitors."""
    client = ctx.find_object(SharkContext).ensure_client()
    data = client.get(f"{_octavia(client)}/v2/lbaas/healthmonitors")
    hms = data.get("healthmonitors", [])
    if not hms:
        console.print("[yellow]No health monitors found.[/yellow]")
        return

    table = Table(title="Health Monitors", show_lines=True)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="bold")
    table.add_column("Type")
    table.add_column("Delay", justify="right")
    table.add_column("Timeout", justify="right")
    table.add_column("Pool ID")
    table.add_column("Status", style="green")

    for h in hms:
        table.add_row(
            h.get("id", ""),
            h.get("name", "") or "—",
            h.get("type", ""),
            str(h.get("delay", "")),
            str(h.get("timeout", "")),
            h.get("pool_id", "") or "—",
            h.get("provisioning_status", ""),
        )
    console.print(table)


@loadbalancer.command("healthmonitor-create")
@click.argument("name")
@click.option("--pool-id", required=True, help="Pool ID.")
@click.option("--type", "hm_type", required=True,
              type=click.Choice(["HTTP", "HTTPS", "PING", "TCP", "TLS-HELLO", "UDP-CONNECT"]))
@click.option("--delay", type=int, required=True, help="Probe interval (seconds).")
@click.option("--timeout", type=int, required=True, help="Probe timeout (seconds).")
@click.option("--max-retries", type=int, default=3, show_default=True, help="Max retries (1-10).")
@click.option("--url-path", default="/", show_default=True, help="HTTP URL path to probe.")
@click.option("--expected-codes", default="200", show_default=True, help="Expected HTTP codes.")
@click.pass_context
def hm_create(ctx: click.Context, name: str, pool_id: str, hm_type: str,
              delay: int, timeout: int, max_retries: int,
              url_path: str, expected_codes: str) -> None:
    """Create a health monitor."""
    client = ctx.find_object(SharkContext).ensure_client()
    body: dict = {
        "name": name,
        "pool_id": pool_id,
        "type": hm_type,
        "delay": delay,
        "timeout": timeout,
        "max_retries": max_retries,
    }
    if hm_type in ("HTTP", "HTTPS"):
        body["url_path"] = url_path
        body["expected_codes"] = expected_codes
    data = client.post(f"{_octavia(client)}/v2/lbaas/healthmonitors", json={"healthmonitor": body})
    h = data.get("healthmonitor", data)
    console.print(f"[green]Health monitor '{h.get('name')}' ({h.get('id')}) created.[/green]")


@loadbalancer.command("healthmonitor-delete")
@click.argument("hm_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def hm_delete(ctx: click.Context, hm_id: str, yes: bool) -> None:
    """Delete a health monitor."""
    if not yes:
        click.confirm(f"Delete health monitor {hm_id}?", abort=True)
    client = ctx.find_object(SharkContext).ensure_client()
    client.delete(f"{_octavia(client)}/v2/lbaas/healthmonitors/{hm_id}")
    console.print(f"[green]Health monitor {hm_id} deleted.[/green]")
