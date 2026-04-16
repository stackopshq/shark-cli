"""``orca cleanup`` — find and remove orphaned resources in the current project."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import click

from orca_cli.core.context import OrcaContext
from orca_cli.core.exceptions import APIError
from orca_cli.core.output import console

# Resource types that can be detected and optionally deleted
CLEANUP_TYPES = [
    "floating-ip", "volume", "snapshot", "port",
    "security-group", "server", "router", "stack", "loadbalancer",
]

FAILED_STACK_STATUSES = {
    "CREATE_FAILED", "UPDATE_FAILED", "ROLLBACK_COMPLETE",
    "UPDATE_ROLLBACK_COMPLETE", "DELETE_FAILED",
}


def _collect(client, url: str, key: str, params: dict | None = None) -> list:
    """Fetch a resource list silently (returns [] if service unavailable)."""
    try:
        return client.get(url, params=params).get(key, [])
    except Exception:
        return []


def _age_days(resource: dict, key: str = "created_at") -> int | None:
    created = resource.get(key, "")
    if not created:
        return None
    try:
        dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt).days
    except (ValueError, TypeError):
        return None


@click.command()
@click.option("--delete", "do_delete", is_flag=True,
              help="Actually delete the detected orphaned resources.")
@click.option("--older-than", "older_than", type=int, default=None, metavar="DAYS",
              help="Flag volumes and snapshots older than N days (implies age check).")
@click.option("--skip", "skip_types", multiple=True,
              type=click.Choice(CLEANUP_TYPES),
              help="Resource type to skip (repeatable).")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation when deleting.")
@click.pass_context
def cleanup(ctx: click.Context, do_delete: bool, older_than: int | None,
            skip_types: tuple, yes: bool) -> None:
    """Find orphaned resources — unused IPs, detached volumes, broken stacks, etc.

    Detects the following by default:
      floating-ip   — not associated with any port
      volume        — detached & available, or in error state
      snapshot      — in error state; or older than --older-than days
      port          — no device attached
      security-group — non-default, not used by any server
      server        — in ERROR state
      router        — no external gateway and no attached interfaces
      stack         — in a failed/rollback state (requires Heat)
      loadbalancer  — in ERROR state (requires Octavia)

    By default only reports findings. Use --delete to clean up.

    \b
    Examples:
      orca cleanup
      orca cleanup --older-than 30
      orca cleanup --skip stack --skip loadbalancer
      orca cleanup --delete --yes
      orca cleanup --older-than 14 --delete --yes
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    skip = set(skip_types)
    issues: list[tuple[str, str, str, str]] = []  # (type, id, name, reason)

    cutoff: datetime | None = None
    if older_than is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=older_than)

    with console.status("[bold cyan]Scanning for orphaned resources…[/bold cyan]"):

        # ── Floating IPs not associated ──────────────────────────────────────
        if "floating-ip" not in skip:
            for f in _collect(client, f"{client.network_url}/v2.0/floatingips", "floatingips"):
                if not f.get("port_id"):
                    issues.append((
                        "floating-ip", f["id"],
                        f.get("floating_ip_address", ""),
                        "not associated with any port",
                    ))

        # ── Volumes ──────────────────────────────────────────────────────────
        if "volume" not in skip:
            for v in _collect(client, f"{client.volume_url}/volumes/detail", "volumes"):
                name = v.get("name") or "—"
                status = v.get("status", "")
                if status == "available" and not v.get("attachments"):
                    age = _age_days(v)
                    reason = "detached & available"
                    if cutoff and age is not None:
                        if age < older_than:
                            continue  # too recent, skip
                        reason = f"detached & available ({age}d old)"
                    issues.append(("volume", v["id"], name, reason))
                elif status == "error":
                    issues.append(("volume", v["id"], name, "error state"))

        # ── Snapshots ────────────────────────────────────────────────────────
        if "snapshot" not in skip:
            for s in _collect(client, f"{client.volume_url}/snapshots/detail", "snapshots"):
                name = s.get("name") or "—"
                if s.get("status") == "error":
                    issues.append(("snapshot", s["id"], name, "error state"))
                elif cutoff:
                    age = _age_days(s)
                    if age is not None and age >= older_than:
                        issues.append(("snapshot", s["id"], name, f"{age}d old"))

        # ── Ports without device ─────────────────────────────────────────────
        if "port" not in skip:
            for p in _collect(client, f"{client.network_url}/v2.0/ports", "ports"):
                if not p.get("device_id") and not p.get("device_owner"):
                    ips = ", ".join(
                        ip.get("ip_address", "") for ip in p.get("fixed_ips", [])
                    )
                    issues.append(("port", p["id"], ips or "—", "no device attached"))

        # ── Unused security groups ────────────────────────────────────────────
        if "security-group" not in skip:
            sgs = _collect(
                client, f"{client.network_url}/v2.0/security-groups", "security_groups"
            )
            servers = _collect(
                client, f"{client.compute_url}/servers/detail", "servers",
                params={"limit": 1000},
            )
            used_sg_ids: set[str] = set()
            for srv in servers:
                for sg in srv.get("security_groups", []):
                    used_sg_ids.add(sg.get("id") or sg.get("name", ""))
            for sg in sgs:
                if sg.get("name") == "default":
                    continue
                if sg["id"] not in used_sg_ids and sg.get("name") not in used_sg_ids:
                    issues.append((
                        "security-group", sg["id"], sg.get("name", ""),
                        "not used by any server",
                    ))

        # ── Servers in ERROR ─────────────────────────────────────────────────
        if "server" not in skip:
            # Reuse servers list if already fetched, otherwise fetch
            _servers = servers if "security-group" not in skip else _collect(
                client, f"{client.compute_url}/servers/detail", "servers",
                params={"limit": 1000},
            )
            for srv in _servers:
                if srv.get("status") == "ERROR":
                    issues.append((
                        "server", srv["id"], srv.get("name", ""), "error state",
                    ))

        # ── Routers with no gateway and no interfaces ────────────────────────
        if "router" not in skip:
            for r in _collect(client, f"{client.network_url}/v2.0/routers", "routers"):
                if r.get("external_gateway_info"):
                    continue
                ports = _collect(
                    client, f"{client.network_url}/v2.0/ports", "ports",
                    params={"device_id": r["id"],
                            "device_owner": "network:router_interface"},
                )
                if not ports:
                    issues.append((
                        "router", r["id"], r.get("name", ""),
                        "no external gateway and no attached interfaces",
                    ))

        # ── Heat stacks in failed/rollback state ─────────────────────────────
        if "stack" not in skip:
            for s in _collect(client, f"{client.orchestration_url}/stacks", "stacks"):
                if s.get("stack_status") in FAILED_STACK_STATUSES:
                    issues.append((
                        "stack", s["id"], s.get("stack_name", ""),
                        s.get("stack_status", "failed"),
                    ))

        # ── Load balancers in ERROR ───────────────────────────────────────────
        if "loadbalancer" not in skip:
            for lb in _collect(
                client,
                f"{client.load_balancer_url}/v2/lbaas/loadbalancers",
                "loadbalancers",
            ):
                if lb.get("provisioning_status") == "ERROR":
                    issues.append((
                        "loadbalancer", lb["id"], lb.get("name", ""),
                        "provisioning_status=ERROR",
                    ))

    # ── Report ────────────────────────────────────────────────────────────────
    if not issues:
        console.print("[bold green]No orphaned resources found.[/bold green]")
        return

    from rich.table import Table
    tbl = Table(title=f"Orphaned Resources ({len(issues)})", show_lines=False)
    tbl.add_column("Type", style="bold")
    tbl.add_column("ID", style="cyan", no_wrap=True)
    tbl.add_column("Name / Info")
    tbl.add_column("Reason", style="yellow")
    for rtype, rid, rname, reason in issues:
        tbl.add_row(rtype, rid, rname, reason)
    console.print()
    console.print(tbl)
    console.print()

    if not do_delete:
        console.print("[dim]Use --delete to clean up these resources.[/dim]")
        return

    # ── Delete ────────────────────────────────────────────────────────────────
    if not yes:
        click.confirm(f"Delete {len(issues)} orphaned resource(s)?", abort=True)

    success = 0
    for rtype, rid, rname, reason in issues:
        label = f"{rtype} {rname} ({rid})"
        try:
            if rtype == "floating-ip":
                client.delete(f"{client.network_url}/v2.0/floatingips/{rid}")
            elif rtype == "volume":
                client.delete(f"{client.volume_url}/volumes/{rid}?cascade=true")
            elif rtype == "snapshot":
                client.delete(f"{client.volume_url}/snapshots/{rid}")
            elif rtype == "port":
                client.delete(f"{client.network_url}/v2.0/ports/{rid}")
            elif rtype == "security-group":
                client.delete(f"{client.network_url}/v2.0/security-groups/{rid}")
            elif rtype == "server":
                client.delete(f"{client.compute_url}/servers/{rid}")
            elif rtype == "router":
                client.delete(f"{client.network_url}/v2.0/routers/{rid}")
            elif rtype == "stack":
                client.delete(f"{client.orchestration_url}/stacks/{rname}/{rid}")
            elif rtype == "loadbalancer":
                client.delete(
                    f"{client.load_balancer_url}/v2/lbaas/loadbalancers/{rid}?cascade=true"
                )
            console.print(f"  [green]✓[/green] {label}")
            success += 1
        except APIError as exc:
            console.print(f"  [red]✗[/red] {label}: {exc}")
        except Exception as exc:
            console.print(f"  [red]✗[/red] {label}: {exc}")

    console.print(f"\n[bold]{success}/{len(issues)} resources cleaned up.[/bold]")
