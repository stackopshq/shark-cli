"""``orca metric`` — query metrics & resources (Gnocchi)."""

from __future__ import annotations

import click

from orca_cli.core.context import OrcaContext
from orca_cli.core.output import output_options, print_list, print_detail, console
from orca_cli.core.validators import validate_id


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
@output_options
@click.pass_context
def resource_type_list(ctx: click.Context, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List resource types."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_gnocchi(client)}/v1/resource_type")
    types = data if isinstance(data, list) else []

    print_list(
        types,
        [
            ("Name", "name", {"style": "bold cyan"}),
            ("Attributes", lambda rt: ", ".join(rt.get("attributes", {}).keys()) if rt.get("attributes") else "—"),
        ],
        title="Resource Types",
        output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent,
        columns=columns,
        empty_msg="No resource types found.",
    )


# ══════════════════════════════════════════════════════════════════════════
#  Resources
# ══════════════════════════════════════════════════════════════════════════

@metric.command("resource-list")
@click.option("--type", "resource_type", default="generic", show_default=True, help="Resource type to list.")
@click.option("--limit", "limit", type=int, default=100, show_default=True,
              help="Max results. Gnocchi can return very large datasets without a limit.")
@output_options
@click.pass_context
def resource_list(ctx: click.Context, resource_type: str, limit: int,
                  output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List resources."""
    client = ctx.find_object(OrcaContext).ensure_client()
    params: dict = {"limit": limit}
    data = client.get(f"{_gnocchi(client)}/v1/resource/{resource_type}", params=params)
    resources = data if isinstance(data, list) else []

    print_list(
        resources,
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Type", "type", {"style": "bold"}),
            ("Original ID", lambda r: r.get("original_resource_id", "") or "—"),
            ("Started At", lambda r: str(r.get("started_at", ""))[:19]),
            ("Metrics", lambda r: str(len(r.get("metrics", {}))), {"justify": "right"}),
        ],
        title=f"Resources ({resource_type})",
        output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent,
        columns=columns,
        empty_msg="No resources found.",
    )


@metric.command("resource-show")
@click.argument("resource_id", callback=validate_id)
@click.option("--type", "resource_type", default="generic", show_default=True, help="Resource type.")
@output_options
@click.pass_context
def resource_show(ctx: click.Context, resource_id: str, resource_type: str,
                  output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show resource details and its metrics."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_gnocchi(client)}/v1/resource/{resource_type}/{resource_id}")

    fields: list[tuple[str, str]] = []
    for key in ["id", "type", "original_resource_id", "project_id", "user_id",
                "started_at", "ended_at", "revision_start", "revision_end"]:
        fields.append((key, str(data.get(key, ""))))

    metrics = data.get("metrics", {})
    if metrics:
        fields.append(("", ""))
        fields.append(("── Metrics ──", ""))
        for name, mid in metrics.items():
            fields.append((f"  {name}", str(mid)))

    print_detail(fields, output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent, columns=columns)


# ══════════════════════════════════════════════════════════════════════════
#  Metrics
# ══════════════════════════════════════════════════════════════════════════

@metric.command("list")
@click.option("--limit", type=int, default=None, help="Max results.")
@output_options
@click.pass_context
def metric_list(ctx: click.Context, limit: int | None,
                output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List metrics."""
    client = ctx.find_object(OrcaContext).ensure_client()
    params = {}
    if limit:
        params["limit"] = limit
    data = client.get(f"{_gnocchi(client)}/v1/metric", params=params)
    metrics = data if isinstance(data, list) else []

    print_list(
        metrics,
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Name", lambda m: m.get("name", "") or "—", {"style": "bold"}),
            ("Unit", lambda m: m.get("unit", "") or "—"),
            ("Archive Policy", lambda m: (
                m.get("archive_policy", {}).get("name", "")
                if isinstance(m.get("archive_policy"), dict)
                else str(m.get("archive_policy_name", ""))
            )),
            ("Resource ID", lambda m: (m.get("resource", {}) or {}).get("id", m.get("resource_id", "")) or "—"),
        ],
        title="Metrics",
        output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent,
        columns=columns,
        empty_msg="No metrics found.",
    )


@metric.command("show")
@click.argument("metric_id", callback=validate_id)
@output_options
@click.pass_context
def metric_show(ctx: click.Context, metric_id: str,
                output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show metric details."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_gnocchi(client)}/v1/metric/{metric_id}")

    fields: list[tuple[str, str]] = []
    for key in ["id", "name", "unit", "resource_id", "archive_policy_name", "created_by_user_id"]:
        fields.append((key, str(data.get(key, ""))))

    ap = data.get("archive_policy", {})
    if isinstance(ap, dict):
        fields.append(("archive_policy", ap.get("name", "")))
        for d in ap.get("definition", []):
            fields.append((
                f"  granularity={d.get('granularity', '')}",
                f"points={d.get('points', '')} timespan={d.get('timespan', '')}",
            ))

    print_detail(fields, output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent, columns=columns)


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
@output_options
@click.pass_context
def metric_measures(ctx: click.Context, metric_id: str, start: str | None,
                    stop: str | None, granularity: str | None,
                    aggregation: str, limit: int | None,
                    output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Get measures (datapoints) for a metric.

    \b
    Examples:
      orca metric measures <metric-id> --start -1h
      orca metric measures <metric-id> --start 2026-04-01 --stop 2026-04-08 --granularity 3600
    """
    client = ctx.find_object(OrcaContext).ensure_client()
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

    # Filter to valid measure entries only
    measures = [m for m in measures if isinstance(m, (list, tuple)) and len(m) >= 3]

    print_list(
        measures,
        [
            ("Timestamp", lambda m: str(m[0]), {"style": "cyan"}),
            ("Granularity", lambda m: str(m[1]), {"justify": "right"}),
            ("Value", lambda m: f"{m[2]:.4f}" if isinstance(m[2], float) else str(m[2]), {"justify": "right", "style": "bold"}),
        ],
        title=f"Measures for {metric_id}",
        output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent,
        columns=columns,
        empty_msg="No measures found.",
    )


# ══════════════════════════════════════════════════════════════════════════
#  Archive Policies
# ══════════════════════════════════════════════════════════════════════════

@metric.command("archive-policy-list")
@output_options
@click.pass_context
def archive_policy_list(ctx: click.Context, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List archive policies."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_gnocchi(client)}/v1/archive_policy")
    policies = data if isinstance(data, list) else []

    print_list(
        policies,
        [
            ("Name", "name", {"style": "bold cyan"}),
            ("Back Window", lambda p: str(p.get("back_window", 0)), {"justify": "right"}),
            ("Aggregation Methods", lambda p: (
                lambda methods: methods[:50] + ("…" if len(methods) > 50 else "")
            )(", ".join(p.get("aggregation_methods", [])))),
            ("Definition", lambda p: "; ".join(
                f"g={d.get('granularity', '')}, pts={d.get('points', '')}"
                for d in p.get("definition", [])
            )),
        ],
        title="Archive Policies",
        output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent,
        columns=columns,
        empty_msg="No archive policies found.",
    )


@metric.command("status")
@output_options
@click.pass_context
def metric_status(ctx: click.Context, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show Gnocchi processing status."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_gnocchi(client)}/v1/status")
    storage = data.get("storage", {})

    fields: list[tuple[str, str]] = [
        ("measures_to_process", str(storage.get("summary", {}).get("measures", ""))),
        ("metrics_having_measures", str(storage.get("summary", {}).get("metrics", ""))),
    ]

    print_detail(fields, output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent, columns=columns)


# ══════════════════════════════════════════════════════════════════════════
#  Metric create / delete / measures-add
# ══════════════════════════════════════════════════════════════════════════

@metric.command("create")
@click.option("--name", required=True, help="Metric name.")
@click.option("--archive-policy-name", default=None,
              help="Archive policy to use (default: low).")
@click.option("--resource-id", default=None,
              help="Resource ID to attach the metric to.")
@click.pass_context
def metric_create(ctx: click.Context, name: str, archive_policy_name: str | None,
                  resource_id: str | None) -> None:
    """Create a Gnocchi metric."""
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {"name": name}
    if archive_policy_name:
        body["archive_policy_name"] = archive_policy_name
    if resource_id:
        body["resource_id"] = resource_id
    m = client.post(f"{_gnocchi(client)}/v1/metric", json=body)
    console.print(f"[green]Metric '{name}' created: {m.get('id', '?')}[/green]")


@metric.command("delete")
@click.argument("metric_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def metric_delete(ctx: click.Context, metric_id: str, yes: bool) -> None:
    """Delete a Gnocchi metric."""
    if not yes:
        click.confirm(f"Delete metric {metric_id}?", abort=True)
    client = ctx.find_object(OrcaContext).ensure_client()
    client.delete(f"{_gnocchi(client)}/v1/metric/{metric_id}")
    console.print(f"[green]Metric {metric_id} deleted.[/green]")


@metric.command("measures-add")
@click.argument("metric_id")
@click.option("--measure", "measures", required=True, multiple=True,
              metavar="TIMESTAMP:VALUE",
              help="Measure as timestamp:value (repeatable). Timestamp: ISO-8601.")
@click.pass_context
def metric_measures_add(ctx: click.Context, metric_id: str,
                        measures: tuple[str, ...]) -> None:
    """Push measures to a metric.

    \b
    Example:
      orca metric measures-add <metric-id> \\
        --measure 2026-01-01T00:00:00:42.5
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    payload = []
    for m in measures:
        if ":" not in m:
            raise click.UsageError(f"Invalid format '{m}', expected TIMESTAMP:VALUE.")
        ts, val = m.rsplit(":", 1)
        payload.append({"timestamp": ts, "value": float(val)})
    client.post(f"{_gnocchi(client)}/v1/metric/{metric_id}/measures", json=payload)
    console.print(f"[green]{len(payload)} measure(s) posted to metric {metric_id}.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  Archive Policy CRUD
# ══════════════════════════════════════════════════════════════════════════

@metric.command("archive-policy-show")
@click.argument("name")
@output_options
@click.pass_context
def archive_policy_show(ctx: click.Context, name: str, output_format: str,
                        columns: tuple[str, ...], fit_width: bool,
                        max_width: int | None, noindent: bool) -> None:
    """Show an archive policy."""
    client = ctx.find_object(OrcaContext).ensure_client()
    p = client.get(f"{_gnocchi(client)}/v1/archive_policy/{name}")
    fields = [
        ("Name", str(p.get("name", ""))),
        ("Definition", str(p.get("definition", []))),
        ("Aggregation Methods", ", ".join(p.get("aggregation_methods", []))),
        ("Back Window", str(p.get("back_window", 0))),
    ]
    print_detail(fields, output_format=output_format, fit_width=fit_width,
                 max_width=max_width, noindent=noindent, columns=columns)


@metric.command("archive-policy-create")
@click.argument("name")
@click.option("--definition", "definitions", required=True, multiple=True,
              metavar="GRANULARITY:POINTS",
              help="Granularity:points pair (repeatable). E.g. 1m:1440.")
@click.option("--aggregation-method", "agg_methods", multiple=True,
              help="Aggregation method (repeatable).")
@click.pass_context
def archive_policy_create(ctx: click.Context, name: str,
                          definitions: tuple[str, ...],
                          agg_methods: tuple[str, ...]) -> None:
    """Create an archive policy.

    \b
    Example:
      orca metric archive-policy-create my-policy \\
        --definition 1m:1440 --definition 1h:720
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    defs = []
    for d in definitions:
        if ":" not in d:
            raise click.UsageError(f"Invalid definition '{d}', expected GRANULARITY:POINTS.")
        gran, pts = d.split(":", 1)
        defs.append({"granularity": gran, "points": int(pts)})
    body: dict = {"name": name, "definition": defs}
    if agg_methods:
        body["aggregation_methods"] = list(agg_methods)
    client.post(f"{_gnocchi(client)}/v1/archive_policy", json=body)
    console.print(f"[green]Archive policy '{name}' created.[/green]")


@metric.command("archive-policy-delete")
@click.argument("name")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def archive_policy_delete(ctx: click.Context, name: str, yes: bool) -> None:
    """Delete an archive policy."""
    if not yes:
        click.confirm(f"Delete archive policy '{name}'?", abort=True)
    client = ctx.find_object(OrcaContext).ensure_client()
    client.delete(f"{_gnocchi(client)}/v1/archive_policy/{name}")
    console.print(f"[green]Archive policy '{name}' deleted.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  Resource Type CRUD
# ══════════════════════════════════════════════════════════════════════════

@metric.command("resource-type-show")
@click.argument("resource_type")
@output_options
@click.pass_context
def resource_type_show(ctx: click.Context, resource_type: str, output_format: str,
                       columns: tuple[str, ...], fit_width: bool,
                       max_width: int | None, noindent: bool) -> None:
    """Show a Gnocchi resource type."""
    client = ctx.find_object(OrcaContext).ensure_client()
    t = client.get(f"{_gnocchi(client)}/v1/resource_type/{resource_type}")
    fields = [
        ("Name", str(t.get("name", ""))),
        ("Attributes", str(t.get("attributes", {}))),
    ]
    print_detail(fields, output_format=output_format, fit_width=fit_width,
                 max_width=max_width, noindent=noindent, columns=columns)


@metric.command("resource-type-create")
@click.argument("name")
@click.option("--attribute", "attributes", multiple=True, metavar="KEY:TYPE",
              help="Resource attribute key:type (repeatable). E.g. host:string.")
@click.pass_context
def resource_type_create(ctx: click.Context, name: str,
                         attributes: tuple[str, ...]) -> None:
    """Create a Gnocchi resource type."""
    client = ctx.find_object(OrcaContext).ensure_client()
    attrs: dict = {}
    for a in attributes:
        if ":" not in a:
            raise click.UsageError(f"Invalid attribute '{a}', expected KEY:TYPE.")
        k, t = a.split(":", 1)
        attrs[k] = {"type": t}
    body: dict = {"name": name, "attributes": attrs}
    client.post(f"{_gnocchi(client)}/v1/resource_type", json=body)
    console.print(f"[green]Resource type '{name}' created.[/green]")


@metric.command("resource-type-delete")
@click.argument("resource_type")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def resource_type_delete(ctx: click.Context, resource_type: str, yes: bool) -> None:
    """Delete a Gnocchi resource type."""
    if not yes:
        click.confirm(f"Delete resource type '{resource_type}'?", abort=True)
    client = ctx.find_object(OrcaContext).ensure_client()
    client.delete(f"{_gnocchi(client)}/v1/resource_type/{resource_type}")
    console.print(f"[green]Resource type '{resource_type}' deleted.[/green]")
