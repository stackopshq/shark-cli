"""``orca qos`` — manage Neutron QoS policies and rules."""

from __future__ import annotations

import click

from orca_cli.core.context import OrcaContext
from orca_cli.core.exceptions import OrcaCLIError
from orca_cli.core.output import console, output_options, print_detail, print_list
from orca_cli.core.validators import validate_id
from orca_cli.services.network import NetworkService

_RULE_TYPES = {
    "bandwidth-limit":   "bandwidth_limit_rules",
    "dscp-marking":      "dscp_marking_rules",
    "minimum-bandwidth": "minimum_bandwidth_rules",
    "minimum-packet-rate": "minimum_packet_rate_rules",
}


@click.group("qos")
def qos_policy() -> None:
    """Manage Neutron QoS policies and rules."""
    pass


# ── Policy CRUD ────────────────────────────────────────────────────────────

@qos_policy.group("policy")
def qos_policy_group() -> None:
    """Manage QoS policies."""


@qos_policy_group.command("list")
@click.option("--shared", is_flag=True, default=False, help="Show only shared policies.")
@output_options
@click.pass_context
def qos_policy_list(ctx, shared, output_format, columns, fit_width, max_width, noindent):
    """List QoS policies."""
    svc = NetworkService(ctx.find_object(OrcaContext).ensure_client())
    params = {"shared": True} if shared else None
    print_list(
        svc.find_qos_policies(params=params),
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Name", "name", {"style": "bold"}),
            ("Shared", lambda p: "Yes" if p.get("shared") else "No"),
            ("Default", lambda p: "Yes" if p.get("is_default") else "No"),
            ("Description", lambda p: (p.get("description") or "")[:40]),
        ],
        title="QoS Policies",
        output_format=output_format, fit_width=fit_width, max_width=max_width,
        noindent=noindent, columns=columns,
        empty_msg="No QoS policies found.",
    )


@qos_policy_group.command("show")
@click.argument("policy_id", callback=validate_id)
@output_options
@click.pass_context
def qos_policy_show(ctx, policy_id, output_format, columns, fit_width, max_width, noindent):
    """Show a QoS policy."""
    svc = NetworkService(ctx.find_object(OrcaContext).ensure_client())
    p = svc.get_qos_policy(policy_id)
    print_detail(
        [(k, str(p.get(k, "") or "")) for k in
         ["id", "name", "shared", "is_default", "description", "project_id"]],
        output_format=output_format, fit_width=fit_width, max_width=max_width,
        noindent=noindent, columns=columns,
    )


@qos_policy_group.command("create")
@click.option("--name", required=True, help="Policy name.")
@click.option("--shared", is_flag=True, default=False, help="Share with all projects.")
@click.option("--default", "is_default", is_flag=True, default=False,
              help="Set as default policy.")
@click.option("--description", default=None, help="Description.")
@click.pass_context
def qos_policy_create(ctx, name, shared, is_default, description):
    """Create a QoS policy."""
    svc = NetworkService(ctx.find_object(OrcaContext).ensure_client())
    body: dict = {"name": name, "shared": shared, "is_default": is_default}
    if description:
        body["description"] = description
    p = svc.create_qos_policy(body)
    console.print(f"[green]QoS policy '{name}' created: {p.get('id', '?')}[/green]")


@qos_policy_group.command("set")
@click.argument("policy_id", callback=validate_id)
@click.option("--name", default=None, help="New name.")
@click.option("--description", default=None, help="New description.")
@click.option("--shared/--no-shared", default=None, help="Share or un-share.")
@click.option("--default/--no-default", "is_default", default=None,
              help="Set or unset as default.")
@click.pass_context
def qos_policy_set(ctx, policy_id, name, description, shared, is_default):
    """Update a QoS policy."""
    body: dict = {}
    if name is not None:
        body["name"] = name
    if description is not None:
        body["description"] = description
    if shared is not None:
        body["shared"] = shared
    if is_default is not None:
        body["is_default"] = is_default
    if not body:
        console.print("[yellow]Nothing to update.[/yellow]")
        return
    svc = NetworkService(ctx.find_object(OrcaContext).ensure_client())
    svc.update_qos_policy(policy_id, body)
    console.print(f"[green]QoS policy {policy_id} updated.[/green]")


@qos_policy_group.command("delete")
@click.argument("policy_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def qos_policy_delete(ctx, policy_id, yes):
    """Delete a QoS policy."""
    svc = NetworkService(ctx.find_object(OrcaContext).ensure_client())
    if not yes:
        click.confirm(f"Delete QoS policy {policy_id}?", abort=True)
    svc.delete_qos_policy(policy_id)
    console.print(f"[green]QoS policy {policy_id} deleted.[/green]")


# ── Rules ─────────────────────────────────────────────────────────────────

@qos_policy.group("rule")
def qos_rule() -> None:
    """Manage QoS rules attached to a policy."""


@qos_rule.command("list")
@click.argument("policy_id", callback=validate_id)
@click.option("--type", "rule_type",
              type=click.Choice(list(_RULE_TYPES)),
              default="bandwidth-limit", show_default=True,
              help="Rule type.")
@output_options
@click.pass_context
def qos_rule_list(ctx, policy_id, rule_type,
                  output_format, columns, fit_width, max_width, noindent):
    """List QoS rules for a policy."""
    svc = NetworkService(ctx.find_object(OrcaContext).ensure_client())
    rules = svc.find_qos_rules(policy_id, _RULE_TYPES[rule_type])
    print_list(
        rules,
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Max Kbps", lambda r: str(r.get("max_kbps", "—"))),
            ("Max Burst Kbps", lambda r: str(r.get("max_burst_kbps", "—"))),
            ("Direction", lambda r: r.get("direction") or "—"),
            ("DSCP Mark", lambda r: str(r.get("dscp_mark", "—"))),
            ("Min Kbps", lambda r: str(r.get("min_kbps", "—"))),
        ],
        title=f"QoS {rule_type} rules for policy {policy_id}",
        output_format=output_format, fit_width=fit_width, max_width=max_width,
        noindent=noindent, columns=columns,
        empty_msg=f"No {rule_type} rules.",
    )


@qos_rule.command("create")
@click.argument("policy_id", callback=validate_id)
@click.option("--type", "rule_type",
              type=click.Choice(list(_RULE_TYPES)),
              default="bandwidth-limit", show_default=True,
              help="Rule type.")
@click.option("--max-kbps", type=int, default=None,
              help="Maximum bandwidth in kbps (bandwidth-limit).")
@click.option("--max-burst-kbps", type=int, default=None,
              help="Maximum burst bandwidth in kbps (bandwidth-limit).")
@click.option("--direction",
              type=click.Choice(["ingress", "egress"]), default="egress",
              help="Traffic direction (bandwidth-limit, minimum-bandwidth).")
@click.option("--dscp-mark", type=int, default=None,
              help="DSCP mark value 0-56 (dscp-marking).")
@click.option("--min-kbps", type=int, default=None,
              help="Minimum bandwidth in kbps (minimum-bandwidth).")
@click.pass_context
def qos_rule_create(ctx, policy_id, rule_type, max_kbps, max_burst_kbps,
                    direction, dscp_mark, min_kbps):
    """Create a QoS rule.

    \b
    Examples:
      orca qos rule-create <policy-id> --type bandwidth-limit --max-kbps 1000
      orca qos rule-create <policy-id> --type dscp-marking --dscp-mark 14
      orca qos rule-create <policy-id> --type minimum-bandwidth --min-kbps 500
    """
    svc = NetworkService(ctx.find_object(OrcaContext).ensure_client())
    endpoint = _RULE_TYPES[rule_type]

    body: dict = {}
    if rule_type == "bandwidth-limit":
        if max_kbps is None:
            raise OrcaCLIError("--max-kbps is required for bandwidth-limit rules.")
        body["max_kbps"] = max_kbps
        body["direction"] = direction
        if max_burst_kbps is not None:
            body["max_burst_kbps"] = max_burst_kbps
    elif rule_type == "dscp-marking":
        if dscp_mark is None:
            raise OrcaCLIError("--dscp-mark is required for dscp-marking rules.")
        body["dscp_mark"] = dscp_mark
    elif rule_type in ("minimum-bandwidth", "minimum-packet-rate"):
        if min_kbps is None:
            raise OrcaCLIError(f"--min-kbps is required for {rule_type} rules.")
        body["min_kbps"] = min_kbps
        body["direction"] = direction

    r = svc.create_qos_rule(policy_id, endpoint, body)
    console.print(f"[green]QoS {rule_type} rule created: {r.get('id', '?')}[/green]")


@qos_rule.command("delete")
@click.argument("policy_id", callback=validate_id)
@click.argument("rule_id", callback=validate_id)
@click.option("--type", "rule_type",
              type=click.Choice(list(_RULE_TYPES)),
              default="bandwidth-limit", show_default=True,
              help="Rule type.")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def qos_rule_delete(ctx, policy_id, rule_id, rule_type, yes):
    """Delete a QoS rule."""
    svc = NetworkService(ctx.find_object(OrcaContext).ensure_client())
    if not yes:
        click.confirm(f"Delete QoS {rule_type} rule {rule_id}?", abort=True)
    svc.delete_qos_rule(policy_id, _RULE_TYPES[rule_type], rule_id)
    console.print(f"[green]QoS rule {rule_id} deleted.[/green]")


# ── ADR-0008 deprecated aliases (backward compatibility) ────────────────
