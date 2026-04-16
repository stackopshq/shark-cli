"""``orca stack`` — manage Heat stacks (orchestration)."""

from __future__ import annotations

import datetime
import time
from pathlib import Path

import click
import yaml

from orca_cli.core.context import OrcaContext
from orca_cli.core.output import console, output_options, print_detail, print_list

# ── Helpers ──────────────────────────────────────────────────────────────


def _heat(client) -> str:
    return client.orchestration_url


def _status_style(status: str) -> str:
    """Return a Rich style string based on Heat stack/resource status."""
    s = (status or "").upper()
    if s.endswith("_COMPLETE") and "DELETE" not in s:
        return "green"
    if s.endswith("_IN_PROGRESS"):
        return "yellow"
    if s.endswith("_FAILED"):
        return "red"
    if "DELETE_COMPLETE" in s:
        return "dim"
    return ""


def _styled_status(status: str) -> str:
    """Wrap *status* in Rich markup."""
    style = _status_style(status)
    if style:
        return f"[{style}]{status}[/{style}]"
    return status


def _resolve_stack(client, stack: str) -> dict:
    """GET a stack by name or ID, returning the full stack dict.

    Heat's ``GET /stacks/<name>`` returns a 302 redirect to
    ``/stacks/<name>/<id>``.  To avoid following redirects we first list
    stacks filtered by name and derive the canonical URL ourselves.
    """
    base = _heat(client)
    # Try listing by name first (no redirect risk)
    data = client.get(f"{base}/stacks", params={"name": stack})
    stacks = data.get("stacks", [])
    if stacks:
        s = stacks[0]
        name = s.get("stack_name", stack)
        sid = s.get("id", "")
        detail = client.get(f"{base}/stacks/{name}/{sid}")
        return detail.get("stack", detail)
    # Fallback: maybe caller passed the canonical ``name/id`` form
    try:
        detail = client.get(f"{base}/stacks/{stack}")
        return detail.get("stack", detail)
    except Exception:
        raise click.ClickException(f"Stack not found: {stack}")


def _parse_params(params: tuple[str, ...]) -> dict:
    """Convert ``('key=value', ...)`` into ``{'key': 'value', ...}``."""
    result: dict = {}
    for p in params:
        if "=" not in p:
            raise click.BadParameter(f"Invalid parameter format: {p!r} (expected key=value)")
        k, v = p.split("=", 1)
        result[k] = v
    return result


def _stringify_dates(obj: object) -> object:
    """Recursively convert datetime.date/datetime instances to ISO strings.

    ``yaml.safe_load`` parses bare YAML dates (e.g. ``heat_template_version:
    2013-05-23``) as ``datetime.date`` objects, which are not JSON-serialisable
    and cause ``TypeError`` when the body is sent to Heat.
    """
    if isinstance(obj, dict):
        return {k: _stringify_dates(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_stringify_dates(i) for i in obj]
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    return obj


def _load_template(path: str) -> dict:
    """Read a local YAML/JSON template file and return it as a dict."""
    content = Path(path).read_text()
    return _stringify_dates(yaml.safe_load(content))


def _load_environment(path: str) -> dict:
    """Read a local environment file and return it as a dict."""
    content = Path(path).read_text()
    return _stringify_dates(yaml.safe_load(content))


def _wait_for_stack(client, stack_name: str, stack_id: str, action: str) -> dict:
    """Poll stack status until a terminal state is reached."""
    terminal_suffixes = ("_COMPLETE", "_FAILED")
    with console.status(f"[bold cyan]Waiting for stack {action}..."):
        while True:
            data = client.get(f"{_heat(client)}/stacks/{stack_name}/{stack_id}")
            stk = data.get("stack", data)
            status = stk.get("stack_status", "")
            if any(status.upper().endswith(s) for s in terminal_suffixes):
                style = _status_style(status)
                console.print(f"Stack {stack_name}: [{style}]{status}[/{style}]")
                reason = stk.get("stack_status_reason", "")
                if reason:
                    console.print(f"[dim]Reason: {reason}[/dim]")
                return stk
            time.sleep(5)


# ══════════════════════════════════════════════════════════════════════════
#  Stack group
# ══════════════════════════════════════════════════════════════════════════

@click.group()
@click.pass_context
def stack(ctx: click.Context) -> None:
    """Manage Heat stacks (orchestration)."""
    pass


# ── list ─────────────────────────────────────────────────────────────────

@stack.command("list")
@output_options
@click.pass_context
def stack_list(ctx: click.Context, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List stacks."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_heat(client)}/stacks")

    stacks = data.get("stacks", [])

    print_list(
        stacks,
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Name", "stack_name", {"style": "bold"}),
            ("Status", lambda s: _styled_status(s.get("stack_status", ""))),
            ("Created", "creation_time"),
            ("Updated", lambda s: s.get("updated_time", "") or "—"),
        ],
        title="Stacks",
        output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent,
        columns=columns,
        empty_msg="No stacks found.",
    )


# ── show ─────────────────────────────────────────────────────────────────

@stack.command("show")
@click.argument("stack_name_or_id")
@output_options
@click.pass_context
def stack_show(ctx: click.Context, stack_name_or_id: str, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show stack details."""
    client = ctx.find_object(OrcaContext).ensure_client()
    stk = _resolve_stack(client, stack_name_or_id)

    fields = [
        ("id", stk.get("id", "")),
        ("stack_name", stk.get("stack_name", "")),
        ("stack_status", _styled_status(stk.get("stack_status", ""))),
        ("stack_status_reason", stk.get("stack_status_reason", "")),
        ("description", stk.get("description", "")),
        ("creation_time", stk.get("creation_time", "")),
        ("updated_time", stk.get("updated_time", "") or "—"),
        ("deletion_time", stk.get("deletion_time", "") or "—"),
        ("timeout_mins", str(stk.get("timeout_mins", ""))),
        ("disable_rollback", str(stk.get("disable_rollback", ""))),
        ("parent", stk.get("parent", "") or "—"),
        ("template_description", stk.get("template_description", "")),
        ("outputs", str(stk.get("outputs", []))),
        ("parameters", str(stk.get("parameters", {}))),
    ]

    print_detail(fields, output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent, columns=columns)


# ── create ───────────────────────────────────────────────────────────────

@stack.command("create")
@click.argument("name")
@click.option("--template", "-t", "template", required=True, help="Template file path or URL.")
@click.option("--environment", "-e", "environment", default=None, help="Environment file path.")
@click.option("--parameter", "parameters", multiple=True, help="Parameter key=value (repeatable).")
@click.option("--timeout", "timeout_mins", type=int, default=None, help="Timeout in minutes.")
@click.option("--wait", "wait", is_flag=True, default=False, help="Wait for stack to reach terminal state.")
@click.pass_context
def stack_create(ctx: click.Context, name: str, template: str, environment: str | None,
                 parameters: tuple[str, ...], timeout_mins: int | None, wait: bool) -> None:
    """Create a stack.

    \b
    Examples:
      orca stack create my-stack -t template.yaml
      orca stack create my-stack -t template.yaml -e env.yaml --parameter key1=val1
      orca stack create my-stack -t template.yaml --timeout 30 --wait
    """
    client = ctx.find_object(OrcaContext).ensure_client()

    body: dict = {"stack_name": name}

    if template.startswith(("http://", "https://")):
        body["template_url"] = template
    else:
        body["template"] = _load_template(template)

    if environment:
        body["environment"] = _load_environment(environment)

    if parameters:
        body["parameters"] = _parse_params(parameters)

    if timeout_mins is not None:
        body["timeout_mins"] = timeout_mins

    data = client.post(f"{_heat(client)}/stacks", json=body)
    stk = data.get("stack", data)
    stack_id = stk.get("id", "")
    console.print(f"[green]Stack '{name}' creation started ({stack_id}).[/green]")

    if wait and stack_id:
        _wait_for_stack(client, name, stack_id, "create")


# ── update ───────────────────────────────────────────────────────────────

@stack.command("update")
@click.argument("stack_name_or_id")
@click.option("--template", "-t", "template", required=True, help="Template file path or URL.")
@click.option("--environment", "-e", "environment", default=None, help="Environment file path.")
@click.option("--parameter", "parameters", multiple=True, help="Parameter key=value (repeatable).")
@click.option("--timeout", "timeout_mins", type=int, default=None, help="Timeout in minutes.")
@click.option("--wait", "wait", is_flag=True, default=False, help="Wait for stack to reach terminal state.")
@click.pass_context
def stack_update(ctx: click.Context, stack_name_or_id: str, template: str, environment: str | None,
                 parameters: tuple[str, ...], timeout_mins: int | None, wait: bool) -> None:
    """Update a stack.

    \b
    Examples:
      orca stack update my-stack -t template.yaml
      orca stack update my-stack -t template.yaml -e env.yaml --parameter key1=val1 --wait
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    stk = _resolve_stack(client, stack_name_or_id)
    s_name = stk["stack_name"]
    s_id = stk["id"]

    body: dict = {}

    if template.startswith(("http://", "https://")):
        body["template_url"] = template
    else:
        body["template"] = _load_template(template)

    if environment:
        body["environment"] = _load_environment(environment)

    if parameters:
        body["parameters"] = _parse_params(parameters)

    if timeout_mins is not None:
        body["timeout_mins"] = timeout_mins

    client.put(f"{_heat(client)}/stacks/{s_name}/{s_id}", json=body)
    console.print(f"[green]Stack '{s_name}' update started.[/green]")

    if wait:
        _wait_for_stack(client, s_name, s_id, "update")


# ── delete ───────────────────────────────────────────────────────────────

@stack.command("delete")
@click.argument("stack_name_or_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.option("--wait", "wait", is_flag=True, default=False, help="Wait for stack deletion to complete.")
@click.pass_context
def stack_delete(ctx: click.Context, stack_name_or_id: str, yes: bool, wait: bool) -> None:
    """Delete a stack."""
    client = ctx.find_object(OrcaContext).ensure_client()
    stk = _resolve_stack(client, stack_name_or_id)
    s_name = stk["stack_name"]
    s_id = stk["id"]

    if not yes:
        click.confirm(f"Delete stack {s_name}?", abort=True)

    client.delete(f"{_heat(client)}/stacks/{s_name}/{s_id}")
    console.print(f"[green]Stack '{s_name}' deletion started.[/green]")

    if wait:
        _wait_for_stack(client, s_name, s_id, "delete")


# ── actions ──────────────────────────────────────────────────────────────

def _stack_action(ctx: click.Context, stack_name_or_id: str, action: dict, label: str) -> None:
    """Send a stack action (check, suspend, resume, cancel_update)."""
    client = ctx.find_object(OrcaContext).ensure_client()
    stk = _resolve_stack(client, stack_name_or_id)
    s_name = stk["stack_name"]
    s_id = stk["id"]
    client.post(f"{_heat(client)}/stacks/{s_name}/{s_id}/actions", json=action)
    console.print(f"[green]{label} request sent for stack '{s_name}'.[/green]")


@stack.command("check")
@click.argument("stack_name_or_id")
@click.pass_context
def stack_check(ctx: click.Context, stack_name_or_id: str) -> None:
    """Check a stack (verify resource states)."""
    _stack_action(ctx, stack_name_or_id, {"check": None}, "Check")


@stack.command("suspend")
@click.argument("stack_name_or_id")
@click.pass_context
def stack_suspend(ctx: click.Context, stack_name_or_id: str) -> None:
    """Suspend a stack."""
    _stack_action(ctx, stack_name_or_id, {"suspend": None}, "Suspend")


@stack.command("resume")
@click.argument("stack_name_or_id")
@click.pass_context
def stack_resume(ctx: click.Context, stack_name_or_id: str) -> None:
    """Resume a suspended stack."""
    _stack_action(ctx, stack_name_or_id, {"resume": None}, "Resume")


@stack.command("cancel")
@click.argument("stack_name_or_id")
@click.pass_context
def stack_cancel(ctx: click.Context, stack_name_or_id: str) -> None:
    """Cancel an in-progress stack update."""
    _stack_action(ctx, stack_name_or_id, {"cancel_update": None}, "Cancel update")


# ══════════════════════════════════════════════════════════════════════════
#  Stack Resources
# ══════════════════════════════════════════════════════════════════════════

@stack.command("resource-list")
@click.argument("stack_name_or_id")
@output_options
@click.pass_context
def resource_list(ctx: click.Context, stack_name_or_id: str, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List resources in a stack."""
    client = ctx.find_object(OrcaContext).ensure_client()
    stk = _resolve_stack(client, stack_name_or_id)
    s_name = stk["stack_name"]
    s_id = stk["id"]

    data = client.get(f"{_heat(client)}/stacks/{s_name}/{s_id}/resources")
    resources = data.get("resources", [])

    print_list(
        resources,
        [
            ("Name", "resource_name", {"style": "bold"}),
            ("Type", "resource_type"),
            ("Status", lambda r: _styled_status(r.get("resource_status", ""))),
            ("Physical ID", lambda r: r.get("physical_resource_id", "") or "—", {"style": "cyan", "no_wrap": True}),
        ],
        title=f"Resources — {s_name}",
        output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent,
        columns=columns,
        empty_msg="No resources found.",
    )


@stack.command("resource-show")
@click.argument("stack_name_or_id")
@click.argument("resource_name")
@output_options
@click.pass_context
def resource_show(ctx: click.Context, stack_name_or_id: str, resource_name: str, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show resource details."""
    client = ctx.find_object(OrcaContext).ensure_client()
    stk = _resolve_stack(client, stack_name_or_id)
    s_name = stk["stack_name"]
    s_id = stk["id"]

    data = client.get(f"{_heat(client)}/stacks/{s_name}/{s_id}/resources/{resource_name}")
    res = data.get("resource", data)

    fields = [
        ("resource_name", res.get("resource_name", "")),
        ("resource_type", res.get("resource_type", "")),
        ("resource_status", _styled_status(res.get("resource_status", ""))),
        ("resource_status_reason", res.get("resource_status_reason", "")),
        ("physical_resource_id", res.get("physical_resource_id", "") or "—"),
        ("logical_resource_id", res.get("logical_resource_id", "")),
        ("description", res.get("description", "")),
        ("creation_time", res.get("creation_time", "")),
        ("updated_time", res.get("updated_time", "") or "—"),
        ("attributes", str(res.get("attributes", {}))),
    ]

    print_detail(fields, output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent, columns=columns)


# ══════════════════════════════════════════════════════════════════════════
#  Stack Events
# ══════════════════════════════════════════════════════════════════════════

@stack.command("event-list")
@click.argument("stack_name_or_id")
@click.option("--resource", "resource_name", default=None, help="Filter by resource name.")
@click.option("--limit", "limit", type=int, default=None, help="Limit number of events.")
@output_options
@click.pass_context
def event_list(ctx: click.Context, stack_name_or_id: str, resource_name: str | None, limit: int | None,
               output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List stack events."""
    client = ctx.find_object(OrcaContext).ensure_client()
    stk = _resolve_stack(client, stack_name_or_id)
    s_name = stk["stack_name"]
    s_id = stk["id"]

    params: dict = {"sort_dir": "desc"}
    if limit is not None:
        params["limit"] = limit

    data = client.get(f"{_heat(client)}/stacks/{s_name}/{s_id}/events", params=params)
    events = data.get("events", [])

    if resource_name:
        events = [e for e in events if e.get("resource_name") == resource_name]

    print_list(
        events,
        [
            ("Timestamp", "event_time"),
            ("Resource", "resource_name", {"style": "bold"}),
            ("Status", lambda e: _styled_status(e.get("resource_status", ""))),
            ("Reason", lambda e: (e.get("resource_status_reason", "") or "")[:80]),
        ],
        title=f"Events — {s_name}",
        output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent,
        columns=columns,
        empty_msg="No events found.",
    )


@stack.command("event-show")
@click.argument("stack_name_or_id")
@click.argument("resource_name")
@click.argument("event_id")
@output_options
@click.pass_context
def event_show(ctx: click.Context, stack_name_or_id: str, resource_name: str, event_id: str,
               output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show event details."""
    client = ctx.find_object(OrcaContext).ensure_client()
    stk = _resolve_stack(client, stack_name_or_id)
    s_name = stk["stack_name"]
    s_id = stk["id"]

    data = client.get(f"{_heat(client)}/stacks/{s_name}/{s_id}/resources/{resource_name}/events/{event_id}")
    evt = data.get("event", data)

    fields = [
        ("id", evt.get("id", "")),
        ("event_time", evt.get("event_time", "")),
        ("resource_name", evt.get("resource_name", "")),
        ("resource_status", _styled_status(evt.get("resource_status", ""))),
        ("resource_status_reason", evt.get("resource_status_reason", "")),
        ("physical_resource_id", evt.get("physical_resource_id", "") or "—"),
        ("logical_resource_id", evt.get("logical_resource_id", "")),
        ("resource_type", evt.get("resource_type", "")),
    ]

    print_detail(fields, output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent, columns=columns)


# ══════════════════════════════════════════════════════════════════════════
#  Stack Outputs
# ══════════════════════════════════════════════════════════════════════════

@stack.command("output-list")
@click.argument("stack_name_or_id")
@output_options
@click.pass_context
def output_list(ctx: click.Context, stack_name_or_id: str, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List stack outputs."""
    client = ctx.find_object(OrcaContext).ensure_client()
    stk = _resolve_stack(client, stack_name_or_id)
    s_name = stk["stack_name"]
    s_id = stk["id"]

    data = client.get(f"{_heat(client)}/stacks/{s_name}/{s_id}/outputs")
    outputs = data.get("outputs", [])

    print_list(
        outputs,
        [
            ("Key", "output_key", {"style": "bold"}),
            ("Description", lambda o: o.get("description", "") or "—"),
        ],
        title=f"Outputs — {s_name}",
        output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent,
        columns=columns,
        empty_msg="No outputs found.",
    )


@stack.command("output-show")
@click.argument("stack_name_or_id")
@click.argument("key")
@output_options
@click.pass_context
def output_show(ctx: click.Context, stack_name_or_id: str, key: str, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show a specific stack output value."""
    client = ctx.find_object(OrcaContext).ensure_client()
    stk = _resolve_stack(client, stack_name_or_id)
    s_name = stk["stack_name"]
    s_id = stk["id"]

    data = client.get(f"{_heat(client)}/stacks/{s_name}/{s_id}/outputs/{key}")
    out = data.get("output", data)

    fields = [
        ("output_key", out.get("output_key", "")),
        ("output_value", str(out.get("output_value", ""))),
        ("description", out.get("description", "") or "—"),
    ]

    print_detail(fields, output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent, columns=columns)


# ══════════════════════════════════════════════════════════════════════════
#  Stack Template
# ══════════════════════════════════════════════════════════════════════════

@stack.command("template-show")
@click.argument("stack_name_or_id")
@click.pass_context
def template_show(ctx: click.Context, stack_name_or_id: str) -> None:
    """Show the stack template (YAML output)."""
    client = ctx.find_object(OrcaContext).ensure_client()
    stk = _resolve_stack(client, stack_name_or_id)
    s_name = stk["stack_name"]
    s_id = stk["id"]

    data = client.get(f"{_heat(client)}/stacks/{s_name}/{s_id}/template")

    from rich.syntax import Syntax
    yaml_output = yaml.dump(data, default_flow_style=False, sort_keys=False)
    console.print(Syntax(yaml_output, "yaml", theme="monokai"))


@stack.command("template-validate")
@click.option("--template", "-t", "template", required=True, help="Template file path or URL.")
@click.option("--environment", "-e", "environment", default=None, help="Environment file path.")
@click.option("--parameter", "parameters", multiple=True, help="Parameter key=value (repeatable).")
@click.pass_context
def template_validate(ctx: click.Context, template: str, environment: str | None,
                      parameters: tuple[str, ...]) -> None:
    """Validate a Heat template.

    \b
    Examples:
      orca stack template-validate -t template.yaml
      orca stack template-validate -t template.yaml -e env.yaml
    """
    client = ctx.find_object(OrcaContext).ensure_client()

    body: dict = {}

    if template.startswith(("http://", "https://")):
        body["template_url"] = template
    else:
        body["template"] = _load_template(template)

    if environment:
        body["environment"] = _load_environment(environment)

    if parameters:
        body["parameters"] = _parse_params(parameters)

    data = client.post(f"{_heat(client)}/validate", json=body)
    console.print("[green]Template is valid.[/green]")

    desc = data.get("Description", data.get("description", ""))
    if desc:
        console.print(f"[bold]Description:[/bold] {desc}")

    params = data.get("Parameters", data.get("parameters", {}))
    if params:
        console.print("[bold]Parameters:[/bold]")
        for name, details in params.items():
            ptype = details.get("Type", details.get("type", ""))
            default = details.get("Default", details.get("default", ""))
            pdesc = details.get("Description", details.get("description", ""))
            console.print(f"  [cyan]{name}[/cyan] ({ptype}) = {default!r}  {pdesc}")


# ══════════════════════════════════════════════════════════════════════════
#  Topology (enhanced view)
# ══════════════════════════════════════════════════════════════════════════

@stack.command("diff")
@click.argument("stack_name_or_id")
@click.option("--template", "-t", "template_path", required=True,
              type=click.Path(exists=True), help="Local template file to compare against.")
@click.pass_context
def stack_diff(ctx: click.Context, stack_name_or_id: str, template_path: str) -> None:
    """Compare a local template with a deployed stack's template.

    Fetches the currently deployed template from Heat and diffs it
    against the local file so you can review changes before running
    ``orca stack update``.

    \b
    Examples:
      orca stack diff my-stack -t template.yaml
      orca stack diff my-stack -t updated-template.yaml
    """
    import difflib

    from rich.syntax import Syntax

    client = ctx.find_object(OrcaContext).ensure_client()
    stk = _resolve_stack(client, stack_name_or_id)
    s_name = stk["stack_name"]
    s_id = stk["id"]

    # Fetch deployed template
    deployed = client.get(f"{_heat(client)}/stacks/{s_name}/{s_id}/template")
    deployed_yaml = yaml.dump(deployed, default_flow_style=False, sort_keys=True)

    # Load local template and normalise through YAML round-trip for fair comparison
    local_raw = _load_template(template_path)
    local_yaml = yaml.dump(local_raw, default_flow_style=False, sort_keys=True)

    deployed_lines = deployed_yaml.splitlines(keepends=True)
    local_lines = local_yaml.splitlines(keepends=True)

    diff = list(difflib.unified_diff(
        deployed_lines, local_lines,
        fromfile=f"deployed ({s_name})",
        tofile=template_path,
    ))

    if not diff:
        console.print(f"[green]No differences — local template matches deployed stack '{s_name}'.[/green]")
        return

    # Count changes
    additions = sum(1 for item in diff if item.startswith("+") and not item.startswith("+++"))
    removals = sum(1 for item in diff if item.startswith("-") and not item.startswith("---"))

    diff_text = "".join(diff)
    console.print(Syntax(diff_text, "diff", theme="monokai"))
    console.print(f"\n[bold]{additions} addition(s), {removals} removal(s)[/bold]")


@stack.command("topology")
@click.argument("stack_name_or_id")
@click.pass_context
def stack_topology(ctx: click.Context, stack_name_or_id: str) -> None:
    """Show stack resource topology as a tree."""
    from rich.tree import Tree

    client = ctx.find_object(OrcaContext).ensure_client()
    stk = _resolve_stack(client, stack_name_or_id)
    s_name = stk["stack_name"]
    s_id = stk["id"]
    s_status = stk.get("stack_status", "")

    tree = Tree(f"[bold]{s_name}[/bold]  {_styled_status(s_status)}")

    data = client.get(f"{_heat(client)}/stacks/{s_name}/{s_id}/resources")
    resources = data.get("resources", [])

    for res in resources:
        r_name = res.get("resource_name", "?")
        r_type = res.get("resource_type", "?")
        r_status = res.get("resource_status", "")
        r_phys = res.get("physical_resource_id", "") or "—"
        tree.add(
            f"[bold]{r_name}[/bold]  [dim]{r_type}[/dim]  "
            f"{_styled_status(r_status)}  [cyan]{r_phys}[/cyan]"
        )

    console.print(tree)


# ══════════════════════════════════════════════════════════════════════════
#  stack abandon
# ══════════════════════════════════════════════════════════════════════════

@stack.command("abandon")
@click.argument("stack_name_or_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.option("--output-file", "out_file", default=None,
              help="Save abandoned stack data to a JSON file.")
@click.pass_context
def stack_abandon(ctx: click.Context, stack_name_or_id: str, yes: bool,
                  out_file: str | None) -> None:
    """Abandon a stack (delete without destroying resources).

    Exports the stack's resource data, then removes the stack record from
    Heat without actually deleting the underlying OpenStack resources.
    """
    import json
    if not yes:
        click.confirm(f"Abandon stack {stack_name_or_id}? (Resources will NOT be deleted)", abort=True)
    client = ctx.find_object(OrcaContext).ensure_client()
    stk = _resolve_stack(client, stack_name_or_id)
    s_name = stk["stack_name"]
    s_id = stk["id"]
    data = client.delete(f"{_heat(client)}/stacks/{s_name}/{s_id}/abandon")
    if out_file:
        Path(out_file).write_text(json.dumps(data, indent=2))
        console.print(f"[green]Stack abandoned. Data written to {out_file}[/green]")
    else:
        console.print(json.dumps(data, indent=2))
        console.print(f"[green]Stack {stack_name_or_id} abandoned.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  stack resource-type-list / resource-type-show
# ══════════════════════════════════════════════════════════════════════════

@stack.command("resource-type-list")
@click.option("--filter", "filter_str", default=None,
              help="Filter resource types by name substring.")
@output_options
@click.pass_context
def stack_resource_type_list(ctx: click.Context, filter_str: str | None,
                             output_format: str, columns: tuple[str, ...],
                             fit_width: bool, max_width: int | None,
                             noindent: bool) -> None:
    """List available Heat resource types."""
    client = ctx.find_object(OrcaContext).ensure_client()
    params: dict = {}
    if filter_str:
        params["name"] = filter_str
    types = client.get(f"{_heat(client)}/resource_types",
                       params=params).get("resource_types", [])
    # resource_types is a list of strings
    items = [{"type": t} for t in types]
    print_list(
        items,
        [("Resource Type", "type", {"style": "cyan"})],
        title="Heat Resource Types",
        output_format=output_format, fit_width=fit_width, max_width=max_width,
        noindent=noindent, columns=columns,
        empty_msg="No resource types found.",
    )


@stack.command("resource-type-show")
@click.argument("resource_type")
@click.option("--template-type", type=click.Choice(["cfn", "hot"]),
              default="hot", show_default=True,
              help="Template format for the resource schema.")
@click.pass_context
def stack_resource_type_show(ctx: click.Context, resource_type: str,
                              template_type: str) -> None:
    """Show the schema for a Heat resource type."""
    import json
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_heat(client)}/resource_types/{resource_type}/template",
                      params={"template_type": template_type})
    console.print(json.dumps(data, indent=2))
