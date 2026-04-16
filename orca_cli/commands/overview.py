"""``orca overview`` — project dashboard (multi-service summary)."""

from __future__ import annotations

import click
from rich.table import Table

from orca_cli.core.context import OrcaContext
from orca_cli.core.output import console


@click.command()
@click.pass_context
def overview(ctx: click.Context) -> None:
    """Show a project dashboard — servers, quotas, volumes, IPs at a glance."""
    client = ctx.find_object(OrcaContext).ensure_client()

    with console.status("[bold cyan]Gathering project overview…[/bold cyan]"):
        # ── Servers (Nova) ───────────────────────────────────────────
        servers_data = client.get(f"{client.compute_url}/servers/detail", params={"limit": 1000})
        servers = servers_data.get("servers", [])

        status_counts: dict[str, int] = {}
        total_vcpus = 0
        total_ram = 0
        for s in servers:
            st = s.get("status", "UNKNOWN")
            status_counts[st] = status_counts.get(st, 0) + 1
            flv = s.get("flavor", {})
            total_vcpus += flv.get("vcpus", 0)
            total_ram += flv.get("ram", 0)

        # ── Volumes (Cinder) ─────────────────────────────────────────
        volumes_data = client.get(f"{client.volume_url}/volumes/detail")
        volumes = volumes_data.get("volumes", [])
        total_vol_gb = sum(v.get("size", 0) for v in volumes)
        vol_status: dict[str, int] = {}
        for v in volumes:
            st = v.get("status", "unknown")
            vol_status[st] = vol_status.get(st, 0) + 1

        # ── Floating IPs (Neutron) ───────────────────────────────────
        fips_data = client.get(f"{client.network_url}/v2.0/floatingips")
        fips = fips_data.get("floatingips", [])
        fips_in_use = sum(1 for f in fips if f.get("port_id"))
        fips_free = len(fips) - fips_in_use

        # ── Networks / Subnets / Routers (Neutron) ───────────────────
        nets = client.get(f"{client.network_url}/v2.0/networks").get("networks", [])
        subnets = client.get(f"{client.network_url}/v2.0/subnets").get("subnets", [])
        routers = client.get(f"{client.network_url}/v2.0/routers").get("routers", [])

        # ── Security Groups (Neutron) ────────────────────────────────
        sgs = client.get(f"{client.network_url}/v2.0/security-groups").get("security_groups", [])

        # ── Key Pairs (Nova) ─────────────────────────────────────────
        kps = client.get(f"{client.compute_url}/os-keypairs").get("keypairs", [])

        # ── Images (Glance) ──────────────────────────────────────────
        images = client.get(f"{client.image_url}/v2/images").get("images", [])

    # ── Render ────────────────────────────────────────────────────────
    console.print()

    # Servers
    table = Table(title="Servers", show_lines=False)
    table.add_column("Status", style="bold")
    table.add_column("Count", justify="right", style="cyan")
    for st in sorted(status_counts):
        style = "green" if st == "ACTIVE" else "yellow" if st == "SHUTOFF" else "red" if "ERROR" in st else ""
        table.add_row(f"[{style}]{st}[/{style}]" if style else st, str(status_counts[st]))
    table.add_row("[bold]Total[/bold]", f"[bold]{len(servers)}[/bold]")
    console.print(table)

    # Resources
    console.print()
    res = Table(title="Resource Usage", show_lines=False)
    res.add_column("Resource", style="bold")
    res.add_column("Used", justify="right", style="cyan")
    res.add_row("vCPUs", str(total_vcpus))
    res.add_row("RAM", f"{total_ram} MB" if total_ram < 1024 else f"{total_ram / 1024:.1f} GB")
    res.add_row("Volumes", f"{len(volumes)} ({total_vol_gb} GB)")
    res.add_row("Floating IPs", f"{len(fips)} ({fips_in_use} in use, {fips_free} free)")
    console.print(res)

    # Networking
    console.print()
    net_table = Table(title="Networking", show_lines=False)
    net_table.add_column("Resource", style="bold")
    net_table.add_column("Count", justify="right", style="cyan")
    net_table.add_row("Networks", str(len(nets)))
    net_table.add_row("Subnets", str(len(subnets)))
    net_table.add_row("Routers", str(len(routers)))
    net_table.add_row("Security Groups", str(len(sgs)))
    net_table.add_row("Key Pairs", str(len(kps)))
    net_table.add_row("Images", str(len(images)))
    console.print(net_table)
    console.print()
