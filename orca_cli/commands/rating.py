"""``orca rating`` — manage CloudKitty rating (modules, pricing, summary, quote)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import click

from orca_cli.core.context import OrcaContext
from orca_cli.core.output import console, output_options, print_detail, print_list
from orca_cli.core.validators import validate_id


def _url(client) -> str:
    return client.rating_url


def _parse_iso(value: str | None) -> str | None:
    """Pass through an ISO 8601 string; leave validation to the server."""
    return value


def _default_window() -> tuple[str, str]:
    """Default window: start of current month → now (UTC)."""
    now = datetime.now(timezone.utc)
    begin = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return begin.isoformat(), now.isoformat()


# ── Root group ────────────────────────────────────────────────────────────────

@click.group()
@click.pass_context
def rating(ctx: click.Context) -> None:
    """Manage CloudKitty rating."""


# ══════════════════════════════════════════════════════════════════════════════
#  rating info / metric-list / metric-show
# ══════════════════════════════════════════════════════════════════════════════

@rating.command("info")
@click.pass_context
def rating_info(ctx: click.Context) -> None:
    """Show CloudKitty configuration (collector, metrics, fetcher)."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_url(client)}/v1/info/config")
    console.print_json(json.dumps(data, indent=2))


@rating.command("metric-list")
@output_options
@click.pass_context
def rating_metric_list(ctx, output_format, columns, fit_width, max_width, noindent):
    """List metrics that CloudKitty is configured to rate."""
    client = ctx.find_object(OrcaContext).ensure_client()
    items = client.get(f"{_url(client)}/v1/info/metrics").get("metrics", [])
    col_defs = [
        ("Metric", "metric_id", {"style": "bold"}),
        ("Unit", "unit"),
        ("Metadata", lambda m: ", ".join(m.get("metadata", []))),
    ]
    print_list(items, col_defs, title="Rated metrics",
               output_format=output_format, columns=columns,
               fit_width=fit_width, max_width=max_width, noindent=noindent)


@rating.command("metric-show")
@click.argument("metric_id")
@output_options
@click.pass_context
def rating_metric_show(ctx, metric_id, output_format, columns, fit_width, max_width, noindent):
    """Show collection details for a rated metric."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_url(client)}/v1/info/metrics/{metric_id}")
    fields = [
        ("Metric", data.get("metric_id", "")),
        ("Unit", data.get("unit", "")),
        ("Metadata", ", ".join(data.get("metadata", []))),
    ]
    print_detail(fields, output_format=output_format, columns=columns,
                 fit_width=fit_width, max_width=max_width, noindent=noindent)


# ══════════════════════════════════════════════════════════════════════════════
#  rating summary / dataframes
# ══════════════════════════════════════════════════════════════════════════════

@rating.command("summary")
@click.option("--begin", default=None, metavar="ISO8601",
              help="Start of the rating window. Defaults to start of current month.")
@click.option("--end", default=None, metavar="ISO8601",
              help="End of the rating window. Defaults to now.")
@click.option("--groupby", multiple=True,
              help="Group results by field (repeatable). Common: type, project_id, user_id.")
@click.option("--filters", multiple=True, metavar="KEY=VALUE",
              help="Filter results (repeatable).")
@output_options
@click.pass_context
def rating_summary(ctx, begin, end, groupby, filters,
                   output_format, columns, fit_width, max_width, noindent):
    """Show rating summary (total cost per resource type / project / …).

    \b
    Examples:
      orca rating summary
      orca rating summary --groupby type
      orca rating summary --begin 2026-01-01T00:00:00 --end 2026-02-01T00:00:00 --groupby project_id
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    if not begin and not end:
        begin, end = _default_window()
    params: dict = {}
    if begin:
        params["begin"] = _parse_iso(begin)
    if end:
        params["end"] = _parse_iso(end)
    if groupby:
        params["groupby"] = list(groupby)
    for f in filters:
        if "=" not in f:
            raise click.BadParameter(f"Expected KEY=VALUE, got '{f}'", param_hint="--filters")
        k, v = f.split("=", 1)
        params[f"filters[{k}]"] = v

    data = client.get(f"{_url(client)}/v2/summary", params=params)
    results = data.get("results", []) or []
    cols = data.get("columns", []) or []
    if not results:
        console.print("No rating data for the given window.")
        return

    items = [dict(zip(cols, row)) for row in results]
    col_defs = [(c.title(), c) for c in cols]
    print_list(items, col_defs, title=f"Rating summary ({data.get('total', len(results))} row(s))",
               output_format=output_format, columns=columns,
               fit_width=fit_width, max_width=max_width, noindent=noindent)


@rating.command("dataframes")
@click.option("--begin", default=None, metavar="ISO8601")
@click.option("--end", default=None, metavar="ISO8601")
@click.option("--limit", type=int, default=None, help="Max dataframes to return.")
@click.pass_context
def rating_dataframes(ctx, begin, end, limit):
    """Show raw rated dataframes (historical cost records).

    Falls back to v1 storage if the v2 endpoint is not exposed.
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    if not begin and not end:
        # Tighter default than summary: last 24 h, dataframes can be huge.
        now = datetime.now(timezone.utc)
        begin = (now - timedelta(days=1)).isoformat()
        end = now.isoformat()

    params: dict = {}
    if begin:
        params["begin"] = begin
    if end:
        params["end"] = end
    if limit:
        params["limit"] = limit

    # v2 is the preferred API but many clouds (e.g. Infomaniak) only expose
    # the v1 storage endpoint. Try v2, fall back to v1 on 404.
    try:
        data = client.get(f"{_url(client)}/v2/dataframes", params=params)
    except Exception:
        data = client.get(f"{_url(client)}/v1/storage/dataframes", params=params)

    frames = data.get("dataframes", []) or data.get("results", [])
    if not frames:
        console.print("No dataframes in the given window.")
        return
    console.print_json(json.dumps(frames, indent=2, default=str))


# ══════════════════════════════════════════════════════════════════════════════
#  rating quote — pre-deployment cost estimate
# ══════════════════════════════════════════════════════════════════════════════

@rating.command("quote")
@click.option("--resource", "resources", required=True, multiple=True,
              metavar="JSON",
              help='Resource JSON, e.g. \'{"service":"instance","desc":{"flavor":"m1.small"},"volume":"1"}\' (repeatable).')
@click.pass_context
def rating_quote(ctx, resources):
    """Get a price estimate for a set of resources (pre-deployment).

    Sends a ``quote`` request to CloudKitty's rating engine. The payload
    format mirrors a rated dataframe: each ``--resource`` is one line
    item (service + metadata + volume).

    \b
    Example:
      orca rating quote --resource '{"service":"instance","desc":{"flavor_id":"2"},"volume":"1"}'
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    body_items: list[dict] = []
    for raw in resources:
        try:
            body_items.append(json.loads(raw))
        except json.JSONDecodeError as exc:
            raise click.BadParameter(f"Invalid JSON: {exc}", param_hint="--resource")
    payload = {"resources": body_items}
    data = client.post(f"{_url(client)}/v1/rating/quote", json=payload)
    if isinstance(data, (int, float, str)):
        console.print(f"Estimated price: [bold]{data}[/bold]")
    else:
        console.print_json(json.dumps(data, indent=2, default=str))


# ══════════════════════════════════════════════════════════════════════════════
#  rating modules (admin)
# ══════════════════════════════════════════════════════════════════════════════

@rating.command("module-list")
@output_options
@click.pass_context
def rating_module_list(ctx, output_format, columns, fit_width, max_width, noindent):
    """List rating modules (hashmap, pyscripts, noop, …). Admin only."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_url(client)}/v1/rating/modules")
    items = data.get("modules", []) if isinstance(data, dict) else data
    col_defs = [
        ("Module", "module_id", {"style": "bold"}),
        ("Enabled", "enabled"),
        ("Priority", "priority", {"justify": "right"}),
        ("Description", "description"),
    ]
    print_list(items, col_defs, title="Rating modules",
               output_format=output_format, columns=columns,
               fit_width=fit_width, max_width=max_width, noindent=noindent)


@rating.command("module-show")
@click.argument("module_id")
@output_options
@click.pass_context
def rating_module_show(ctx, module_id, output_format, columns, fit_width, max_width, noindent):
    """Show a rating module. Admin only."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_url(client)}/v1/rating/modules/{module_id}")
    fields = [
        ("Module", data.get("module_id", "")),
        ("Enabled", data.get("enabled", "")),
        ("Priority", data.get("priority", "")),
        ("Description", data.get("description", "")),
        ("Hot config", data.get("hot_config", "")),
    ]
    print_detail(fields, output_format=output_format, columns=columns,
                 fit_width=fit_width, max_width=max_width, noindent=noindent)


def _module_put(client, module_id: str, patch: dict) -> None:
    """PUT the full module representation with the given patch applied.

    CloudKitty's module PUT is a full-replacement; fetch-merge-send.
    """
    current = client.get(f"{_url(client)}/v1/rating/modules/{module_id}")
    body = {k: v for k, v in current.items() if k != "module_id"}
    body.update(patch)
    client.put(f"{_url(client)}/v1/rating/modules/{module_id}", json=body)


@rating.command("module-enable")
@click.argument("module_id")
@click.pass_context
def rating_module_enable(ctx, module_id):
    """Enable a rating module. Admin only."""
    client = ctx.find_object(OrcaContext).ensure_client()
    _module_put(client, module_id, {"enabled": True})
    console.print(f"Rating module [bold]{module_id}[/bold] enabled.")


@rating.command("module-disable")
@click.argument("module_id")
@click.pass_context
def rating_module_disable(ctx, module_id):
    """Disable a rating module. Admin only."""
    client = ctx.find_object(OrcaContext).ensure_client()
    _module_put(client, module_id, {"enabled": False})
    console.print(f"Rating module [bold]{module_id}[/bold] disabled.")


@rating.command("module-set-priority")
@click.argument("module_id")
@click.argument("priority", type=int)
@click.pass_context
def rating_module_set_priority(ctx, module_id, priority):
    """Set module priority (higher runs first). Admin only."""
    client = ctx.find_object(OrcaContext).ensure_client()
    _module_put(client, module_id, {"priority": priority})
    console.print(f"Rating module [bold]{module_id}[/bold] priority set to [bold]{priority}[/bold].")


# ══════════════════════════════════════════════════════════════════════════════
#  rating hashmap — services / fields / mappings / thresholds / groups
# ══════════════════════════════════════════════════════════════════════════════

_HM = "/v1/rating/module_config/hashmap"


@rating.group("hashmap")
def rating_hashmap() -> None:
    """Configure the HashMap rating module. Admin only."""


# ── services ──────────────────────────────────────────────────────────────────

@rating_hashmap.command("service-list")
@output_options
@click.pass_context
def hm_service_list(ctx, output_format, columns, fit_width, max_width, noindent):
    """List HashMap services (one per rated metric)."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_url(client)}{_HM}/services")
    items = data.get("services", []) if isinstance(data, dict) else data
    print_list(
        items,
        [("Service ID", "service_id", {"style": "cyan"}),
         ("Name", "name", {"style": "bold"})],
        title="HashMap services",
        output_format=output_format, columns=columns,
        fit_width=fit_width, max_width=max_width, noindent=noindent,
    )


@rating_hashmap.command("service-create")
@click.argument("name")
@click.pass_context
def hm_service_create(ctx, name):
    """Create a HashMap service (one per rated metric)."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.post(f"{_url(client)}{_HM}/services", json={"name": name})
    console.print(f"HashMap service [bold]{name}[/bold] created "
                  f"(ID: {data.get('service_id', '?')}).")


@rating_hashmap.command("service-delete")
@click.argument("service_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def hm_service_delete(ctx, service_id, yes):
    """Delete a HashMap service."""
    if not yes:
        click.confirm(f"Delete HashMap service {service_id}?", abort=True)
    client = ctx.find_object(OrcaContext).ensure_client()
    client.delete(f"{_url(client)}{_HM}/services/{service_id}")
    console.print(f"HashMap service [bold]{service_id}[/bold] deleted.")


# ── fields ────────────────────────────────────────────────────────────────────

@rating_hashmap.command("field-list")
@click.option("--service-id", callback=validate_id,
              help="Filter fields by service ID.")
@output_options
@click.pass_context
def hm_field_list(ctx, service_id, output_format, columns, fit_width, max_width, noindent):
    """List HashMap fields (metadata keys a service is rated on)."""
    client = ctx.find_object(OrcaContext).ensure_client()
    params = {"service_id": service_id} if service_id else {}
    data = client.get(f"{_url(client)}{_HM}/fields", params=params)
    items = data.get("fields", []) if isinstance(data, dict) else data
    print_list(
        items,
        [("Field ID", "field_id", {"style": "cyan"}),
         ("Name", "name", {"style": "bold"}),
         ("Service ID", "service_id")],
        title="HashMap fields",
        output_format=output_format, columns=columns,
        fit_width=fit_width, max_width=max_width, noindent=noindent,
    )


@rating_hashmap.command("field-create")
@click.argument("service_id", callback=validate_id)
@click.argument("name")
@click.pass_context
def hm_field_create(ctx, service_id, name):
    """Create a HashMap field under a service."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.post(f"{_url(client)}{_HM}/fields",
                       json={"service_id": service_id, "name": name})
    console.print(f"HashMap field [bold]{name}[/bold] created "
                  f"(ID: {data.get('field_id', '?')}).")


@rating_hashmap.command("field-delete")
@click.argument("field_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def hm_field_delete(ctx, field_id, yes):
    """Delete a HashMap field."""
    if not yes:
        click.confirm(f"Delete HashMap field {field_id}?", abort=True)
    client = ctx.find_object(OrcaContext).ensure_client()
    client.delete(f"{_url(client)}{_HM}/fields/{field_id}")
    console.print(f"HashMap field [bold]{field_id}[/bold] deleted.")


# ── mappings (rate a specific value) ──────────────────────────────────────────

@rating_hashmap.command("mapping-list")
@click.option("--service-id", callback=validate_id, default=None)
@click.option("--field-id", callback=validate_id, default=None)
@click.option("--group-id", callback=validate_id, default=None)
@output_options
@click.pass_context
def hm_mapping_list(ctx, service_id, field_id, group_id,
                    output_format, columns, fit_width, max_width, noindent):
    """List HashMap mappings (value → price)."""
    client = ctx.find_object(OrcaContext).ensure_client()
    params = {}
    if service_id:
        params["service_id"] = service_id
    if field_id:
        params["field_id"] = field_id
    if group_id:
        params["group_id"] = group_id
    data = client.get(f"{_url(client)}{_HM}/mappings", params=params)
    items = data.get("mappings", []) if isinstance(data, dict) else data
    print_list(
        items,
        [("Mapping ID", "mapping_id", {"style": "cyan"}),
         ("Value", "value"),
         ("Cost", "cost", {"justify": "right", "style": "bold green"}),
         ("Type", "type"),
         ("Field ID", "field_id")],
        title="HashMap mappings",
        output_format=output_format, columns=columns,
        fit_width=fit_width, max_width=max_width, noindent=noindent,
    )


@rating_hashmap.command("mapping-create")
@click.option("--field-id", callback=validate_id, default=None,
              help="Field ID the mapping applies to. Required unless --service-id is given.")
@click.option("--service-id", callback=validate_id, default=None,
              help="Service ID for a service-level mapping (no field).")
@click.option("--value", default=None,
              help="Field value to match. Omit for service-level mappings.")
@click.option("--cost", required=True,
              help="Price (e.g. 0.05).")
@click.option("--type", "mapping_type", default="flat", show_default=True,
              type=click.Choice(["flat", "rate"]),
              help="flat = price per unit, rate = multiplier.")
@click.option("--group-id", callback=validate_id, default=None,
              help="Group ID (HashMap group).")
@click.pass_context
def hm_mapping_create(ctx, field_id, service_id, value, cost, mapping_type, group_id):
    """Create a HashMap mapping.

    \b
    Examples:
      # Flat 0.05/hour for flavor m1.small:
      orca rating hashmap mapping-create --field-id <flavor_field_id> --value m1.small --cost 0.05

      # Service-level 0.10 multiplier:
      orca rating hashmap mapping-create --service-id <svc_id> --cost 1.10 --type rate
    """
    if not field_id and not service_id:
        raise click.UsageError("Provide either --field-id or --service-id.")
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {"cost": cost, "type": mapping_type}
    if field_id:
        body["field_id"] = field_id
    if service_id:
        body["service_id"] = service_id
    if value is not None:
        body["value"] = value
    if group_id:
        body["group_id"] = group_id
    data = client.post(f"{_url(client)}{_HM}/mappings", json=body)
    console.print(f"HashMap mapping created (ID: [bold]{data.get('mapping_id', '?')}[/bold]).")


@rating_hashmap.command("mapping-delete")
@click.argument("mapping_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def hm_mapping_delete(ctx, mapping_id, yes):
    """Delete a HashMap mapping."""
    if not yes:
        click.confirm(f"Delete HashMap mapping {mapping_id}?", abort=True)
    client = ctx.find_object(OrcaContext).ensure_client()
    client.delete(f"{_url(client)}{_HM}/mappings/{mapping_id}")
    console.print(f"HashMap mapping [bold]{mapping_id}[/bold] deleted.")


# ── thresholds (price tier based on quantity) ─────────────────────────────────

@rating_hashmap.command("threshold-list")
@click.option("--service-id", callback=validate_id, default=None)
@click.option("--field-id", callback=validate_id, default=None)
@click.option("--group-id", callback=validate_id, default=None)
@output_options
@click.pass_context
def hm_threshold_list(ctx, service_id, field_id, group_id,
                      output_format, columns, fit_width, max_width, noindent):
    """List HashMap thresholds."""
    client = ctx.find_object(OrcaContext).ensure_client()
    params = {}
    if service_id:
        params["service_id"] = service_id
    if field_id:
        params["field_id"] = field_id
    if group_id:
        params["group_id"] = group_id
    data = client.get(f"{_url(client)}{_HM}/thresholds", params=params)
    items = data.get("thresholds", []) if isinstance(data, dict) else data
    print_list(
        items,
        [("Threshold ID", "threshold_id", {"style": "cyan"}),
         ("Level", "level", {"justify": "right"}),
         ("Cost", "cost", {"justify": "right", "style": "bold green"}),
         ("Type", "type"),
         ("Field ID", "field_id")],
        title="HashMap thresholds",
        output_format=output_format, columns=columns,
        fit_width=fit_width, max_width=max_width, noindent=noindent,
    )


@rating_hashmap.command("threshold-create")
@click.option("--field-id", callback=validate_id, default=None)
@click.option("--service-id", callback=validate_id, default=None)
@click.option("--level", required=True, help="Quantity level at which this tier starts.")
@click.option("--cost", required=True)
@click.option("--type", "threshold_type", default="flat", show_default=True,
              type=click.Choice(["flat", "rate"]))
@click.option("--group-id", callback=validate_id, default=None)
@click.pass_context
def hm_threshold_create(ctx, field_id, service_id, level, cost, threshold_type, group_id):
    """Create a HashMap threshold."""
    if not field_id and not service_id:
        raise click.UsageError("Provide either --field-id or --service-id.")
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {"level": level, "cost": cost, "type": threshold_type}
    if field_id:
        body["field_id"] = field_id
    if service_id:
        body["service_id"] = service_id
    if group_id:
        body["group_id"] = group_id
    data = client.post(f"{_url(client)}{_HM}/thresholds", json=body)
    console.print(f"HashMap threshold created (ID: [bold]{data.get('threshold_id', '?')}[/bold]).")


@rating_hashmap.command("threshold-delete")
@click.argument("threshold_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def hm_threshold_delete(ctx, threshold_id, yes):
    """Delete a HashMap threshold."""
    if not yes:
        click.confirm(f"Delete HashMap threshold {threshold_id}?", abort=True)
    client = ctx.find_object(OrcaContext).ensure_client()
    client.delete(f"{_url(client)}{_HM}/thresholds/{threshold_id}")
    console.print(f"HashMap threshold [bold]{threshold_id}[/bold] deleted.")


# ── groups ────────────────────────────────────────────────────────────────────

@rating_hashmap.command("group-list")
@output_options
@click.pass_context
def hm_group_list(ctx, output_format, columns, fit_width, max_width, noindent):
    """List HashMap groups (shared metadata across mappings)."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_url(client)}{_HM}/groups")
    items = data.get("groups", []) if isinstance(data, dict) else data
    print_list(
        items,
        [("Group ID", "group_id", {"style": "cyan"}),
         ("Name", "name", {"style": "bold"})],
        title="HashMap groups",
        output_format=output_format, columns=columns,
        fit_width=fit_width, max_width=max_width, noindent=noindent,
    )


@rating_hashmap.command("group-create")
@click.argument("name")
@click.pass_context
def hm_group_create(ctx, name):
    """Create a HashMap group."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.post(f"{_url(client)}{_HM}/groups", json={"name": name})
    console.print(f"HashMap group [bold]{name}[/bold] created "
                  f"(ID: {data.get('group_id', '?')}).")


@rating_hashmap.command("group-delete")
@click.argument("group_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def hm_group_delete(ctx, group_id, yes):
    """Delete a HashMap group."""
    if not yes:
        click.confirm(f"Delete HashMap group {group_id}?", abort=True)
    client = ctx.find_object(OrcaContext).ensure_client()
    client.delete(f"{_url(client)}{_HM}/groups/{group_id}")
    console.print(f"HashMap group [bold]{group_id}[/bold] deleted.")
