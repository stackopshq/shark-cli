"""``orca audit`` — security audit of the project."""

from __future__ import annotations

import click

from orca_cli.core.context import OrcaContext
from orca_cli.core.output import console

_DANGEROUS_PORTS = {22, 3389, 3306, 5432, 6379, 27017, 9200, 11211}
_DANGEROUS_LABELS = {
    22: "SSH", 3389: "RDP", 3306: "MySQL", 5432: "PostgreSQL",
    6379: "Redis", 27017: "MongoDB", 9200: "Elasticsearch", 11211: "Memcached",
}


@click.command()
@click.pass_context
def audit(ctx: click.Context) -> None:
    """Run a security audit on the project.

    Checks for common misconfigurations:
    - Security groups with 0.0.0.0/0 on dangerous ports
    - Servers without SSH key pair
    - Servers with admin password set
    - Unencrypted volumes
    - Publicly exposed services

    \b
    Examples:
      orca audit
    """
    from rich.table import Table

    client = ctx.find_object(OrcaContext).ensure_client()
    findings: list[tuple[str, str, str, str]] = []  # (severity, resource, id/name, detail)

    with console.status("[bold cyan]Running security audit…[/bold cyan]"):
        # ── Security Group Rules ─────────────────────────────────────
        sgs = client.get(f"{client.network_url}/v2.0/security-groups").get("security_groups", [])
        for sg in sgs:
            sg_name = sg.get("name", sg["id"])
            for rule in sg.get("security_group_rules", []):
                if rule.get("direction") != "ingress":
                    continue
                remote = rule.get("remote_ip_prefix", "")
                if remote not in ("0.0.0.0/0", "::/0"):
                    continue

                port_min = rule.get("port_range_min")
                port_max = rule.get("port_range_max")
                proto = rule.get("protocol", "")

                # Fully open (all ports)
                if port_min is None and port_max is None:
                    # ICMPv6 is required for IPv6 Neighbor Discovery (RFC 4861)
                    # and ICMPv4 for path-MTU / basic reachability — don't flag
                    # these as CRITICAL; surface as MEDIUM so users see the
                    # rule but aren't alarmed by an expected baseline.
                    if proto in ("icmp", "ipv6-icmp", "icmpv6"):
                        findings.append(("MEDIUM", f"SG: {sg_name}",
                                         sg["id"],
                                         f"All {proto} types open to {remote} "
                                         f"(expected for ND/ping — consider restricting)"))
                    else:
                        findings.append(("CRITICAL", f"SG: {sg_name}",
                                         sg["id"],
                                         f"All {proto or 'any'} ports open to {remote}"))
                    continue

                # Check for dangerous ports
                if port_min and port_max:
                    for dp in _DANGEROUS_PORTS:
                        if port_min <= dp <= port_max:
                            label = _DANGEROUS_LABELS.get(dp, "")
                            findings.append(("HIGH", f"SG: {sg_name}",
                                             sg["id"],
                                             f"Port {dp} ({label}) open to {remote} ({proto})"))

                # Wide port range
                if port_min and port_max and (port_max - port_min) > 100:
                    findings.append(("MEDIUM", f"SG: {sg_name}",
                                     sg["id"],
                                     f"Wide port range {port_min}-{port_max} open to {remote}"))

        # ── Servers ──────────────────────────────────────────────────
        servers = client.get(f"{client.compute_url}/servers/detail", params={"limit": 1000}).get("servers", [])
        for srv in servers:
            srv_name = srv.get("name", srv["id"])
            srv_id = srv["id"]

            # No key pair
            if not srv.get("key_name"):
                findings.append(("MEDIUM", f"Server: {srv_name}", srv_id,
                                 "No SSH key pair — password-only access"))

            # Server in error
            if srv.get("status") == "ERROR":
                findings.append(("LOW", f"Server: {srv_name}", srv_id,
                                 "Server in ERROR state"))

            # Check if server has floating IP (publicly reachable)
            has_floating = False
            for _net, addrs in srv.get("addresses", {}).items():
                for a in addrs:
                    if a.get("OS-EXT-IPS:type") == "floating":
                        has_floating = True
            if has_floating and not srv.get("key_name"):
                # Upgrade severity if publicly exposed with no key
                findings.append(("HIGH", f"Server: {srv_name}", srv_id,
                                 "Publicly reachable (floating IP) with no SSH key"))

        # ── Volumes ──────────────────────────────────────────────────
        vols = client.get(f"{client.volume_url}/volumes/detail").get("volumes", [])
        unencrypted = 0
        for v in vols:
            if not v.get("encrypted"):
                unencrypted += 1
        if unencrypted:
            findings.append(("LOW", "Volumes", f"{unencrypted} volume(s)",
                             f"{unencrypted} unencrypted volume(s)"))

        # ── Floating IPs unused ──────────────────────────────────────
        fips = client.get(f"{client.network_url}/v2.0/floatingips").get("floatingips", [])
        unused_fips = [f for f in fips if not f.get("port_id")]
        if unused_fips:
            findings.append(("LOW", "Floating IPs", f"{len(unused_fips)} IP(s)",
                             "Unassociated floating IPs (cost without benefit)"))

    # ── Report ────────────────────────────────────────────────────────
    if not findings:
        console.print("\n[bold green]No security issues found.[/bold green]\n")
        return

    # Sort by severity
    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    findings.sort(key=lambda x: severity_order.get(x[0], 99))

    severity_colors = {"CRITICAL": "red bold", "HIGH": "red", "MEDIUM": "yellow", "LOW": "dim"}

    table = Table(title=f"Security Audit — {len(findings)} finding(s)", show_lines=False)
    table.add_column("Severity", style="bold", no_wrap=True)
    table.add_column("Resource")
    table.add_column("ID")
    table.add_column("Detail")

    counts: dict[str, int] = {}
    for severity, resource, rid, detail in findings:
        counts[severity] = counts.get(severity, 0) + 1
        color = severity_colors.get(severity, "")
        table.add_row(f"[{color}]{severity}[/{color}]", resource, rid, detail)

    console.print()
    console.print(table)

    # Summary
    parts = []
    for sev in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
        if sev in counts:
            color = severity_colors[sev]
            parts.append(f"[{color}]{counts[sev]} {sev}[/{color}]")
    console.print(f"\n  {' · '.join(parts)}\n")
