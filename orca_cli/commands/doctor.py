"""``orca doctor`` — pre-deployment health check and environment diagnostics."""

from __future__ import annotations

import click

from orca_cli.core.context import OrcaContext
from orca_cli.core.output import console


@click.command()
@click.option("--fix", is_flag=True, help="Attempt to fix auto-correctable issues.")
@click.option("--cidr", default=None,
              help="CIDR for auto-created security group rules (--fix). "
                   "Defaults to interactive prompt when a TTY is detected, otherwise 0.0.0.0/0.")
@click.pass_context
def doctor(ctx: click.Context, fix: bool, cidr: str | None) -> None:
    """Run a pre-deployment health check on your OpenStack environment.

    Verifies authentication, quota headroom, default security group rules,
    and service availability. No destructive operations are performed
    unless --fix is specified.

    \b
    Checks performed:
      ✓ Authentication & token validity
      ✓ Service reachability (Nova, Neutron, Cinder, Glance)
      ✓ Compute quota headroom (instances, cores, RAM)
      ✓ Volume quota headroom
      ✓ Network quota headroom (floating IPs, security groups)
      ✓ Default security group SSH/ICMP rules

    \b
    Quota thresholds:
      Green  < 70%   — comfortable headroom
      Yellow 70–90%  — monitor closely
      Red    ≥ 90%   — critical, next deploy may fail
    """

    orca_ctx = ctx.find_object(OrcaContext)
    client = orca_ctx.ensure_client()

    issues: list[tuple[str, str, str]] = []  # (level, check, message)
    # Levels: OK | WARN | ERROR | INFO
    # ERROR is used for both hard failures and quota-critical (≥ 90%)

    def _ok(check: str, msg: str) -> None:
        issues.append(("OK", check, msg))

    def _warn(check: str, msg: str) -> None:
        issues.append(("WARN", check, msg))

    def _error(check: str, msg: str) -> None:
        issues.append(("ERROR", check, msg))

    def _info(check: str, msg: str) -> None:
        issues.append(("INFO", check, msg))

    def _pct(used: int, total: int) -> int:
        return int(used / total * 100) if total > 0 else 0

    def _quota(check: str, used: int, total: int, unit: str = "") -> None:
        """Emit OK / WARN / ERROR based on 3-tier quota thresholds."""
        if total <= 0:
            _info(check, "No limit set")
            return
        pct = _pct(used, total)
        suffix = f" {unit}" if unit else ""
        val = f"{used}/{total}{suffix} ({pct}%)"
        if pct >= 90:
            _error(check, f"{val} — quota critical, next operation may fail!")
        elif pct >= 70:
            _warn(check, f"{val} — monitor closely")
        else:
            _ok(check, val)

    console.print("\n[bold cyan]orca doctor — running environment health checks…[/bold cyan]\n")

    # ── 0. Resolve CIDR for --fix operations (once, before any API calls) ──
    import sys as _sys
    _fix_cidr = "0.0.0.0/0"
    if fix:
        if cidr:
            _fix_cidr = cidr
        elif _sys.stdin.isatty():
            from orca_cli.core.wizard import select_cidr
            _fix_cidr = select_cidr()

    # ── 1. Auth check — gates all subsequent checks ────────────────────────
    try:
        td = client._token_data
        user = td.get("user", {}).get("name", "unknown")
        project = td.get("project", {}).get("name", "unknown")
        _ok("Authentication", f"Authenticated as [bold]{user}[/bold] in project [bold]{project}[/bold]")
    except Exception as exc:
        _error("Authentication", f"Token data unavailable: {exc}")
        _info("Remaining checks", "Skipped — fix authentication first")
        _render(issues, fix=False)
        return

    # ── 2. Service reachability (independent — one failure ≠ abort) ────────
    svc_up: dict[str, bool] = {}
    _SVC = {
        "Nova (compute)":    (client.compute_url,  f"{client.compute_url}/limits"),
        "Neutron (network)": (client.network_url,  f"{client.network_url}/v2.0/networks?limit=1"),
        "Cinder (volume)":   (client.volume_url,   f"{client.volume_url}/limits"),
        "Glance (image)":    (client.image_url,    f"{client.image_url}/v2/images?limit=1"),
    }
    for svc_name, (_, test_url) in _SVC.items():
        try:
            client.get(test_url)
            _ok(f"Service: {svc_name}", "Reachable")
            svc_up[svc_name] = True
        except Exception as exc:
            _error(f"Service: {svc_name}", f"Unreachable — {exc}")
            svc_up[svc_name] = False

    # ── 3. Compute quotas (skip if Nova is down) ───────────────────────────
    if svc_up.get("Nova (compute)", False):
        try:
            q = (
                client.get(f"{client.compute_url}/limits")
                .get("limits", {})
                .get("absolute", {})
            )
            _quota("Compute: instances",
                   q.get("totalInstancesUsed", 0), q.get("maxTotalInstances", -1))
            _quota("Compute: vCPUs",
                   q.get("totalCoresUsed", 0), q.get("maxTotalCores", -1))
            ram_used = q.get("totalRAMUsed", 0)
            ram_max  = q.get("maxTotalRAMSize", -1)
            _quota("Compute: RAM",
                   ram_used // 1024, ram_max // 1024 if ram_max > 0 else -1, unit="GB")
        except Exception as exc:
            _error("Compute quotas", f"Could not retrieve — {exc}")
    else:
        _info("Compute quotas", "Skipped — Nova unreachable")

    # ── 4. Volume quotas (skip if Cinder is down) ─────────────────────────
    if svc_up.get("Cinder (volume)", False):
        try:
            vq = (
                client.get(f"{client.volume_url}/limits")
                .get("limits", {})
                .get("absolute", {})
            )
            _quota("Volume: count",
                   vq.get("totalVolumesUsed", 0), vq.get("maxTotalVolumes", -1))
            _quota("Volume: GB",
                   vq.get("totalGigabytesUsed", 0),
                   vq.get("maxTotalVolumeGigabytes", -1), unit="GB")
        except Exception as exc:
            _error("Volume quotas", f"Could not retrieve — {exc}")
    else:
        _info("Volume quotas", "Skipped — Cinder unreachable")

    # ── 5. Network quotas (skip if Neutron is down) ────────────────────────
    if svc_up.get("Neutron (network)", False):
        try:
            project_id = client._token_data.get("project", {}).get("id", "")
            if project_id:
                nq = (
                    client.get(f"{client.network_url}/v2.0/quotas/{project_id}/details")
                    .get("quota", {})
                )
                fip_used  = nq.get("floatingip", {}).get("used", 0)
                fip_limit = nq.get("floatingip", {}).get("limit", -1)
                sg_used   = nq.get("security_group", {}).get("used", 0)
                sg_limit  = nq.get("security_group", {}).get("limit", -1)
                _quota("Network: floating IPs",  fip_used, fip_limit)
                _quota("Network: security groups", sg_used, sg_limit)
        except Exception as exc:
            _error("Network quotas", f"Could not retrieve — {exc}")
    else:
        _info("Network quotas", "Skipped — Neutron unreachable")

    # ── 6. Default security group SSH/ICMP (skip if Neutron is down) ───────
    if svc_up.get("Neutron (network)", False):
        try:
            sgs = client.get(
                f"{client.network_url}/v2.0/security-groups",
                params={"name": "default"},
            ).get("security_groups", [])

            if not sgs:
                _info("Security: default SG", "No 'default' security group found")
            else:
                default_sg = sgs[0]
                rules = default_sg.get("security_group_rules", [])

                has_ssh = any(
                    r.get("port_range_min") == 22
                    and r.get("direction") == "ingress"
                    and r.get("protocol") in ("tcp", None)
                    for r in rules
                )
                has_icmp = any(
                    r.get("protocol") == "icmp" and r.get("direction") == "ingress"
                    for r in rules
                )

                if has_ssh:
                    _ok("Security: SSH (port 22)", "Allowed in 'default' security group")
                else:
                    _warn(
                        "Security: SSH (port 22)",
                        "Not open in 'default' SG — new VMs unreachable via SSH",
                    )
                    if fix:
                        client.post(
                            f"{client.network_url}/v2.0/security-group-rules",
                            json={"security_group_rule": {
                                "security_group_id": default_sg["id"],
                                "direction": "ingress", "protocol": "tcp",
                                "port_range_min": 22, "port_range_max": 22,
                                "ethertype": "IPv4",
                                "remote_ip_prefix": _fix_cidr,
                            }},
                        )
                        console.print(f"[green]  → SSH rule added ({_fix_cidr}) to 'default' security group.[/green]")

                if has_icmp:
                    _ok("Security: ICMP (ping)", "Allowed in 'default' security group")
                else:
                    _warn("Security: ICMP (ping)", "Not open in 'default' SG — ping will fail")
                    if fix:
                        client.post(
                            f"{client.network_url}/v2.0/security-group-rules",
                            json={"security_group_rule": {
                                "security_group_id": default_sg["id"],
                                "direction": "ingress", "protocol": "icmp",
                                "ethertype": "IPv4",
                                "remote_ip_prefix": _fix_cidr,
                            }},
                        )
                        console.print(f"[green]  → ICMP rule added ({_fix_cidr}) to 'default' security group.[/green]")

        except Exception as exc:
            _error("Security groups", f"Could not check — {exc}")
    else:
        _info("Security: default SG", "Skipped — Neutron unreachable")

    _render(issues, fix=fix)


# ── Rendering ─────────────────────────────────────────────────────────────

def _render(issues: list[tuple[str, str, str]], *, fix: bool) -> None:
    from rich.table import Table

    _STYLE = {
        "OK":    ("[bold green]✓[/bold green]",   "green"),
        "WARN":  ("[bold yellow]⚠[/bold yellow]", "yellow"),
        "ERROR": ("[bold red]✗[/bold red]",        "red"),
        "INFO":  ("[bold blue]ℹ[/bold blue]",      "blue"),
    }

    table = Table(title="Health Check Results", show_lines=False)
    table.add_column("", width=3)
    table.add_column("Check", style="bold", min_width=30)
    table.add_column("Result", min_width=40)

    for level, check, msg in issues:
        icon, color = _STYLE[level]
        table.add_row(icon, check, f"[{color}]{msg}[/{color}]")

    console.print(table)
    console.print()

    errors = sum(1 for level, _, _ in issues if level == "ERROR")
    warns  = sum(1 for level, _, _ in issues if level == "WARN")
    oks    = sum(1 for level, _, _ in issues if level == "OK")

    if errors:
        console.print(
            f"[bold red]{errors} critical issue(s)[/bold red]  "
            f"[yellow]{warns} warning(s)[/yellow]  "
            f"[green]{oks} OK[/green]"
        )
        if fix:
            console.print("[dim]Auto-fixes applied where possible.[/dim]")
        else:
            console.print("[dim]Run with --fix to auto-correct fixable issues.[/dim]")
    elif warns:
        console.print(
            f"[green]{oks} OK[/green]  [yellow]{warns} warning(s)[/yellow] — "
            "environment functional, review warnings above"
        )
    else:
        console.print(f"[bold green]All {oks} checks passed — environment ready![/bold green]")
    console.print()
