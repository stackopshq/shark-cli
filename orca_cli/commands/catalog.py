"""``orca catalog`` — list available service endpoints from Keystone."""

from __future__ import annotations

import click

from orca_cli.core.context import OrcaContext
from orca_cli.core.output import console, output_options, print_list


@click.command("catalog")
@output_options
@click.pass_context
def catalog(ctx: click.Context, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List available service endpoints from the Keystone catalog."""
    client = ctx.find_object(OrcaContext).ensure_client()

    if not client._catalog:
        console.print("[yellow]No service catalog available.[/yellow]")
        return

    items = []
    for svc in client._catalog:
        for ep in svc.get("endpoints", []):
            items.append({
                "service": svc.get("name", ""),
                "type": svc.get("type", ""),
                "interface": ep.get("interface", ""),
                "url": ep.get("url", ""),
            })

    print_list(
        items,
        [
            ("Service", "service", {"style": "bold"}),
            ("Type", "type", {"style": "cyan"}),
            ("Interface", "interface"),
            ("URL", "url"),
        ],
        title="Service Catalog",
        output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent,
        columns=columns,
        empty_msg="No service catalog available.",
    )
