"""``orca export`` — export project infrastructure as YAML/JSON."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any

import click
import yaml

from orca_cli.core.context import OrcaContext
from orca_cli.core.output import console
from orca_cli.core.validators import safe_output_path

VALID_RESOURCE_TYPES = (
    "servers",
    "volumes",
    "networks",
    "routers",
    "floating_ips",
    "security_groups",
    "keypairs",
    "images",
)


# Each export type's transitive fetch dependencies. Lookup maps are
# built from these raw fetches; nothing is fetched twice.
_DEPS: dict[str, set[str]] = {
    "servers":         {"servers", "images", "networks", "ports", "floatingips"},
    "volumes":         {"volumes", "servers"},
    "networks":        {"networks", "subnets"},
    "routers":         {"routers", "ports", "subnets", "networks"},
    "floating_ips":    {"floatingips", "servers", "ports"},
    "security_groups": {"security_groups"},
    "keypairs":        {"keypairs"},
    "images":          {"images"},
}


# ── Collector helpers ────────────────────────────────────────────────────
#
# All collectors take pre-fetched data (no HTTP calls). The export
# command fans out the fetches once at the top and then assembles the
# output in-memory.


def _collect_servers(
    servers: list[dict],
    image_map: dict[str, str],
    fip_by_port: dict[str, dict],
) -> list[dict]:
    """Enrich servers with resolved names."""
    results: list[dict] = []
    for srv in servers:
        # Resolve image name
        image_ref = srv.get("image", {})
        image_id = image_ref.get("id", "") if isinstance(image_ref, dict) else ""
        image_name = image_map.get(image_id, image_id)

        # Build network entries
        net_entries: list[dict] = []
        for net_name, addrs in srv.get("addresses", {}).items():
            for addr in addrs:
                entry: dict[str, Any] = {
                    "network": net_name,
                    "ip": addr.get("addr", ""),
                }
                # Check for floating IP associated via port
                port_id = addr.get("OS-EXT-IPS:port_id", "")
                if port_id and port_id in fip_by_port:
                    entry["floating_ip"] = fip_by_port[port_id]["floating_ip_address"]
                elif addr.get("OS-EXT-IPS:type") == "floating":
                    entry["floating_ip"] = addr.get("addr", "")
                net_entries.append(entry)

        # Attached volumes
        vol_attachments = [
            {"id": att.get("volumeId", att.get("id", "")), "device": att.get("device", "")}
            for att in srv.get("os-extended-volumes:volumes_attached", [])
        ]

        # Security groups
        sg_names = [sg.get("name", "") for sg in srv.get("security_groups", [])]

        results.append({
            "id": srv.get("id", ""),
            "name": srv.get("name", ""),
            "status": srv.get("status", ""),
            "flavor": srv.get("flavor", {}).get("original_name", srv.get("flavor", {}).get("id", "")),
            "image": image_name,
            "key_name": srv.get("key_name", ""),
            "networks": net_entries,
            "security_groups": sg_names,
            "volumes": vol_attachments,
            "created": srv.get("created", ""),
        })

    return results


def _collect_volumes(volumes: list[dict], server_map: dict[str, str]) -> list[dict]:
    """Resolve attached server names on volumes."""
    results: list[dict] = []
    for vol in volumes:
        attachments = vol.get("attachments", [])
        attached_server_id = attachments[0].get("server_id", "") if attachments else ""
        attached_to = server_map.get(attached_server_id, attached_server_id) if attached_server_id else None

        results.append({
            "id": vol.get("id", ""),
            "name": vol.get("name", ""),
            "size": vol.get("size", 0),
            "status": vol.get("status", ""),
            "type": vol.get("volume_type", ""),
            "bootable": vol.get("bootable", "false") == "true",
            "attached_to": attached_to,
        })

    return results


def _collect_networks(networks: list[dict], subnet_map: dict[str, dict]) -> list[dict]:
    """Inline subnets into networks."""
    results: list[dict] = []
    for net in networks:
        subnets_out: list[dict] = []
        for sid in net.get("subnets", []):
            sub = subnet_map.get(sid)
            if sub:
                subnets_out.append({
                    "id": sub.get("id", ""),
                    "name": sub.get("name", ""),
                    "cidr": sub.get("cidr", ""),
                    "gateway": sub.get("gateway_ip", ""),
                    "dns_nameservers": sub.get("dns_nameservers", []),
                    "allocation_pools": [
                        {"start": p.get("start", ""), "end": p.get("end", "")}
                        for p in sub.get("allocation_pools", [])
                    ],
                })

        results.append({
            "id": net.get("id", ""),
            "name": net.get("name", ""),
            "subnets": subnets_out,
        })

    return results


def _collect_routers(
    routers: list[dict],
    ports: list[dict],
    subnet_map: dict[str, dict],
    network_map: dict[str, str],
) -> list[dict]:
    """Routers with their interfaces (router-ports filtered client-side)."""
    # Group router-interface ports by their router id
    ports_by_router: dict[str, list[dict]] = {}
    for port in ports:
        if port.get("device_owner") != "network:router_interface":
            continue
        rid = port.get("device_id", "")
        ports_by_router.setdefault(rid, []).append(port)

    results: list[dict] = []
    for rtr in routers:
        ext_gw = rtr.get("external_gateway_info") or {}
        ext_net_id = ext_gw.get("network_id", "")
        ext_net_name = network_map.get(ext_net_id, ext_net_id)

        interfaces: list[dict] = []
        for port in ports_by_router.get(rtr.get("id", ""), []):
            for fixed_ip in port.get("fixed_ips", []):
                subnet_id = fixed_ip.get("subnet_id", "")
                sub = subnet_map.get(subnet_id, {})
                interfaces.append({
                    "subnet": sub.get("name", subnet_id),
                    "ip": fixed_ip.get("ip_address", ""),
                })

        results.append({
            "id": rtr.get("id", ""),
            "name": rtr.get("name", ""),
            "external_network": ext_net_name,
            "interfaces": interfaces,
        })

    return results


def _collect_floating_ips(
    fips: list[dict],
    server_map: dict[str, str],
    port_device_map: dict[str, str],
) -> list[dict]:
    """Resolve attached server names on floating IPs."""
    results: list[dict] = []
    for fip in fips:
        port_id = fip.get("port_id", "")
        device_id = port_device_map.get(port_id, "") if port_id else ""
        attached_to = server_map.get(device_id, device_id) if device_id else None

        results.append({
            "id": fip.get("id", ""),
            "ip": fip.get("floating_ip_address", ""),
            "status": fip.get("status", ""),
            "attached_to": attached_to,
            "port_id": port_id or None,
        })

    return results


def _collect_security_groups(sgs: list[dict]) -> list[dict]:
    """Reformat security groups + rules."""
    results: list[dict] = []
    for sg in sgs:
        rules_out: list[dict] = []
        for rule in sg.get("security_group_rules", []):
            port_min = rule.get("port_range_min")
            port_max = rule.get("port_range_max")
            if port_min is None and port_max is None:
                port_range = "all"
            else:
                port_range = f"{port_min}-{port_max}"

            rules_out.append({
                "direction": rule.get("direction", ""),
                "protocol": rule.get("protocol") or "any",
                "port_range": port_range,
                "remote_ip_prefix": rule.get("remote_ip_prefix") or "0.0.0.0/0",
            })

        results.append({
            "id": sg.get("id", ""),
            "name": sg.get("name", ""),
            "rules": rules_out,
        })

    return results


def _collect_keypairs(keypairs: list[dict]) -> list[dict]:
    """Flatten keypair wrappers."""
    results: list[dict] = []
    for kp_wrapper in keypairs:
        kp = kp_wrapper.get("keypair", kp_wrapper)
        results.append({
            "name": kp.get("name", ""),
            "fingerprint": kp.get("fingerprint", ""),
            "type": kp.get("type", "ssh"),
        })

    return results


def _collect_images(images: list[dict]) -> list[dict]:
    """Pretty-print image sizes."""
    results: list[dict] = []
    for img in images:
        size_bytes = img.get("size") or 0
        size_gb = round(size_bytes / (1024 ** 3), 1) if size_bytes else 0

        results.append({
            "id": img.get("id", ""),
            "name": img.get("name", ""),
            "status": img.get("status", ""),
            "size_gb": size_gb,
            "min_disk": img.get("min_disk", 0),
            "min_ram": img.get("min_ram", 0),
        })

    return results


# ── Fetchers (one per resource type, all independent) ─────────────────────


def _fetchers(client: Any) -> dict[str, Any]:
    return {
        "servers": lambda: client.paginate(
            f"{client.compute_url}/servers/detail", "servers"),
        "volumes": lambda: client.paginate(
            f"{client.volume_url}/volumes/detail", "volumes"),
        "networks": lambda: client.paginate(
            f"{client.network_url}/v2.0/networks", "networks"),
        "subnets": lambda: client.paginate(
            f"{client.network_url}/v2.0/subnets", "subnets"),
        "routers": lambda: client.paginate(
            f"{client.network_url}/v2.0/routers", "routers"),
        "ports": lambda: client.paginate(
            f"{client.network_url}/v2.0/ports", "ports"),
        "floatingips": lambda: client.paginate(
            f"{client.network_url}/v2.0/floatingips", "floatingips"),
        "security_groups": lambda: client.paginate(
            f"{client.network_url}/v2.0/security-groups", "security_groups"),
        "keypairs": lambda: client.get(
            f"{client.compute_url}/os-keypairs").get("keypairs", []),
        "images": lambda: client.paginate(
            f"{client.image_url}/v2/images", "images"),
    }


# ── Main command ─────────────────────────────────────────────────────────


@click.command()
@click.option("--output", "-o", default=None, help="Output file path (default: stdout).")
@click.option("--resources", "-r", default=None,
              help="Comma-separated resource types to export (default: all).")
@click.option("--format", "-f", "fmt", type=click.Choice(["yaml", "json"]),
              default="yaml", help="Output format.")
@click.pass_context
def export(ctx: click.Context, output: str | None, resources: str | None, fmt: str) -> None:  # noqa: C901
    """Export project infrastructure as YAML/JSON."""
    client = ctx.find_object(OrcaContext).ensure_client()
    orca_ctx = ctx.find_object(OrcaContext)

    # Determine which resource types to export
    if resources:
        requested = [r.strip() for r in resources.split(",")]
        invalid = [r for r in requested if r not in VALID_RESOURCE_TYPES]
        if invalid:
            raise click.BadParameter(
                f"Invalid resource type(s): {', '.join(invalid)}. "
                f"Valid types: {', '.join(VALID_RESOURCE_TYPES)}",
                param_hint="'--resources'",
            )
        export_types = set(requested)
    else:
        export_types = set(VALID_RESOURCE_TYPES)

    # Compute the union of raw fetches needed by the chosen export types.
    # A user asking only for "keypairs" pays for one HTTP call, not nine.
    needed_fetches: set[str] = set()
    for et in export_types:
        needed_fetches.update(_DEPS[et])

    fetchers = _fetchers(client)

    with console.status("[bold cyan]Exporting infrastructure...[/bold cyan]"):
        # ── Phase 1: parallel fan-out (one HTTP call per resource type) ──
        raw: dict[str, list] = {}
        with ThreadPoolExecutor(max_workers=len(needed_fetches)) as pool:
            futures = {
                pool.submit(fetchers[name]): name for name in needed_fetches
            }
            for fut in as_completed(futures):
                name = futures[fut]
                try:
                    raw[name] = fut.result()
                except Exception as exc:
                    console.print(
                        f"[yellow]Warning: could not fetch {name}: {exc}[/yellow]"
                    )
                    raw[name] = []

        # ── Phase 2: build lookup maps from in-memory data ───────────────
        image_map = {img["id"]: img.get("name", img["id"])
                     for img in raw.get("images", [])}
        server_map = {srv["id"]: srv.get("name", srv["id"])
                      for srv in raw.get("servers", [])}
        network_map = {net["id"]: net.get("name", net["id"])
                       for net in raw.get("networks", [])}
        subnet_map = {sub["id"]: sub for sub in raw.get("subnets", [])}
        port_device_map = {p["id"]: p.get("device_id", "")
                           for p in raw.get("ports", [])}
        fip_by_port = {fip["port_id"]: fip
                       for fip in raw.get("floatingips", [])
                       if fip.get("port_id")}

        # ── Phase 3: assemble the output payload (no HTTP) ───────────────
        result: dict[str, Any] = {}

        if "servers" in export_types:
            result["servers"] = _collect_servers(
                raw["servers"], image_map, fip_by_port)
        if "volumes" in export_types:
            result["volumes"] = _collect_volumes(raw["volumes"], server_map)
        if "networks" in export_types:
            result["networks"] = _collect_networks(raw["networks"], subnet_map)
        if "routers" in export_types:
            result["routers"] = _collect_routers(
                raw["routers"], raw["ports"], subnet_map, network_map)
        if "floating_ips" in export_types:
            result["floating_ips"] = _collect_floating_ips(
                raw["floatingips"], server_map, port_device_map)
        if "security_groups" in export_types:
            result["security_groups"] = _collect_security_groups(
                raw["security_groups"])
        if "keypairs" in export_types:
            result["keypairs"] = _collect_keypairs(raw["keypairs"])
        if "images" in export_types:
            result["images"] = _collect_images(raw["images"])

    # ── Build header comment ─────────────────────────────────────────
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    profile_name = orca_ctx.profile or "default"

    # ── Serialise and output ─────────────────────────────────────────
    if fmt == "json":
        payload = json.dumps(result, indent=2, default=str)
    else:
        header = (
            f"# orca infrastructure export\n"
            f"# Generated: {timestamp}\n"
            f"# Profile: {profile_name}\n\n"
        )
        payload = header + yaml.dump(result, default_flow_style=False, sort_keys=False)

    if output:
        out_path = safe_output_path(output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload)
        console.print(f"[green]Infrastructure exported to {out_path}[/green]")
    else:
        console.print(payload, highlight=False)
