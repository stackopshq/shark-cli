"""``orca network`` — manage networks, subnets, ports & routers (Neutron v2)."""

from __future__ import annotations

import click

from orca_cli.core.aliases import add_command_with_alias
from orca_cli.core.context import OrcaContext
from orca_cli.core.output import console, output_options, print_detail, print_list
from orca_cli.core.validators import validate_id
from orca_cli.services.network import NetworkService

# ══════════════════════════════════════════════════════════════════════════
#  Networks
# ══════════════════════════════════════════════════════════════════════════

@click.group()
@click.pass_context
def network(ctx: click.Context) -> None:
    """Manage networks, subnets, ports & routers."""
    pass


# ── nested sub-groups (ADR-0008 — openstackclient-style naming) ───────────


@network.group("agent")
def network_agent() -> None:
    """Manage Neutron agents (admin)."""


@network.group("auto-allocated-topology")
def network_auto_allocated_topology() -> None:
    """Manage the project's auto-allocated topology."""


@network.group("port")
def network_port() -> None:
    """Manage Neutron ports."""


@network.group("rbac")
def network_rbac() -> None:
    """Manage RBAC policies on networks/qos/subnetpools/etc."""


@network.group("router")
def network_router() -> None:
    """Manage Neutron routers."""


@network_router.group("add")
def network_router_add() -> None:
    """Attach a sub-resource to a router (interface, route)."""


@network_router.group("remove")
def network_router_remove() -> None:
    """Detach a sub-resource from a router."""


@network_router.group("set")
def network_router_set() -> None:
    """Set a router-level attribute (gateway)."""


@network_router.group("unset")
def network_router_unset() -> None:
    """Clear a router-level attribute (gateway)."""


@network.group("segment")
def network_segment() -> None:
    """Manage network segments."""


@network.group("subnet")
def network_subnet() -> None:
    """Manage Neutron subnets."""


@network.command("list")
@output_options
@click.pass_context
def network_list(ctx: click.Context, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List networks."""
    svc = NetworkService(ctx.find_object(OrcaContext).ensure_client())
    networks = svc.find()

    print_list(
        networks,
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Name", "name", {"style": "bold"}),
            ("Subnets", lambda net: ", ".join(net.get("subnets", [])) or "—"),
            ("Status", "status", {"style": "green"}),
            ("External", lambda net: str(net.get("router:external", ""))),
            ("Shared", lambda net: str(net.get("shared", ""))),
        ],
        title="Networks",
        output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent,
        columns=columns,
        empty_msg="No networks found.",
    )


@network.command("show")
@click.argument("network_id", callback=validate_id)
@output_options
@click.pass_context
def network_show(ctx: click.Context, network_id: str, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show network details."""
    svc = NetworkService(ctx.find_object(OrcaContext).ensure_client())
    net = svc.get(network_id)

    fields = []
    for key in ["id", "name", "status", "admin_state_up", "shared",
                "router:external", "mtu", "subnets", "availability_zones",
                "created_at", "updated_at"]:
        val = net.get(key, "")
        fields.append((key, str(val) if val is not None else ""))

    print_detail(fields, output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent, columns=columns)


@network.command("create")
@click.argument("name")
@click.option("--admin-state/--no-admin-state", default=True, show_default=True, help="Admin state up.")
@click.option("--shared", is_flag=True, help="Shared across projects.")
@click.pass_context
def network_create(ctx: click.Context, name: str, admin_state: bool, shared: bool) -> None:
    """Create a network."""
    svc = NetworkService(ctx.find_object(OrcaContext).ensure_client())
    net = svc.create({"name": name, "admin_state_up": admin_state, "shared": shared})
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
    svc = NetworkService(ctx.find_object(OrcaContext).ensure_client())
    svc.update(network_id, body)
    console.print(f"[green]Network {network_id} updated.[/green]")


@network.command("delete")
@click.argument("network_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def network_delete(ctx: click.Context, network_id: str, yes: bool) -> None:
    """Delete a network."""
    if not yes:
        click.confirm(f"Delete network {network_id}?", abort=True)
    svc = NetworkService(ctx.find_object(OrcaContext).ensure_client())
    svc.delete(network_id)
    console.print(f"[green]Network {network_id} deleted.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  Subnets
# ══════════════════════════════════════════════════════════════════════════

@network_subnet.command("list")
@output_options
@click.pass_context
def subnet_list(ctx: click.Context, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List subnets."""
    svc = NetworkService(ctx.find_object(OrcaContext).ensure_client())
    subnets = svc.find_subnets()

    print_list(
        subnets,
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Name", lambda s: s.get("name", "") or "—", {"style": "bold"}),
            ("CIDR", "cidr"),
            ("Gateway", lambda s: s.get("gateway_ip", "") or "—"),
            ("Network ID", "network_id"),
            ("IP Ver.", lambda s: str(s.get("ip_version", "")), {"justify": "right"}),
        ],
        title="Subnets",
        output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent,
        columns=columns,
        empty_msg="No subnets found.",
    )


@network_subnet.command("show")
@click.argument("subnet_id", callback=validate_id)
@output_options
@click.pass_context
def subnet_show(ctx: click.Context, subnet_id: str, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show subnet details."""
    svc = NetworkService(ctx.find_object(OrcaContext).ensure_client())
    sub = svc.get_subnet(subnet_id)

    fields = []
    for key in ["id", "name", "cidr", "ip_version", "gateway_ip", "enable_dhcp",
                "dns_nameservers", "allocation_pools", "network_id", "created_at"]:
        fields.append((key, str(sub.get(key, ""))))

    print_detail(fields, output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent, columns=columns)


@network_subnet.command("create")
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
    svc = NetworkService(ctx.find_object(OrcaContext).ensure_client())
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

    sub = svc.create_subnet(body)
    console.print(f"[green]Subnet '{sub.get('name')}' ({sub.get('id')}) created — {cidr}.[/green]")


@network_subnet.command("delete")
@click.argument("subnet_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def subnet_delete(ctx: click.Context, subnet_id: str, yes: bool) -> None:
    """Delete a subnet."""
    if not yes:
        click.confirm(f"Delete subnet {subnet_id}?", abort=True)
    svc = NetworkService(ctx.find_object(OrcaContext).ensure_client())
    svc.delete_subnet(subnet_id)
    console.print(f"[green]Subnet {subnet_id} deleted.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  Ports
# ══════════════════════════════════════════════════════════════════════════

@network_port.command("list")
@click.option("--network-id", default=None, help="Filter by network ID.")
@output_options
@click.pass_context
def port_list(ctx: click.Context, network_id: str | None, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List ports."""
    svc = NetworkService(ctx.find_object(OrcaContext).ensure_client())
    params = {"network_id": network_id} if network_id else None
    ports = svc.find_ports(params=params)

    print_list(
        ports,
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Name", lambda p: p.get("name", "") or "—", {"style": "bold"}),
            ("MAC", "mac_address"),
            ("Fixed IPs", lambda p: ", ".join(
                ip.get("ip_address", "") for ip in p.get("fixed_ips", [])
            ) or "—"),
            ("Status", "status", {"style": "green"}),
            ("Device Owner", lambda p: p.get("device_owner", "") or "—"),
        ],
        title="Ports",
        output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent,
        columns=columns,
        empty_msg="No ports found.",
    )


@network_port.command("show")
@click.argument("port_id", callback=validate_id)
@output_options
@click.pass_context
def port_show(ctx: click.Context, port_id: str, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show port details."""
    svc = NetworkService(ctx.find_object(OrcaContext).ensure_client())
    port = svc.get_port(port_id)

    fields = []
    for key in ["id", "name", "mac_address", "fixed_ips", "status",
                "admin_state_up", "network_id", "device_id", "device_owner",
                "security_groups", "created_at"]:
        fields.append((key, str(port.get(key, ""))))

    print_detail(fields, output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent, columns=columns)


@network_port.command("create")
@click.option("--network-id", required=True, help="Network ID.")
@click.option("--name", default=None, help="Port name.")
@click.option("--fixed-ip", default=None, help="Fixed IP address.")
@click.pass_context
def port_create(ctx: click.Context, network_id: str, name: str | None, fixed_ip: str | None) -> None:
    """Create a port."""
    svc = NetworkService(ctx.find_object(OrcaContext).ensure_client())
    body: dict = {"network_id": network_id}
    if name:
        body["name"] = name
    if fixed_ip:
        body["fixed_ips"] = [{"ip_address": fixed_ip}]

    port = svc.create_port(body)
    ips = ", ".join(ip.get("ip_address", "") for ip in port.get("fixed_ips", []))
    console.print(f"[green]Port {port.get('id')} created — {ips}.[/green]")


@network_port.command("update")
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
    svc = NetworkService(ctx.find_object(OrcaContext).ensure_client())
    svc.update_port(port_id, body)
    console.print(f"[green]Port {port_id} updated.[/green]")


@network_port.command("delete")
@click.argument("port_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def port_delete(ctx: click.Context, port_id: str, yes: bool) -> None:
    """Delete a port."""
    if not yes:
        click.confirm(f"Delete port {port_id}?", abort=True)
    svc = NetworkService(ctx.find_object(OrcaContext).ensure_client())
    svc.delete_port(port_id)
    console.print(f"[green]Port {port_id} deleted.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  Routers
# ══════════════════════════════════════════════════════════════════════════

@network_router.command("list")
@output_options
@click.pass_context
def router_list(ctx: click.Context, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List routers."""
    svc = NetworkService(ctx.find_object(OrcaContext).ensure_client())
    routers = svc.find_routers()

    print_list(
        routers,
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Name", lambda r: r.get("name", "") or "—", {"style": "bold"}),
            ("Status", "status", {"style": "green"}),
            ("External GW", lambda r: (r.get("external_gateway_info") or {}).get("network_id", "—")
                if r.get("external_gateway_info") else "—"),
            ("Admin Up", lambda r: str(r.get("admin_state_up", ""))),
        ],
        title="Routers",
        output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent,
        columns=columns,
        empty_msg="No routers found.",
    )


@network_router.command("show")
@click.argument("router_id", callback=validate_id)
@output_options
@click.pass_context
def router_show(ctx: click.Context, router_id: str, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show router details."""
    svc = NetworkService(ctx.find_object(OrcaContext).ensure_client())
    r = svc.get_router(router_id)

    fields = []
    for key in ["id", "name", "status", "admin_state_up",
                "external_gateway_info", "routes", "created_at"]:
        fields.append((key, str(r.get(key, ""))))

    print_detail(fields, output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent, columns=columns)


@network_router.command("create")
@click.argument("name")
@click.option("--external-network", default=None, help="External network ID for gateway.")
@click.pass_context
def router_create(ctx: click.Context, name: str, external_network: str | None) -> None:
    """Create a router."""
    svc = NetworkService(ctx.find_object(OrcaContext).ensure_client())
    body: dict = {"name": name, "admin_state_up": True}
    if external_network:
        body["external_gateway_info"] = {"network_id": external_network}

    r = svc.create_router(body)
    console.print(f"[green]Router '{r.get('name')}' ({r.get('id')}) created.[/green]")


@network_router.command("update")
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
    svc = NetworkService(ctx.find_object(OrcaContext).ensure_client())
    svc.update_router(router_id, body)
    console.print(f"[green]Router {router_id} updated.[/green]")


@network_router.command("delete")
@click.argument("router_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def router_delete(ctx: click.Context, router_id: str, yes: bool) -> None:
    """Delete a router."""
    if not yes:
        click.confirm(f"Delete router {router_id}?", abort=True)
    svc = NetworkService(ctx.find_object(OrcaContext).ensure_client())
    svc.delete_router(router_id)
    console.print(f"[green]Router {router_id} deleted.[/green]")


@network_router_add.command("interface")
@click.argument("router_id", callback=validate_id)
@click.option("--subnet-id", required=True, help="Subnet to attach.")
@click.pass_context
def router_add_interface(ctx: click.Context, router_id: str, subnet_id: str) -> None:
    """Add a subnet interface to a router."""
    svc = NetworkService(ctx.find_object(OrcaContext).ensure_client())
    svc.add_router_interface(router_id, {"subnet_id": subnet_id})
    console.print(f"[green]Subnet {subnet_id} added to router {router_id}.[/green]")


@network_router_remove.command("interface")
@click.argument("router_id", callback=validate_id)
@click.option("--subnet-id", required=True, help="Subnet to detach.")
@click.pass_context
def router_remove_interface(ctx: click.Context, router_id: str, subnet_id: str) -> None:
    """Remove a subnet interface from a router."""
    svc = NetworkService(ctx.find_object(OrcaContext).ensure_client())
    svc.remove_router_interface(router_id, {"subnet_id": subnet_id})
    console.print(f"[green]Subnet {subnet_id} removed from router {router_id}.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  Topology
# ══════════════════════════════════════════════════════════════════════════

@network.command("topology")
@click.option("--network-id", "filter_net", default=None, help="Show only this network.")
@click.pass_context
def network_topology(ctx: click.Context, filter_net: str | None) -> None:
    """Display the network topology as a tree.

    Shows networks → subnets → connected ports with device info
    (servers, routers, DHCP, load-balancers).

    \b
    Examples:
      orca network topology
      orca network topology --network-id <id>
    """
    from rich.tree import Tree

    client = ctx.find_object(OrcaContext).ensure_client()
    svc = NetworkService(client)

    with console.status("[bold cyan]Building topology…[/bold cyan]"):
        # Fetch all resources
        if filter_net:
            nets = [svc.get(filter_net)]
        else:
            nets = svc.find()

        subnets = svc.find_subnets()
        ports = svc.find_ports()
        routers = svc.find_routers()

        # Fetch servers for name resolution
        try:
            servers_data = client.get(f"{client.compute_url}/servers/detail", params={"limit": 1000})
            servers = {s["id"]: s.get("name", s["id"]) for s in servers_data.get("servers", [])}
        except Exception:
            servers = {}

        # Index
        router_map = {r["id"]: r.get("name", r["id"]) for r in routers}

        # Ports indexed by network
        ports_by_net: dict[str, list] = {}
        for port in ports:
            net_id = port.get("network_id", "")
            ports_by_net.setdefault(net_id, []).append(port)

    # Build tree
    root = Tree("[bold]Network Topology[/bold]")

    for net in sorted(nets, key=lambda n: n.get("name", "")):
        net_id = net.get("id", "")
        net_name = net.get("name", net_id)
        ext = " [dim](external)[/dim]" if net.get("router:external") else ""
        net_node = root.add(f"[bold cyan]{net_name}[/bold cyan]  [dim]{net_id}[/dim]{ext}")

        # Subnets
        net_subnets = [s for s in subnets if s.get("network_id") == net_id]
        for sub in net_subnets:
            sub_label = f"[yellow]{sub.get('name', '')}[/yellow]  {sub.get('cidr', '')}  [dim]{sub['id']}[/dim]"
            sub_node = net_node.add(sub_label)

            # GW
            gw = sub.get("gateway_ip")
            if gw:
                sub_node.add(f"[dim]gateway: {gw}[/dim]")

        # Ports on this network
        net_ports = ports_by_net.get(net_id, [])
        if net_ports:
            ports_node = net_node.add(f"[bold]Ports ({len(net_ports)})[/bold]")
            for p in sorted(net_ports, key=lambda x: x.get("device_owner", "")):
                owner = p.get("device_owner", "")
                dev_id = p.get("device_id", "")
                ips = ", ".join(ip.get("ip_address", "") for ip in p.get("fixed_ips", []))
                mac = p.get("mac_address", "")

                # Resolve device name
                if "compute:" in owner:
                    dev_label = f"[green]server: {servers.get(dev_id, dev_id[:8])}[/green]"
                elif "router" in owner:
                    dev_label = f"[magenta]router: {router_map.get(dev_id, dev_id[:8])}[/magenta]"
                elif "dhcp" in owner:
                    dev_label = "[dim]DHCP agent[/dim]"
                elif "loadbalancer" in owner or "octavia" in owner:
                    dev_label = f"[blue]load-balancer: {dev_id[:8]}[/blue]"
                elif owner:
                    dev_label = f"{owner}: {dev_id[:8]}"
                else:
                    dev_label = "[dim]unbound[/dim]"

                port_label = f"{dev_label}  {ips}  [dim]{mac}[/dim]"
                ports_node.add(port_label)

    console.print()
    console.print(root)
    console.print()


# ── net-trace ────────────────────────────────────────────────────────────

@network.command("trace")
@click.argument("server_id")
@click.pass_context
def net_trace(ctx: click.Context, server_id: str) -> None:
    """Trace the full network path for a server instance.

    Shows every hop: fixed IP → port → security groups → router →
    floating IP, with status and IDs at each step.

    \b
    Examples:
      orca network trace <server-id>
      orca network trace <server-name>
    """
    from rich.tree import Tree

    client = ctx.find_object(OrcaContext).ensure_client()
    svc = NetworkService(client)

    # ── Resolve server ──
    try:
        srv_data = client.get(f"{client.compute_url}/servers/{server_id}")
        srv = srv_data.get("server", srv_data)
    except Exception:
        data = client.get(f"{client.compute_url}/servers/detail",
                          params={"name": server_id})
        matches = data.get("servers", [])
        if not matches:
            raise click.ClickException(f"Server '{server_id}' not found.") from None
        if len(matches) > 1:
            for m in matches:
                console.print(f"  {m['id']}  {m.get('name', '')}")
            raise click.ClickException("Multiple matches — use the server ID.") from None
        srv = matches[0]

    srv_name = srv.get("name", server_id)
    srv_id = srv.get("id", server_id)
    srv_status = srv.get("status", "?")
    status_color = {"ACTIVE": "green", "SHUTOFF": "dim", "ERROR": "red"}.get(srv_status, "yellow")

    console.print()
    tree = Tree(
        f"[bold cyan]Server:[/bold cyan] {srv_name}  "
        f"[dim]({srv_id})[/dim]  [{status_color}]{srv_status}[/{status_color}]"
    )

    # ── Fetch all ports for this server ──
    ports = svc.find_ports(params={"device_id": srv_id})

    if not ports:
        tree.add("[yellow]No ports attached[/yellow]")
        console.print(tree)
        console.print()
        return

    # ── Fetch floating IPs, security groups, routers, subnets ──
    with console.status("[bold]Tracing network path..."):
        fips = svc.find_floating_ips()
        fip_by_port = {f["port_id"]: f for f in fips if f.get("port_id")}

        sg_map = {sg["id"]: sg for sg in svc.find_security_groups()}

        routers = svc.find_routers()

        subnet_map = {s["id"]: s for s in svc.find_subnets()}

        network_map = {n["id"]: n for n in svc.find()}

    # ── Build trace for each port ──
    for port in ports:
        port_id = port.get("id", "?")
        mac = port.get("mac_address", "?")
        port_status = port.get("status", "?")
        net_id = port.get("network_id", "")
        net_info = network_map.get(net_id, {})
        net_name = net_info.get("name", net_id[:8])

        port_branch = tree.add(
            f"[bold]Port:[/bold] [dim]{port_id}[/dim]  "
            f"MAC: {mac}  status: {port_status}  "
            f"network: [cyan]{net_name}[/cyan]"
        )

        # Fixed IPs
        for fixed in port.get("fixed_ips", []):
            ip = fixed.get("ip_address", "?")
            subnet_id = fixed.get("subnet_id", "")
            subnet = subnet_map.get(subnet_id, {})
            subnet_name = subnet.get("name", subnet_id[:8])
            cidr = subnet.get("cidr", "")
            gw = subnet.get("gateway_ip", "")

            ip_branch = port_branch.add(
                f"[green bold]Fixed IP:[/green bold] {ip}  "
                f"subnet: [yellow]{subnet_name}[/yellow] ({cidr})"
            )
            if gw:
                ip_branch.add(f"[dim]Gateway: {gw}[/dim]")

        # Security Groups
        sg_ids = port.get("security_group_ids", port.get("security_groups", []))
        if sg_ids:
            sg_branch = port_branch.add("[bold]Security Groups:[/bold]")
            for sg_id in sg_ids:
                sg = sg_map.get(sg_id, {})
                sg_name = sg.get("name", sg_id[:8])
                rules = sg.get("security_group_rules", [])

                # Count ingress rules with 0.0.0.0/0
                wide_open = sum(
                    1 for r in rules
                    if r.get("direction") == "ingress"
                    and r.get("remote_ip_prefix") in ("0.0.0.0/0", "::/0")
                )
                warning = f"  [red bold]⚠ {wide_open} wide-open ingress[/red bold]" if wide_open else ""
                sg_node = sg_branch.add(
                    f"[magenta]{sg_name}[/magenta]  [dim]({sg_id})[/dim]  "
                    f"{len(rules)} rules{warning}"
                )

                # Show ingress rules summary
                ingress = [r for r in rules if r.get("direction") == "ingress"]
                for r in ingress[:10]:  # cap display at 10
                    proto = r.get("protocol") or "any"
                    pmin = r.get("port_range_min")
                    pmax = r.get("port_range_max")
                    remote = r.get("remote_ip_prefix") or r.get("remote_group_id", "")[:8] or "any"
                    if pmin and pmax:
                        port_str = f"{pmin}-{pmax}" if pmin != pmax else str(pmin)
                    else:
                        port_str = "all"
                    color = "red" if remote in ("0.0.0.0/0", "::/0") else "dim"
                    sg_node.add(f"[{color}]ingress {proto}/{port_str} ← {remote}[/{color}]")
                if len(ingress) > 10:
                    sg_node.add(f"[dim]... +{len(ingress) - 10} more[/dim]")

        # Router (find router for the subnets)
        subnet_ids = [f.get("subnet_id") for f in port.get("fixed_ips", [])]
        found_router = False
        for router in routers:
            r_id = router.get("id", "")
            # Check if this router has an interface on any of this port's subnets
            try:
                r_ports = svc.find_ports(params={
                    "device_id": r_id, "device_owner": "network:router_interface"
                })
            except Exception:
                r_ports = []
            r_subnets = set()
            for rp in r_ports:
                for fi in rp.get("fixed_ips", []):
                    r_subnets.add(fi.get("subnet_id"))

            common = set(subnet_ids) & r_subnets
            if common:
                found_router = True
                r_name = router.get("name", r_id[:8])
                ext_gw = router.get("external_gateway_info", {})
                ext_net_id = ext_gw.get("network_id", "") if ext_gw else ""
                ext_net = network_map.get(ext_net_id, {})
                ext_net_name = ext_net.get("name", ext_net_id[:8]) if ext_net_id else "none"
                ext_ips = ", ".join(
                    ip.get("ip_address", "")
                    for ip in (ext_gw.get("external_fixed_ips", []) if ext_gw else [])
                )
                port_branch.add(
                    f"[magenta bold]Router:[/magenta bold] {r_name}  [dim]({r_id})[/dim]  "
                    f"→ ext: [cyan]{ext_net_name}[/cyan]"
                    + (f"  ({ext_ips})" if ext_ips else "")
                )
                break

        if not found_router:
            port_branch.add("[dim]No router found for this subnet[/dim]")

        # Floating IP
        fip = fip_by_port.get(port_id)
        if fip:
            fip_addr = fip.get("floating_ip_address", "?")
            fip_status = fip.get("status", "?")
            fip_color = "green" if fip_status == "ACTIVE" else "red"
            fip_net_id = fip.get("floating_network_id", "")
            fip_net = network_map.get(fip_net_id, {})
            fip_net_name = fip_net.get("name", fip_net_id[:8])
            port_branch.add(
                f"[{fip_color} bold]Floating IP:[/{fip_color} bold] {fip_addr}  "
                f"[{fip_color}]{fip_status}[/{fip_color}]  "
                f"network: [cyan]{fip_net_name}[/cyan]  "
                f"[dim]({fip.get('id', '')})[/dim]"
            )
        else:
            port_branch.add("[dim]No floating IP[/dim]")

    console.print(tree)
    console.print()


# ══════════════════════════════════════════════════════════════════════════
#  subnet-update
# ══════════════════════════════════════════════════════════════════════════

@network_subnet.command("update")
@click.argument("subnet_id", callback=validate_id)
@click.option("--name", default=None, help="New name.")
@click.option("--description", default=None, help="New description.")
@click.option("--dns-nameserver", "dns_nameservers", multiple=True,
              help="DNS nameserver IP (repeatable, replaces existing list).")
@click.option("--enable-dhcp/--disable-dhcp", default=None,
              help="Enable or disable DHCP.")
@click.pass_context
def network_subnet_update(ctx: click.Context, subnet_id: str, name: str | None,
                          description: str | None, dns_nameservers: tuple[str, ...],
                          enable_dhcp: bool | None) -> None:
    """Update a subnet."""
    body: dict = {}
    if name is not None:
        body["name"] = name
    if description is not None:
        body["description"] = description
    if dns_nameservers:
        body["dns_nameservers"] = list(dns_nameservers)
    if enable_dhcp is not None:
        body["enable_dhcp"] = enable_dhcp
    if not body:
        console.print("[yellow]Nothing to update.[/yellow]")
        return
    svc = NetworkService(ctx.find_object(OrcaContext).ensure_client())
    svc.update_subnet(subnet_id, body)
    console.print(f"[green]Subnet {subnet_id} updated.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  network agent-*
# ══════════════════════════════════════════════════════════════════════════

@network_agent.command("list")
@click.option("--host", default=None, help="Filter by host.")
@click.option("--agent-type", default=None, help="Filter by agent type.")
@output_options
@click.pass_context
def network_agent_list(ctx: click.Context, host: str | None, agent_type: str | None,
                       output_format: str, columns: tuple[str, ...],
                       fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List Neutron agents."""
    svc = NetworkService(ctx.find_object(OrcaContext).ensure_client())
    params: dict = {}
    if host:
        params["host"] = host
    if agent_type:
        params["agent_type"] = agent_type
    agents = svc.find_agents(params=params or None)
    print_list(
        agents,
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Agent Type", "agent_type", {"style": "bold"}),
            ("Host", "host"),
            ("Availability Zone", lambda a: a.get("availability_zone") or "—"),
            ("Alive", lambda a: "[green]Yes[/green]" if a.get("alive") else "[red]No[/red]"),
            ("Admin State", lambda a:
             "[green]UP[/green]" if a.get("admin_state_up") else "[yellow]DOWN[/yellow]"),
            ("Binary", "binary"),
        ],
        title="Network Agents",
        output_format=output_format, fit_width=fit_width, max_width=max_width,
        noindent=noindent, columns=columns,
        empty_msg="No agents found.",
    )


@network_agent.command("show")
@click.argument("agent_id", callback=validate_id)
@output_options
@click.pass_context
def network_agent_show(ctx: click.Context, agent_id: str,
                       output_format: str, columns: tuple[str, ...],
                       fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show a Neutron agent's details."""
    svc = NetworkService(ctx.find_object(OrcaContext).ensure_client())
    agent = svc.get_agent(agent_id)
    print_detail(
        [(k, str(agent.get(k, "") or "")) for k in
         ["id", "agent_type", "binary", "host", "availability_zone",
          "alive", "admin_state_up", "started_at", "heartbeat_timestamp", "description"]],
        output_format=output_format, fit_width=fit_width, max_width=max_width,
        noindent=noindent, columns=columns,
    )


@network_agent.command("set")
@click.argument("agent_id", callback=validate_id)
@click.option("--enable/--disable", default=None, help="Enable or disable the agent.")
@click.option("--description", default=None, help="New description.")
@click.pass_context
def network_agent_set(ctx: click.Context, agent_id: str, enable: bool | None,
                      description: str | None) -> None:
    """Update a Neutron agent."""
    body: dict = {}
    if enable is not None:
        body["admin_state_up"] = enable
    if description is not None:
        body["description"] = description
    if not body:
        console.print("[yellow]Nothing to update.[/yellow]")
        return
    svc = NetworkService(ctx.find_object(OrcaContext).ensure_client())
    svc.update_agent(agent_id, body)
    console.print(f"[green]Agent {agent_id} updated.[/green]")


@network_agent.command("delete")
@click.argument("agent_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def network_agent_delete(ctx: click.Context, agent_id: str, yes: bool) -> None:
    """Delete a Neutron agent record."""
    if not yes:
        click.confirm(f"Delete agent {agent_id}?", abort=True)
    svc = NetworkService(ctx.find_object(OrcaContext).ensure_client())
    svc.delete_agent(agent_id)
    console.print(f"[green]Agent {agent_id} deleted.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  network rbac-*
# ══════════════════════════════════════════════════════════════════════════

@network_rbac.command("list")
@click.option("--object-type", default=None,
              type=click.Choice(["network", "qos_policy", "security_group",
                                 "address_group", "address_scope", "subnetpool"]),
              help="Filter by object type.")
@output_options
@click.pass_context
def network_rbac_list(ctx: click.Context, object_type: str | None,
                      output_format: str, columns: tuple[str, ...],
                      fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List RBAC policies."""
    svc = NetworkService(ctx.find_object(OrcaContext).ensure_client())
    params = {"object_type": object_type} if object_type else None
    policies = svc.find_rbac_policies(params=params)
    print_list(
        policies,
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Object Type", "object_type"),
            ("Object ID", "object_id"),
            ("Action", "action"),
            ("Target Project", "target_tenant"),
        ],
        title="RBAC Policies",
        output_format=output_format, fit_width=fit_width, max_width=max_width,
        noindent=noindent, columns=columns,
        empty_msg="No RBAC policies found.",
    )


@network_rbac.command("show")
@click.argument("rbac_id", callback=validate_id)
@output_options
@click.pass_context
def network_rbac_show(ctx: click.Context, rbac_id: str,
                      output_format: str, columns: tuple[str, ...],
                      fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show an RBAC policy."""
    svc = NetworkService(ctx.find_object(OrcaContext).ensure_client())
    p = svc.get_rbac_policy(rbac_id)
    print_detail(
        [(k, str(p.get(k, "") or "")) for k in
         ["id", "object_type", "object_id", "action", "target_tenant", "project_id"]],
        output_format=output_format, fit_width=fit_width, max_width=max_width,
        noindent=noindent, columns=columns,
    )


@network_rbac.command("create")
@click.option("--object-type", required=True,
              type=click.Choice(["network", "qos_policy", "security_group",
                                 "address_group", "address_scope", "subnetpool"]),
              help="Type of the shared object.")
@click.option("--object", "object_id", required=True,
              help="ID of the object to share.")
@click.option("--action", required=True,
              type=click.Choice(["access_as_shared", "access_as_external"]),
              help="RBAC action.")
@click.option("--target-project", required=True,
              help="Project ID to grant access to (use '*' for all projects).")
@click.pass_context
def network_rbac_create(ctx: click.Context, object_type: str, object_id: str,
                        action: str, target_project: str) -> None:
    """Create an RBAC policy to share a network resource.

    \b
    Example — share a network with all projects:
      orca network rbac-create \\
        --object-type network \\
        --object <network-id> \\
        --action access_as_shared \\
        --target-project '*'
    """
    svc = NetworkService(ctx.find_object(OrcaContext).ensure_client())
    p = svc.create_rbac_policy({
        "object_type": object_type,
        "object_id": object_id,
        "action": action,
        "target_tenant": target_project,
    })
    console.print(f"[green]RBAC policy created: {p.get('id', '?')}[/green]")


@network_rbac.command("delete")
@click.argument("rbac_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def network_rbac_delete(ctx: click.Context, rbac_id: str, yes: bool) -> None:
    """Delete an RBAC policy."""
    if not yes:
        click.confirm(f"Delete RBAC policy {rbac_id}?", abort=True)
    svc = NetworkService(ctx.find_object(OrcaContext).ensure_client())
    svc.delete_rbac_policy(rbac_id)
    console.print(f"[green]RBAC policy {rbac_id} deleted.[/green]")


@network_rbac.command("update")
@click.argument("rbac_id", callback=validate_id)
@click.option("--target-project", required=True,
              help="New target project ID (use '*' for all projects).")
@click.pass_context
def network_rbac_update(ctx: click.Context, rbac_id: str, target_project: str) -> None:
    """Update the target project of an RBAC policy.

    \b
    Example:
      orca network rbac-update <rbac-id> --target-project <project-id>
      orca network rbac-update <rbac-id> --target-project '*'
    """
    svc = NetworkService(ctx.find_object(OrcaContext).ensure_client())
    svc.update_rbac_policy(rbac_id, {"target_tenant": target_project})
    console.print(f"[green]RBAC policy {rbac_id} updated.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  port unset
# ══════════════════════════════════════════════════════════════════════════


@network_port.command("unset")
@click.argument("port_id", callback=validate_id)
@click.option("--security-group", "security_groups", multiple=True,
              help="Security group ID to remove (repeatable).")
@click.option("--qos-policy", "clear_qos", is_flag=True, default=False,
              help="Remove the QoS policy from the port.")
@click.option("--description", "clear_description", is_flag=True, default=False,
              help="Clear the port description.")
@click.pass_context
def network_port_unset(ctx: click.Context, port_id: str,
                       security_groups: tuple[str, ...],
                       clear_qos: bool, clear_description: bool) -> None:
    """Remove properties from a port.

    \b
    Examples:
      orca network port-unset <port-id> --security-group <sg-id>
      orca network port-unset <port-id> --qos-policy
      orca network port-unset <port-id> --description
    """
    svc = NetworkService(ctx.find_object(OrcaContext).ensure_client())
    did_something = False
    body: dict = {}

    if security_groups:
        # Fetch current SGs, remove the specified ones, then PUT
        current = svc.get_port(port_id)
        current_sgs = [sg for sg in current.get("security_groups", [])
                       if sg not in security_groups]
        body["security_groups"] = current_sgs
        did_something = True

    if clear_qos:
        body["qos_policy_id"] = None
        did_something = True

    if clear_description:
        body["description"] = ""
        did_something = True

    if not did_something:
        console.print("[yellow]Nothing to unset — provide --security-group, --qos-policy, or --description.[/yellow]")
        return

    svc.update_port(port_id, body)
    console.print(f"[green]Port {port_id} updated.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  router gateway set/unset
# ══════════════════════════════════════════════════════════════════════════


@network_router_set.command("gateway")
@click.argument("router_id", callback=validate_id)
@click.option("--external-network", "network_id", required=True,
              help="External network ID to use as gateway.")
@click.option("--enable-snat/--disable-snat", "snat", default=None,
              help="Enable or disable SNAT on the gateway.")
@click.pass_context
def network_router_set_gateway(ctx: click.Context, router_id: str,
                               network_id: str, snat: bool | None) -> None:
    """Set (or replace) the external gateway on a router.

    \b
    Examples:
      orca network router-set-gateway <router-id> --external-network <net-id>
      orca network router-set-gateway <router-id> --external-network <net-id> --enable-snat
    """
    svc = NetworkService(ctx.find_object(OrcaContext).ensure_client())
    gw: dict = {"network_id": network_id}
    if snat is not None:
        gw["enable_snat"] = snat
    svc.update_router(router_id, {"external_gateway_info": gw})
    console.print(f"[green]Gateway set on router {router_id} → network {network_id}.[/green]")


@network_router_unset.command("gateway")
@click.argument("router_id", callback=validate_id)
@click.pass_context
def network_router_unset_gateway(ctx: click.Context, router_id: str) -> None:
    """Remove the external gateway from a router.

    \b
    Example:
      orca network router-unset-gateway <router-id>
    """
    svc = NetworkService(ctx.find_object(OrcaContext).ensure_client())
    svc.update_router(router_id, {"external_gateway_info": {}})
    console.print(f"[green]Gateway removed from router {router_id}.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  router static routes (extraroutes)
# ══════════════════════════════════════════════════════════════════════════


@network_router_add.command("route")
@click.argument("router_id", callback=validate_id)
@click.option("--destination", required=True, metavar="CIDR",
              help="Destination network (e.g. 10.1.0.0/24).")
@click.option("--nexthop", required=True, metavar="IP",
              help="Next-hop IP address.")
@click.pass_context
def network_router_add_route(ctx: click.Context, router_id: str,
                              destination: str, nexthop: str) -> None:
    """Add a static route to a router (requires extraroute-atomic extension).

    \b
    Example:
      orca network router-add-route <router-id> --destination 10.1.0.0/24 --nexthop 192.168.1.1
    """
    svc = NetworkService(ctx.find_object(OrcaContext).ensure_client())
    svc.add_router_routes(router_id, [{"destination": destination, "nexthop": nexthop}])
    console.print(
        f"[green]Route {destination} via {nexthop} added to router {router_id}.[/green]"
    )


@network_router_remove.command("route")
@click.argument("router_id", callback=validate_id)
@click.option("--destination", required=True, metavar="CIDR",
              help="Destination network to remove.")
@click.option("--nexthop", required=True, metavar="IP",
              help="Next-hop IP address.")
@click.pass_context
def network_router_remove_route(ctx: click.Context, router_id: str,
                                destination: str, nexthop: str) -> None:
    """Remove a static route from a router (requires extraroute-atomic extension).

    \b
    Example:
      orca network router-remove-route <router-id> --destination 10.1.0.0/24 --nexthop 192.168.1.1
    """
    svc = NetworkService(ctx.find_object(OrcaContext).ensure_client())
    svc.remove_router_routes(router_id, [{"destination": destination, "nexthop": nexthop}])
    console.print(
        f"[green]Route {destination} via {nexthop} removed from router {router_id}.[/green]"
    )


# ══════════════════════════════════════════════════════════════════════════════
#  Network Segments (Neutron segments extension)
# ══════════════════════════════════════════════════════════════════════════════

@network_segment.command("list")
@click.option("--network-id", default=None, help="Filter by network ID.")
@output_options
@click.pass_context
def network_segment_list(ctx, network_id, output_format, columns, fit_width, max_width, noindent):
    """List network segments."""
    svc = NetworkService(ctx.find_object(OrcaContext).ensure_client())
    params = {"network_id": network_id} if network_id else None
    print_list(
        svc.find_segments(params=params),
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Name", "name", {"style": "bold"}),
            ("Network ID", "network_id"),
            ("Network Type", "network_type"),
            ("Physical Network", lambda s: s.get("physical_network") or "—"),
            ("Segmentation ID", lambda s: str(s.get("segmentation_id") or "—")),
        ],
        title="Network Segments",
        output_format=output_format, columns=columns,
        fit_width=fit_width, max_width=max_width, noindent=noindent,
        empty_msg="No segments found.",
    )


@network_segment.command("show")
@click.argument("segment_id", callback=validate_id)
@output_options
@click.pass_context
def network_segment_show(ctx, segment_id, output_format, columns, fit_width, max_width, noindent):
    """Show a network segment."""
    svc = NetworkService(ctx.find_object(OrcaContext).ensure_client())
    s = svc.get_segment(segment_id)
    print_detail(
        [(k, str(s.get(k, "") or "")) for k in
         ("id", "name", "network_id", "network_type",
          "physical_network", "segmentation_id", "description")],
        output_format=output_format, columns=columns,
        fit_width=fit_width, max_width=max_width, noindent=noindent,
    )


@network_segment.command("create")
@click.argument("name")
@click.option("--network-id", required=True, help="Network ID this segment belongs to.")
@click.option("--network-type", required=True,
              type=click.Choice(["flat", "geneve", "gre", "local", "vlan", "vxlan"]),
              help="Network type.")
@click.option("--physical-network", default=None, help="Physical network name.")
@click.option("--segment", "segmentation_id", type=int, default=None,
              help="Segmentation ID (VLAN ID or tunnel ID).")
@click.option("--description", default=None, help="Segment description.")
@click.pass_context
def network_segment_create(ctx, name, network_id, network_type, physical_network,
                           segmentation_id, description):
    """Create a network segment."""
    svc = NetworkService(ctx.find_object(OrcaContext).ensure_client())
    body: dict = {"name": name, "network_id": network_id, "network_type": network_type}
    if physical_network:
        body["physical_network"] = physical_network
    if segmentation_id is not None:
        body["segmentation_id"] = segmentation_id
    if description:
        body["description"] = description
    s = svc.create_segment(body)
    console.print(f"[green]Segment '{s.get('name')}' ({s.get('id')}) created.[/green]")


@network_segment.command("set")
@click.argument("segment_id", callback=validate_id)
@click.option("--name", default=None, help="New name.")
@click.option("--description", default=None, help="New description.")
@click.pass_context
def network_segment_set(ctx, segment_id, name, description):
    """Update a network segment."""
    body: dict = {}
    if name is not None:
        body["name"] = name
    if description is not None:
        body["description"] = description
    if not body:
        console.print("[yellow]Nothing to update.[/yellow]")
        return
    svc = NetworkService(ctx.find_object(OrcaContext).ensure_client())
    svc.update_segment(segment_id, body)
    console.print(f"[green]Segment {segment_id} updated.[/green]")


@network_segment.command("delete")
@click.argument("segment_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def network_segment_delete(ctx, segment_id, yes):
    """Delete a network segment."""
    if not yes:
        click.confirm(f"Delete segment {segment_id}?", abort=True)
    svc = NetworkService(ctx.find_object(OrcaContext).ensure_client())
    svc.delete_segment(segment_id)
    console.print(f"[green]Segment {segment_id} deleted.[/green]")


# ══════════════════════════════════════════════════════════════════════════════
#  Auto-allocated topology (Neutron auto-allocation extension)
# ══════════════════════════════════════════════════════════════════════════════

@network_auto_allocated_topology.command("show")
@click.option("--project-id", default=None, help="Project ID (default: current project).")
@click.option("--check-resources", is_flag=True,
              help="Validate resources without creating topology.")
@output_options
@click.pass_context
def network_auto_allocated_topology_show(ctx, project_id, check_resources,
                                         output_format, columns, fit_width,
                                         max_width, noindent):
    """Show or create the auto-allocated topology for a project.

    \b
    Examples:
      orca network auto-allocated-topology-show
      orca network auto-allocated-topology-show --project-id <pid>
      orca network auto-allocated-topology-show --check-resources
    """
    svc = NetworkService(ctx.find_object(OrcaContext).ensure_client())
    topo = svc.get_auto_allocated_topology(project_id or "null",
                                           dry_run=check_resources)
    print_detail(
        [(k, str(topo.get(k, "") or "")) for k in
         ("id", "tenant_id")],
        output_format=output_format, columns=columns,
        fit_width=fit_width, max_width=max_width, noindent=noindent,
    )


@network_auto_allocated_topology.command("delete")
@click.option("--project-id", default=None, help="Project ID (default: current project).")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def network_auto_allocated_topology_delete(ctx, project_id, yes):
    """Delete the auto-allocated topology for a project."""
    if not yes:
        click.confirm("Delete auto-allocated topology?", abort=True)
    svc = NetworkService(ctx.find_object(OrcaContext).ensure_client())
    svc.delete_auto_allocated_topology(project_id or "null")
    console.print("[green]Auto-allocated topology deleted.[/green]")


# ── Deprecated aliases (ADR-0008) ─────────────────────────────────────────

for _legacy, _primary, _path in [
    ("agent-delete",       network_agent.commands["delete"],  "network agent delete"),
    ("agent-list",         network_agent.commands["list"],    "network agent list"),
    ("agent-set",          network_agent.commands["set"],     "network agent set"),
    ("agent-show",         network_agent.commands["show"],    "network agent show"),
    ("auto-allocated-topology-delete",
        network_auto_allocated_topology.commands["delete"],
        "network auto-allocated-topology delete"),
    ("auto-allocated-topology-show",
        network_auto_allocated_topology.commands["show"],
        "network auto-allocated-topology show"),
    ("port-create",        network_port.commands["create"],   "network port create"),
    ("port-delete",        network_port.commands["delete"],   "network port delete"),
    ("port-list",          network_port.commands["list"],     "network port list"),
    ("port-show",          network_port.commands["show"],     "network port show"),
    ("port-unset",         network_port.commands["unset"],    "network port unset"),
    ("port-update",        network_port.commands["update"],   "network port update"),
    ("rbac-create",        network_rbac.commands["create"],   "network rbac create"),
    ("rbac-delete",        network_rbac.commands["delete"],   "network rbac delete"),
    ("rbac-list",          network_rbac.commands["list"],     "network rbac list"),
    ("rbac-show",          network_rbac.commands["show"],     "network rbac show"),
    ("rbac-update",        network_rbac.commands["update"],   "network rbac update"),
    ("router-create",      network_router.commands["create"], "network router create"),
    ("router-delete",      network_router.commands["delete"], "network router delete"),
    ("router-list",        network_router.commands["list"],   "network router list"),
    ("router-show",        network_router.commands["show"],   "network router show"),
    ("router-update",      network_router.commands["update"], "network router update"),
    ("router-add-interface",
        network_router_add.commands["interface"],
        "network router add interface"),
    ("router-add-route",
        network_router_add.commands["route"],
        "network router add route"),
    ("router-remove-interface",
        network_router_remove.commands["interface"],
        "network router remove interface"),
    ("router-remove-route",
        network_router_remove.commands["route"],
        "network router remove route"),
    ("router-set-gateway",
        network_router_set.commands["gateway"],
        "network router set gateway"),
    ("router-unset-gateway",
        network_router_unset.commands["gateway"],
        "network router unset gateway"),
    ("segment-create",     network_segment.commands["create"], "network segment create"),
    ("segment-delete",     network_segment.commands["delete"], "network segment delete"),
    ("segment-list",       network_segment.commands["list"],   "network segment list"),
    ("segment-set",        network_segment.commands["set"],    "network segment set"),
    ("segment-show",       network_segment.commands["show"],   "network segment show"),
    ("subnet-create",      network_subnet.commands["create"],  "network subnet create"),
    ("subnet-delete",      network_subnet.commands["delete"],  "network subnet delete"),
    ("subnet-list",        network_subnet.commands["list"],    "network subnet list"),
    ("subnet-show",        network_subnet.commands["show"],    "network subnet show"),
    ("subnet-update",      network_subnet.commands["update"],  "network subnet update"),
]:
    add_command_with_alias(network, _primary, legacy_name=_legacy, primary_path=_path)
del _legacy, _primary, _path
