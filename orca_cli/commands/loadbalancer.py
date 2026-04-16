"""``orca loadbalancer`` — manage load balancers (Octavia)."""

from __future__ import annotations

import click

from orca_cli.core.context import OrcaContext
from orca_cli.core.exceptions import APIError
from orca_cli.core.output import console, output_options, print_detail, print_list
from orca_cli.core.validators import validate_id


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
@output_options
@click.pass_context
def lb_list(ctx: click.Context, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List load balancers."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_octavia(client)}/v2/lbaas/loadbalancers")
    lbs = data.get("loadbalancers", [])

    print_list(
        lbs,
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Name", lambda lb: lb.get("name", "") or "—", {"style": "bold"}),
            ("VIP Address", "vip_address"),
            ("Prov. Status", "provisioning_status", {"style": "green"}),
            ("Oper. Status", "operating_status"),
            ("Provider", "provider"),
        ],
        title="Load Balancers",
        output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent,
        columns=columns,
        empty_msg="No load balancers found.",
    )


@loadbalancer.command("show")
@click.argument("lb_id", callback=validate_id)
@output_options
@click.pass_context
def lb_show(ctx: click.Context, lb_id: str, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show load balancer details."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_octavia(client)}/v2/lbaas/loadbalancers/{lb_id}")
    lb = data.get("loadbalancer", data)

    fields = [
        (key, str(lb.get(key, "")))
        for key in [
            "id", "name", "description", "vip_address", "vip_subnet_id",
            "vip_network_id", "vip_port_id", "provider",
            "provisioning_status", "operating_status",
            "admin_state_up", "listeners", "pools",
            "created_at", "updated_at",
        ]
    ]
    print_detail(fields, output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent, columns=columns)


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
      orca loadbalancer create my-lb --subnet-id <subnet-id>
    """
    client = ctx.find_object(OrcaContext).ensure_client()
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
    client = ctx.find_object(OrcaContext).ensure_client()
    params = {"cascade": "true"} if cascade else {}
    try:
        client.delete(f"{_octavia(client)}/v2/lbaas/loadbalancers/{lb_id}", params=params)
    except APIError as exc:
        if exc.status_code == 409:
            raise click.ClickException(
                f"Load balancer {lb_id} is busy (provisioning in progress). "
                "Wait for it to reach ACTIVE or ERROR state before deleting."
            )
        raise
    console.print(f"[green]Load balancer {lb_id} deletion started.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  Listeners
# ══════════════════════════════════════════════════════════════════════════

@loadbalancer.command("listener-list")
@output_options
@click.pass_context
def listener_list(ctx: click.Context, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List listeners."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_octavia(client)}/v2/lbaas/listeners")
    listeners = data.get("listeners", [])

    print_list(
        listeners,
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Name", lambda item: item.get("name", "") or "—", {"style": "bold"}),
            ("Protocol", "protocol"),
            ("Port", lambda item: str(item.get("protocol_port", "")), {"justify": "right"}),
            ("LB ID", lambda item: (item.get("loadbalancers") or [{}])[0].get("id", "") if item.get("loadbalancers") else ""),
            ("Status", "provisioning_status", {"style": "green"}),
        ],
        title="Listeners",
        output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent,
        columns=columns,
        empty_msg="No listeners found.",
    )


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
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {
        "name": name,
        "loadbalancer_id": loadbalancer_id,
        "protocol": protocol,
        "protocol_port": protocol_port,
    }
    if default_pool_id:
        body["default_pool_id"] = default_pool_id
    data = client.post(f"{_octavia(client)}/v2/lbaas/listeners", json={"listener": body})
    listener = data.get("listener", data)
    console.print(f"[green]Listener '{listener.get('name')}' ({listener.get('id')}) created on port {protocol_port}.[/green]")


@loadbalancer.command("listener-show")
@click.argument("listener_id", callback=validate_id)
@output_options
@click.pass_context
def listener_show(ctx: click.Context, listener_id: str, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show listener details."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_octavia(client)}/v2/lbaas/listeners/{listener_id}")
    listener = data.get("listener", data)

    fields = [
        (key, str(listener.get(key, "")))
        for key in [
            "id", "name", "protocol", "protocol_port", "default_pool_id",
            "connection_limit", "provisioning_status", "operating_status",
            "admin_state_up", "created_at", "updated_at",
        ]
    ]
    print_detail(fields, output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent, columns=columns)


@loadbalancer.command("listener-delete")
@click.argument("listener_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def listener_delete(ctx: click.Context, listener_id: str, yes: bool) -> None:
    """Delete a listener."""
    if not yes:
        click.confirm(f"Delete listener {listener_id}?", abort=True)
    client = ctx.find_object(OrcaContext).ensure_client()
    client.delete(f"{_octavia(client)}/v2/lbaas/listeners/{listener_id}")
    console.print(f"[green]Listener {listener_id} deleted.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  Pools
# ══════════════════════════════════════════════════════════════════════════

@loadbalancer.command("pool-list")
@output_options
@click.pass_context
def pool_list(ctx: click.Context, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List pools."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_octavia(client)}/v2/lbaas/pools")
    pools = data.get("pools", [])

    print_list(
        pools,
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Name", lambda p: p.get("name", "") or "—", {"style": "bold"}),
            ("Protocol", "protocol"),
            ("LB Algorithm", "lb_algorithm"),
            ("Members", lambda p: str(len(p.get("members", []))), {"justify": "right"}),
            ("Status", "provisioning_status", {"style": "green"}),
        ],
        title="Pools",
        output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent,
        columns=columns,
        empty_msg="No pools found.",
    )


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
    client = ctx.find_object(OrcaContext).ensure_client()
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
@output_options
@click.pass_context
def pool_show(ctx: click.Context, pool_id: str, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show pool details."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_octavia(client)}/v2/lbaas/pools/{pool_id}")
    p = data.get("pool", data)

    fields = [
        (key, str(p.get(key, "")))
        for key in [
            "id", "name", "protocol", "lb_algorithm", "session_persistence",
            "healthmonitor_id", "provisioning_status", "operating_status",
            "admin_state_up", "created_at", "updated_at",
        ]
    ]
    print_detail(fields, output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent, columns=columns)


@loadbalancer.command("pool-delete")
@click.argument("pool_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def pool_delete(ctx: click.Context, pool_id: str, yes: bool) -> None:
    """Delete a pool."""
    if not yes:
        click.confirm(f"Delete pool {pool_id}?", abort=True)
    client = ctx.find_object(OrcaContext).ensure_client()
    client.delete(f"{_octavia(client)}/v2/lbaas/pools/{pool_id}")
    console.print(f"[green]Pool {pool_id} deleted.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  Members
# ══════════════════════════════════════════════════════════════════════════

@loadbalancer.command("member-list")
@click.argument("pool_id", callback=validate_id)
@output_options
@click.pass_context
def member_list(ctx: click.Context, pool_id: str, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List members in a pool."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_octavia(client)}/v2/lbaas/pools/{pool_id}/members")
    members = data.get("members", [])

    print_list(
        members,
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Name", lambda m: m.get("name", "") or "—", {"style": "bold"}),
            ("Address", "address"),
            ("Port", lambda m: str(m.get("protocol_port", "")), {"justify": "right"}),
            ("Weight", lambda m: str(m.get("weight", "")), {"justify": "right"}),
            ("Status", "operating_status", {"style": "green"}),
        ],
        title=f"Members in pool {pool_id}",
        output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent,
        columns=columns,
        empty_msg="No members found.",
    )


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
    client = ctx.find_object(OrcaContext).ensure_client()
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
    client = ctx.find_object(OrcaContext).ensure_client()
    client.delete(f"{_octavia(client)}/v2/lbaas/pools/{pool_id}/members/{member_id}")
    console.print(f"[green]Member {member_id} removed.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  Health Monitors
# ══════════════════════════════════════════════════════════════════════════

@loadbalancer.command("healthmonitor-list")
@output_options
@click.pass_context
def hm_list(ctx: click.Context, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List health monitors."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_octavia(client)}/v2/lbaas/healthmonitors")
    hms = data.get("healthmonitors", [])

    print_list(
        hms,
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Name", lambda h: h.get("name", "") or "—", {"style": "bold"}),
            ("Type", "type"),
            ("Delay", lambda h: str(h.get("delay", "")), {"justify": "right"}),
            ("Timeout", lambda h: str(h.get("timeout", "")), {"justify": "right"}),
            ("Pool ID", lambda h: h.get("pool_id", "") or "—"),
            ("Status", "provisioning_status", {"style": "green"}),
        ],
        title="Health Monitors",
        output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent,
        columns=columns,
        empty_msg="No health monitors found.",
    )


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
    client = ctx.find_object(OrcaContext).ensure_client()
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
    client = ctx.find_object(OrcaContext).ensure_client()
    client.delete(f"{_octavia(client)}/v2/lbaas/healthmonitors/{hm_id}")
    console.print(f"[green]Health monitor {hm_id} deleted.[/green]")


@loadbalancer.command("healthmonitor-show")
@click.argument("hm_id", callback=validate_id)
@output_options
@click.pass_context
def hm_show(ctx: click.Context, hm_id: str, output_format: str, columns: tuple[str, ...],
            fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show health monitor details."""
    client = ctx.find_object(OrcaContext).ensure_client()
    h = client.get(f"{_octavia(client)}/v2/lbaas/healthmonitors/{hm_id}").get("healthmonitor", {})
    fields = [(k, str(h.get(k, "") or "")) for k in
              ["id", "name", "type", "pool_id", "delay", "timeout", "max_retries",
               "url_path", "expected_codes", "provisioning_status",
               "admin_state_up", "created_at", "updated_at"]]
    print_detail(fields, output_format=output_format, fit_width=fit_width,
                 max_width=max_width, noindent=noindent, columns=columns)


@loadbalancer.command("healthmonitor-set")
@click.argument("hm_id", callback=validate_id)
@click.option("--name", default=None, help="New name.")
@click.option("--delay", type=int, default=None, help="Probe interval (seconds).")
@click.option("--timeout", type=int, default=None, help="Probe timeout (seconds).")
@click.option("--max-retries", type=int, default=None, help="Max retries.")
@click.option("--url-path", default=None, help="HTTP URL path to probe.")
@click.option("--expected-codes", default=None, help="Expected HTTP codes.")
@click.option("--enable/--disable", "admin_state_up", default=None,
              help="Enable or disable the health monitor.")
@click.pass_context
def hm_set(ctx: click.Context, hm_id: str, name: str | None, delay: int | None,
           timeout: int | None, max_retries: int | None, url_path: str | None,
           expected_codes: str | None, admin_state_up: bool | None) -> None:
    """Update a health monitor."""
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {}
    for k, v in [("name", name), ("delay", delay), ("timeout", timeout),
                 ("max_retries", max_retries), ("url_path", url_path),
                 ("expected_codes", expected_codes), ("admin_state_up", admin_state_up)]:
        if v is not None:
            body[k] = v
    if not body:
        console.print("[yellow]Nothing to update.[/yellow]")
        return
    client.put(f"{_octavia(client)}/v2/lbaas/healthmonitors/{hm_id}",
               json={"healthmonitor": body})
    console.print(f"[green]Health monitor {hm_id} updated.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  Load Balancer set / stats / status
# ══════════════════════════════════════════════════════════════════════════

@loadbalancer.command("set")
@click.argument("lb_id", callback=validate_id)
@click.option("--name", default=None, help="New name.")
@click.option("--description", default=None, help="New description.")
@click.option("--enable/--disable", "admin_state_up", default=None,
              help="Enable or disable the load balancer.")
@click.pass_context
def lb_set(ctx: click.Context, lb_id: str, name: str | None, description: str | None,
           admin_state_up: bool | None) -> None:
    """Update a load balancer."""
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {}
    for k, v in [("name", name), ("description", description),
                 ("admin_state_up", admin_state_up)]:
        if v is not None:
            body[k] = v
    if not body:
        console.print("[yellow]Nothing to update.[/yellow]")
        return
    client.put(f"{_octavia(client)}/v2/lbaas/loadbalancers/{lb_id}",
               json={"loadbalancer": body})
    console.print(f"[green]Load balancer {lb_id} updated.[/green]")


@loadbalancer.command("stats-show")
@click.argument("lb_id", callback=validate_id)
@output_options
@click.pass_context
def lb_stats_show(ctx: click.Context, lb_id: str, output_format: str,
                  columns: tuple[str, ...], fit_width: bool,
                  max_width: int | None, noindent: bool) -> None:
    """Show load balancer statistics."""
    client = ctx.find_object(OrcaContext).ensure_client()
    stats = client.get(
        f"{_octavia(client)}/v2/lbaas/loadbalancers/{lb_id}/stats"
    ).get("stats", {})
    fields = [(k, str(stats.get(k, 0))) for k in
              ["active_connections", "bytes_in", "bytes_out",
               "request_errors", "total_connections"]]
    print_detail(fields, output_format=output_format, fit_width=fit_width,
                 max_width=max_width, noindent=noindent, columns=columns)


@loadbalancer.command("status-show")
@click.argument("lb_id", callback=validate_id)
@click.pass_context
def lb_status_show(ctx: click.Context, lb_id: str) -> None:
    """Show load balancer operating status tree."""
    import json
    client = ctx.find_object(OrcaContext).ensure_client()
    status = client.get(
        f"{_octavia(client)}/v2/lbaas/loadbalancers/{lb_id}/statuses"
    ).get("statuses", {})
    console.print(json.dumps(status, indent=2))


# ══════════════════════════════════════════════════════════════════════════
#  Listener set
# ══════════════════════════════════════════════════════════════════════════

@loadbalancer.command("listener-set")
@click.argument("listener_id", callback=validate_id)
@click.option("--name", default=None, help="New name.")
@click.option("--description", default=None, help="New description.")
@click.option("--default-pool-id", default=None, help="New default pool ID.")
@click.option("--connection-limit", type=int, default=None,
              help="Max connections (-1 for unlimited).")
@click.option("--enable/--disable", "admin_state_up", default=None,
              help="Enable or disable the listener.")
@click.pass_context
def listener_set(ctx: click.Context, listener_id: str, name: str | None,
                 description: str | None, default_pool_id: str | None,
                 connection_limit: int | None, admin_state_up: bool | None) -> None:
    """Update a listener."""
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {}
    for k, v in [("name", name), ("description", description),
                 ("default_pool_id", default_pool_id),
                 ("connection_limit", connection_limit),
                 ("admin_state_up", admin_state_up)]:
        if v is not None:
            body[k] = v
    if not body:
        console.print("[yellow]Nothing to update.[/yellow]")
        return
    client.put(f"{_octavia(client)}/v2/lbaas/listeners/{listener_id}",
               json={"listener": body})
    console.print(f"[green]Listener {listener_id} updated.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  Pool set
# ══════════════════════════════════════════════════════════════════════════

@loadbalancer.command("pool-set")
@click.argument("pool_id", callback=validate_id)
@click.option("--name", default=None, help="New name.")
@click.option("--description", default=None, help="New description.")
@click.option("--algorithm", "lb_algorithm",
              type=click.Choice(["ROUND_ROBIN", "LEAST_CONNECTIONS", "SOURCE_IP"]),
              default=None, help="New LB algorithm.")
@click.option("--enable/--disable", "admin_state_up", default=None,
              help="Enable or disable the pool.")
@click.pass_context
def pool_set(ctx: click.Context, pool_id: str, name: str | None, description: str | None,
             lb_algorithm: str | None, admin_state_up: bool | None) -> None:
    """Update a pool."""
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {}
    for k, v in [("name", name), ("description", description),
                 ("lb_algorithm", lb_algorithm), ("admin_state_up", admin_state_up)]:
        if v is not None:
            body[k] = v
    if not body:
        console.print("[yellow]Nothing to update.[/yellow]")
        return
    client.put(f"{_octavia(client)}/v2/lbaas/pools/{pool_id}", json={"pool": body})
    console.print(f"[green]Pool {pool_id} updated.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  Member show / set
# ══════════════════════════════════════════════════════════════════════════

@loadbalancer.command("member-show")
@click.argument("pool_id", callback=validate_id)
@click.argument("member_id", callback=validate_id)
@output_options
@click.pass_context
def member_show(ctx: click.Context, pool_id: str, member_id: str,
                output_format: str, columns: tuple[str, ...],
                fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show member details."""
    client = ctx.find_object(OrcaContext).ensure_client()
    m = client.get(
        f"{_octavia(client)}/v2/lbaas/pools/{pool_id}/members/{member_id}"
    ).get("member", {})
    fields = [(k, str(m.get(k, "") or "")) for k in
              ["id", "name", "address", "protocol_port", "weight", "subnet_id",
               "operating_status", "provisioning_status", "admin_state_up",
               "created_at", "updated_at"]]
    print_detail(fields, output_format=output_format, fit_width=fit_width,
                 max_width=max_width, noindent=noindent, columns=columns)


@loadbalancer.command("member-set")
@click.argument("pool_id", callback=validate_id)
@click.argument("member_id", callback=validate_id)
@click.option("--name", default=None, help="New name.")
@click.option("--weight", type=int, default=None, help="New weight (0-256).")
@click.option("--enable/--disable", "admin_state_up", default=None,
              help="Enable or disable the member.")
@click.pass_context
def member_set(ctx: click.Context, pool_id: str, member_id: str, name: str | None,
               weight: int | None, admin_state_up: bool | None) -> None:
    """Update a pool member."""
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {}
    for k, v in [("name", name), ("weight", weight), ("admin_state_up", admin_state_up)]:
        if v is not None:
            body[k] = v
    if not body:
        console.print("[yellow]Nothing to update.[/yellow]")
        return
    client.put(f"{_octavia(client)}/v2/lbaas/pools/{pool_id}/members/{member_id}",
               json={"member": body})
    console.print(f"[green]Member {member_id} updated.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  L7 Policies
# ══════════════════════════════════════════════════════════════════════════

_L7_ACTIONS = ["REDIRECT_TO_POOL", "REDIRECT_TO_URL", "REJECT", "REDIRECT_PREFIX"]


@loadbalancer.command("l7policy-list")
@output_options
@click.pass_context
def l7policy_list(ctx: click.Context, output_format: str, columns: tuple[str, ...],
                  fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List L7 policies."""
    client = ctx.find_object(OrcaContext).ensure_client()
    policies = client.get(f"{_octavia(client)}/v2/lbaas/l7policies").get("l7policies", [])
    print_list(
        policies,
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Name", lambda p: p.get("name") or "—", {"style": "bold"}),
            ("Action", "action"),
            ("Listener ID", "listener_id"),
            ("Position", lambda p: str(p.get("position", "—")), {"justify": "right"}),
            ("Status", "provisioning_status", {"style": "green"}),
        ],
        title="L7 Policies",
        output_format=output_format, fit_width=fit_width, max_width=max_width,
        noindent=noindent, columns=columns,
        empty_msg="No L7 policies found.",
    )


@loadbalancer.command("l7policy-show")
@click.argument("l7policy_id", callback=validate_id)
@output_options
@click.pass_context
def l7policy_show(ctx: click.Context, l7policy_id: str, output_format: str,
                  columns: tuple[str, ...], fit_width: bool,
                  max_width: int | None, noindent: bool) -> None:
    """Show L7 policy details."""
    client = ctx.find_object(OrcaContext).ensure_client()
    p = client.get(
        f"{_octavia(client)}/v2/lbaas/l7policies/{l7policy_id}"
    ).get("l7policy", {})
    fields = [(k, str(p.get(k, "") or "")) for k in
              ["id", "name", "listener_id", "action", "redirect_pool_id",
               "redirect_url", "redirect_prefix", "position",
               "provisioning_status", "admin_state_up", "created_at"]]
    print_detail(fields, output_format=output_format, fit_width=fit_width,
                 max_width=max_width, noindent=noindent, columns=columns)


@loadbalancer.command("l7policy-create")
@click.option("--listener-id", required=True, callback=validate_id,
              help="Listener to attach the policy to.")
@click.option("--action", required=True, type=click.Choice(_L7_ACTIONS),
              help="Policy action.")
@click.option("--name", default=None, help="Policy name.")
@click.option("--description", default=None, help="Description.")
@click.option("--position", type=int, default=None, help="Policy position (order).")
@click.option("--redirect-pool-id", default=None,
              help="Pool to redirect to (REDIRECT_TO_POOL).")
@click.option("--redirect-url", default=None,
              help="URL to redirect to (REDIRECT_TO_URL).")
@click.option("--redirect-prefix", default=None,
              help="URL prefix to redirect to (REDIRECT_PREFIX).")
@click.pass_context
def l7policy_create(ctx: click.Context, listener_id: str, action: str,
                    name: str | None, description: str | None,
                    position: int | None, redirect_pool_id: str | None,
                    redirect_url: str | None, redirect_prefix: str | None) -> None:
    """Create an L7 policy.

    \b
    Examples:
      orca loadbalancer l7policy-create --listener-id <id> --action REJECT
      orca loadbalancer l7policy-create --listener-id <id> \\
        --action REDIRECT_TO_POOL --redirect-pool-id <pool-id>
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {"listener_id": listener_id, "action": action}
    for k, v in [("name", name), ("description", description), ("position", position),
                 ("redirect_pool_id", redirect_pool_id), ("redirect_url", redirect_url),
                 ("redirect_prefix", redirect_prefix)]:
        if v is not None:
            body[k] = v
    p = client.post(f"{_octavia(client)}/v2/lbaas/l7policies",
                    json={"l7policy": body}).get("l7policy", {})
    console.print(f"[green]L7 policy '{p.get('name', p.get('id', '?'))}' created: {p.get('id', '?')}[/green]")


@loadbalancer.command("l7policy-set")
@click.argument("l7policy_id", callback=validate_id)
@click.option("--name", default=None, help="New name.")
@click.option("--description", default=None, help="New description.")
@click.option("--action", type=click.Choice(_L7_ACTIONS), default=None, help="New action.")
@click.option("--position", type=int, default=None, help="New position.")
@click.option("--redirect-pool-id", default=None, help="New redirect pool ID.")
@click.option("--redirect-url", default=None, help="New redirect URL.")
@click.option("--enable/--disable", "admin_state_up", default=None,
              help="Enable or disable.")
@click.pass_context
def l7policy_set(ctx: click.Context, l7policy_id: str, name: str | None,
                 description: str | None, action: str | None, position: int | None,
                 redirect_pool_id: str | None, redirect_url: str | None,
                 admin_state_up: bool | None) -> None:
    """Update an L7 policy."""
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {}
    for k, v in [("name", name), ("description", description), ("action", action),
                 ("position", position), ("redirect_pool_id", redirect_pool_id),
                 ("redirect_url", redirect_url), ("admin_state_up", admin_state_up)]:
        if v is not None:
            body[k] = v
    if not body:
        console.print("[yellow]Nothing to update.[/yellow]")
        return
    client.put(f"{_octavia(client)}/v2/lbaas/l7policies/{l7policy_id}",
               json={"l7policy": body})
    console.print(f"[green]L7 policy {l7policy_id} updated.[/green]")


@loadbalancer.command("l7policy-delete")
@click.argument("l7policy_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def l7policy_delete(ctx: click.Context, l7policy_id: str, yes: bool) -> None:
    """Delete an L7 policy."""
    if not yes:
        click.confirm(f"Delete L7 policy {l7policy_id}?", abort=True)
    client = ctx.find_object(OrcaContext).ensure_client()
    client.delete(f"{_octavia(client)}/v2/lbaas/l7policies/{l7policy_id}")
    console.print(f"[green]L7 policy {l7policy_id} deleted.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  L7 Rules
# ══════════════════════════════════════════════════════════════════════════

_L7_RULE_TYPES = ["COOKIE", "FILE_TYPE", "HEADER", "HOST_NAME", "PATH",
                  "SSL_CONN_HAS_CERT", "SSL_VERIFY_RESULT", "SSL_DN_FIELD"]
_L7_RULE_COMPARE = ["CONTAINS", "ENDS_WITH", "EQUAL_TO", "REGEX", "STARTS_WITH"]


@loadbalancer.command("l7rule-list")
@click.argument("l7policy_id", callback=validate_id)
@output_options
@click.pass_context
def l7rule_list(ctx: click.Context, l7policy_id: str, output_format: str,
                columns: tuple[str, ...], fit_width: bool,
                max_width: int | None, noindent: bool) -> None:
    """List L7 rules for a policy."""
    client = ctx.find_object(OrcaContext).ensure_client()
    rules = client.get(
        f"{_octavia(client)}/v2/lbaas/l7policies/{l7policy_id}/rules"
    ).get("rules", [])
    print_list(
        rules,
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Type", "type"),
            ("Compare Type", "compare_type"),
            ("Value", "value"),
            ("Invert", lambda r: "yes" if r.get("invert") else "no"),
            ("Status", "provisioning_status", {"style": "green"}),
        ],
        title=f"L7 Rules for policy {l7policy_id}",
        output_format=output_format, fit_width=fit_width, max_width=max_width,
        noindent=noindent, columns=columns,
        empty_msg="No L7 rules.",
    )


@loadbalancer.command("l7rule-show")
@click.argument("l7policy_id", callback=validate_id)
@click.argument("l7rule_id", callback=validate_id)
@output_options
@click.pass_context
def l7rule_show(ctx: click.Context, l7policy_id: str, l7rule_id: str,
                output_format: str, columns: tuple[str, ...],
                fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show L7 rule details."""
    client = ctx.find_object(OrcaContext).ensure_client()
    r = client.get(
        f"{_octavia(client)}/v2/lbaas/l7policies/{l7policy_id}/rules/{l7rule_id}"
    ).get("rule", {})
    fields = [(k, str(r.get(k, "") or "")) for k in
              ["id", "type", "compare_type", "key", "value", "invert",
               "provisioning_status", "admin_state_up", "created_at"]]
    print_detail(fields, output_format=output_format, fit_width=fit_width,
                 max_width=max_width, noindent=noindent, columns=columns)


@loadbalancer.command("l7rule-create")
@click.argument("l7policy_id", callback=validate_id)
@click.option("--type", "rule_type", required=True,
              type=click.Choice(_L7_RULE_TYPES), help="Rule type.")
@click.option("--compare-type", required=True,
              type=click.Choice(_L7_RULE_COMPARE), help="Comparison type.")
@click.option("--value", required=True, help="Value to compare against.")
@click.option("--key", default=None, help="Key (for HEADER, COOKIE rules).")
@click.option("--invert", is_flag=True, help="Invert the match result.")
@click.pass_context
def l7rule_create(ctx: click.Context, l7policy_id: str, rule_type: str,
                  compare_type: str, value: str, key: str | None,
                  invert: bool) -> None:
    """Create an L7 rule.

    \b
    Examples:
      orca loadbalancer l7rule-create <policy-id> \\
        --type PATH --compare-type STARTS_WITH --value /api
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {"type": rule_type, "compare_type": compare_type, "value": value}
    if key:
        body["key"] = key
    if invert:
        body["invert"] = True
    r = client.post(
        f"{_octavia(client)}/v2/lbaas/l7policies/{l7policy_id}/rules",
        json={"rule": body},
    ).get("rule", {})
    console.print(f"[green]L7 rule created: {r.get('id', '?')}[/green]")


@loadbalancer.command("l7rule-set")
@click.argument("l7policy_id", callback=validate_id)
@click.argument("l7rule_id", callback=validate_id)
@click.option("--type", "rule_type", type=click.Choice(_L7_RULE_TYPES),
              default=None, help="New rule type.")
@click.option("--compare-type", type=click.Choice(_L7_RULE_COMPARE),
              default=None, help="New comparison type.")
@click.option("--value", default=None, help="New value.")
@click.option("--key", default=None, help="New key.")
@click.option("--invert/--no-invert", default=None, help="Invert match.")
@click.option("--enable/--disable", "admin_state_up", default=None,
              help="Enable or disable the rule.")
@click.pass_context
def l7rule_set(ctx: click.Context, l7policy_id: str, l7rule_id: str,
               rule_type: str | None, compare_type: str | None, value: str | None,
               key: str | None, invert: bool | None, admin_state_up: bool | None) -> None:
    """Update an L7 rule."""
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {}
    for k, v in [("type", rule_type), ("compare_type", compare_type),
                 ("value", value), ("key", key), ("invert", invert),
                 ("admin_state_up", admin_state_up)]:
        if v is not None:
            body[k] = v
    if not body:
        console.print("[yellow]Nothing to update.[/yellow]")
        return
    client.put(
        f"{_octavia(client)}/v2/lbaas/l7policies/{l7policy_id}/rules/{l7rule_id}",
        json={"rule": body},
    )
    console.print(f"[green]L7 rule {l7rule_id} updated.[/green]")


@loadbalancer.command("l7rule-delete")
@click.argument("l7policy_id", callback=validate_id)
@click.argument("l7rule_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def l7rule_delete(ctx: click.Context, l7policy_id: str, l7rule_id: str, yes: bool) -> None:
    """Delete an L7 rule."""
    if not yes:
        click.confirm(f"Delete L7 rule {l7rule_id}?", abort=True)
    client = ctx.find_object(OrcaContext).ensure_client()
    client.delete(
        f"{_octavia(client)}/v2/lbaas/l7policies/{l7policy_id}/rules/{l7rule_id}"
    )
    console.print(f"[green]L7 rule {l7rule_id} deleted.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  Amphora (admin)
# ══════════════════════════════════════════════════════════════════════════

@loadbalancer.command("amphora-list")
@click.option("--lb-id", "loadbalancer_id", default=None,
              help="Filter by load balancer ID.")
@click.option("--status", default=None, help="Filter by amphora status.")
@output_options
@click.pass_context
def amphora_list(ctx: click.Context, loadbalancer_id: str | None, status: str | None,
                 output_format: str, columns: tuple[str, ...],
                 fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List amphora (admin)."""
    client = ctx.find_object(OrcaContext).ensure_client()
    params: dict = {}
    if loadbalancer_id:
        params["loadbalancer_id"] = loadbalancer_id
    if status:
        params["status"] = status
    amphorae = client.get(f"{_octavia(client)}/v2/octavia/amphorae",
                          params=params).get("amphorae", [])
    print_list(
        amphorae,
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("LB ID", "loadbalancer_id"),
            ("Status", "status", {"style": "green"}),
            ("Role", "role"),
            ("Compute ID", "compute_id"),
            ("HA IP", "ha_ip"),
        ],
        title="Amphorae",
        output_format=output_format, fit_width=fit_width, max_width=max_width,
        noindent=noindent, columns=columns,
        empty_msg="No amphorae found.",
    )


@loadbalancer.command("amphora-show")
@click.argument("amphora_id", callback=validate_id)
@output_options
@click.pass_context
def amphora_show(ctx: click.Context, amphora_id: str, output_format: str,
                 columns: tuple[str, ...], fit_width: bool,
                 max_width: int | None, noindent: bool) -> None:
    """Show amphora details (admin)."""
    client = ctx.find_object(OrcaContext).ensure_client()
    a = client.get(
        f"{_octavia(client)}/v2/octavia/amphorae/{amphora_id}"
    ).get("amphora", {})
    fields = [(k, str(a.get(k, "") or "")) for k in
              ["id", "loadbalancer_id", "compute_id", "status", "role",
               "lb_network_ip", "ha_ip", "ha_port_id",
               "vrrp_ip", "vrrp_interface", "vrrp_priority",
               "cert_expiration", "created_at", "updated_at"]]
    print_detail(fields, output_format=output_format, fit_width=fit_width,
                 max_width=max_width, noindent=noindent, columns=columns)


@loadbalancer.command("amphora-failover")
@click.argument("amphora_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def amphora_failover(ctx: click.Context, amphora_id: str, yes: bool) -> None:
    """Trigger a failover for an amphora (admin)."""
    if not yes:
        click.confirm(f"Failover amphora {amphora_id}?", abort=True)
    client = ctx.find_object(OrcaContext).ensure_client()
    client.put(f"{_octavia(client)}/v2/octavia/amphorae/{amphora_id}/failover",
               json={})
    console.print(f"[green]Failover triggered for amphora {amphora_id}.[/green]")
