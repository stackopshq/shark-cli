"""Live auto-refreshing dashboard for OpenStack project resources."""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any

import click
from rich.console import Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from orca_cli.core.context import OrcaContext
from orca_cli.core.output import console

# ── Status colour mapping ────────────────────────────────────────────────

_STATUS_COLORS: dict[str, str] = {
    "ACTIVE": "green",
    "SHUTOFF": "dim",
    "ERROR": "red bold",
    "BUILD": "yellow",
    "RESIZE": "magenta",
    "VERIFY_RESIZE": "magenta",
    "PAUSED": "yellow",
    "SUSPENDED": "yellow",
    "SHELVED": "dim",
    "SHELVED_OFFLOADED": "dim",
    "DELETED": "dim strike",
    "REBOOT": "cyan",
    "HARD_REBOOT": "cyan",
    "MIGRATING": "magenta",
    "RESCUE": "yellow",
}


def _styled_status(status: str) -> Text:
    """Return a Rich Text object with colour applied for the given status."""
    style = _STATUS_COLORS.get(status.upper(), "white")
    return Text(status.upper(), style=style)


# ── IP extraction helper ─────────────────────────────────────────────────

def _extract_ip(addresses: dict[str, list[dict]]) -> str:
    """Pick the best IP to display — prefer floating, fall back to first fixed."""
    floating: str | None = None
    first_fixed: str | None = None

    for net_name, addrs in addresses.items():
        for addr in addrs:
            addr_type = addr.get("OS-EXT-IPS:type", "")
            if addr_type == "floating" or "floating" in net_name.lower():
                floating = floating or addr.get("addr", "")
            elif first_fixed is None:
                first_fixed = addr.get("addr", "")

    return floating or first_fixed or "—"


# ── Safe API fetchers ────────────────────────────────────────────────────

def _fetch_servers(client: Any) -> list[dict]:
    try:
        data = client.get(f"{client.compute_url}/servers/detail")
        return data.get("servers", [])
    except Exception:
        return []


def _fetch_volumes(client: Any) -> list[dict]:
    try:
        data = client.get(f"{client.volume_url}/volumes/detail")
        return data.get("volumes", [])
    except Exception:
        return []


def _fetch_floating_ips(client: Any) -> list[dict]:
    try:
        data = client.get(f"{client.network_url}/v2.0/floatingips")
        return data.get("floatingips", [])
    except Exception:
        return []


def _fetch_networks(client: Any) -> list[dict]:
    try:
        data = client.get(f"{client.network_url}/v2.0/networks")
        return data.get("networks", [])
    except Exception:
        return []


def _fetch_recent_events(client: Any, servers: list[dict], limit: int = 5) -> list[dict]:
    """Fetch the most recent instance actions across the first N servers."""
    events: list[dict] = []
    for srv in servers[:10]:
        try:
            data = client.get(
                f"{client.compute_url}/servers/{srv['id']}/os-instance-actions"
            )
            actions = data.get("instanceActions", [])
            for action in actions:
                action["_server_name"] = srv.get("name", srv["id"][:8])
            events.extend(actions)
        except Exception:
            continue

    # Sort by start_time descending, take the most recent ones
    events.sort(key=lambda e: e.get("start_time", ""), reverse=True)
    return events[:limit]


# ── Dashboard builder ────────────────────────────────────────────────────

def _build_dashboard(client: Any, interval: int) -> Group:
    """Assemble the full dashboard renderable."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Fetch data
    servers = _fetch_servers(client)
    volumes = _fetch_volumes(client)
    fips = _fetch_floating_ips(client)
    networks = _fetch_networks(client)
    events = _fetch_recent_events(client, servers)

    # ── Header ────────────────────────────────────────────────────────
    header = Text.assemble(
        ("  orca watch", "bold cyan"),
        ("  —  ", "dim"),
        (now, "bold white"),
        ("  —  ", "dim"),
        (f"refresh every {interval}s", "dim"),
        ("  —  ", "dim"),
        ("press Ctrl+C to exit", "dim italic"),
    )

    # ── Servers table ─────────────────────────────────────────────────
    srv_table = Table(
        title="Servers",
        title_style="bold cyan",
        expand=True,
        show_lines=False,
        border_style="bright_black",
        header_style="bold",
        padding=(0, 1),
    )
    srv_table.add_column("ID", style="dim", max_width=8, no_wrap=True)
    srv_table.add_column("Name", style="bold")
    srv_table.add_column("Status", no_wrap=True)
    srv_table.add_column("Flavor", style="cyan")
    srv_table.add_column("IP", style="yellow")

    if servers:
        for s in servers:
            flavor_name = ""
            flavor_info = s.get("flavor", {})
            if isinstance(flavor_info, dict):
                flavor_name = flavor_info.get("original_name", "") or flavor_info.get("id", "")
            srv_table.add_row(
                s["id"][:8],
                s.get("name", ""),
                _styled_status(s.get("status", "UNKNOWN")),
                str(flavor_name),
                _extract_ip(s.get("addresses", {})),
            )
    else:
        srv_table.add_row("—", "No servers found", "", "", "")

    # ── Resource summary ──────────────────────────────────────────────
    active_servers = sum(1 for s in servers if s.get("status", "").upper() == "ACTIVE")
    total_servers = len(servers)

    in_use_volumes = sum(1 for v in volumes if v.get("status", "").lower() == "in-use")
    total_volumes = len(volumes)
    total_vol_gb = sum(v.get("size", 0) for v in volumes)

    assigned_fips = sum(1 for f in fips if f.get("fixed_ip_address"))
    total_fips = len(fips)

    total_networks = len(networks)

    summary_parts = [
        ("Servers: ", "bold"),
        (f"{active_servers} active", "green"),
        (f" / {total_servers} total", ""),
        ("  |  ", "dim"),
        ("Volumes: ", "bold"),
        (f"{in_use_volumes} in-use", "green"),
        (f" / {total_volumes} total", ""),
        (f" ({total_vol_gb} GB)", "dim"),
        ("  |  ", "dim"),
        ("Floating IPs: ", "bold"),
        (f"{assigned_fips} assigned", "green"),
        (f" / {total_fips} total", ""),
        ("  |  ", "dim"),
        ("Networks: ", "bold"),
        (f"{total_networks}", ""),
    ]

    # Handle N/A cases inline
    if not volumes and total_volumes == 0:
        summary_parts[4:8] = [("Volumes: ", "bold"), ("N/A", "dim")]
    if not fips and total_fips == 0:
        pass  # 0/0 is fine — means no floating IPs provisioned

    summary_text = Text.assemble(*summary_parts)
    summary_panel = Panel(
        summary_text,
        title="Resources",
        title_align="left",
        border_style="bright_black",
        padding=(0, 1),
    )

    # ── Recent events table ───────────────────────────────────────────
    evt_table = Table(
        title="Recent Events",
        title_style="bold cyan",
        expand=True,
        show_lines=False,
        border_style="bright_black",
        header_style="bold",
        padding=(0, 1),
    )
    evt_table.add_column("Timestamp", style="dim", no_wrap=True)
    evt_table.add_column("Server", style="bold")
    evt_table.add_column("Action", style="cyan")
    evt_table.add_column("Status", no_wrap=True)

    if events:
        for ev in events:
            ts = ev.get("start_time", "—")
            if ts and len(ts) > 19:
                ts = ts[:19]
            action_status = ev.get("message", "") or ev.get("result", "—") or "—"
            evt_table.add_row(
                ts,
                ev.get("_server_name", "—"),
                ev.get("action", "—"),
                action_status,
            )
    else:
        evt_table.add_row("—", "No recent events", "", "")

    # ── Compose layout ────────────────────────────────────────────────
    return Group(
        header,
        Text(""),
        Panel(srv_table, border_style="bright_black", padding=(0, 0)),
        summary_panel,
        Panel(evt_table, border_style="bright_black", padding=(0, 0)),
    )


# ── Click command ────────────────────────────────────────────────────────

@click.command()
@click.option(
    "--interval", "-i",
    default=10,
    show_default=True,
    type=click.IntRange(min=1),
    help="Refresh interval in seconds.",
)
@click.pass_context
def watch(ctx: click.Context, interval: int) -> None:  # pragma: no cover
    """Live dashboard — auto-refreshing project overview."""
    client = ctx.find_object(OrcaContext).ensure_client()

    try:
        with Live(console=console, refresh_per_second=1, screen=True) as live:
            while True:
                renderable = _build_dashboard(client, interval)
                live.update(renderable)
                time.sleep(interval)
    except KeyboardInterrupt:
        pass
