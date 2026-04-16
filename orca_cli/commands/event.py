"""``orca event`` — browse Nova instance actions and events."""

from __future__ import annotations

from datetime import datetime

import click
from rich.table import Table
from rich.tree import Tree

from orca_cli.core.context import OrcaContext
from orca_cli.core.output import console, output_options, print_detail, print_list
from orca_cli.core.validators import validate_id

# ── Helpers ──────────────────────────────────────────────────────────────

_ACTION_COLORS: dict[str, str] = {
    "create": "green",
    "delete": "red",
    "stop": "yellow",
    "shelve": "yellow",
    "start": "cyan",
    "unshelve": "cyan",
    "reboot": "cyan",
    "resize": "magenta",
    "migrate": "magenta",
}


def _parse_ts(raw: str | None) -> datetime | None:
    """Parse an ISO-8601 timestamp, stripping a trailing ``Z`` if present."""
    if not raw:
        return None
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


def _format_ts(raw: str | None) -> str:
    ts = _parse_ts(raw)
    return ts.strftime("%Y-%m-%d %H:%M:%S") if ts else ""


def _duration_str(start: str | None, finish: str | None) -> str:
    ts_start = _parse_ts(start)
    ts_finish = _parse_ts(finish)
    if not ts_start or not ts_finish:
        return ""
    delta = ts_finish - ts_start
    total = int(delta.total_seconds())
    if total < 0:
        return ""
    if total < 60:
        return f"{total}s"
    minutes, seconds = divmod(total, 60)
    return f"{minutes}m {seconds}s"


def _colored_action(action: str) -> str:
    color = _ACTION_COLORS.get(action, "white")
    return f"[{color}]{action}[/{color}]"


def _colored_result(result: str | None) -> str:
    if not result:
        return ""
    if result.lower() == "success":
        return f"[green]{result}[/green]"
    if result.lower() == "error":
        return f"[red]{result}[/red]"
    return result


# ── Group ────────────────────────────────────────────────────────────────

@click.group()
@click.pass_context
def event(ctx: click.Context) -> None:
    """Browse instance actions and events (Nova)."""
    pass


# ── list ─────────────────────────────────────────────────────────────────

@event.command("list")
@click.argument("server_id", callback=validate_id)
@output_options
@click.pass_context
def event_list(
    ctx: click.Context,
    server_id: str,
    output_format: str,
    columns: tuple[str, ...],
    fit_width: bool,
    max_width: int | None,
    noindent: bool,
) -> None:
    """List instance actions for a server.

    \b
    Examples:
      orca event list <server-id>
      orca event list <server-id> -f json
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    url = f"{client.compute_url}/servers/{server_id}/os-instance-actions"
    data = client.get(url)

    actions = data.get("instanceActions", [])

    def _action_styled(item: dict) -> str:
        return _colored_action(item.get("action", ""))

    column_defs = [
        ("Action", _action_styled),
        ("Request ID", "request_id", {"no_wrap": True}),
        ("Start Time", lambda i: _format_ts(i.get("start_time"))),
        ("User ID", "user_id", {"no_wrap": True}),
        ("Message", lambda i: i.get("message") or ""),
    ]

    print_list(
        actions,
        column_defs,
        title=f"Instance Actions — {server_id}",
        output_format=output_format,
        columns=columns,
        fit_width=fit_width,
        max_width=max_width,
        noindent=noindent,
        empty_msg="No instance actions found.",
    )


# ── show ─────────────────────────────────────────────────────────────────

@event.command("show")
@click.argument("server_id", callback=validate_id)
@click.argument("request_id")
@output_options
@click.pass_context
def event_show(
    ctx: click.Context,
    server_id: str,
    request_id: str,
    output_format: str,
    columns: tuple[str, ...],
    fit_width: bool,
    max_width: int | None,
    noindent: bool,
) -> None:
    """Show details for a single instance action, including sub-events.

    \b
    Examples:
      orca event show <server-id> <request-id>
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    url = f"{client.compute_url}/servers/{server_id}/os-instance-actions/{request_id}"
    data = client.get(url)

    action = data.get("instanceAction", data)

    fields = [
        ("Action", _colored_action(action.get("action", ""))),
        ("Request ID", action.get("request_id", "")),
        ("Start Time", _format_ts(action.get("start_time"))),
        ("User ID", action.get("user_id", "")),
        ("Project ID", action.get("project_id", "")),
        ("Message", action.get("message") or ""),
    ]

    print_detail(
        fields,
        output_format=output_format,
        columns=columns,
        fit_width=fit_width,
        max_width=max_width,
        noindent=noindent,
    )

    # Sub-events table
    events = action.get("events", [])
    if not events:
        return

    console.print()
    table = Table(title="Sub-Events", show_lines=False)
    table.add_column("Event", style="bold")
    table.add_column("Start Time")
    table.add_column("Finish Time")
    table.add_column("Result")
    table.add_column("Duration")

    for ev in events:
        table.add_row(
            ev.get("event", ""),
            _format_ts(ev.get("start_time")),
            _format_ts(ev.get("finish_time")),
            _colored_result(ev.get("result")),
            _duration_str(ev.get("start_time"), ev.get("finish_time")),
        )

    console.print(table)


# ── all ──────────────────────────────────────────────────────────────────

@event.command("all")
@click.option("--limit", default=50, show_default=True, help="Max number of events to display.")
@click.option("--action", "action_filter", default=None, help="Filter by action type (e.g. create, delete).")
@output_options
@click.pass_context
def event_all(
    ctx: click.Context,
    limit: int,
    action_filter: str | None,
    output_format: str,
    columns: tuple[str, ...],
    fit_width: bool,
    max_width: int | None,
    noindent: bool,
) -> None:
    """List recent instance actions across ALL servers.

    Fetches all servers, then gathers their actions, merges, and sorts by
    start time (newest first).

    \b
    Examples:
      orca event all
      orca event all --limit 20
      orca event all --action create
    """
    client = ctx.find_object(OrcaContext).ensure_client()

    with console.status("Fetching events..."):
        servers_data = client.get(
            f"{client.compute_url}/servers/detail", params={"limit": 1000},
        )
        servers = servers_data.get("servers", [])

        server_map: dict[str, str] = {}
        for srv in servers:
            server_map[srv["id"]] = srv.get("name", srv["id"])

        all_actions: list[dict] = []
        for srv in servers:
            srv_id = srv["id"]
            data = client.get(
                f"{client.compute_url}/servers/{srv_id}/os-instance-actions",
            )
            for act in data.get("instanceActions", []):
                act["_server_name"] = server_map.get(srv_id, srv_id)
                act["_server_id"] = srv_id
                all_actions.append(act)

    # Filter by action type
    if action_filter:
        all_actions = [a for a in all_actions if a.get("action") == action_filter]

    # Sort by start_time descending
    all_actions.sort(key=lambda a: a.get("start_time", ""), reverse=True)

    # Apply limit
    all_actions = all_actions[:limit]

    def _server_col(item: dict) -> str:
        return f"{item.get('_server_name', '')} ({item.get('_server_id', '')})"

    def _action_styled(item: dict) -> str:
        return _colored_action(item.get("action", ""))

    column_defs = [
        ("Server", _server_col),
        ("Action", _action_styled),
        ("Request ID", "request_id", {"no_wrap": True}),
        ("Start Time", lambda i: _format_ts(i.get("start_time"))),
        ("User ID", "user_id"),
    ]

    print_list(
        all_actions,
        column_defs,
        title="Recent Instance Actions (All Servers)",
        output_format=output_format,
        columns=columns,
        fit_width=fit_width,
        max_width=max_width,
        noindent=noindent,
        empty_msg="No instance actions found.",
    )


# ── timeline ─────────────────────────────────────────────────────────────

@event.command("timeline")
@click.argument("server_id", callback=validate_id)
@click.pass_context
def event_timeline(ctx: click.Context, server_id: str) -> None:
    """Show a chronological timeline of all actions for a server.

    Renders a Rich Tree with each action as a branch and sub-events as leaves.

    \b
    Examples:
      orca event timeline <server-id>
    """
    client = ctx.find_object(OrcaContext).ensure_client()

    # Fetch all actions
    data = client.get(
        f"{client.compute_url}/servers/{server_id}/os-instance-actions",
    )
    actions = data.get("instanceActions", [])

    if not actions:
        console.print("[yellow]No instance actions found.[/yellow]")
        return

    # Sort chronologically (oldest first)
    actions.sort(key=lambda a: a.get("start_time", ""))

    tree = Tree(f"[bold]Timeline — {server_id}[/bold]")

    for act in actions:
        action_name = act.get("action", "unknown")
        color = _ACTION_COLORS.get(action_name, "white")
        start = _format_ts(act.get("start_time"))
        request_id = act.get("request_id", "")

        branch = tree.add(
            f"[{color} bold]{action_name}[/{color} bold]  "
            f"[dim]{start}[/dim]  "
            f"[dim italic]{request_id}[/dim italic]"
        )

        # Fetch sub-events for this action
        detail_data = client.get(
            f"{client.compute_url}/servers/{server_id}/os-instance-actions/{request_id}",
        )
        detail = detail_data.get("instanceAction", {})
        events = detail.get("events", [])

        if not events:
            branch.add("[dim]no sub-events[/dim]")
            continue

        for ev in events:
            ev_name = ev.get("event", "")
            result = ev.get("result", "")
            duration = _duration_str(ev.get("start_time"), ev.get("finish_time"))
            result_styled = _colored_result(result)
            duration_part = f"  [dim]({duration})[/dim]" if duration else ""

            branch.add(f"{ev_name}  {result_styled}{duration_part}")

    console.print()
    console.print(tree)
    console.print()
