"""``orca limits`` — show compute limits and quotas."""

from __future__ import annotations

import click

from orca_cli.core.context import OrcaContext


def _nova(client) -> str:
    return client.compute_url


@click.group()
@click.pass_context
def limits(ctx: click.Context) -> None:
    """Show compute limits and quotas."""
    pass


@limits.command("show")
@click.option("--project", "project_id", default=None, help="Show limits for a specific project (admin).")
@click.pass_context
def limits_show(ctx, project_id):
    """Show compute quotas and current usage for this project."""
    client = ctx.find_object(OrcaContext).ensure_client()
    params = {}
    if project_id:
        params["tenant_id"] = project_id
    data = client.get(f"{_nova(client)}/limits", params=params)
    lims = data.get("limits", {})
    absolute = lims.get("absolute", {})

    from rich.table import Table
    table = Table(title="Compute Limits", show_lines=False)
    table.add_column("Resource", style="bold")
    table.add_column("Used", justify="right")
    table.add_column("Max", justify="right")

    pairs = [
        ("Instances", "totalInstancesUsed", "maxTotalInstances"),
        ("vCPUs", "totalCoresUsed", "maxTotalCores"),
        ("RAM (MB)", "totalRAMUsed", "maxTotalRAMSize"),
        ("Keypairs", "totalKeyPairsUsed", "maxTotalKeypairs"),
        ("Security Groups", "totalSecurityGroupsUsed", "maxTotalSecurityGroups"),
        ("Floating IPs", "totalFloatingIpsUsed", "maxTotalFloatingIps"),
        ("Server Meta", None, "maxServerMeta"),
        ("Injected Files", None, "maxInjectedFiles"),
        ("Injected File Size", None, "maxInjectedFileContentBytes"),
    ]

    from orca_cli.core.output import console as _console
    for label, used_key, max_key in pairs:
        used = str(absolute.get(used_key, "—")) if used_key else "—"
        max_val = str(absolute.get(max_key, "—"))
        table.add_row(label, used, max_val)

    _console.print(table)
