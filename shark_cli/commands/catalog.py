"""``shark catalog`` — list available service endpoints from Keystone."""

from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from shark_cli.core.context import SharkContext

console = Console()


@click.command("catalog")
@click.pass_context
def catalog(ctx: click.Context) -> None:
    """List available service endpoints from the Keystone catalog."""
    client = ctx.find_object(SharkContext).ensure_client()

    if not client._catalog:
        console.print("[yellow]No service catalog available.[/yellow]")
        return

    table = Table(title="Service Catalog", show_lines=True)
    table.add_column("Service", style="bold")
    table.add_column("Type", style="cyan")
    table.add_column("Interface")
    table.add_column("URL")

    for svc in client._catalog:
        svc_name = svc.get("name", "")
        svc_type = svc.get("type", "")
        for ep in svc.get("endpoints", []):
            table.add_row(
                svc_name,
                svc_type,
                ep.get("interface", ""),
                ep.get("url", ""),
            )

    console.print(table)
