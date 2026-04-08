"""``shark security-group`` — manage security groups (Neutron)."""

from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from shark_cli.core.context import SharkContext
from shark_cli.core.validators import validate_id

console = Console()


@click.group("security-group")
@click.pass_context
def security_group(ctx: click.Context) -> None:
    """Manage security groups."""
    pass


@security_group.command("list")
@click.pass_context
def sg_list(ctx: click.Context) -> None:
    """List security groups."""
    client = ctx.find_object(SharkContext).ensure_client()
    url = f"{client.network_url}/v2.0/security-groups"
    data = client.get(url)

    groups = data.get("security_groups", [])

    if not groups:
        console.print("[yellow]No security groups found.[/yellow]")
        return

    table = Table(title="Security Groups", show_lines=True)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="bold")
    table.add_column("Description")
    table.add_column("Rules", justify="right")

    for sg in groups:
        table.add_row(
            sg.get("id", ""),
            sg.get("name", ""),
            sg.get("description", "") or "—",
            str(len(sg.get("security_group_rules", []))),
        )

    console.print(table)


@security_group.command("show")
@click.argument("group_id", callback=validate_id)
@click.pass_context
def sg_show(ctx: click.Context, group_id: str) -> None:
    """Show security group details and rules."""
    client = ctx.find_object(SharkContext).ensure_client()
    url = f"{client.network_url}/v2.0/security-groups/{group_id}"
    data = client.get(url)

    sg = data.get("security_group", data)

    console.print(f"\n[bold]{sg.get('name', group_id)}[/bold]  ({sg.get('id', '')})")
    console.print(f"  {sg.get('description', '')}\n")

    rules = sg.get("security_group_rules", [])
    if not rules:
        console.print("[yellow]No rules.[/yellow]")
        return

    table = Table(title="Rules", show_lines=True)
    table.add_column("Direction")
    table.add_column("Ether Type")
    table.add_column("Protocol")
    table.add_column("Port Range")
    table.add_column("Remote IP / Group")

    for r in rules:
        port_min = r.get("port_range_min")
        port_max = r.get("port_range_max")
        if port_min and port_max:
            port_range = f"{port_min}-{port_max}" if port_min != port_max else str(port_min)
        else:
            port_range = "any"

        remote = r.get("remote_ip_prefix") or r.get("remote_group_id") or "any"

        table.add_row(
            r.get("direction", ""),
            r.get("ethertype", ""),
            r.get("protocol") or "any",
            port_range,
            remote,
        )

    console.print(table)


@security_group.command("create")
@click.argument("name")
@click.option("--description", default="", help="Description.")
@click.pass_context
def sg_create(ctx: click.Context, name: str, description: str) -> None:
    """Create a security group."""
    client = ctx.find_object(SharkContext).ensure_client()
    url = f"{client.network_url}/v2.0/security-groups"
    data = client.post(url, json={"security_group": {"name": name, "description": description}})
    sg = data.get("security_group", data)
    console.print(f"[green]Security group '{sg.get('name')}' ({sg.get('id')}) created.[/green]")


@security_group.command("update")
@click.argument("group_id", callback=validate_id)
@click.option("--name", default=None, help="New name.")
@click.option("--description", default=None, help="New description.")
@click.pass_context
def sg_update(ctx: click.Context, group_id: str, name: str | None, description: str | None) -> None:
    """Update a security group."""
    body: dict = {}
    if name is not None:
        body["name"] = name
    if description is not None:
        body["description"] = description
    if not body:
        console.print("[yellow]Nothing to update.[/yellow]")
        return
    client = ctx.find_object(SharkContext).ensure_client()
    url = f"{client.network_url}/v2.0/security-groups/{group_id}"
    client.put(url, json={"security_group": body})
    console.print(f"[green]Security group {group_id} updated.[/green]")


@security_group.command("delete")
@click.argument("group_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def sg_delete(ctx: click.Context, group_id: str, yes: bool) -> None:
    """Delete a security group."""
    if not yes:
        click.confirm(f"Delete security group {group_id}?", abort=True)
    client = ctx.find_object(SharkContext).ensure_client()
    url = f"{client.network_url}/v2.0/security-groups/{group_id}"
    client.delete(url)
    console.print(f"[green]Security group {group_id} deleted.[/green]")


@security_group.command("rule-add")
@click.argument("group_id", callback=validate_id)
@click.option("--direction", type=click.Choice(["ingress", "egress"]), required=True)
@click.option("--protocol", default=None, help="Protocol (tcp, udp, icmp, or number).")
@click.option("--port-min", type=int, default=None, help="Min port (or single port).")
@click.option("--port-max", type=int, default=None, help="Max port. Defaults to port-min.")
@click.option("--remote-ip", default=None, help="Remote IP prefix (CIDR).")
@click.option("--remote-group", default=None, help="Remote security group ID.")
@click.option("--ethertype", type=click.Choice(["IPv4", "IPv6"]), default="IPv4", show_default=True)
@click.pass_context
def sg_rule_add(ctx: click.Context, group_id: str, direction: str, protocol: str | None,
                port_min: int | None, port_max: int | None,
                remote_ip: str | None, remote_group: str | None, ethertype: str) -> None:
    """Add a rule to a security group.

    \b
    Examples:
      shark security-group rule-add <id> --direction ingress --protocol tcp --port-min 22
      shark security-group rule-add <id> --direction ingress --protocol tcp --port-min 80 --port-max 443 --remote-ip 0.0.0.0/0
    """
    client = ctx.find_object(SharkContext).ensure_client()
    body: dict = {
        "security_group_id": group_id,
        "direction": direction,
        "ethertype": ethertype,
    }
    if protocol:
        body["protocol"] = protocol
    if port_min is not None:
        body["port_range_min"] = port_min
        body["port_range_max"] = port_max if port_max is not None else port_min
    if remote_ip:
        body["remote_ip_prefix"] = remote_ip
    if remote_group:
        body["remote_group_id"] = remote_group

    url = f"{client.network_url}/v2.0/security-group-rules"
    data = client.post(url, json={"security_group_rule": body})
    rule = data.get("security_group_rule", data)
    console.print(f"[green]Rule {rule.get('id')} added to {group_id}.[/green]")


@security_group.command("rule-delete")
@click.argument("rule_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def sg_rule_delete(ctx: click.Context, rule_id: str, yes: bool) -> None:
    """Delete a security group rule."""
    if not yes:
        click.confirm(f"Delete rule {rule_id}?", abort=True)
    client = ctx.find_object(SharkContext).ensure_client()
    url = f"{client.network_url}/v2.0/security-group-rules/{rule_id}"
    client.delete(url)
    console.print(f"[green]Rule {rule_id} deleted.[/green]")
