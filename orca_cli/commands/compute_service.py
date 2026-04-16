"""``orca compute-service`` — manage Nova compute services (operator)."""

from __future__ import annotations

import click

from orca_cli.core.context import OrcaContext
from orca_cli.core.output import console, output_options, print_list


@click.group("compute-service")
def compute_service() -> None:
    """Manage Nova compute services (nova-compute, nova-conductor, …)."""
    pass


@compute_service.command("list")
@click.option("--host", default=None, help="Filter by hostname.")
@click.option("--binary", default=None, help="Filter by binary (e.g. nova-compute).")
@output_options
@click.pass_context
def compute_service_list(ctx, host, binary,
                         output_format, columns, fit_width, max_width, noindent):
    """List compute services."""
    client = ctx.find_object(OrcaContext).ensure_client()
    params = {}
    if host:
        params["host"] = host
    if binary:
        params["binary"] = binary

    services = client.get(f"{client.compute_url}/os-services",
                          params=params).get("services", [])

    print_list(
        services,
        [
            ("ID", "id", {"style": "cyan"}),
            ("Binary", "binary", {"style": "bold"}),
            ("Host", "host"),
            ("Zone", lambda s: s.get("zone") or "—"),
            ("Status", lambda s: (
                "[green]enabled[/green]" if s.get("status") == "enabled"
                else "[yellow]disabled[/yellow]"
            )),
            ("State", lambda s: (
                "[green]up[/green]" if s.get("state") == "up"
                else "[red]down[/red]"
            )),
            ("Updated", lambda s: (s.get("updated_at") or "")[:19]),
            ("Disabled Reason", lambda s: s.get("disabled_reason") or "—"),
        ],
        title="Compute Services",
        output_format=output_format, fit_width=fit_width, max_width=max_width,
        noindent=noindent, columns=columns,
        empty_msg="No compute services found.",
    )


@compute_service.command("set")
@click.argument("service_id")
@click.option("--enable/--disable", default=None,
              help="Enable or disable the service.")
@click.option("--disabled-reason", default=None,
              help="Reason for disabling (used with --disable).")
@click.option("--force-down/--no-force-down", default=None,
              help="Force the service down (for evacuate scenarios).")
@click.pass_context
def compute_service_set(ctx, service_id, enable, disabled_reason, force_down):
    """Enable, disable, or force-down a compute service.

    \b
    Examples:
      orca compute-service set 1 --disable --disabled-reason "maintenance"
      orca compute-service set 1 --enable
      orca compute-service set 1 --force-down
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {}

    if enable is not None:
        body["status"] = "enabled" if enable else "disabled"
    if disabled_reason is not None:
        body["disabled_reason"] = disabled_reason
    if force_down is not None:
        body["forced_down"] = force_down

    if not body:
        console.print("[yellow]Nothing to update. Use --enable/--disable or --force-down.[/yellow]")
        return

    client.put(f"{client.compute_url}/os-services/{service_id}", json=body)
    console.print(f"[green]Compute service {service_id} updated.[/green]")


@compute_service.command("delete")
@click.argument("service_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def compute_service_delete(ctx, service_id, yes):
    """Force-delete a compute service record.

    Use this to remove stale service entries after a host is decommissioned.
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    if not yes:
        click.confirm(f"Force-delete compute service {service_id}?", abort=True)
    client.delete(f"{client.compute_url}/os-services/{service_id}")
    console.print(f"[green]Compute service {service_id} deleted.[/green]")
