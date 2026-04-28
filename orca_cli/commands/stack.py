"""``orca stack`` — manage Heat stacks (orchestration)."""

from __future__ import annotations

import datetime
import json
import time
from pathlib import Path

import click
import yaml

from orca_cli.core.context import OrcaContext
from orca_cli.core.exceptions import OrcaCLIError
from orca_cli.core.output import console, output_options, print_detail, print_list
from orca_cli.core.validators import safe_output_path, validate_id
from orca_cli.models.orchestration import Stack
from orca_cli.services.orchestration import OrchestrationService

# ── Helpers ──────────────────────────────────────────────────────────────


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


def _resolve_stack(client, stack: str) -> Stack:
    """GET a stack by name or ID, returning the full stack dict.

    Heat's ``GET /stacks/<name>`` returns a 302 redirect to
    ``/stacks/<name>/<id>``.  To avoid following redirects we first list
    stacks filtered by name and derive the canonical URL ourselves.
    """
    svc = OrchestrationService(client)
    # Try listing by name first (no redirect risk)
    stacks = svc.find(params={"name": stack})
    if stacks:
        s = stacks[0]
        name = s.get("stack_name", stack)
        sid = s.get("id", "")
        return svc.get(name, sid)
    # Caller may have passed a UUID — list with id filter (Heat accepts
    # both query keys, but a name=<uuid> filter returns nothing).
    stacks = svc.find(params={"id": stack})
    if stacks:
        s = stacks[0]
        name = s.get("stack_name", stack)
        sid = s.get("id", stack)
        return svc.get(name, sid)
    # Fallback: maybe caller passed the canonical ``name/id`` form
    try:
        return svc.get(stack)
    except Exception as exc:
        raise OrcaCLIError(f"Stack not found: {stack}") from exc


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
    parsed: dict = yaml.safe_load(content) or {}
    result = _stringify_dates(parsed)
    assert isinstance(result, dict)  # noqa: S101 — invariant: dict in -> dict out
    return result


def _load_environment(path: str) -> dict:
    """Read a local environment file and return it as a dict."""
    content = Path(path).read_text()
    parsed: dict = yaml.safe_load(content) or {}
    result = _stringify_dates(parsed)
    assert isinstance(result, dict)  # noqa: S101 — invariant: dict in -> dict out
    return result


def _wait_for_stack(client, stack_name: str, stack_id: str, action: str) -> Stack:
    """Poll stack status until a terminal state is reached."""
    svc = OrchestrationService(client)
    terminal_suffixes = ("_COMPLETE", "_FAILED")
    with console.status(f"[bold cyan]Waiting for stack {action}..."):
        while True:
            stk = svc.get(stack_name, stack_id)
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
    svc = OrchestrationService(client)
    stacks = svc.find()

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

    svc = OrchestrationService(client)
    stk = svc.create(body)
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

    OrchestrationService(client).update(s_name, s_id, body)
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

    OrchestrationService(client).delete(s_name, s_id)
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
    OrchestrationService(client).action(s_name, s_id, action)
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

    resources = OrchestrationService(client).find_resources(s_name, s_id)

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

    res = OrchestrationService(client).get_resource(s_name, s_id, resource_name)

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

    events = OrchestrationService(client).find_events(s_name, s_id, params=params)

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

    evt = OrchestrationService(client).get_event(s_name, s_id, resource_name, event_id)

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

    outputs = OrchestrationService(client).find_outputs(s_name, s_id)

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

    out = OrchestrationService(client).get_output(s_name, s_id, key)

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

    data = OrchestrationService(client).get_template(s_name, s_id)

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

    data = OrchestrationService(client).validate_template(body)
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
    deployed = OrchestrationService(client).get_template(s_name, s_id)
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

    resources = OrchestrationService(client).find_resources(s_name, s_id)

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
    data = OrchestrationService(client).abandon(s_name, s_id)
    if out_file:
        out = safe_output_path(out_file)
        out.write_text(json.dumps(data, indent=2))
        console.print(f"[green]Stack abandoned. Data written to {out}[/green]")
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
    types = OrchestrationService(client).find_resource_types(
        params=params or None,
    )
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
    data = OrchestrationService(client).get_resource_type_template(
        resource_type, params={"template_type": template_type},
    )
    console.print(json.dumps(data, indent=2))


# ══════════════════════════════════════════════════════════════════════
#  stack snapshot
# ══════════════════════════════════════════════════════════════════════


@stack.group("snapshot")
def stack_snapshot() -> None:
    """Manage stack snapshots (Heat snapshot/restore)."""


@stack_snapshot.command("create")
@click.argument("stack_name_or_id")
@click.option("--name", default=None, help="Snapshot name (auto if omitted).")
@click.pass_context
def stack_snapshot_create(ctx, stack_name_or_id, name):
    """Take a snapshot of a stack's current state."""
    client = ctx.find_object(OrcaContext).ensure_client()
    stk = _resolve_stack(client, stack_name_or_id)
    snap = OrchestrationService(client).create_snapshot(
        stk["stack_name"], stk["id"], snapshot_name=name,
    )
    console.print(f"[green]Snapshot created: {snap.get('id', '?')}[/green]")


@stack_snapshot.command("list")
@click.argument("stack_name_or_id")
@output_options
@click.pass_context
def stack_snapshot_list(ctx, stack_name_or_id,
                         output_format, columns, fit_width, max_width, noindent):
    """List snapshots of a stack."""
    client = ctx.find_object(OrcaContext).ensure_client()
    stk = _resolve_stack(client, stack_name_or_id)
    items = OrchestrationService(client).find_snapshots(
        stk["stack_name"], stk["id"],
    )
    if not items:
        console.print("No snapshots found.")
        return
    print_list(
        items,
        [("ID", "id"), ("Name", "name"), ("Status", "status"),
         ("Status Reason", "status_reason"), ("Created", "creation_time")],
        title=f"Snapshots of stack {stk['stack_name']}",
        output_format=output_format, columns=columns,
        fit_width=fit_width, max_width=max_width, noindent=noindent,
    )


@stack_snapshot.command("show")
@click.argument("stack_name_or_id")
@click.argument("snapshot_id", callback=validate_id)
@output_options
@click.pass_context
def stack_snapshot_show(ctx, stack_name_or_id, snapshot_id,
                         output_format, columns, fit_width, max_width, noindent):
    """Show a stack snapshot."""
    client = ctx.find_object(OrcaContext).ensure_client()
    stk = _resolve_stack(client, stack_name_or_id)
    snap = OrchestrationService(client).get_snapshot(
        stk["stack_name"], stk["id"], snapshot_id,
    )
    console.print(json.dumps(snap, indent=2))


@stack_snapshot.command("delete")
@click.argument("stack_name_or_id")
@click.argument("snapshot_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def stack_snapshot_delete(ctx, stack_name_or_id, snapshot_id, yes):
    """Delete a stack snapshot."""
    if not yes:
        click.confirm(f"Delete snapshot {snapshot_id}?", abort=True)
    client = ctx.find_object(OrcaContext).ensure_client()
    stk = _resolve_stack(client, stack_name_or_id)
    OrchestrationService(client).delete_snapshot(
        stk["stack_name"], stk["id"], snapshot_id,
    )
    console.print(f"[green]Snapshot {snapshot_id} deleted.[/green]")


@stack_snapshot.command("restore")
@click.argument("stack_name_or_id")
@click.argument("snapshot_id", callback=validate_id)
@click.pass_context
def stack_snapshot_restore(ctx, stack_name_or_id, snapshot_id):
    """Restore a stack to a previous snapshot."""
    client = ctx.find_object(OrcaContext).ensure_client()
    stk = _resolve_stack(client, stack_name_or_id)
    OrchestrationService(client).restore_snapshot(
        stk["stack_name"], stk["id"], snapshot_id,
    )
    console.print(f"[green]Stack restoring from snapshot {snapshot_id}...[/green]")


# ══════════════════════════════════════════════════════════════════════
#  stack adopt / files / environment / failures
# ══════════════════════════════════════════════════════════════════════


@stack.command("adopt")
@click.argument("name")
@click.option("-t", "--template", required=True,
              type=click.Path(exists=True, dir_okay=False),
              help="Template file (yaml/json).")
@click.option("--adopt-file", required=True,
              type=click.Path(exists=True, dir_okay=False),
              help="JSON file with the adopt_stack_data payload "
                   "(existing resources to adopt).")
@click.option("--parameter", multiple=True,
              help="Parameter key=value (repeatable).")
@click.option("--timeout", type=int, default=None,
              help="Timeout in minutes.")
@click.pass_context
def stack_adopt(ctx, name, template, adopt_file, parameter, timeout):
    """Adopt existing resources into a new stack."""
    from pathlib import Path
    tpl = Path(template).read_text()
    adopt_data = Path(adopt_file).read_text()
    body: dict = {
        "stack_name": name,
        "template": tpl,
        "adopt_stack_data": adopt_data,
        "parameters": _parse_params(parameter),
    }
    if timeout is not None:
        body["timeout_mins"] = timeout
    client = ctx.find_object(OrcaContext).ensure_client()
    stk = OrchestrationService(client).adopt(body)
    console.print(f"[green]Stack '{name}' adopted: {stk.get('id', '?')}[/green]")


@stack.group("environment")
def stack_environment() -> None:
    """Inspect a stack's resolved environment."""


@stack_environment.command("show")
@click.argument("stack_name_or_id")
@click.pass_context
def stack_environment_show(ctx, stack_name_or_id):
    """Show the resolved environment of a stack."""
    client = ctx.find_object(OrcaContext).ensure_client()
    stk = _resolve_stack(client, stack_name_or_id)
    env = OrchestrationService(client).get_environment(
        stk["stack_name"], stk["id"],
    )
    console.print(json.dumps(env, indent=2))


@stack.group("file")
def stack_file() -> None:
    """Inspect files referenced by a stack template."""


@stack_file.command("list")
@click.argument("stack_name_or_id")
@click.pass_context
def stack_file_list(ctx, stack_name_or_id):
    """List local files referenced by a stack template."""
    client = ctx.find_object(OrcaContext).ensure_client()
    stk = _resolve_stack(client, stack_name_or_id)
    files = OrchestrationService(client).get_files(stk["stack_name"], stk["id"])
    if not files:
        console.print("No files referenced.")
        return
    for path in sorted(files):
        console.print(path)


@stack.group("failures")
def stack_failures() -> None:
    """Inspect failed events on a stack."""


@stack_failures.command("list")
@click.argument("stack_name_or_id")
@click.pass_context
def stack_failures_list(ctx, stack_name_or_id):
    """List events on a stack whose resource_status is FAILED."""
    client = ctx.find_object(OrcaContext).ensure_client()
    svc = OrchestrationService(client)
    stk = _resolve_stack(client, stack_name_or_id)
    events = svc.find_events(stk["stack_name"], stk["id"])
    failures = [e for e in events if "FAILED" in (e.get("resource_status") or "")]
    if not failures:
        console.print("No failed events on this stack.")
        return
    print_list(
        failures,
        [("Resource", "resource_name"),
         ("Status", "resource_status"),
         ("Reason", "resource_status_reason"),
         ("Time", "event_time")],
        title=f"Failures on {stk['stack_name']}",
        output_format="table",
    )


# ══════════════════════════════════════════════════════════════════════
#  stack resource actions: signal, mark-unhealthy, metadata
#
# Note: ``resource-list`` and ``resource-show`` exist as legacy
# top-level commands (whitelisted in test_naming_convention). The new
# action sub-commands live under a dedicated ``resource`` sub-group.
# ══════════════════════════════════════════════════════════════════════


@stack.group("resource")
def stack_resource() -> None:
    """Per-resource actions on a stack (signal, metadata, mark-unhealthy)."""


@stack_resource.command("signal")
@click.argument("stack_name_or_id")
@click.argument("resource_name")
@click.option("--data", default=None,
              help="JSON body to send as the signal payload.")
@click.pass_context
def stack_resource_signal(ctx, stack_name_or_id, resource_name, data):
    """Send a signal to a stack resource (e.g. WaitCondition)."""
    body = json.loads(data) if data else {}
    client = ctx.find_object(OrcaContext).ensure_client()
    stk = _resolve_stack(client, stack_name_or_id)
    OrchestrationService(client).signal_resource(
        stk["stack_name"], stk["id"], resource_name, body,
    )
    console.print(f"[green]Signal sent to resource {resource_name}.[/green]")


@stack_resource.command("mark-unhealthy")
@click.argument("stack_name_or_id")
@click.argument("resource_name")
@click.option("--reason", default=None, help="Status reason.")
@click.pass_context
def stack_resource_mark_unhealthy(ctx, stack_name_or_id, resource_name, reason):
    """Mark a stack resource as unhealthy (forces re-create on update)."""
    client = ctx.find_object(OrcaContext).ensure_client()
    stk = _resolve_stack(client, stack_name_or_id)
    OrchestrationService(client).mark_resource_unhealthy(
        stk["stack_name"], stk["id"], resource_name, status_reason=reason,
    )
    console.print(f"[green]Resource {resource_name} marked unhealthy.[/green]")


@stack_resource.command("metadata")
@click.argument("stack_name_or_id")
@click.argument("resource_name")
@click.pass_context
def stack_resource_metadata(ctx, stack_name_or_id, resource_name):
    """Show the metadata of a stack resource."""
    client = ctx.find_object(OrcaContext).ensure_client()
    stk = _resolve_stack(client, stack_name_or_id)
    meta = OrchestrationService(client).get_resource_metadata(
        stk["stack_name"], stk["id"], resource_name,
    )
    console.print(json.dumps(meta, indent=2))
