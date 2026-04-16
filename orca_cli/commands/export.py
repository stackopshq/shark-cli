"""``orca export`` — export project infrastructure as YAML/JSON."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import click
import yaml

from orca_cli.core.context import OrcaContext
from orca_cli.core.output import console

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


# ── Collector helpers ────────────────────────────────────────────────────


def _collect_servers(
    client: Any,
    image_map: dict[str, str],
    network_map: dict[str, str],
    fip_by_port: dict[str, dict],
) -> list[dict]:
    """Fetch servers and enrich with resolved names."""
    data = client.get(f"{client.compute_url}/servers/detail", params={"limit": 1000})
    servers = data.get("servers", [])

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


def _collect_volumes(client: Any, server_map: dict[str, str]) -> list[dict]:
    """Fetch volumes and resolve attached server names."""
    data = client.get(f"{client.volume_url}/volumes/detail")
    volumes = data.get("volumes", [])

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


def _collect_networks(client: Any, subnet_map: dict[str, dict]) -> list[dict]:
    """Fetch networks with their subnets inlined."""
    data = client.get(f"{client.network_url}/v2.0/networks")
    networks = data.get("networks", [])

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


def _collect_routers(client: Any, subnet_map: dict[str, dict], network_map: dict[str, str]) -> list[dict]:
    """Fetch routers with their interfaces."""
    data = client.get(f"{client.network_url}/v2.0/routers")
    routers = data.get("routers", [])

    # Get router interface ports
    ports_data = client.get(
        f"{client.network_url}/v2.0/ports",
        params={"device_owner": "network:router_interface"},
    )
    router_ports = ports_data.get("ports", [])

    # Group ports by router (device_id)
    ports_by_router: dict[str, list[dict]] = {}
    for port in router_ports:
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
    client: Any,
    server_map: dict[str, str],
    port_device_map: dict[str, str],
) -> list[dict]:
    """Fetch floating IPs and resolve attached server names."""
    data = client.get(f"{client.network_url}/v2.0/floatingips")
    fips = data.get("floatingips", [])

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


def _collect_security_groups(client: Any) -> list[dict]:
    """Fetch security groups with their rules."""
    data = client.get(f"{client.network_url}/v2.0/security-groups")
    sgs = data.get("security_groups", [])

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


def _collect_keypairs(client: Any) -> list[dict]:
    """Fetch keypairs."""
    data = client.get(f"{client.compute_url}/os-keypairs")
    keypairs = data.get("keypairs", [])

    results: list[dict] = []
    for kp_wrapper in keypairs:
        kp = kp_wrapper.get("keypair", kp_wrapper)
        results.append({
            "name": kp.get("name", ""),
            "fingerprint": kp.get("fingerprint", ""),
            "type": kp.get("type", "ssh"),
        })

    return results


def _collect_images(client: Any) -> list[dict]:
    """Fetch images."""
    data = client.get(f"{client.image_url}/v2/images")
    images = data.get("images", [])

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


# ── Main command ─────────────────────────────────────────────────────────


@click.command()
@click.option("--output", "-o", default=None, help="Output file path (default: stdout).")
@click.option("--resources", "-r", default=None,
              help="Comma-separated resource types to export (default: all).")
@click.option("--format", "-f", "fmt", type=click.Choice(["yaml", "json"]),
              default="yaml", help="Output format.")
@click.pass_context
def export(ctx: click.Context, output: str | None, resources: str | None, fmt: str) -> None:
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

    with console.status("[bold cyan]Exporting infrastructure...[/bold cyan]"):
        # ── Build lookup maps ────────────────────────────────────────

        # Image map (id -> name)
        image_map: dict[str, str] = {}
        try:
            images_data = client.get(f"{client.image_url}/v2/images")
            for img in images_data.get("images", []):
                image_map[img["id"]] = img.get("name", img["id"])
        except Exception:
            pass

        # Server map (id -> name) — needed by volumes, floating_ips
        server_map: dict[str, str] = {}
        try:
            servers_data = client.get(
                f"{client.compute_url}/servers/detail", params={"limit": 1000},
            )
            for srv in servers_data.get("servers", []):
                server_map[srv["id"]] = srv.get("name", srv["id"])
        except Exception:
            pass

        # Network map (id -> name)
        network_map: dict[str, str] = {}
        try:
            nets_data = client.get(f"{client.network_url}/v2.0/networks")
            for net in nets_data.get("networks", []):
                network_map[net["id"]] = net.get("name", net["id"])
        except Exception:
            pass

        # Subnet map (id -> full subnet dict)
        subnet_map: dict[str, dict] = {}
        try:
            subnets_data = client.get(f"{client.network_url}/v2.0/subnets")
            for sub in subnets_data.get("subnets", []):
                subnet_map[sub["id"]] = sub
        except Exception:
            pass

        # Port device map (port_id -> device_id) — for floating IP resolution
        port_device_map: dict[str, str] = {}
        fip_by_port: dict[str, dict] = {}
        try:
            ports_data = client.get(f"{client.network_url}/v2.0/ports")
            for port in ports_data.get("ports", []):
                port_device_map[port["id"]] = port.get("device_id", "")
        except Exception:
            pass

        # Floating IP by port (for server network enrichment)
        try:
            fips_data = client.get(f"{client.network_url}/v2.0/floatingips")
            for fip in fips_data.get("floatingips", []):
                pid = fip.get("port_id")
                if pid:
                    fip_by_port[pid] = fip
        except Exception:
            pass

        # ── Collect each resource type ───────────────────────────────

        result: dict[str, Any] = {}

        if "servers" in export_types:
            try:
                result["servers"] = _collect_servers(client, image_map, network_map, fip_by_port)
            except Exception as exc:
                console.print(f"[yellow]Warning: could not export servers: {exc}[/yellow]")

        if "volumes" in export_types:
            try:
                result["volumes"] = _collect_volumes(client, server_map)
            except Exception as exc:
                console.print(f"[yellow]Warning: could not export volumes: {exc}[/yellow]")

        if "networks" in export_types:
            try:
                result["networks"] = _collect_networks(client, subnet_map)
            except Exception as exc:
                console.print(f"[yellow]Warning: could not export networks: {exc}[/yellow]")

        if "routers" in export_types:
            try:
                result["routers"] = _collect_routers(client, subnet_map, network_map)
            except Exception as exc:
                console.print(f"[yellow]Warning: could not export routers: {exc}[/yellow]")

        if "floating_ips" in export_types:
            try:
                result["floating_ips"] = _collect_floating_ips(client, server_map, port_device_map)
            except Exception as exc:
                console.print(f"[yellow]Warning: could not export floating_ips: {exc}[/yellow]")

        if "security_groups" in export_types:
            try:
                result["security_groups"] = _collect_security_groups(client)
            except Exception as exc:
                console.print(f"[yellow]Warning: could not export security_groups: {exc}[/yellow]")

        if "keypairs" in export_types:
            try:
                result["keypairs"] = _collect_keypairs(client)
            except Exception as exc:
                console.print(f"[yellow]Warning: could not export keypairs: {exc}[/yellow]")

        if "images" in export_types:
            try:
                result["images"] = _collect_images(client)
            except Exception as exc:
                console.print(f"[yellow]Warning: could not export images: {exc}[/yellow]")

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
        out_path = Path(output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload)
        console.print(f"[green]Infrastructure exported to {out_path}[/green]")
    else:
        console.print(payload, highlight=False)
