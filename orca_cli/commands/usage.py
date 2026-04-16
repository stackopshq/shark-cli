"""``orca usage`` — project resource usage report (Nova simple-tenant-usage)."""

from __future__ import annotations

import click

from orca_cli.core.context import OrcaContext
from orca_cli.core.output import console, output_options, print_list


@click.command()
@click.option("--start", default=None, help="Start date (YYYY-MM-DD). Default: 30 days ago.")
@click.option("--end", default=None, help="End date (YYYY-MM-DD). Default: today.")
@output_options
@click.pass_context
def usage(ctx: click.Context, start: str | None, end: str | None,
          output_format: str, columns: tuple[str, ...], fit_width: bool,
          max_width: int | None, noindent: bool) -> None:
    """Show project resource usage over a period.

    Displays per-server CPU hours, RAM hours, disk usage, and uptime
    from the Nova simple-tenant-usage API.

    \b
    Examples:
      orca usage
      orca usage --start 2026-04-01 --end 2026-04-14
    """
    from datetime import datetime, timedelta, timezone

    client = ctx.find_object(OrcaContext).ensure_client()

    now = datetime.now(timezone.utc)
    if end:
        end_dt = datetime.strptime(end, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    else:
        end_dt = now
    if start:
        start_dt = datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    else:
        start_dt = end_dt - timedelta(days=30)

    start_str = start_dt.strftime("%Y-%m-%dT00:00:00")
    end_str = end_dt.strftime("%Y-%m-%dT23:59:59")

    with console.status("[bold cyan]Fetching usage data…[/bold cyan]"):
        data = client.get(
            f"{client.compute_url}/os-simple-tenant-usage",
            params={"start": start_str, "end": end_str, "detailed": 1},
        )

    usages = data.get("tenant_usages", [])
    if not usages:
        console.print("[yellow]No usage data for this period.[/yellow]")
        return

    tenant = usages[0] if usages else {}

    # ── Summary ──────────────────────────────────────────────────────
    if output_format == "table":
        from rich.table import Table

        summary = Table(title=f"Usage Summary  ({start_dt.date()} → {end_dt.date()})", show_lines=False)
        summary.add_column("Metric", style="bold")
        summary.add_column("Value", justify="right", style="cyan")

        total_cpu_h = tenant.get("total_vcpus_usage", 0)
        total_ram_h = tenant.get("total_memory_mb_usage", 0)
        total_disk_h = tenant.get("total_local_gb_usage", 0)
        total_hours = tenant.get("total_hours", 0)

        summary.add_row("Total vCPU·hours", f"{total_cpu_h:.1f}")
        summary.add_row("Total RAM·hours (MB)", f"{total_ram_h:.1f}")
        summary.add_row("Total Disk·hours (GB)", f"{total_disk_h:.1f}")
        summary.add_row("Total Server·hours", f"{total_hours:.1f}")
        summary.add_row("Active Servers", str(len(tenant.get("server_usages", []))))

        console.print()
        console.print(summary)
        console.print()

    # ── Per-server breakdown ─────────────────────────────────────────
    server_usages = tenant.get("server_usages", [])

    rows = []
    for su in sorted(server_usages, key=lambda x: x.get("hours", 0), reverse=True):
        rows.append({
            "name": su.get("name", ""),
            "instance_id": su.get("instance_id", ""),
            "state": su.get("state", ""),
            "vcpus": su.get("vcpus", 0),
            "ram_mb": su.get("memory_mb", 0),
            "disk_gb": su.get("local_gb", 0),
            "hours": f"{su.get('hours', 0):.1f}",
            "started": str(su.get("started_at", ""))[:19],
            "ended": str(su.get("ended_at", "") or "—")[:19],
        })

    print_list(
        rows,
        [
            ("Name", "name", {"style": "bold"}),
            ("Instance ID", "instance_id", {"style": "cyan", "no_wrap": True}),
            ("State", "state", {"style": "green"}),
            ("vCPUs", "vcpus", {"justify": "right"}),
            ("RAM (MB)", "ram_mb", {"justify": "right"}),
            ("Disk (GB)", "disk_gb", {"justify": "right"}),
            ("Hours", "hours", {"justify": "right"}),
            ("Started", "started"),
            ("Ended", "ended"),
        ],
        title="Per-Server Usage",
        output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent,
        columns=columns,
        empty_msg="No per-server data.",
    )
