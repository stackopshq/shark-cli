"""``orca find`` — universal search across OpenStack resources.

Matches a query (case-insensitive substring) against every ID, name, IP, CIDR,
fingerprint, and device_id across servers, ports, floating IPs, volumes,
networks, subnets, routers, security groups, images, and keypairs.

Example use cases:
  - "Which resources use IP 10.0.0.5?"  → scans ports, FIPs, server addresses.
  - "Who owns the UUID fragment abc12345?"
  - "Find every resource matching 'web'".
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable

import click
from rich.table import Table

from orca_cli.core.context import OrcaContext
from orca_cli.core.output import console

# ── Per-resource search helpers ──────────────────────────────────────────

def _safe_list(client, url: str, key: str, params: dict | None = None) -> list[dict]:
    """GET *url*, return data[key] as list — swallow all errors to []."""
    try:
        data = client.get(url, params=params or {})
        return data.get(key, []) or []
    except Exception:
        return []


def _contains(value: Any, q: str) -> bool:
    return isinstance(value, str) and q in value.lower()


def _find_servers(client, q: str) -> list[tuple[dict, str]]:
    servers = _safe_list(client, f"{client.compute_url}/servers/detail",
                         "servers", params={"limit": 500})
    hits: list[tuple[dict, str]] = []
    for s in servers:
        why = None
        if _contains(s.get("id"), q):
            why = "id"
        elif _contains(s.get("name"), q):
            why = "name"
        else:
            for addrs in (s.get("addresses") or {}).values():
                for a in addrs:
                    ip = a.get("addr") or ""
                    if q in ip.lower():
                        why = f"ip={ip}"
                        break
                if why:
                    break
        if why:
            hits.append((s, why))
    return hits


def _find_ports(client, q: str) -> list[tuple[dict, str]]:
    ports = _safe_list(client, f"{client.network_url}/v2.0/ports", "ports")
    hits = []
    for p in ports:
        why = None
        if _contains(p.get("id"), q):
            why = "id"
        elif _contains(p.get("name"), q):
            why = "name"
        elif _contains(p.get("device_id"), q):
            why = f"device_id={p['device_id'][:8]}"
        elif _contains(p.get("mac_address"), q):
            why = f"mac={p['mac_address']}"
        else:
            for f in p.get("fixed_ips") or []:
                ip = f.get("ip_address", "")
                if q in ip.lower():
                    why = f"ip={ip}"
                    break
        if why:
            hits.append((p, why))
    return hits


def _find_floatingips(client, q: str) -> list[tuple[dict, str]]:
    fips = _safe_list(client, f"{client.network_url}/v2.0/floatingips", "floatingips")
    hits = []
    for f in fips:
        why = None
        if _contains(f.get("id"), q):
            why = "id"
        elif q in (f.get("floating_ip_address") or "").lower():
            why = f"floating={f['floating_ip_address']}"
        elif q in (f.get("fixed_ip_address") or "").lower():
            why = f"fixed={f['fixed_ip_address']}"
        if why:
            hits.append((f, why))
    return hits


def _find_volumes(client, q: str) -> list[tuple[dict, str]]:
    vols = _safe_list(client, f"{client.volume_url}/volumes/detail", "volumes")
    hits = []
    for v in vols:
        why = None
        if _contains(v.get("id"), q):
            why = "id"
        elif _contains(v.get("name"), q):
            why = "name"
        if why:
            hits.append((v, why))
    return hits


def _find_networks(client, q: str) -> list[tuple[dict, str]]:
    nets = _safe_list(client, f"{client.network_url}/v2.0/networks", "networks")
    hits = []
    for n in nets:
        why = None
        if _contains(n.get("id"), q):
            why = "id"
        elif _contains(n.get("name"), q):
            why = "name"
        if why:
            hits.append((n, why))
    return hits


def _find_subnets(client, q: str) -> list[tuple[dict, str]]:
    subnets = _safe_list(client, f"{client.network_url}/v2.0/subnets", "subnets")
    hits = []
    for s in subnets:
        why = None
        if _contains(s.get("id"), q):
            why = "id"
        elif _contains(s.get("name"), q):
            why = "name"
        elif q in (s.get("cidr") or "").lower():
            why = f"cidr={s['cidr']}"
        if why:
            hits.append((s, why))
    return hits


def _find_security_groups(client, q: str) -> list[tuple[dict, str]]:
    sgs = _safe_list(client, f"{client.network_url}/v2.0/security-groups",
                     "security_groups")
    hits = []
    for sg in sgs:
        why = None
        if _contains(sg.get("id"), q):
            why = "id"
        elif _contains(sg.get("name"), q):
            why = "name"
        if why:
            hits.append((sg, why))
    return hits


def _find_images(client, q: str) -> list[tuple[dict, str]]:
    images = _safe_list(client, f"{client.image_url}/v2/images", "images",
                        params={"limit": 500})
    hits = []
    for i in images:
        why = None
        if _contains(i.get("id"), q):
            why = "id"
        elif _contains(i.get("name"), q):
            why = "name"
        if why:
            hits.append((i, why))
    return hits


def _find_keypairs(client, q: str) -> list[tuple[dict, str]]:
    raw = _safe_list(client, f"{client.compute_url}/os-keypairs", "keypairs")
    hits = []
    for wrapper in raw:
        kp = wrapper.get("keypair", wrapper)
        why = None
        if _contains(kp.get("name"), q):
            why = "name"
        elif q in (kp.get("fingerprint") or "").lower():
            why = f"fingerprint={(kp.get('fingerprint') or '')[:20]}…"
        if why:
            hits.append((kp, why))
    return hits


def _find_routers(client, q: str) -> list[tuple[dict, str]]:
    routers = _safe_list(client, f"{client.network_url}/v2.0/routers", "routers")
    hits = []
    for r in routers:
        why = None
        if _contains(r.get("id"), q):
            why = "id"
        elif _contains(r.get("name"), q):
            why = "name"
        else:
            gw = r.get("external_gateway_info") or {}
            for ip_info in gw.get("external_fixed_ips") or []:
                ip = ip_info.get("ip_address", "")
                if q in ip.lower():
                    why = f"gw={ip}"
                    break
        if why:
            hits.append((r, why))
    return hits


# Registry: resource key → (display name, searcher, extra-column extractor)
_SEARCHERS: dict[str, Callable] = {
    "servers": _find_servers,
    "ports": _find_ports,
    "floatingips": _find_floatingips,
    "volumes": _find_volumes,
    "networks": _find_networks,
    "subnets": _find_subnets,
    "security_groups": _find_security_groups,
    "routers": _find_routers,
    "images": _find_images,
    "keypairs": _find_keypairs,
}


def _extra(resource: str, item: dict) -> str:
    """One-line status/summary column per resource type."""
    if resource == "servers":
        return item.get("status", "")
    if resource == "ports":
        tag = " attached" if item.get("device_id") else ""
        return f"{item.get('status', '')}{tag}"
    if resource == "floatingips":
        return item.get("status", "")
    if resource == "volumes":
        return f"{item.get('size', '?')}GB {item.get('status', '')}"
    if resource == "networks":
        return "shared" if item.get("shared") else item.get("status", "")
    if resource == "subnets":
        return item.get("cidr", "")
    if resource == "keypairs":
        return item.get("type", "ssh")
    if resource == "routers":
        return item.get("status", "")
    return ""


def _render(resource: str, hits: list[tuple[dict, str]]) -> None:
    pretty = resource.replace("_", " ").title()
    table = Table(
        title=f"{pretty} ({len(hits)})",
        title_style="bold cyan",
        title_justify="left",
        border_style="bright_black",
        header_style="bold",
        show_lines=False,
    )
    table.add_column("ID", style="dim", no_wrap=True)
    table.add_column("Name", style="bold")
    table.add_column("Matched")
    table.add_column("Extra", style="dim")

    for item, why in hits:
        raw_id = item.get("id") or item.get("name") or "—"
        short = raw_id[:8] if len(raw_id) > 8 else raw_id
        name = item.get("name") or "—"
        table.add_row(short, name, why, _extra(resource, item))

    console.print(table)


# ── Click command ────────────────────────────────────────────────────────

@click.command("find")
@click.argument("query")
@click.option("--type", "-t", "resource_types", multiple=True,
              type=click.Choice(list(_SEARCHERS.keys())),
              help="Restrict search to one or more resource types (repeatable).")
@click.pass_context
def find(ctx: click.Context, query: str, resource_types: tuple) -> None:
    """Universal search across every OpenStack resource.

    Matches the query (case-insensitive substring) against IDs, names, IPs,
    CIDRs, fingerprints, MAC addresses, and device references.

    \b
    Examples:
      orca find 10.0.0.5                    # who uses this IP?
      orca find web                         # anything matching 'web'
      orca find abc12345                    # by partial UUID
      orca find 10.0.0.5 -t ports -t servers
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    q = query.lower()
    types = tuple(resource_types) or tuple(_SEARCHERS.keys())

    # Fan out — network/keystone calls are independent, parallelise them.
    results: dict[str, list[tuple[dict, str]]] = {}
    with ThreadPoolExecutor(max_workers=len(types)) as pool:
        futures = {pool.submit(_SEARCHERS[t], client, q): t for t in types}
        for fut in as_completed(futures):
            t = futures[fut]
            try:
                results[t] = fut.result()
            except Exception:
                results[t] = []

    # Render in a stable (input) order.
    total = 0
    for t in types:
        hits = results.get(t) or []
        if hits:
            _render(t, hits)
            total += len(hits)

    if total == 0:
        console.print(f"[yellow]No matches for '{query}'.[/yellow]")
    else:
        console.print(
            f"\n[dim]{total} match(es) across {sum(1 for t in types if results.get(t))} "
            f"resource type(s).[/dim]"
        )
