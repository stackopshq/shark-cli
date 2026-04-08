"""``shark metric`` — query metrics & resources (Gnocchi)."""

from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from shark_cli.core.context import SharkContext
from shark_cli.core.validators import validate_id

console = Console()


def _gnocchi(client) -> str:
    return client.metric_url


# ══════════════════════════════════════════════════════════════════════════
#  Top-level group
# ══════════════════════════════════════════════════════════════════════════

@click.group()
@click.pass_context
def metric(ctx: click.Context) -> None:
    """Query metrics, measures & resources (Gnocchi)."""
    pass


# ══════════════════════════════════════════════════════════════════════════
#  Resource types
# ══════════════════════════════════════════════════════════════════════════

@metric.command("resource-type-list")
@click.pass_context
def resource_type_list(ctx: click.Context) -> None:
    """List resource types."""
    client = ctx.find_object(SharkContext).ensure_client()
    data = client.get(f"{_gnocchi(client)}/v1/resource_type")
    types = data if isinstance(data, list) else []
    if not types:
        console.print("[yellow]No resource types found.[/yellow]")
        return

    table = Table(title="Resource Types", show_lines=True)
    table.add_column("Name", style="bold cyan")
    table.add_column("Attributes")

    for rt in types:
        attrs = rt.get("attributes", {})
        attr_str = ", ".join(attrs.keys()) if attrs else "—"
        table.add_row(rt.get("name", ""), attr_str)
    console.print(table)


# ══════════════════════════════════════════════════════════════════════════
#  Resources
# ══════════════════════════════════════════════════════════════════════════

@metric.command("resource-list")
@click.option("--type", "resource_type", default="generic", show_default=True, help="Resource type to list.")
@click.option("--limit", "limit", type=int, default=None, help="Max results.")
@click.pass_context
def resource_list(ctx: click.Context, resource_type: str, limit: int | None) -> None:
    """List resources."""
    client = ctx.find_object(SharkContext).ensure_client()
    params = {}
    if limit:
        params["limit"] = limit
    data = client.get(f"{_gnocchi(client)}/v1/resource/{resource_type}", params=params)
    resources = data if isinstance(data, list) else []
    if not resources:
        console.print("[yellow]No resources found.[/yellow]")
        return

    table = Table(title=f"Resources ({resource_type})", show_lines=True)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Type", style="bold")
    table.add_column("Original ID")
    table.add_column("Started At")
    table.add_column("Metrics", justify="right")

    for r in resources:
        metrics = r.get("metrics", {})
        table.add_row(
            r.get("id", ""),
            r.get("type", ""),
            r.get("original_resource_id", "") or "—",
            str(r.get("started_at", ""))[:19],
            str(len(metrics)),
        )
    console.print(table)


@metric.command("resource-show")
@click.argument("resource_id", callback=validate_id)
@click.option("--type", "resource_type", default="generic", show_default=True, help="Resource type.")
@click.pass_context
def resource_show(ctx: click.Context, resource_id: str, resource_type: str) -> None:
    """Show resource details and its metrics."""
    client = ctx.find_object(SharkContext).ensure_client()
    data = client.get(f"{_gnocchi(client)}/v1/resource/{resource_type}/{resource_id}")

    table = Table(title=f"Resource {resource_id}", show_lines=True)
    table.add_column("Property", style="bold cyan")
    table.add_column("Value")

    for key in ["id", "type", "original_resource_id", "project_id", "user_id",
                "started_at", "ended_at", "revision_start", "revision_end"]:
        table.add_row(key, str(data.get(key, "")))

    metrics = data.get("metrics", {})
    if metrics:
        table.add_row("", "")
        table.add_row("[bold]── Metrics ──[/bold]", "")
        for name, mid in metrics.items():
            table.add_row(f"  {name}", str(mid))

    console.print(table)


# ══════════════════════════════════════════════════════════════════════════
#  Metrics
# ══════════════════════════════════════════════════════════════════════════

@metric.command("list")
@click.option("--limit", type=int, default=None, help="Max results.")
@click.pass_context
def metric_list(ctx: click.Context, limit: int | None) -> None:
    """List metrics."""
    client = ctx.find_object(SharkContext).ensure_client()
    params = {}
    if limit:
        params["limit"] = limit
    data = client.get(f"{_gnocchi(client)}/v1/metric", params=params)
    metrics = data if isinstance(data, list) else []
    if not metrics:
        console.print("[yellow]No metrics found.[/yellow]")
        return

    table = Table(title="Metrics", show_lines=True)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="bold")
    table.add_column("Unit")
    table.add_column("Archive Policy")
    table.add_column("Resource ID")

    for m in metrics:
        res = m.get("resource", {}) or {}
        table.add_row(
            m.get("id", ""),
            m.get("name", "") or "—",
            m.get("unit", "") or "—",
            m.get("archive_policy", {}).get("name", "") if isinstance(m.get("archive_policy"), dict) else str(m.get("archive_policy_name", "")),
            res.get("id", m.get("resource_id", "")) or "—",
        )
    console.print(table)


@metric.command("show")
@click.argument("metric_id", callback=validate_id)
@click.pass_context
def metric_show(ctx: click.Context, metric_id: str) -> None:
    """Show metric details."""
    client = ctx.find_object(SharkContext).ensure_client()
    data = client.get(f"{_gnocchi(client)}/v1/metric/{metric_id}")

    table = Table(title=f"Metric {data.get('name') or metric_id}", show_lines=True)
    table.add_column("Property", style="bold cyan")
    table.add_column("Value")

    for key in ["id", "name", "unit", "resource_id", "archive_policy_name", "created_by_user_id"]:
        table.add_row(key, str(data.get(key, "")))

    ap = data.get("archive_policy", {})
    if isinstance(ap, dict):
        table.add_row("archive_policy", ap.get("name", ""))
        defs = ap.get("definition", [])
        for d in defs:
            table.add_row(
                f"  granularity={d.get('granularity', '')}",
                f"points={d.get('points', '')} timespan={d.get('timespan', '')}",
            )

    console.print(table)


# ══════════════════════════════════════════════════════════════════════════
#  Measures
# ══════════════════════════════════════════════════════════════════════════

@metric.command("measures")
@click.argument("metric_id", callback=validate_id)
@click.option("--start", default=None, help="Start timestamp (ISO 8601 or relative e.g. -1h).")
@click.option("--stop", default=None, help="Stop timestamp.")
@click.option("--granularity", default=None, help="Granularity in seconds.")
@click.option("--aggregation", default="mean", show_default=True, help="Aggregation method.")
@click.option("--limit", type=int, default=None, help="Max measures to return.")
@click.pass_context
def metric_measures(ctx: click.Context, metric_id: str, start: str | None,
                    stop: str | None, granularity: str | None,
                    aggregation: str, limit: int | None) -> None:
    """Get measures (datapoints) for a metric.

    \b
    Examples:
      shark metric measures <metric-id> --start -1h
      shark metric measures <metric-id> --start 2026-04-01 --stop 2026-04-08 --granularity 3600
    """
    client = ctx.find_object(SharkContext).ensure_client()
    params: dict = {"aggregation": aggregation}
    if start:
        params["start"] = start
    if stop:
        params["stop"] = stop
    if granularity:
        params["granularity"] = granularity
    if limit:
        params["limit"] = limit

    data = client.get(f"{_gnocchi(client)}/v1/metric/{metric_id}/measures", params=params)
    measures = data if isinstance(data, list) else []
    if not measures:
        console.print("[yellow]No measures found.[/yellow]")
        return

    table = Table(title=f"Measures for {metric_id}", show_lines=False)
    table.add_column("Timestamp", style="cyan")
    table.add_column("Granularity", justify="right")
    table.add_column("Value", justify="right", style="bold")

    for m in measures:
        if isinstance(m, (list, tuple)) and len(m) >= 3:
            table.add_row(str(m[0]), str(m[1]), f"{m[2]:.4f}" if isinstance(m[2], float) else str(m[2]))
    console.print(table)


# ══════════════════════════════════════════════════════════════════════════
#  Archive Policies
# ══════════════════════════════════════════════════════════════════════════

@metric.command("archive-policy-list")
@click.pass_context
def archive_policy_list(ctx: click.Context) -> None:
    """List archive policies."""
    client = ctx.find_object(SharkContext).ensure_client()
    data = client.get(f"{_gnocchi(client)}/v1/archive_policy")
    policies = data if isinstance(data, list) else []
    if not policies:
        console.print("[yellow]No archive policies found.[/yellow]")
        return

    table = Table(title="Archive Policies", show_lines=True)
    table.add_column("Name", style="bold cyan")
    table.add_column("Back Window", justify="right")
    table.add_column("Aggregation Methods")
    table.add_column("Definition")

    for p in policies:
        methods = ", ".join(p.get("aggregation_methods", []))
        defs = p.get("definition", [])
        def_str = "; ".join(
            f"g={d.get('granularity','')}, pts={d.get('points','')}"
            for d in defs
        )
        table.add_row(
            p.get("name", ""),
            str(p.get("back_window", 0)),
            methods[:50] + ("…" if len(methods) > 50 else ""),
            def_str,
        )
    console.print(table)


@metric.command("status")
@click.pass_context
def metric_status(ctx: click.Context) -> None:
    """Show Gnocchi processing status."""
    client = ctx.find_object(SharkContext).ensure_client()
    data = client.get(f"{_gnocchi(client)}/v1/status")
    storage = data.get("storage", {})

    table = Table(title="Gnocchi Status", show_lines=True)
    table.add_column("Property", style="bold cyan")
    table.add_column("Value")

    table.add_row("measures_to_process", str(storage.get("summary", {}).get("measures", "")))
    table.add_row("metrics_having_measures", str(storage.get("summary", {}).get("metrics", "")))
    console.print(table)
