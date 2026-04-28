"""``orca alarm`` — manage OpenStack Alarms (Aodh)."""

from __future__ import annotations

import json

import click

from orca_cli.core.aliases import add_command_with_alias
from orca_cli.core.context import OrcaContext
from orca_cli.core.output import console, output_options, print_detail, print_list
from orca_cli.core.validators import validate_id
from orca_cli.services.alarm import AlarmService


def _state_style(state: str) -> str:
    s = (state or "").lower()
    if s == "ok":
        return "green"
    if s == "alarm":
        return "red"
    return "yellow"


# ── Root group ────────────────────────────────────────────────────────────────

@click.group()
@click.pass_context
def alarm(ctx: click.Context) -> None:
    """Manage Aodh alarms."""


# ══════════════════════════════════════════════════════════════════════════════
#  Alarm CRUD
# ══════════════════════════════════════════════════════════════════════════════

@alarm.command("list")
@click.option("--type", "alarm_type", default=None, help="Filter by alarm type.")
@click.option("--state", default=None,
              type=click.Choice(["ok", "alarm", "insufficient_data"]),
              help="Filter by state.")
@click.option("--enabled/--disabled", default=None, help="Filter by enabled status.")
@click.option("--name", default=None, help="Filter by alarm name.")
@click.option("--limit", type=int, default=None, help="Max number of alarms to return.")
@output_options
@click.pass_context
def alarm_list(ctx, alarm_type, state, enabled, name, limit,
               output_format, columns, fit_width, max_width, noindent):
    """List alarms."""
    client = ctx.find_object(OrcaContext).ensure_client()
    svc = AlarmService(client)
    params: dict = {}
    if alarm_type:
        params["type"] = alarm_type
    if state:
        params["state"] = state
    if enabled is not None:
        params["enabled"] = str(enabled).lower()
    if name:
        params["name"] = name
    if limit:
        params["limit"] = limit
    items = svc.find(params=params or None)
    if not items:
        console.print("No alarms found.")
        return
    col_defs = [
        ("Alarm ID", "alarm_id"),
        ("Name", "name"),
        ("Type", "type"),
        ("State", lambda a: f"[{_state_style(a.get('state', ''))}]{a.get('state', '')}[/{_state_style(a.get('state', ''))}]"),
        ("Severity", "severity"),
        ("Enabled", "enabled"),
    ]
    print_list(items, col_defs, title="Alarms",
               output_format=output_format, columns=columns,
               fit_width=fit_width, max_width=max_width, noindent=noindent)


@alarm.command("show")
@click.argument("alarm_id", callback=validate_id)
@output_options
@click.pass_context
def alarm_show(ctx, alarm_id, output_format, columns, fit_width, max_width, noindent):
    """Show an alarm."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = AlarmService(client).get(alarm_id)
    rule_key = f"{data.get('type', 'unknown')}_rule"
    rule = data.get(rule_key, data.get("composite_rule", {}))
    fields = [
        ("Alarm ID", data.get("alarm_id", "")),
        ("Name", data.get("name", "")),
        ("Type", data.get("type", "")),
        ("State", data.get("state", "")),
        ("Severity", data.get("severity", "")),
        ("Enabled", data.get("enabled", "")),
        ("Description", data.get("description", "")),
        ("Project ID", data.get("project_id", "")),
        ("User ID", data.get("user_id", "")),
        ("Repeat Actions", data.get("repeat_actions", "")),
        ("Alarm Actions", ", ".join(data.get("alarm_actions", []))),
        ("OK Actions", ", ".join(data.get("ok_actions", []))),
        ("Insufficient Data Actions", ", ".join(data.get("insufficient_data_actions", []))),
        ("Rule", json.dumps(rule, indent=2) if rule else ""),
        ("Timestamp", data.get("timestamp", "")),
        ("State Timestamp", data.get("state_timestamp", "")),
    ]
    print_detail(fields,
                 output_format=output_format, columns=columns,
                 fit_width=fit_width, max_width=max_width, noindent=noindent)


@alarm.command("create")
@click.option("--name", required=True, help="Alarm name.")
@click.option("--type", "alarm_type", required=True,
              type=click.Choice([
                  "gnocchi_resources_threshold",
                  "gnocchi_aggregation_by_metrics_threshold",
                  "gnocchi_aggregation_by_resources_threshold",
                  "event", "composite", "loadbalancer_member_health", "threshold",
              ]), help="Alarm type.")
@click.option("--rule", "rule_json", required=True, metavar="JSON",
              help="Type-specific rule as a JSON string.")
@click.option("--description", default="", help="Alarm description.")
@click.option("--severity", default="low",
              type=click.Choice(["low", "moderate", "critical"]),
              help="Alarm severity.")
@click.option("--enabled/--disabled", default=True, help="Enable or disable the alarm.")
@click.option("--repeat-actions/--no-repeat-actions", default=False,
              help="Re-trigger actions on each evaluation while in alarm state.")
@click.option("--alarm-action", "alarm_actions", multiple=True, metavar="URL",
              help="Webhook URL to call when entering alarm state. Repeatable.")
@click.option("--ok-action", "ok_actions", multiple=True, metavar="URL",
              help="Webhook URL to call when entering ok state. Repeatable.")
@click.option("--insufficient-data-action", "insufficient_data_actions", multiple=True,
              metavar="URL", help="Webhook URL to call on insufficient data. Repeatable.")
@output_options
@click.pass_context
def alarm_create(ctx, name, alarm_type, rule_json, description, severity, enabled,
                 repeat_actions, alarm_actions, ok_actions, insufficient_data_actions,
                 output_format, columns, fit_width, max_width, noindent):
    """Create an alarm."""
    client = ctx.find_object(OrcaContext).ensure_client()
    try:
        rule = json.loads(rule_json)
    except json.JSONDecodeError as exc:
        raise click.BadParameter(f"Invalid JSON: {exc}", param_hint="--rule") from exc
    rule_key = "composite_rule" if alarm_type == "composite" else f"{alarm_type}_rule"
    body = {
        "name": name,
        "type": alarm_type,
        rule_key: rule,
        "description": description,
        "severity": severity,
        "enabled": enabled,
        "repeat_actions": repeat_actions,
        "alarm_actions": list(alarm_actions),
        "ok_actions": list(ok_actions),
        "insufficient_data_actions": list(insufficient_data_actions),
    }
    data = AlarmService(client).create(body)
    fields = [
        ("Alarm ID", data.get("alarm_id", "")),
        ("Name", data.get("name", "")),
        ("Type", data.get("type", "")),
        ("State", data.get("state", "")),
        ("Severity", data.get("severity", "")),
        ("Enabled", data.get("enabled", "")),
    ]
    print_detail(fields,
                 output_format=output_format, columns=columns,
                 fit_width=fit_width, max_width=max_width, noindent=noindent)


@alarm.command("set")
@click.argument("alarm_id", callback=validate_id)
@click.option("--name", default=None, help="New alarm name.")
@click.option("--description", default=None, help="New description.")
@click.option("--severity", default=None,
              type=click.Choice(["low", "moderate", "critical"]))
@click.option("--enabled/--disabled", default=None, help="Enable or disable.")
@click.option("--repeat-actions/--no-repeat-actions", default=None)
@click.option("--rule", "rule_json", default=None, metavar="JSON",
              help="Updated type-specific rule as JSON.")
@click.option("--alarm-action", "alarm_actions", multiple=True, metavar="URL")
@click.option("--ok-action", "ok_actions", multiple=True, metavar="URL")
@click.option("--insufficient-data-action", "insufficient_data_actions", multiple=True,
              metavar="URL")
@click.pass_context
def alarm_set(ctx, alarm_id, name, description, severity, enabled, repeat_actions,
              rule_json, alarm_actions, ok_actions, insufficient_data_actions):
    """Update an alarm."""
    client = ctx.find_object(OrcaContext).ensure_client()
    svc = AlarmService(client)
    updates: dict = {}
    if name is not None:
        updates["name"] = name
    if description is not None:
        updates["description"] = description
    if severity is not None:
        updates["severity"] = severity
    if enabled is not None:
        updates["enabled"] = enabled
    if repeat_actions is not None:
        updates["repeat_actions"] = repeat_actions
    if alarm_actions:
        updates["alarm_actions"] = list(alarm_actions)
    if ok_actions:
        updates["ok_actions"] = list(ok_actions)
    if insufficient_data_actions:
        updates["insufficient_data_actions"] = list(insufficient_data_actions)
    rule_update: dict | None = None
    if rule_json is not None:
        try:
            rule_update = json.loads(rule_json)
        except json.JSONDecodeError as exc:
            raise click.BadParameter(f"Invalid JSON: {exc}", param_hint="--rule") from exc
    if not updates and rule_update is None:
        console.print("Nothing to update.")
        return

    # Aodh PUT wants the full alarm representation — fetch, merge, send.
    current = svc.get(alarm_id)
    body = dict(current)
    body.update(updates)
    if rule_update is not None:
        atype = current.get("type", "")
        rule_key = "composite_rule" if atype == "composite" else f"{atype}_rule"
        body[rule_key] = rule_update
    # Aodh rejects read-only fields on PUT
    for ro in ("alarm_id", "project_id", "user_id", "timestamp",
               "state_timestamp", "state_reason", "state_reason_data"):
        body.pop(ro, None)
    svc.update(alarm_id, body)
    console.print(f"Alarm [bold]{alarm_id}[/bold] updated.")


@alarm.command("delete")
@click.argument("alarm_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def alarm_delete(ctx, alarm_id, yes):
    """Delete an alarm."""
    client = ctx.find_object(OrcaContext).ensure_client()
    if not yes:
        click.confirm(f"Delete alarm {alarm_id}?", abort=True)
    AlarmService(client).delete(alarm_id)
    console.print(f"Alarm [bold]{alarm_id}[/bold] deleted.")


# ══════════════════════════════════════════════════════════════════════════════
#  Alarm State
# ══════════════════════════════════════════════════════════════════════════════

@alarm.group("state")
def alarm_state() -> None:
    """Inspect or override an alarm's evaluation state."""


@alarm_state.command("get")
@click.argument("alarm_id", callback=validate_id)
@click.pass_context
def alarm_state_get(ctx, alarm_id):
    """Get the current state of an alarm."""
    client = ctx.find_object(OrcaContext).ensure_client()
    state = AlarmService(client).get_state(alarm_id)
    if isinstance(state, str):
        state = state.strip('"')
    style = _state_style(state)
    console.print(f"[{style}]{state}[/{style}]")


@alarm_state.command("set")
@click.argument("alarm_id", callback=validate_id)
@click.argument("state", type=click.Choice(["ok", "alarm", "insufficient_data"]))
@click.pass_context
def alarm_state_set(ctx, alarm_id, state):
    """Set the state of an alarm."""
    client = ctx.find_object(OrcaContext).ensure_client()
    AlarmService(client).set_state(alarm_id, state)
    console.print(f"Alarm [bold]{alarm_id}[/bold] state set to [bold]{state}[/bold].")


add_command_with_alias(alarm, alarm_state_get,
                        legacy_name="state-get", primary_path="alarm state get")
add_command_with_alias(alarm, alarm_state_set,
                        legacy_name="state-set", primary_path="alarm state set")


# ══════════════════════════════════════════════════════════════════════════════
#  Alarm History
# ══════════════════════════════════════════════════════════════════════════════

@alarm.command("history")
@click.argument("alarm_id", callback=validate_id)
@click.option("--limit", type=int, default=None, help="Max number of history entries.")
@output_options
@click.pass_context
def alarm_history(ctx, alarm_id, limit, output_format, columns, fit_width, max_width, noindent):
    """Show the change history of an alarm."""
    client = ctx.find_object(OrcaContext).ensure_client()
    params: dict = {}
    if limit:
        params["limit"] = limit
    items = AlarmService(client).find_history(alarm_id, params=params or None)
    if not items:
        console.print("No history found.")
        return
    col_defs = [
        ("Timestamp", "timestamp"),
        ("Type", "type"),
        ("Detail", "detail"),
        ("User ID", "user_id"),
    ]
    print_list(items, col_defs, title=f"History for {alarm_id}",
               output_format=output_format, columns=columns,
               fit_width=fit_width, max_width=max_width, noindent=noindent)


# ══════════════════════════════════════════════════════════════════════════════
#  Capabilities
# ══════════════════════════════════════════════════════════════════════════════

@alarm.command("capabilities")
@click.pass_context
def alarm_capabilities(ctx):
    """Show Aodh API capabilities."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = AlarmService(client).get_capabilities()
    console.print_json(json.dumps(data, indent=2))


# ══════════════════════════════════════════════════════════════════════════════
#  Quotas
# ══════════════════════════════════════════════════════════════════════════════

@alarm.group("quota")
def alarm_quota() -> None:
    """Inspect or set Aodh per-project alarm quota."""


@alarm_quota.command("set")
@click.argument("project_id", callback=validate_id)
@click.option("--alarms", "alarm_quota_value", type=int, required=True,
              help="Maximum number of alarms for the project.")
@click.pass_context
def alarm_quota_set(ctx, project_id, alarm_quota_value):
    """Set alarm quota for a project."""
    client = ctx.find_object(OrcaContext).ensure_client()
    body = {
        "project_id": project_id,
        "quotas": [{"resource": "alarms", "limit": alarm_quota_value}],
    }
    AlarmService(client).update_quota(body)
    console.print(f"Quota for project [bold]{project_id}[/bold] set to [bold]{alarm_quota_value}[/bold] alarms.")


add_command_with_alias(alarm, alarm_quota_set,
                        legacy_name="quota-set", primary_path="alarm quota set")
