"""``orca quota`` — show project quotas and usage (Nova + Neutron + Cinder)."""

from __future__ import annotations

import click

from orca_cli.core.context import OrcaContext
from orca_cli.core.output import console, output_options, print_list
from orca_cli.services.compute import ComputeService
from orca_cli.services.network import NetworkService
from orca_cli.services.volume import VolumeService


@click.command()
@output_options
@click.pass_context
def quota(ctx: click.Context, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show project quotas — Nova, Neutron and Cinder usage vs limits."""
    client = ctx.find_object(OrcaContext).ensure_client()

    rows: list[dict] = []

    with console.status("[bold cyan]Fetching quotas…[/bold cyan]"):
        # ── Nova (compute) ───────────────────────────────────────────
        try:
            nova = ComputeService(client).get_limits()
            rows.extend([
                _row("Compute", "Instances", nova.get("totalInstancesUsed", 0), nova.get("maxTotalInstances", -1)),
                _row("Compute", "vCPUs", nova.get("totalCoresUsed", 0), nova.get("maxTotalCores", -1)),
                _row("Compute", "RAM (MB)", nova.get("totalRAMUsed", 0), nova.get("maxTotalRAMSize", -1)),
                _row("Compute", "Key Pairs", "—", nova.get("maxTotalKeypairs", -1)),
                _row("Compute", "Server Groups", nova.get("totalServerGroupsUsed", 0), nova.get("maxServerGroups", -1)),
            ])
        except Exception:
            rows.append(_row("Compute", "(unavailable)", "—", "—"))

        # ── Cinder (volume) ──────────────────────────────────────────
        try:
            cinder = VolumeService(client).get_limits()
            rows.extend([
                _row("Volume", "Volumes", cinder.get("totalVolumesUsed", 0), cinder.get("maxTotalVolumes", -1)),
                _row("Volume", "Volume Storage (GB)", cinder.get("totalGigabytesUsed", 0), cinder.get("maxTotalVolumeGigabytes", -1)),
                _row("Volume", "Snapshots", cinder.get("totalSnapshotsUsed", 0), cinder.get("maxTotalSnapshots", -1)),
                _row("Volume", "Backups", cinder.get("totalBackupsUsed", 0), cinder.get("maxTotalBackups", -1)),
                _row("Volume", "Backup Storage (GB)", cinder.get("totalBackupGigabytesUsed", 0), cinder.get("maxTotalBackupGigabytes", -1)),
            ])
        except Exception:
            rows.append(_row("Volume", "(unavailable)", "—", "—"))

        # ── Neutron (network) ────────────────────────────────────────
        try:
            net_svc = NetworkService(client)
            quotas = net_svc.find_quotas()
            if quotas:
                q = quotas[0]
            else:
                q = net_svc.get_quota(client.project_id)

            # Count current usage
            nets = len(net_svc.find())
            subnets = len(net_svc.find_subnets())
            ports = len(net_svc.find_ports())
            routers = len(net_svc.find_routers())
            fips = len(net_svc.find_floating_ips())
            sgs = len(net_svc.find_security_groups())

            rows.extend([
                _row("Network", "Networks", nets, q.get("network", -1)),
                _row("Network", "Subnets", subnets, q.get("subnet", -1)),
                _row("Network", "Ports", ports, q.get("port", -1)),
                _row("Network", "Routers", routers, q.get("router", -1)),
                _row("Network", "Floating IPs", fips, q.get("floatingip", -1)),
                _row("Network", "Security Groups", sgs, q.get("security_group", -1)),
                _row("Network", "SG Rules", "—", q.get("security_group_rule", -1)),
            ])
        except Exception:
            rows.append(_row("Network", "(unavailable)", "—", "—"))

    print_list(
        rows,
        [
            ("Service", "service", {"style": "bold"}),
            ("Resource", "resource"),
            ("Used", "used", {"justify": "right", "style": "cyan"}),
            ("Limit", "limit", {"justify": "right"}),
            ("Usage", "usage", {"justify": "right"}),
        ],
        title="Project Quotas",
        output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent,
        columns=columns,
        empty_msg="No quota information available.",
    )


def _row(service: str, resource: str, used: object, limit: object) -> dict:
    used_s = str(used)
    limit_s = "unlimited" if limit == -1 else str(limit)
    if used_s != "—" and limit_s != "unlimited" and limit_s != "—":
        try:
            pct = int(used) / int(limit) * 100  # type: ignore[call-overload]
            color = "green" if pct < 70 else "yellow" if pct < 90 else "red"
            usage = f"[{color}]{pct:.0f}%[/{color}]"
        except (ValueError, ZeroDivisionError):
            usage = "—"
    else:
        usage = "—"
    return {"service": service, "resource": resource, "used": used_s, "limit": limit_s, "usage": usage}
