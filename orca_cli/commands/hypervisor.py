"""``orca hypervisor`` — manage hypervisors (Nova)."""

from __future__ import annotations

import click

from orca_cli.core.context import OrcaContext
from orca_cli.core.output import output_options, print_detail, print_list


def _nova(client) -> str:
    return client.compute_url


@click.group()
@click.pass_context
def hypervisor(ctx: click.Context) -> None:
    """Manage hypervisors (Nova)."""
    pass


@hypervisor.command("list")
@output_options
@click.pass_context
def hypervisor_list(ctx, output_format, columns, fit_width, max_width, noindent):
    """List hypervisors."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_nova(client)}/os-hypervisors/detail")
    print_list(
        data.get("hypervisors", []),
        [
            ("ID", "id", {"style": "cyan"}),
            ("Hostname", "hypervisor_hostname", {"style": "bold"}),
            ("Type", "hypervisor_type"),
            ("State", lambda h: f"[green]{h.get('state')}[/green]" if h.get("state") == "up" else f"[red]{h.get('state')}[/red]"),
            ("Status", lambda h: f"[green]{h.get('status')}[/green]" if h.get("status") == "enabled" else f"[yellow]{h.get('status')}[/yellow]"),
            ("vCPUs", lambda h: f"{h.get('vcpus_used', 0)}/{h.get('vcpus', 0)}", {"justify": "right"}),
            ("RAM used/total (MB)", lambda h: f"{h.get('memory_mb_used', 0)}/{h.get('memory_mb', 0)}", {"justify": "right"}),
            ("Running VMs", "running_vms", {"justify": "right"}),
        ],
        title="Hypervisors",
        output_format=output_format, columns=columns,
        fit_width=fit_width, max_width=max_width, noindent=noindent,
        empty_msg="No hypervisors found.",
    )


@hypervisor.command("show")
@click.argument("hypervisor_id")
@output_options
@click.pass_context
def hypervisor_show(ctx, hypervisor_id, output_format, columns, fit_width, max_width, noindent):
    """Show hypervisor details."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_nova(client)}/os-hypervisors/{hypervisor_id}")
    h = data.get("hypervisor", data)
    print_detail(
        [
            ("ID", str(h.get("id", ""))),
            ("Hostname", h.get("hypervisor_hostname", "")),
            ("Type", h.get("hypervisor_type", "")),
            ("Version", str(h.get("hypervisor_version", ""))),
            ("State", h.get("state", "")),
            ("Status", h.get("status", "")),
            ("Host IP", h.get("host_ip", "")),
            ("vCPUs (used/total)", f"{h.get('vcpus_used', 0)}/{h.get('vcpus', 0)}"),
            ("RAM used (MB)", str(h.get("memory_mb_used", 0))),
            ("RAM total (MB)", str(h.get("memory_mb", 0))),
            ("Disk used (GB)", str(h.get("local_gb_used", 0))),
            ("Disk total (GB)", str(h.get("local_gb", 0))),
            ("Running VMs", str(h.get("running_vms", 0))),
            ("Current Workload", str(h.get("current_workload", 0))),
        ],
        output_format=output_format, columns=columns,
        fit_width=fit_width, max_width=max_width, noindent=noindent,
    )


@hypervisor.command("stats")
@click.pass_context
def hypervisor_stats(ctx):
    """Show aggregated hypervisor statistics."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_nova(client)}/os-hypervisors/statistics")
    stats = data.get("hypervisor_statistics", data)

    from rich.table import Table
    table = Table(title="Hypervisor Statistics", show_header=False)
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")

    for k, v in stats.items():
        table.add_row(k.replace("_", " ").title(), str(v))

    from orca_cli.core.output import console as _console
    _console.print(table)


def _pct(used: int, total: int) -> float:
    if not total:
        return 0.0
    return round(100.0 * used / total, 1)


def _color_pct(p: float) -> str:
    if p >= 90:
        return f"[red bold]{p}%[/red bold]"
    if p >= 70:
        return f"[yellow]{p}%[/yellow]"
    return f"[green]{p}%[/green]"


def _bar(p: float, width: int = 8) -> str:
    filled = max(0, min(width, int(p * width / 100)))
    color = "red" if p >= 90 else ("yellow" if p >= 70 else "green")
    return f"[{color}]{'█' * filled}[/{color}]{'░' * (width - filled)}"


@hypervisor.command("usage")
@click.option("--sort-by", type=click.Choice(["cpu", "ram", "disk", "max", "vms"]),
              default="max", show_default=True,
              help="Metric to sort by. 'max' picks the worst of CPU/RAM/disk per host.")
@click.option("--reverse", is_flag=True,
              help="Sort least-loaded first (default: most-loaded first).")
@click.option("--threshold", type=click.IntRange(0, 100), default=0, show_default=True,
              help="Only show hypervisors whose 'max' fill rate is ≥ this percentage.")
@click.option("--top", "top_n", type=int, default=None,
              help="Show only the top N hypervisors after sorting.")
@output_options
@click.pass_context
def hypervisor_usage(ctx, sort_by, reverse, threshold, top_n,
                     output_format, columns, fit_width, max_width, noindent):
    """Show fill rate per hypervisor, sorted by load.

    Combines vCPU, RAM and disk usage into a per-host 'score' (the worst
    dimension) so the most-saturated hypervisors surface at the top.

    \b
    Color thresholds:
      Green  < 70%   — comfortable headroom
      Yellow 70–90%  — monitor closely
      Red    ≥ 90%   — critical
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_nova(client)}/os-hypervisors/detail")
    hypervisors = data.get("hypervisors", [])

    enriched = []
    for h in hypervisors:
        cpu = _pct(h.get("vcpus_used", 0), h.get("vcpus", 0))
        ram = _pct(h.get("memory_mb_used", 0), h.get("memory_mb", 0))
        disk = _pct(h.get("local_gb_used", 0), h.get("local_gb", 0))
        enriched.append({
            **h,
            "_cpu_pct": cpu,
            "_ram_pct": ram,
            "_disk_pct": disk,
            "_max_pct": max(cpu, ram, disk),
        })

    if threshold:
        enriched = [h for h in enriched if h["_max_pct"] >= threshold]

    sort_key = {"cpu": "_cpu_pct", "ram": "_ram_pct", "disk": "_disk_pct",
                "max": "_max_pct", "vms": "running_vms"}[sort_by]
    enriched.sort(key=lambda h: h.get(sort_key, 0) or 0, reverse=not reverse)

    if top_n is not None and top_n > 0:
        enriched = enriched[:top_n]

    print_list(
        enriched,
        [
            ("Hostname", "hypervisor_hostname", {"style": "bold"}),
            ("State", lambda h: f"[green]{h.get('state')}[/green]" if h.get("state") == "up"
                                else f"[red]{h.get('state')}[/red]"),
            ("vCPU", lambda h: f"{h.get('vcpus_used', 0)}/{h.get('vcpus', 0)}",
             {"justify": "right"}),
            ("CPU%", lambda h: f"{_bar(h['_cpu_pct'])} {_color_pct(h['_cpu_pct'])}"),
            ("RAM (GB)", lambda h: f"{h.get('memory_mb_used', 0)//1024}/{h.get('memory_mb', 0)//1024}",
             {"justify": "right"}),
            ("RAM%", lambda h: f"{_bar(h['_ram_pct'])} {_color_pct(h['_ram_pct'])}"),
            ("Disk (GB)", lambda h: f"{h.get('local_gb_used', 0)}/{h.get('local_gb', 0)}",
             {"justify": "right"}),
            ("Disk%", lambda h: f"{_bar(h['_disk_pct'])} {_color_pct(h['_disk_pct'])}"),
            ("VMs", "running_vms", {"justify": "right"}),
            ("Score", lambda h: _color_pct(h["_max_pct"])),
        ],
        title="Hypervisor Usage (sorted by " + sort_by + ")",
        output_format=output_format, columns=columns,
        fit_width=fit_width, max_width=max_width, noindent=noindent,
        empty_msg="No hypervisors match the filter.",
    )
