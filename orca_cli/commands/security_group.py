"""``orca security-group`` — manage security groups (Neutron)."""

from __future__ import annotations

import click

from orca_cli.core.context import OrcaContext
from orca_cli.core.output import output_options, print_list, console
from orca_cli.core.validators import validate_id


@click.group("security-group")
@click.pass_context
def security_group(ctx: click.Context) -> None:
    """Manage security groups."""
    pass


@security_group.command("list")
@output_options
@click.pass_context
def sg_list(ctx: click.Context, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List security groups."""
    client = ctx.find_object(OrcaContext).ensure_client()
    url = f"{client.network_url}/v2.0/security-groups"
    data = client.get(url)

    print_list(
        data.get("security_groups", []),
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Name", "name", {"style": "bold"}),
            ("Description", lambda sg: sg.get("description", "") or "—"),
            ("Rules", lambda sg: str(len(sg.get("security_group_rules", []))), {"justify": "right"}),
        ],
        title="Security Groups",
        output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent,
        columns=columns,
        empty_msg="No security groups found.",
    )


@security_group.command("show")
@click.argument("group_id", callback=validate_id)
@output_options
@click.pass_context
def sg_show(ctx: click.Context, group_id: str, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show security group details and rules."""
    client = ctx.find_object(OrcaContext).ensure_client()
    url = f"{client.network_url}/v2.0/security-groups/{group_id}"
    data = client.get(url)

    sg = data.get("security_group", data)

    if output_format == "table":
        console.print(f"\n[bold]{sg.get('name', group_id)}[/bold]  ({sg.get('id', '')})")
        console.print(f"  {sg.get('description', '')}\n")

    rules = sg.get("security_group_rules", [])

    def _port_range(r: dict) -> str:
        port_min = r.get("port_range_min")
        port_max = r.get("port_range_max")
        if port_min and port_max:
            return f"{port_min}-{port_max}" if port_min != port_max else str(port_min)
        return "any"

    print_list(
        rules,
        [
            ("Direction", "direction"),
            ("Ether Type", "ethertype"),
            ("Protocol", lambda r: r.get("protocol") or "any"),
            ("Port Range", _port_range),
            ("Remote IP / Group", lambda r: r.get("remote_ip_prefix") or r.get("remote_group_id") or "any"),
        ],
        title="Rules",
        output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent,
        columns=columns,
        empty_msg="No rules.",
    )


@security_group.command("create")
@click.argument("name")
@click.option("--description", default="", help="Description.")
@click.pass_context
def sg_create(ctx: click.Context, name: str, description: str) -> None:
    """Create a security group."""
    client = ctx.find_object(OrcaContext).ensure_client()
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
    client = ctx.find_object(OrcaContext).ensure_client()
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
    client = ctx.find_object(OrcaContext).ensure_client()
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
      orca security-group rule-add <id> --direction ingress --protocol tcp --port-min 22
      orca security-group rule-add <id> --direction ingress --protocol tcp --port-min 80 --port-max 443 --remote-ip 0.0.0.0/0
    """
    client = ctx.find_object(OrcaContext).ensure_client()
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


@security_group.command("clone")
@click.argument("source_id", callback=validate_id)
@click.argument("new_name")
@click.option("--description", default=None, help="Description for the new group.")
@click.pass_context
def sg_clone(ctx: click.Context, source_id: str, new_name: str, description: str | None) -> None:
    """Clone a security group (copy all rules to a new group).

    \b
    Examples:
      orca security-group clone <source-id> my-new-sg
      orca security-group clone <source-id> prod-sg --description "Production rules"
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    base_url = f"{client.network_url}/v2.0"

    # Fetch source group
    src_data = client.get(f"{base_url}/security-groups/{source_id}")
    src = src_data.get("security_group", src_data)
    src_name = src.get("name", source_id)

    desc = description if description is not None else f"Clone of {src_name}"

    # Create new group
    new_data = client.post(f"{base_url}/security-groups",
                           json={"security_group": {"name": new_name, "description": desc}})
    new_sg = new_data.get("security_group", new_data)
    new_id = new_sg.get("id", "")

    console.print(f"[green]Created security group '{new_name}' ({new_id}).[/green]")

    # Copy rules (skip default egress rules that are auto-created)
    rules = src.get("security_group_rules", [])
    copied = 0
    for rule in rules:
        body: dict = {
            "security_group_id": new_id,
            "direction": rule.get("direction"),
            "ethertype": rule.get("ethertype"),
        }
        if rule.get("protocol"):
            body["protocol"] = rule["protocol"]
        if rule.get("port_range_min") is not None:
            body["port_range_min"] = rule["port_range_min"]
        if rule.get("port_range_max") is not None:
            body["port_range_max"] = rule["port_range_max"]
        if rule.get("remote_ip_prefix"):
            body["remote_ip_prefix"] = rule["remote_ip_prefix"]
        if rule.get("remote_group_id"):
            # If the rule references the source group itself, point it to the new group
            if rule["remote_group_id"] == source_id:
                body["remote_group_id"] = new_id
            else:
                body["remote_group_id"] = rule["remote_group_id"]

        try:
            client.post(f"{base_url}/security-group-rules",
                        json={"security_group_rule": body})
            copied += 1
        except Exception:
            # Skip rules that conflict with auto-created defaults
            pass

    console.print(f"[green]{copied}/{len(rules)} rules copied from '{src_name}' → '{new_name}'.[/green]")


@security_group.command("rule-delete")
@click.argument("rule_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def sg_rule_delete(ctx: click.Context, rule_id: str, yes: bool) -> None:
    """Delete a security group rule."""
    if not yes:
        click.confirm(f"Delete rule {rule_id}?", abort=True)
    client = ctx.find_object(OrcaContext).ensure_client()
    url = f"{client.network_url}/v2.0/security-group-rules/{rule_id}"
    client.delete(url)
    console.print(f"[green]Rule {rule_id} deleted.[/green]")


# ── cleanup ──────────────────────────────────────────────────────────────

@security_group.command("cleanup")
@click.option("--delete", "-d", "do_delete", is_flag=True, default=False,
              help="Actually delete the unused security groups.")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation (with --delete).")
@click.pass_context
def sg_cleanup(ctx: click.Context, do_delete: bool, yes: bool) -> None:
    """Find security groups not attached to any port.

    Lists orphaned SGs that are likely leftovers from tests or deleted
    instances. Use --delete to remove them.

    The 'default' security group is always skipped.

    \b
    Examples:
      orca security-group cleanup              # dry run
      orca security-group cleanup --delete     # interactive delete
      orca security-group cleanup --delete -y  # auto-delete all
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    base = f"{client.network_url}/v2.0"

    with console.status("[bold]Scanning security groups and ports..."):
        sgs = client.get(f"{base}/security-groups").get("security_groups", [])
        ports = client.get(f"{base}/ports").get("ports", [])

    # Collect all SG IDs actually in use by any port
    used_sg_ids: set[str] = set()
    for port in ports:
        for sg_id in port.get("security_groups", []):
            used_sg_ids.add(sg_id)

    # Find orphans (skip "default")
    orphans = [
        sg for sg in sgs
        if sg["id"] not in used_sg_ids and sg.get("name") != "default"
    ]

    if not orphans:
        console.print("[green]No orphaned security groups found.[/green]")
        return

    from rich.table import Table

    table = Table(title=f"Orphaned Security Groups ({len(orphans)})", show_lines=False)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="bold")
    table.add_column("Description")
    table.add_column("Rules", justify="right")

    for sg in orphans:
        table.add_row(
            sg["id"],
            sg.get("name", ""),
            (sg.get("description", "") or "")[:50],
            str(len(sg.get("security_group_rules", []))),
        )

    console.print()
    console.print(table)

    if not do_delete:
        console.print(f"\n[yellow]{len(orphans)} unused security group(s). "
                       "Use --delete to remove them.[/yellow]\n")
        return

    if not yes:
        click.confirm(f"\nDelete {len(orphans)} orphaned security group(s)?", abort=True)

    deleted = 0
    errors = 0
    for sg in orphans:
        try:
            client.delete(f"{base}/security-groups/{sg['id']}")
            console.print(f"  [green]Deleted[/green] {sg.get('name', '')} ({sg['id']})")
            deleted += 1
        except Exception as exc:
            console.print(f"  [red]Failed[/red] {sg.get('name', '')} ({sg['id']}): {exc}")
            errors += 1

    console.print(f"\n[green]{deleted} deleted[/green]", end="")
    if errors:
        console.print(f", [red]{errors} failed[/red]")
    else:
        console.print()
    console.print()
