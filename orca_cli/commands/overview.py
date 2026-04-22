"""``orca overview`` — project dashboard (multi-service summary)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable

import click
from rich.table import Table

from orca_cli.core.context import OrcaContext
from orca_cli.core.output import console
from orca_cli.services.compute import ComputeService
from orca_cli.services.image import ImageService
from orca_cli.services.network import NetworkService
from orca_cli.services.server import ServerService
from orca_cli.services.volume import VolumeService


@click.command()
@click.pass_context
def overview(ctx: click.Context) -> None:
    """Show a project dashboard — servers, quotas, volumes, IPs at a glance."""
    client = ctx.find_object(OrcaContext).ensure_client()
    net_svc = NetworkService(client)
    compute_svc = ComputeService(client)
    server_svc = ServerService(client)
    volume_svc = VolumeService(client)

    fetchers: dict[str, Callable[[], list[Any]]] = {
        "servers": server_svc.find_all,
        "volumes": volume_svc.find_all,
        "fips": lambda: net_svc.find_all_floating_ips(),
        "nets": lambda: net_svc.find_all(),
        "subnets": lambda: net_svc.find_all_subnets(),
        "routers": lambda: net_svc.find_all_routers(),
        "sgs": lambda: net_svc.find_all_security_groups(),
        "kps": compute_svc.find_keypairs,
        "images": lambda: ImageService(client).find_all(),
    }

    with console.status("[bold cyan]Gathering project overview…[/bold cyan]"):
        results: dict[str, list] = {}
        with ThreadPoolExecutor(max_workers=len(fetchers)) as pool:
            future_map = {pool.submit(fn): name for name, fn in fetchers.items()}
            for fut in as_completed(future_map):
                name = future_map[fut]
                try:
                    results[name] = fut.result()
                except Exception:
                    results[name] = []

    servers = results["servers"]
    volumes = results["volumes"]
    fips = results["fips"]
    nets = results["nets"]
    subnets = results["subnets"]
    routers = results["routers"]
    sgs = results["sgs"]
    kps = results["kps"]
    images = results["images"]

    status_counts: dict[str, int] = {}
    total_vcpus = 0
    total_ram = 0
    for s in servers:
        st = s.get("status", "UNKNOWN")
        status_counts[st] = status_counts.get(st, 0) + 1
        flv = s.get("flavor", {})
        total_vcpus += flv.get("vcpus", 0)
        total_ram += flv.get("ram", 0)

    total_vol_gb = sum(v.get("size", 0) for v in volumes)
    fips_in_use = sum(1 for f in fips if f.get("port_id"))
    fips_free = len(fips) - fips_in_use

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
