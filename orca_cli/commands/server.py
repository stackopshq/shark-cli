"""``orca server`` — manage servers (Nova)."""

from __future__ import annotations

import fnmatch
import os
import time

import click

from orca_cli.core import cache
from orca_cli.core.completions import (
    complete_flavors,
    complete_images,
    complete_keypairs,
    complete_networks,
    complete_security_groups,
    complete_servers,
)
from orca_cli.core.context import OrcaContext
from orca_cli.core.output import console, output_options, print_detail, print_list
from orca_cli.core.validators import validate_id
from orca_cli.core.waiter import wait_for_resource


@click.group()
@click.pass_context
def server(ctx: click.Context) -> None:
    """Manage compute servers."""
    pass


# ── list ──────────────────────────────────────────────────────────────────

@server.command("list")
@click.option("--limit", default=50, show_default=True, help="Max number of servers to return.")
@output_options
@click.pass_context
def server_list(ctx: click.Context, limit: int, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List servers."""
    client = ctx.find_object(OrcaContext).ensure_client()
    url = f"{client.compute_url}/servers/detail"
    data = client.get(url, params={"limit": limit})

    servers = data.get("servers", [])

    def _addresses(srv: dict) -> str:
        parts = []
        for net_name, addrs in srv.get("addresses", {}).items():
            for a in addrs:
                parts.append(f"{net_name}={a.get('addr', '?')}")
        return ", ".join(parts) or "—"

    def _flavor(srv: dict) -> str:
        flavor = srv.get("flavor", {})
        return str(flavor.get("original_name", flavor.get("id", "")))

    column_defs = [
        ("ID", "id", {"style": "cyan", "no_wrap": True}),
        ("Name", "name", {"style": "bold"}),
        ("Status", "status", {"style": "green"}),
        ("Networks", _addresses),
        ("Flavor", _flavor),
    ]

    print_list(
        servers,
        column_defs,
        title="Servers",
        output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent,
        columns=columns,
        empty_msg="No servers found.",
    )


# ── show ──────────────────────────────────────────────────────────────────

@server.command("show")
@click.argument("server_id", callback=validate_id)
@output_options
@click.pass_context
def server_show(ctx: click.Context, server_id: str, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show server details."""
    client = ctx.find_object(OrcaContext).ensure_client()
    url = f"{client.compute_url}/servers/{server_id}"
    data = client.get(url)

    srv = data.get("server", data)

    # Power state mapping (Nova integer → label)
    power_states = {
        0: "NOSTATE",
        1: "Running",
        3: "Paused",
        4: "Shutdown",
        6: "Crashed",
        7: "Suspended",
    }

    fields: list[tuple[str, str]] = []

    fields.append(("ID", srv.get("id", "")))
    fields.append(("Name", srv.get("name", "")))
    fields.append(("Status", srv.get("status", "")))

    power_state = srv.get("OS-EXT-STS:power_state")
    if power_state is not None:
        fields.append(("Power State", power_states.get(power_state, str(power_state))))
    task_state = srv.get("OS-EXT-STS:task_state")
    fields.append(("Task State", str(task_state) if task_state else "None"))
    vm_state = srv.get("OS-EXT-STS:vm_state")
    if vm_state is not None:
        fields.append(("VM State", vm_state))

    # Availability zone
    az = srv.get("OS-EXT-AZ:availability_zone")
    if az:
        fields.append(("Availability Zone", az))

    # Disk config
    disk_config = srv.get("OS-DCF:diskConfig")
    if disk_config:
        fields.append(("Disk Config", disk_config))

    # Flavor
    flavor = srv.get("flavor", {})
    flavor_name = flavor.get("original_name", flavor.get("id", ""))
    flavor_id = flavor.get("id", "")
    if flavor_name and flavor_id and flavor_name != flavor_id:
        fields.append(("Flavor", f"{flavor_name} ({flavor_id})"))
    else:
        fields.append(("Flavor", flavor_name or flavor_id))

    # Image
    image = srv.get("image", {})
    if isinstance(image, dict) and image:
        image_id = image.get("id", "")
        fields.append(("Image", image_id))
    elif isinstance(image, str):
        fields.append(("Image", image))
    else:
        fields.append(("Image", ""))

    # Addresses
    addr_parts = []
    for net_name, addrs in srv.get("addresses", {}).items():
        for a in addrs:
            addr_parts.append(f"{net_name}={a.get('addr', '?')}")
    fields.append(("Addresses", ", ".join(addr_parts) if addr_parts else ""))

    fields.append(("Key Name", srv.get("key_name", "") or "—"))

    # Security groups
    security_groups = srv.get("security_groups", [])
    if security_groups:
        sg_names = ", ".join(f"name='{sg.get('name', '')}'" for sg in security_groups)
        fields.append(("Security Groups", sg_names))

    fields.append(("Config Drive", str(srv.get("config_drive", ""))))
    fields.append(("Created", srv.get("created", "")))
    fields.append(("Updated", srv.get("updated", "")))

    # Usage timestamps
    launched_at = srv.get("OS-SRV-USG:launched_at")
    if launched_at:
        fields.append(("Launched At", launched_at))
    terminated_at = srv.get("OS-SRV-USG:terminated_at")
    fields.append(("Terminated At", str(terminated_at) if terminated_at else "None"))

    # Access IPs
    access_ipv4 = srv.get("accessIPv4", "")
    access_ipv6 = srv.get("accessIPv6", "")
    if access_ipv4:
        fields.append(("Access IPv4", access_ipv4))
    if access_ipv6:
        fields.append(("Access IPv6", access_ipv6))

    # Project / user
    fields.append(("Project ID", srv.get("tenant_id", "")))
    fields.append(("User ID", srv.get("user_id", "")))
    fields.append(("Host ID", srv.get("hostId", "")))

    # Host attributes (admin-only, may be absent)
    host = srv.get("OS-EXT-SRV-ATTR:host")
    if host:
        fields.append(("Host", host))
    hypervisor = srv.get("OS-EXT-SRV-ATTR:hypervisor_hostname")
    if hypervisor:
        fields.append(("Hypervisor", hypervisor))
    instance_name = srv.get("OS-EXT-SRV-ATTR:instance_name")
    if instance_name:
        fields.append(("Instance Name", instance_name))

    # Progress
    progress = srv.get("progress")
    if progress is not None:
        fields.append(("Progress", str(progress)))

    # Metadata / properties
    metadata = srv.get("metadata", {})
    if metadata:
        props = ", ".join(f"{k}={v}" for k, v in metadata.items())
        fields.append(("Properties", props))

    # Volumes attached
    volumes = srv.get("os-extended-volumes:volumes_attached", [])
    if volumes:
        vol_ids = ", ".join(v.get("id", "") for v in volumes)
        fields.append(("Volumes Attached", vol_ids))
    else:
        fields.append(("Volumes Attached", ""))

    print_detail(fields, output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent, columns=columns)


# ── create ────────────────────────────────────────────────────────────────

@server.command("create")
@click.option("--name", default=None, help="Server name.")
@click.option("--flavor", "flavor_id", default=None, shell_complete=complete_flavors,
              help="Flavor ID (see 'orca flavor list').")
@click.option("--image", "image_id", default=None, shell_complete=complete_images,
              help="Image ID (see 'orca image list').")
@click.option("--disk-size", type=int, default=20, show_default=True, help="Boot volume size in GB.")
@click.option("--network", "network_id", default=None, shell_complete=complete_networks,
              help="Network ID (see 'orca network list').")
@click.option("--key-name", default=None, shell_complete=complete_keypairs,
              help="SSH key pair name (see 'orca keypair list').")
@click.option("--security-group", "security_groups", multiple=True, shell_complete=complete_security_groups,
              help="Security group name (repeatable).")
@click.option("--wait", is_flag=True, help="Wait until the server reaches ACTIVE status.")
@click.option("--interactive", "-i", is_flag=True,
              help="Step-by-step wizard — browse images, flavors, and networks interactively.")
@click.pass_context
def server_create(
    ctx: click.Context,
    name: str | None,
    flavor_id: str | None,
    image_id: str | None,
    disk_size: int,
    network_id: str | None,
    key_name: str | None,
    security_groups: tuple[str, ...],
    wait: bool,
    interactive: bool,
) -> None:
    """Create a new server (boot from volume).

    \b
    Non-interactive example:
      orca server create \\
        --name my-vm \\
        --flavor <flavor-id> \\
        --image <image-id> \\
        --disk-size 30 \\
        --network <network-id> \\
        --key-name my-key \\
        --wait

    \b
    Interactive wizard:
      orca server create -i
    """
    from orca_cli.core import wizard as wiz

    orca_ctx = ctx.find_object(OrcaContext)
    client = orca_ctx.ensure_client()

    sg_list: list[str] = list(security_groups)
    vcpus = 0
    ram_mb = 0

    if interactive:
        console.print("\n[bold cyan]orca server create — interactive wizard[/bold cyan]\n")

        if not name:
            name = click.prompt("  Server name", prompt_suffix=" > ")

        if not image_id:
            image_id, image_name = wiz.select_image(client)
            console.print(f"  [green]✓[/green] Image: {image_name} ({image_id})")
        else:
            image_name = image_id

        if not flavor_id:
            flavor_id, flavor_name, vcpus, ram_mb = wiz.select_flavor(client)
            console.print(f"  [green]✓[/green] Flavor: {flavor_name} ({vcpus} vCPUs, {wiz._fmt_ram(ram_mb)})")

        if not network_id:
            net = wiz.select_network(client)
            if net:
                network_id, net_name = net
                console.print(f"  [green]✓[/green] Network: {net_name} ({network_id})")

        if not key_name:
            key_name = wiz.select_keypair(client)
            if key_name:
                console.print(f"  [green]✓[/green] Keypair: {key_name}")

        if not sg_list:
            sg_list = wiz.select_security_groups(client)
            if sg_list:
                console.print(f"  [green]✓[/green] Security groups: {', '.join(sg_list)}")

        # Quota preview
        if vcpus or ram_mb:
            wiz.quota_preview(client, vcpus, ram_mb)

        # CLI equivalent
        cmd = wiz.build_server_command(
            name=name or "", image_id=image_id or "", flavor_id=flavor_id or "",
            disk_size=disk_size, network_id=network_id,
            key_name=key_name, security_groups=sg_list,
        )
        console.print(f"\n[dim]Equivalent command:[/dim]\n[dim]{cmd}[/dim]\n")

        if not click.confirm("  Create server?", default=True):
            console.print("[yellow]Aborted.[/yellow]")
            return
    else:
        # Non-interactive: validate required fields manually
        missing = []
        if not name:
            missing.append("--name")
        if not flavor_id:
            missing.append("--flavor")
        if not image_id:
            missing.append("--image")
        if missing:
            raise click.UsageError(
                f"Missing required option(s): {', '.join(missing)}. "
                "Use -i / --interactive for the guided wizard."
            )

    body: dict = {
        "name": name,
        "flavorRef": flavor_id,
        "block_device_mapping_v2": [
            {
                "boot_index": 0,
                "uuid": image_id,
                "source_type": "image",
                "destination_type": "volume",
                "volume_size": disk_size,
                "delete_on_termination": True,
            }
        ],
    }

    if network_id:
        body["networks"] = [{"uuid": network_id}]
    if key_name:
        body["key_name"] = key_name
    if sg_list:
        body["security_groups"] = [{"name": sg} for sg in sg_list]

    url = f"{client.compute_url}/servers"
    data = client.post(url, json={"server": body})

    srv = data.get("server", data)
    srv_id = srv.get("id", "?")
    admin_pass = srv.get("adminPass", "")

    cache.invalidate(orca_ctx.profile, "servers")

    console.print("\n[bold green]Server created successfully![/bold green]")
    console.print(f"  [cyan]ID:[/cyan]       {srv_id}")
    console.print(f"  [cyan]Name:[/cyan]     {name}")
    console.print(f"  [cyan]Disk:[/cyan]     {disk_size} GB (boot volume)")
    if admin_pass:
        console.print(f"  [cyan]Password:[/cyan] {admin_pass}")

    if wait:
        console.print()
        wait_for_resource(
            client,
            url=f"{client.compute_url}/servers/{srv_id}",
            resource_key="server",
            target_status="ACTIVE",
            label=f"Server {name} ({srv_id})",
        )
    else:
        console.print(f"\nUse [bold]orca server show {srv_id}[/bold] to track provisioning.\n")


# ── delete ────────────────────────────────────────────────────────────────

@server.command("delete")
@click.argument("server_id", callback=validate_id, shell_complete=complete_servers)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.option("--dry-run", is_flag=True, help="Show what would be deleted without deleting.")
@click.option("--wait", is_flag=True, help="Wait until the server is fully deleted.")
@click.pass_context
def server_delete(ctx: click.Context, server_id: str, yes: bool, dry_run: bool, wait: bool) -> None:
    """Delete a server."""
    orca_ctx = ctx.find_object(OrcaContext)
    client = orca_ctx.ensure_client()
    url = f"{client.compute_url}/servers/{server_id}"

    if dry_run:
        data = client.get(url)
        srv = data.get("server", data)
        console.print("[yellow]Would delete server:[/yellow]")
        console.print(f"  ID:     {srv.get('id', server_id)}")
        console.print(f"  Name:   {srv.get('name', '—')}")
        console.print(f"  Status: {srv.get('status', '—')}")
        console.print(f"  Image:  {srv.get('image', {}).get('id', '—') if isinstance(srv.get('image'), dict) else '—'}")
        return

    if not yes:
        click.confirm(f"Delete server {server_id}?", abort=True)

    client.delete(url)
    cache.invalidate(orca_ctx.profile, "servers")

    if wait:
        wait_for_resource(
            client, url, "server", "DELETED",
            label=f"Server {server_id}",
            delete_mode=True,
        )
    else:
        console.print(f"[green]Server {server_id} deleted.[/green]")


# ── start / stop / reboot ─────────────────────────────────────────────────

def _server_action(ctx: click.Context, server_id: str, action: dict, label: str) -> None:
    client = ctx.find_object(OrcaContext).ensure_client()
    url = f"{client.compute_url}/servers/{server_id}/action"
    client.post(url, json=action)
    console.print(f"[green]{label} request sent for {server_id}.[/green]")


@server.command("start")
@click.argument("server_id", callback=validate_id, shell_complete=complete_servers)
@click.option("--wait", is_flag=True, help="Wait until the server reaches ACTIVE status.")
@click.pass_context
def server_start(ctx: click.Context, server_id: str, wait: bool) -> None:
    """Start (resume) a stopped server."""
    _server_action(ctx, server_id, {"os-start": None}, "Start")
    if wait:
        client = ctx.find_object(OrcaContext).ensure_client()
        wait_for_resource(client, f"{client.compute_url}/servers/{server_id}",
                          "server", "ACTIVE", label=f"Server {server_id}")


@server.command("stop")
@click.argument("server_id", callback=validate_id, shell_complete=complete_servers)
@click.option("--wait", is_flag=True, help="Wait until the server reaches SHUTOFF status.")
@click.pass_context
def server_stop(ctx: click.Context, server_id: str, wait: bool) -> None:
    """Stop (shut down) a server."""
    _server_action(ctx, server_id, {"os-stop": None}, "Stop")
    if wait:
        client = ctx.find_object(OrcaContext).ensure_client()
        wait_for_resource(client, f"{client.compute_url}/servers/{server_id}",
                          "server", "SHUTOFF", label=f"Server {server_id}")


@server.command("reboot")
@click.argument("server_id", callback=validate_id, shell_complete=complete_servers)
@click.option("--hard", is_flag=True, help="Perform a hard reboot.")
@click.option("--wait", is_flag=True, help="Wait until the server reaches ACTIVE status.")
@click.pass_context
def server_reboot(ctx: click.Context, server_id: str, hard: bool, wait: bool) -> None:
    """Reboot a server."""
    reboot_type = "HARD" if hard else "SOFT"
    _server_action(ctx, server_id, {"reboot": {"type": reboot_type}}, f"Reboot ({reboot_type})")
    if wait:
        client = ctx.find_object(OrcaContext).ensure_client()
        wait_for_resource(client, f"{client.compute_url}/servers/{server_id}",
                          "server", "ACTIVE", label=f"Server {server_id}")


# ── pause / unpause ──────────────────────────────────────────────────────

@server.command("pause")
@click.argument("server_id", callback=validate_id)
@click.pass_context
def server_pause(ctx: click.Context, server_id: str) -> None:
    """Pause a server (freeze in memory)."""
    _server_action(ctx, server_id, {"pause": None}, "Pause")


@server.command("unpause")
@click.argument("server_id", callback=validate_id)
@click.pass_context
def server_unpause(ctx: click.Context, server_id: str) -> None:
    """Unpause a paused server."""
    _server_action(ctx, server_id, {"unpause": None}, "Unpause")


# ── suspend / resume ─────────────────────────────────────────────────────

@server.command("suspend")
@click.argument("server_id", callback=validate_id)
@click.pass_context
def server_suspend(ctx: click.Context, server_id: str) -> None:
    """Suspend a server (save to disk)."""
    _server_action(ctx, server_id, {"suspend": None}, "Suspend")


@server.command("resume")
@click.argument("server_id", callback=validate_id)
@click.pass_context
def server_resume(ctx: click.Context, server_id: str) -> None:
    """Resume a suspended server."""
    _server_action(ctx, server_id, {"resume": None}, "Resume")


# ── lock / unlock ─────────────────────────────────────────────────────────

@server.command("lock")
@click.argument("server_id", callback=validate_id)
@click.pass_context
def server_lock(ctx: click.Context, server_id: str) -> None:
    """Lock a server (prevent actions by non-admin)."""
    _server_action(ctx, server_id, {"lock": None}, "Lock")


@server.command("unlock")
@click.argument("server_id", callback=validate_id)
@click.pass_context
def server_unlock(ctx: click.Context, server_id: str) -> None:
    """Unlock a locked server."""
    _server_action(ctx, server_id, {"unlock": None}, "Unlock")


# ── rescue / unrescue ─────────────────────────────────────────────────────

@server.command("rescue")
@click.argument("server_id", callback=validate_id)
@click.option("--image", default=None, help="Rescue image ID (optional).")
@click.option("--password", "admin_pass", default=None, help="Admin password for rescue mode.")
@click.pass_context
def server_rescue(ctx: click.Context, server_id: str, image: str | None, admin_pass: str | None) -> None:
    """Put a server in rescue mode."""
    body: dict = {}
    if image:
        body["rescue_image_ref"] = image
    if admin_pass:
        body["adminPass"] = admin_pass

    client = ctx.find_object(OrcaContext).ensure_client()
    url = f"{client.compute_url}/servers/{server_id}/action"
    data = client.post(url, json={"rescue": body if body else None})

    if data and data.get("adminPass"):
        console.print(f"[green]Rescue mode enabled for {server_id}.[/green]")
        console.print(f"  [cyan]Rescue password:[/cyan] {data['adminPass']}")
    else:
        console.print(f"[green]Rescue mode enabled for {server_id}.[/green]")


@server.command("unrescue")
@click.argument("server_id", callback=validate_id)
@click.pass_context
def server_unrescue(ctx: click.Context, server_id: str) -> None:
    """Exit rescue mode."""
    _server_action(ctx, server_id, {"unrescue": None}, "Unrescue")


# ── shelve / unshelve ─────────────────────────────────────────────────────

@server.command("shelve")
@click.argument("server_id", callback=validate_id, shell_complete=complete_servers)
@click.option("--wait", is_flag=True, help="Wait until the server reaches SHELVED_OFFLOADED status.")
@click.pass_context
def server_shelve(ctx: click.Context, server_id: str, wait: bool) -> None:
    """Shelve a server (snapshot + shut down, frees resources)."""
    _server_action(ctx, server_id, {"shelve": None}, "Shelve")
    if wait:
        client = ctx.find_object(OrcaContext).ensure_client()
        wait_for_resource(client, f"{client.compute_url}/servers/{server_id}",
                          "server", "SHELVED_OFFLOADED", label=f"Server {server_id}")


@server.command("unshelve")
@click.argument("server_id", callback=validate_id, shell_complete=complete_servers)
@click.option("--wait", is_flag=True, help="Wait until the server reaches ACTIVE status.")
@click.pass_context
def server_unshelve(ctx: click.Context, server_id: str, wait: bool) -> None:
    """Unshelve (restore) a shelved server."""
    _server_action(ctx, server_id, {"unshelve": None}, "Unshelve")
    if wait:
        client = ctx.find_object(OrcaContext).ensure_client()
        wait_for_resource(client, f"{client.compute_url}/servers/{server_id}",
                          "server", "ACTIVE", label=f"Server {server_id}")


# ── resize / confirm / revert ─────────────────────────────────────────────

@server.command("resize")
@click.argument("server_id", callback=validate_id)
@click.option("--flavor", required=True, help="Target flavor ID.")
@click.pass_context
def server_resize(ctx: click.Context, server_id: str, flavor: str) -> None:
    """Resize a server to a new flavor."""
    _server_action(ctx, server_id, {"resize": {"flavorRef": flavor}}, "Resize")
    console.print("[dim]Use 'orca server confirm-resize' or 'orca server revert-resize' after.[/dim]")


@server.command("confirm-resize")
@click.argument("server_id", callback=validate_id)
@click.pass_context
def server_confirm_resize(ctx: click.Context, server_id: str) -> None:
    """Confirm a pending resize."""
    _server_action(ctx, server_id, {"confirmResize": None}, "Confirm resize")


@server.command("revert-resize")
@click.argument("server_id", callback=validate_id)
@click.pass_context
def server_revert_resize(ctx: click.Context, server_id: str) -> None:
    """Revert a pending resize (restore original flavor)."""
    _server_action(ctx, server_id, {"revertResize": None}, "Revert resize")


# ── rebuild ───────────────────────────────────────────────────────────────

@server.command("rebuild")
@click.argument("server_id", callback=validate_id)
@click.option("--image", required=True, help="New image ID.")
@click.option("--name", "new_name", default=None, help="New server name (optional).")
@click.option("--password", "admin_pass", default=None, help="New admin password (optional).")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def server_rebuild(ctx: click.Context, server_id: str, image: str, new_name: str | None, admin_pass: str | None, yes: bool) -> None:
    """Rebuild a server with a new image (reinstall)."""
    if not yes:
        click.confirm(f"Rebuild server {server_id}? This will reinstall the OS.", abort=True)

    body: dict = {"imageRef": image}
    if new_name:
        body["name"] = new_name
    if admin_pass:
        body["adminPass"] = admin_pass

    client = ctx.find_object(OrcaContext).ensure_client()
    url = f"{client.compute_url}/servers/{server_id}/action"
    data = client.post(url, json={"rebuild": body})

    srv = data.get("server", data) if data else {}
    console.print(f"[green]Rebuild started for {server_id}.[/green]")
    if srv.get("adminPass"):
        console.print(f"  [cyan]New password:[/cyan] {srv['adminPass']}")


# ── rename ────────────────────────────────────────────────────────────────

@server.command("rename")
@click.argument("server_id", callback=validate_id)
@click.argument("new_name")
@click.pass_context
def server_rename(ctx: click.Context, server_id: str, new_name: str) -> None:
    """Rename a server."""
    client = ctx.find_object(OrcaContext).ensure_client()
    url = f"{client.compute_url}/servers/{server_id}"
    client.put(url, json={"server": {"name": new_name}})
    console.print(f"[green]Server {server_id} renamed to '{new_name}'.[/green]")


# ── create-image (snapshot) ───────────────────────────────────────────────

@server.command("create-image")
@click.argument("server_id", callback=validate_id)
@click.argument("image_name")
@click.pass_context
def server_create_image(ctx: click.Context, server_id: str, image_name: str) -> None:
    """Create a snapshot image from a server."""
    client = ctx.find_object(OrcaContext).ensure_client()
    url = f"{client.compute_url}/servers/{server_id}/action"
    client.post(url, json={"createImage": {"name": image_name}})
    console.print(f"[green]Image '{image_name}' creation started from {server_id}.[/green]")
    console.print("[dim]Use 'orca image list' to track progress.[/dim]")


# ── volume attachments ────────────────────────────────────────────────────

@server.command("attach-volume")
@click.argument("server_id", callback=validate_id)
@click.argument("volume_id", callback=validate_id)
@click.option("--device", default=None, help="Device name (e.g. /dev/vdb). Auto-assigned if omitted.")
@click.pass_context
def server_attach_volume(ctx: click.Context, server_id: str, volume_id: str, device: str | None) -> None:
    """Attach a volume to a server.

    \b
    Examples:
      orca server attach-volume <server-id> <volume-id>
      orca server attach-volume <server-id> <volume-id> --device /dev/vdc
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    url = f"{client.compute_url}/servers/{server_id}/os-volume_attachments"
    body: dict = {"volumeId": volume_id}
    if device:
        body["device"] = device
    data = client.post(url, json={"volumeAttachment": body})

    att = data.get("volumeAttachment", data) if data else {}
    dev = att.get("device", "auto")
    console.print(f"[green]Volume {volume_id} attached to {server_id} as {dev}.[/green]")


@server.command("detach-volume")
@click.argument("server_id", callback=validate_id)
@click.argument("volume_id", callback=validate_id)
@click.pass_context
def server_detach_volume(ctx: click.Context, server_id: str, volume_id: str) -> None:
    """Detach a volume from a server."""
    client = ctx.find_object(OrcaContext).ensure_client()
    url = f"{client.compute_url}/servers/{server_id}/os-volume_attachments/{volume_id}"
    client.delete(url)
    console.print(f"[green]Volume {volume_id} detached from {server_id}.[/green]")


@server.command("list-volumes")
@click.argument("server_id", callback=validate_id)
@output_options
@click.pass_context
def server_list_volumes(ctx: click.Context, server_id: str, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List volumes attached to a server."""
    client = ctx.find_object(OrcaContext).ensure_client()
    url = f"{client.compute_url}/servers/{server_id}/os-volume_attachments"
    data = client.get(url)

    attachments = data.get("volumeAttachments", [])

    column_defs = [
        ("Volume ID", "volumeId", {"style": "cyan", "no_wrap": True}),
        ("Device", "device", {"style": "bold"}),
        ("Attachment ID", "id", {"style": "dim"}),
    ]

    print_list(
        attachments,
        column_defs,
        title=f"Volumes attached to {server_id}",
        output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent,
        columns=columns,
        empty_msg="No volumes attached.",
    )


# ── network interface attachments ─────────────────────────────────────────

@server.command("attach-interface")
@click.argument("server_id", callback=validate_id)
@click.option("--port-id", default=None, help="Existing port ID to attach.")
@click.option("--net-id", default=None, help="Network ID (creates a new port automatically).")
@click.option("--fixed-ip", default=None, help="Fixed IP for the new port (requires --net-id).")
@click.pass_context
def server_attach_interface(ctx: click.Context, server_id: str, port_id: str | None,
                            net_id: str | None, fixed_ip: str | None) -> None:
    """Attach a network interface (port) to a server.

    \b
    Examples:
      orca server attach-interface <server-id> --port-id <port-id>
      orca server attach-interface <server-id> --net-id <network-id>
    """
    if not port_id and not net_id:
        raise click.ClickException("Provide --port-id or --net-id.")

    client = ctx.find_object(OrcaContext).ensure_client()
    url = f"{client.compute_url}/servers/{server_id}/os-interface"
    body: dict = {}
    if port_id:
        body["port_id"] = port_id
    elif net_id:
        body["net_id"] = net_id
        if fixed_ip:
            body["fixed_ips"] = [{"ip_address": fixed_ip}]

    data = client.post(url, json={"interfaceAttachment": body})
    att = data.get("interfaceAttachment", data) if data else {}
    ips = ", ".join(ip.get("ip_address", "") for ip in att.get("fixed_ips", []))
    console.print(f"[green]Interface attached to {server_id} — port {att.get('port_id', '')} ({ips}).[/green]")


@server.command("detach-interface")
@click.argument("server_id", callback=validate_id)
@click.argument("port_id", callback=validate_id)
@click.pass_context
def server_detach_interface(ctx: click.Context, server_id: str, port_id: str) -> None:
    """Detach a network interface (port) from a server."""
    client = ctx.find_object(OrcaContext).ensure_client()
    url = f"{client.compute_url}/servers/{server_id}/os-interface/{port_id}"
    client.delete(url)
    console.print(f"[green]Interface {port_id} detached from {server_id}.[/green]")


@server.command("list-interfaces")
@click.argument("server_id", callback=validate_id)
@output_options
@click.pass_context
def server_list_interfaces(ctx: click.Context, server_id: str, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List network interfaces attached to a server."""
    client = ctx.find_object(OrcaContext).ensure_client()
    url = f"{client.compute_url}/servers/{server_id}/os-interface"
    data = client.get(url)

    attachments = data.get("interfaceAttachments", [])

    def _fixed_ips(att: dict) -> str:
        return ", ".join(ip.get("ip_address", "") for ip in att.get("fixed_ips", []))

    column_defs = [
        ("Port ID", "port_id", {"style": "cyan", "no_wrap": True}),
        ("Network ID", "net_id"),
        ("Fixed IPs", _fixed_ips),
        ("MAC", "mac_addr", {"style": "dim"}),
        ("Status", "port_state", {"style": "green"}),
    ]

    print_list(
        attachments,
        column_defs,
        title=f"Interfaces on {server_id}",
        output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent,
        columns=columns,
        empty_msg="No interfaces attached.",
    )


# ── password ──────────────────────────────────────────────────────────────

@server.command("password")
@click.argument("server_id", callback=validate_id)
@click.option(
    "--key", "private_key_path",
    type=click.Path(exists=True),
    default=None,
    help="Path to the RSA private key used to decrypt. Tries ~/.ssh/orca-* if omitted.",
)
@click.option("--raw", is_flag=True, help="Print the encrypted password without decrypting.")
@click.pass_context
def server_password(ctx: click.Context, server_id: str, private_key_path: str | None, raw: bool) -> None:
    """Retrieve and decrypt the server admin password.

    \b
    The password is encrypted with your SSH public key at boot and
    stored in the server metadata. This command fetches it and
    decrypts it locally with your private key (RSA only).

    \b
    Examples:
      orca server password <server-id>
      orca server password <server-id> --key ~/.ssh/orca-my-key
      orca server password <server-id> --raw
    """
    import base64
    import subprocess
    import tempfile
    from pathlib import Path

    client = ctx.find_object(OrcaContext).ensure_client()
    url = f"{client.compute_url}/servers/{server_id}/os-server-password"
    data = client.get(url)

    encrypted_b64 = data.get("password", "")

    if not encrypted_b64:
        console.print("[yellow]No password set for this server (metadata empty).[/yellow]")
        console.print("[dim]The password may not be available yet if the server is still booting.[/dim]")
        return

    if raw:
        console.print(f"[bold]Encrypted password (base64):[/bold]\n{encrypted_b64}")
        return

    # Resolve private key
    key_path: Path | None = None
    if private_key_path:
        key_path = Path(private_key_path)
    else:
        ssh_dir = Path.home() / ".ssh"
        # Try orca-* keys first, then common defaults
        candidates = sorted(ssh_dir.glob("orca-*"))
        candidates = [c for c in candidates if not c.name.endswith(".pub")]
        candidates += [
            ssh_dir / "id_rsa",
            ssh_dir / "id_ecdsa",
        ]
        for candidate in candidates:
            if candidate.exists() and not candidate.name.endswith(".pub"):
                key_path = candidate
                break

    if not key_path or not key_path.exists():
        raise click.ClickException(
            "No private key found. Use --key <path> to specify your RSA private key."
        )

    console.print(f"[dim]Using key: {key_path}[/dim]")

    # Decode the base64 encrypted password
    try:
        encrypted_bytes = base64.b64decode(encrypted_b64)
    except Exception:
        raise click.ClickException("Failed to decode encrypted password (invalid base64).")

    # Decrypt with openssl
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as tmp:
        tmp.write(encrypted_bytes)
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            [
                "openssl", "pkeyutl", "-decrypt",
                "-inkey", str(key_path),
                "-in", tmp_path,
            ],
            capture_output=True,
        )

        if result.returncode != 0:
            # Fallback to older rsautl for compatibility
            result = subprocess.run(
                [
                    "openssl", "rsautl", "-decrypt",
                    "-inkey", str(key_path),
                    "-in", tmp_path,
                ],
                capture_output=True,
            )

        if result.returncode != 0:
            stderr = result.stderr.decode(errors="replace").strip()
            raise click.ClickException(
                f"Decryption failed. Make sure you use the matching RSA private key.\n"
                f"  openssl error: {stderr}"
            )

        password = result.stdout.decode().strip()
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    console.print(f"\n[bold green]Admin password for {server_id}:[/bold green]")
    console.print(f"  [bold]{password}[/bold]\n")


# ── console-log ───────────────────────────────────────────────────────────

@server.command("console-log")
@click.argument("server_id", callback=validate_id)
@click.option("--lines", "length", default=50, show_default=True, help="Number of lines to retrieve (0 = all).")
@click.pass_context
def server_console_log(ctx: click.Context, server_id: str, length: int) -> None:
    """Show the server console output (boot log).

    \b
    Examples:
      orca server console-log <server-id>
      orca server console-log <server-id> --lines 100
      orca server console-log <server-id> --lines 0   # all output
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    url = f"{client.compute_url}/servers/{server_id}/action"

    body: dict = {"os-getConsoleOutput": {}}
    if length > 0:
        body["os-getConsoleOutput"]["length"] = length

    data = client.post(url, json=body)

    output = ""
    if data:
        output = data.get("output", "")

    if not output:
        console.print("[yellow]No console output available yet.[/yellow]")
        return

    console.print(f"[bold]Console log for {server_id}[/bold] (last {length} lines):\n")
    console.print(output)


# ── console-url ───────────────────────────────────────────────────────────

@server.command("console-url")
@click.argument("server_id", callback=validate_id, shell_complete=complete_servers)
@click.option(
    "--type", "console_type",
    type=click.Choice(["novnc", "xvpvnc", "spice-html5", "rdp-html5", "serial"], case_sensitive=False),
    default="novnc",
    show_default=True,
    help="Console type.",
)
@click.option("--open", "open_browser", is_flag=True,
              help="Open the URL in the default system browser immediately.")
@click.pass_context
def server_console_url(ctx: click.Context, server_id: str, console_type: str,
                       open_browser: bool) -> None:
    """Get a URL to access the server console (VNC/SPICE/serial).

    \b
    Examples:
      orca server console-url <server-id>
      orca server console-url <server-id> --type spice-html5
      orca server console-url <server-id> --open
    """
    client = ctx.find_object(OrcaContext).ensure_client()

    protocol_map = {
        "novnc":      ("vnc",    "novnc"),
        "xvpvnc":     ("vnc",    "xvpvnc"),
        "spice-html5": ("spice",  "spice-html5"),
        "rdp-html5":  ("rdp",    "rdp-html5"),
        "serial":     ("serial", "serial"),
    }
    protocol, remote_type = protocol_map[console_type]

    url = f"{client.compute_url}/servers/{server_id}/remote-consoles"
    data = client.post(url, json={
        "remote_console": {"protocol": protocol, "type": remote_type}
    })

    console_data = data.get("remote_console", data)
    console_url = console_data.get("url", "")

    if not console_url:
        console.print("[yellow]No console URL returned.[/yellow]")
        return

    console.print(f"\n[bold]Console URL[/bold] ([dim]{console_type}[/dim]):")
    console.print(f"  [cyan]{console_url}[/cyan]")

    if open_browser:
        import webbrowser
        webbrowser.open(console_url)
        console.print("[dim]  → Opening in default browser…[/dim]")
    else:
        console.print("\n[dim]Tip: use --open to launch in browser automatically.[/dim]")
    console.print()


# ── ssh ──────────────────────────────────────────────────────────────────

# os_distro → default cloud-init SSH user (matches official cloud images).
_DISTRO_USER: dict[str, str] = {
    "ubuntu": "ubuntu",
    "debian": "debian",
    "centos": "centos",
    "rhel": "cloud-user",
    "rocky": "rocky",
    "almalinux": "almalinux",
    "fedora": "fedora",
    "amazon": "ec2-user",
    "opensuse": "opensuse",
    "suse": "opensuse",
    "arch": "arch",
    "alpine": "alpine",
    "freebsd": "freebsd",
    "coreos": "core",
    "flatcar": "core",
}


def _pick_ssh_ip(srv: dict, prefer_fixed: bool = False) -> str | None:
    """Pick the best IP. Floating wins unless prefer_fixed is set."""
    floating = None
    fixed = None
    for _net, addrs in srv.get("addresses", {}).items():
        for a in addrs:
            if a.get("OS-EXT-IPS:type") == "floating":
                floating = floating or a.get("addr")
            elif not fixed:
                fixed = a.get("addr")
    if prefer_fixed:
        return fixed or floating
    return floating or fixed


def _detect_ssh_user(client, srv: dict) -> str | None:
    """Read image metadata, map os_distro → cloud-init default user.

    For boot-from-volume servers Nova returns ``"image": ""`` (or a dict
    without ``id``). Fall back to the ``volume_image_metadata`` carried on
    the attached boot volume — Cinder preserves the source image's
    ``os_distro`` there.
    """
    distro: str = ""

    # 1) Try image reference on the server
    image = srv.get("image")
    if isinstance(image, dict) and image.get("id"):
        try:
            data = client.get(f"{client.image_url}/v2/images/{image['id']}")
            distro = (data.get("os_distro") or "").lower()
        except Exception:
            distro = ""

    # 2) Fallback: look at the boot volume's image metadata
    if not distro:
        volumes = srv.get("os-extended-volumes:volumes_attached") or []
        if volumes:
            vol_id = volumes[0].get("id")
            if vol_id:
                try:
                    vol = client.get(f"{client.volume_url}/volumes/{vol_id}")
                    vmeta = vol.get("volume", {}).get("volume_image_metadata") or {}
                    distro = (vmeta.get("os_distro") or "").lower()
                except Exception:
                    distro = ""

    return _DISTRO_USER.get(distro) if distro else None


def _find_ssh_key(keypair_name: str | None) -> str | None:
    """Search ~/.ssh for a private key matching the keypair name.

    Tries exact filename variants in order of specificity. Falls back to
    default keys (id_ed25519/id_rsa/id_ecdsa) only if no name-specific match
    is found. Never returns an unrelated key that merely shares the ``orca-``
    prefix — that silent mismatch led to auth failures on hosts with leftover
    keys from earlier projects.
    """
    from pathlib import Path
    ssh_dir = Path.home() / ".ssh"
    if not ssh_dir.is_dir():
        return None

    candidates: list = []
    if keypair_name:
        candidates += [
            ssh_dir / f"orca-{keypair_name}",        # keypair generate default
            ssh_dir / f"orca-{keypair_name}.pem",
            ssh_dir / f"{keypair_name}.pem",         # keypair create default
            ssh_dir / keypair_name,
            ssh_dir / f"{keypair_name}.key",
        ]
    candidates += [ssh_dir / "id_ed25519", ssh_dir / "id_rsa", ssh_dir / "id_ecdsa"]

    for c in candidates:
        if c.is_file() and not c.name.endswith(".pub"):
            return str(c)
    return None


@server.command("ssh", context_settings=dict(ignore_unknown_options=True))
@click.argument("server_id", shell_complete=complete_servers)
@click.argument("remote_args", nargs=-1, type=click.UNPROCESSED)
@click.option("--user", "-u", "ssh_user", default=None,
              help="SSH user. Default: auto-detected from image os_distro.")
@click.option("--key", "-i", "key_path", type=click.Path(), default=None,
              help="Private key path. Default: matched from keypair name in ~/.ssh.")
@click.option("--port", "-p", "ssh_port", type=int, default=22, show_default=True,
              help="SSH port.")
@click.option("--fixed", "use_fixed", is_flag=True,
              help="Use the fixed IP instead of the floating IP.")
@click.option("--dry-run", is_flag=True,
              help="Print the ssh command without executing it.")
@click.option("--extra", default=None,
              help="Extra SSH options (e.g. '-o StrictHostKeyChecking=no').")
@click.pass_context
def server_ssh(ctx: click.Context, server_id: str, remote_args: tuple,
               ssh_user: str | None, key_path: str | None, ssh_port: int,
               use_fixed: bool, dry_run: bool, extra: str | None) -> None:
    """SSH into a server by name or ID.

    Auto-resolves the IP (floating > fixed), the SSH user (from image
    ``os_distro`` metadata), and the private key (matched from the attached
    keypair name in ``~/.ssh/``).

    \b
    Examples:
      orca server ssh web-1                      # auto-detect everything
      orca server ssh web-1 ls /var/log          # run a remote command
      orca server ssh web-1 -u root -i ~/.ssh/k  # override user / key
      orca server ssh web-1 --fixed              # use fixed IP
      orca server ssh web-1 --dry-run            # print command, don't exec
    """
    client = ctx.find_object(OrcaContext).ensure_client()

    # Resolve server — try by ID, fallback to name search
    try:
        data = client.get(f"{client.compute_url}/servers/{server_id}")
        srv = data.get("server", data)
    except Exception:
        data = client.get(f"{client.compute_url}/servers/detail", params={"name": server_id})
        matches = data.get("servers", [])
        if not matches:
            raise click.ClickException(f"Server '{server_id}' not found.")
        if len(matches) > 1:
            console.print(f"[yellow]Multiple servers match '{server_id}':[/yellow]")
            for m in matches:
                console.print(f"  {m['id']}  {m.get('name', '')}")
            raise click.ClickException("Be more specific or use the server ID.")
        srv = matches[0]

    name = srv.get("name") or server_id

    ip = _pick_ssh_ip(srv, prefer_fixed=use_fixed)
    if not ip:
        raise click.ClickException(f"No IP address found for server '{name}'.")

    if not ssh_user:
        ssh_user = _detect_ssh_user(client, srv) or "root"

    if not key_path:
        key_path = _find_ssh_key(srv.get("key_name"))

    cmd = ["ssh"]
    if key_path:
        cmd.extend(["-i", key_path])
    if ssh_port != 22:
        cmd.extend(["-p", str(ssh_port)])
    if extra:
        cmd.extend(extra.split())
    cmd.append(f"{ssh_user}@{ip}")
    if remote_args:
        cmd.extend(remote_args)

    console.print(
        f"[dim]→[/dim] [bold cyan]{ssh_user}@{ip}[/bold cyan]  "
        f"[dim](server={name}, key={key_path or 'default'})[/dim]"
    )
    console.print(f"[dim]$ {' '.join(cmd)}[/dim]")

    if dry_run:
        return
    os.execvp("ssh", cmd)  # pragma: no cover


# ── snapshot (server + volumes) ──────────────────────────────────────────

@server.command("snapshot")
@click.argument("server_id", callback=validate_id)
@click.option("--name", default=None, help="Snapshot name prefix. Default: server name.")
@click.pass_context
def server_snapshot(ctx: click.Context, server_id: str, name: str | None) -> None:
    """Snapshot a server AND all its attached volumes.

    Creates a server image snapshot plus a Cinder snapshot for each
    attached volume — all in one command.

    \b
    Examples:
      orca server snapshot <server-id>
      orca server snapshot <server-id> --name "before-upgrade"
    """
    client = ctx.find_object(OrcaContext).ensure_client()

    # Get server info
    srv_data = client.get(f"{client.compute_url}/servers/{server_id}")
    srv = srv_data.get("server", srv_data)
    srv_name = srv.get("name", server_id)
    prefix = name or srv_name

    # 1. Create server image snapshot
    image_name = f"{prefix}-image"
    console.print(f"[bold]Creating server image snapshot:[/bold] {image_name}")
    client.post(f"{client.compute_url}/servers/{server_id}/action",
                json={"createImage": {"name": image_name}})
    console.print(f"  [green]✓[/green] Image '{image_name}' creation started.")

    # 2. Snapshot attached volumes
    vol_data = client.get(f"{client.compute_url}/servers/{server_id}/os-volume_attachments")
    attachments = vol_data.get("volumeAttachments", [])

    if not attachments:
        console.print("  [dim]No attached volumes to snapshot.[/dim]")
    else:
        for att in attachments:
            vol_id = att.get("volumeId", "")
            device = att.get("device", "?")
            snap_name = f"{prefix}-vol-{device.split('/')[-1]}"
            console.print(f"[bold]Snapshotting volume {vol_id}[/bold] ({device}): {snap_name}")
            client.post(f"{client.volume_url}/snapshots",
                        json={"snapshot": {"volume_id": vol_id, "name": snap_name, "force": True}})
            console.print(f"  [green]✓[/green] Snapshot '{snap_name}' creation started.")

    console.print(f"\n[bold green]Snapshot complete for '{srv_name}'.[/bold green]")
    console.print("[dim]Use 'orca image list' and 'orca volume snapshot-list' to track progress.[/dim]")


# ── wait ─────────────────────────────────────────────────────────────────

@server.command("wait")
@click.argument("server_id", callback=validate_id)
@click.option("--status", "target_status", default="ACTIVE", show_default=True,
              help="Target status to wait for.")
@click.option("--timeout", default=300, show_default=True, type=int,
              help="Timeout in seconds.")
@click.option("--interval", default=5, show_default=True, type=int,
              help="Poll interval in seconds.")
@click.pass_context
def server_wait(ctx: click.Context, server_id: str, target_status: str, timeout: int, interval: int) -> None:
    """Wait for a server to reach a target status.

    Polls the server status until it matches the target or the timeout
    is reached. Useful in scripts and automation.

    \b
    Examples:
      orca server wait <id> --status ACTIVE
      orca server wait <id> --status SHUTOFF --timeout 120
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    target = target_status.upper()
    start = time.monotonic()

    with console.status(f"[bold cyan]Waiting for {server_id} → {target}…[/bold cyan]") as spinner:
        while True:
            data = client.get(f"{client.compute_url}/servers/{server_id}")
            srv = data.get("server", data)
            current = srv.get("status", "UNKNOWN").upper()

            if current == target:
                elapsed = time.monotonic() - start
                console.print(f"[green]Server {server_id} is {target} ({elapsed:.0f}s).[/green]")
                return

            if current == "ERROR":
                fault = srv.get("fault", {}).get("message", "")
                msg = f"Server {server_id} entered ERROR state."
                if fault:
                    msg += f" Fault: {fault}"
                raise click.ClickException(msg)

            elapsed = time.monotonic() - start
            if elapsed >= timeout:
                raise click.ClickException(
                    f"Timeout after {timeout}s. Server is still '{current}'."
                )

            spinner.update(f"[bold cyan]Waiting for {server_id} → {target} (current: {current}, {elapsed:.0f}s)…[/bold cyan]")
            time.sleep(interval)


# ── bulk ─────────────────────────────────────────────────────────────────

@server.command("bulk")
@click.argument("action", type=click.Choice(["start", "stop", "reboot", "delete"], case_sensitive=False))
@click.option("--name", "name_pattern", default=None, help="Filter by name (supports wildcards: dev-*).")
@click.option("--status", "status_filter", default=None, help="Filter by status (e.g. ERROR, SHUTOFF).")
@click.option("--all", "select_all", is_flag=True, help="Select all servers (use with caution).")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def server_bulk(ctx: click.Context, action: str, name_pattern: str | None,
                status_filter: str | None, select_all: bool, yes: bool) -> None:
    """Perform an action on multiple servers at once.

    \b
    Examples:
      orca server bulk stop --name "dev-*"
      orca server bulk delete --status ERROR --yes
      orca server bulk reboot --name "web-*" --status ACTIVE
    """
    if not name_pattern and not status_filter and not select_all:
        raise click.ClickException("Provide --name, --status, or --all to select servers.")

    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{client.compute_url}/servers/detail", params={"limit": 1000})
    servers = data.get("servers", [])

    # Filter
    matched = []
    for s in servers:
        if name_pattern and not fnmatch.fnmatch(s.get("name", ""), name_pattern):
            continue
        if status_filter and s.get("status", "").upper() != status_filter.upper():
            continue
        matched.append(s)

    if not matched:
        console.print("[yellow]No servers match the given filters.[/yellow]")
        return

    # Show what will be affected
    console.print(f"\n[bold]{action.upper()}[/bold] will affect {len(matched)} server(s):\n")
    for s in matched:
        console.print(f"  {s['id']}  {s.get('name', '')}  [{s.get('status', '')}]")
    console.print()

    if not yes:
        click.confirm(f"Proceed with {action.upper()} on {len(matched)} server(s)?", abort=True)

    action_map = {
        "start": {"os-start": None},
        "stop": {"os-stop": None},
        "reboot": {"reboot": {"type": "SOFT"}},
    }

    success = 0
    for s in matched:
        sid = s["id"]
        sname = s.get("name", sid)
        try:
            if action == "delete":
                client.delete(f"{client.compute_url}/servers/{sid}")
            else:
                client.post(f"{client.compute_url}/servers/{sid}/action",
                            json=action_map[action])
            console.print(f"  [green]✓[/green] {sname} ({sid})")
            success += 1
        except Exception as e:
            console.print(f"  [red]✗[/red] {sname} ({sid}): {e}")

    console.print(f"\n[bold]{success}/{len(matched)} servers processed.[/bold]")


# ── clone ────────────────────────────────────────────────────────────────

@server.command("clone")
@click.argument("server_id", callback=validate_id)
@click.option("--name", required=True, help="Name for the cloned server.")
@click.option("--disk-size", type=int, default=None, help="Boot volume size in GB. Default: same as source.")
@click.pass_context
def server_clone(ctx: click.Context, server_id: str, name: str, disk_size: int | None) -> None:
    """Clone a server — recreate one with the same config.

    Copies flavor, network, security groups, key pair, and boot
    volume size from the source server into a new one.

    \b
    Examples:
      orca server clone <id> --name web-02
      orca server clone <id> --name web-02 --disk-size 50
    """
    client = ctx.find_object(OrcaContext).ensure_client()

    # Fetch source server
    data = client.get(f"{client.compute_url}/servers/{server_id}")
    src = data.get("server", data)
    src_name = src.get("name", server_id)

    # Flavor
    flavor = src.get("flavor", {})
    flavor_id = flavor.get("id", "")
    if not flavor_id:
        raise click.ClickException("Cannot determine source server flavor.")

    # Image — get from boot volume
    image_id = ""
    if isinstance(src.get("image"), dict) and src["image"].get("id"):
        image_id = src["image"]["id"]

    # If booted from volume, get the image from the volume
    src_disk = disk_size
    if not image_id or not src_disk:
        vol_data = client.get(f"{client.compute_url}/servers/{server_id}/os-volume_attachments")
        attachments = vol_data.get("volumeAttachments", [])
        boot_att = None
        for a in attachments:
            # Boot volume is usually /dev/vda or /dev/sda
            dev = a.get("device", "")
            if "vda" in dev or "sda" in dev:
                boot_att = a
                break
        if not boot_att and attachments:
            boot_att = attachments[0]

        if boot_att:
            vol_id = boot_att.get("volumeId", "")
            if vol_id:
                vol = client.get(f"{client.volume_url}/volumes/{vol_id}").get("volume", {})
                if not src_disk:
                    src_disk = vol.get("size", 20)
                if not image_id:
                    image_id = vol.get("volume_image_metadata", {}).get("image_id", "")

    if not image_id:
        raise click.ClickException(
            "Cannot determine source image. The server may have been booted from a "
            "volume without image metadata."
        )
    if not src_disk:
        src_disk = 20

    # Network
    networks = []
    for net_name, addrs in src.get("addresses", {}).items():
        # We need network IDs, not names — fetch from ports
        break

    # Get ports to find network IDs
    ifaces = client.get(f"{client.compute_url}/servers/{server_id}/os-interface")
    for att in ifaces.get("interfaceAttachments", []):
        net_id = att.get("net_id", "")
        if net_id and net_id not in [n["uuid"] for n in networks]:
            networks.append({"uuid": net_id})

    # Security groups
    security_groups = [{"name": sg.get("name")} for sg in src.get("security_groups", [])]

    # Key pair
    key_name = src.get("key_name")

    # Build the new server
    body: dict = {
        "name": name,
        "flavorRef": flavor_id,
        "block_device_mapping_v2": [
            {
                "boot_index": 0,
                "uuid": image_id,
                "source_type": "image",
                "destination_type": "volume",
                "volume_size": src_disk,
                "delete_on_termination": True,
            }
        ],
    }
    if networks:
        body["networks"] = networks
    if security_groups:
        body["security_groups"] = security_groups
    if key_name:
        body["key_name"] = key_name

    console.print(f"[bold]Cloning '{src_name}' → '{name}'[/bold]")
    console.print(f"  Flavor:  {flavor_id}")
    console.print(f"  Image:   {image_id}")
    console.print(f"  Disk:    {src_disk} GB")
    console.print(f"  Key:     {key_name or '—'}")
    console.print(f"  SGs:     {', '.join(sg['name'] for sg in security_groups) or '—'}")
    console.print(f"  Nets:    {len(networks)}")
    console.print()

    result = client.post(f"{client.compute_url}/servers", json={"server": body})
    new_srv = result.get("server", result)
    new_id = new_srv.get("id", "?")

    console.print(f"[bold green]Server '{name}' ({new_id}) creation started.[/bold green]")
    console.print(f"[dim]Use 'orca server show {new_id}' to track progress.[/dim]")


# ── diff ─────────────────────────────────────────────────────────────────

@server.command("diff")
@click.argument("server_a", callback=validate_id)
@click.argument("server_b", callback=validate_id)
@click.pass_context
def server_diff(ctx: click.Context, server_a: str, server_b: str) -> None:
    """Compare two servers side by side.

    Highlights differences in flavor, image, network, security groups,
    status, and other configuration.

    \b
    Examples:
      orca server diff <id1> <id2>
    """
    from rich.table import Table

    client = ctx.find_object(OrcaContext).ensure_client()

    data_a = client.get(f"{client.compute_url}/servers/{server_a}").get("server", {})
    data_b = client.get(f"{client.compute_url}/servers/{server_b}").get("server", {})

    def _flavor_str(srv: dict) -> str:
        f = srv.get("flavor", {})
        return f.get("original_name", f.get("id", "?"))

    def _image_str(srv: dict) -> str:
        img = srv.get("image")
        if isinstance(img, dict):
            return img.get("id", "—")
        return str(img) if img else "—"

    def _addresses_str(srv: dict) -> str:
        parts = []
        for net, addrs in srv.get("addresses", {}).items():
            for a in addrs:
                parts.append(f"{net}={a.get('addr', '?')}")
        return ", ".join(parts) or "—"

    def _sgs_str(srv: dict) -> str:
        return ", ".join(sorted(sg.get("name", "") for sg in srv.get("security_groups", []))) or "—"

    def _meta_str(srv: dict) -> str:
        m = srv.get("metadata", {})
        if not m:
            return "—"
        return ", ".join(f"{k}={v}" for k, v in m.items())

    fields = [
        ("Name", lambda s: s.get("name", "")),
        ("Status", lambda s: s.get("status", "")),
        ("Flavor", _flavor_str),
        ("Image", _image_str),
        ("Key Pair", lambda s: s.get("key_name", "") or "—"),
        ("Availability Zone", lambda s: s.get("OS-EXT-AZ:availability_zone", "") or "—"),
        ("Addresses", _addresses_str),
        ("Security Groups", _sgs_str),
        ("Power State", lambda s: {0: "NOSTATE", 1: "Running", 3: "Paused", 4: "Shutdown", 6: "Crashed", 7: "Suspended"}.get(s.get("OS-EXT-STS:power_state", 0), "?")),
        ("VM State", lambda s: s.get("OS-EXT-STS:vm_state", "") or "—"),
        ("Task State", lambda s: s.get("OS-EXT-STS:task_state") or "—"),
        ("Created", lambda s: s.get("created", "")),
        ("Updated", lambda s: s.get("updated", "")),
        ("Host", lambda s: s.get("OS-EXT-SRV-ATTR:host", "") or "—"),
        ("Metadata", _meta_str),
    ]

    name_a = data_a.get("name", server_a)
    name_b = data_b.get("name", server_b)

    table = Table(title=f"Diff: {name_a} ↔ {name_b}", show_lines=False)
    table.add_column("Field", style="bold cyan", no_wrap=True)
    table.add_column(name_a, style="white")
    table.add_column(name_b, style="white")
    table.add_column("", no_wrap=True)  # diff marker

    diffs = 0
    for label, fn in fields:
        val_a = str(fn(data_a))
        val_b = str(fn(data_b))
        if val_a != val_b:
            marker = "[red bold]≠[/red bold]"
            diffs += 1
        else:
            marker = "[green]=[/green]"
        table.add_row(label, val_a, val_b, marker)

    console.print()
    console.print(table)
    if diffs:
        console.print(f"\n  [red]{diffs} difference(s)[/red]\n")
    else:
        console.print("\n  [green]Servers are identical.[/green]\n")


# ── port-forward (SSH tunnel) ───────────────────────────────────────────

@server.command("port-forward")
@click.argument("server_id")
@click.argument("port_mapping")
@click.option("--user", "-u", "ssh_user", default=None,
              help="SSH user. Default: 'root'.")
@click.option("--key", "-i", "key_path", type=click.Path(), default=None,
              help="Private key path.")
@click.option("--ssh-port", "-p", type=int, default=22, show_default=True,
              help="SSH port on the server.")
@click.option("--reverse", "-R", is_flag=True, default=False,
              help="Reverse tunnel (remote → local).")
@click.option("--background", "-b", "bg", is_flag=True, default=False,
              help="Run tunnel in background (-f -N).")
@click.pass_context
def server_port_forward(
    ctx: click.Context, server_id: str, port_mapping: str,
    ssh_user: str | None, key_path: str | None, ssh_port: int,
    reverse: bool, bg: bool,
) -> None:
    """Create an SSH tunnel (port forward) to a server.

    PORT_MAPPING format: LOCAL_PORT:REMOTE_HOST:REMOTE_PORT

    \b
    Examples:
      orca server port-forward <id> 8080:localhost:80          # local forward
      orca server port-forward <id> 3306:db-server:3306        # forward to internal host
      orca server port-forward <id> 9090:localhost:9090 -R     # reverse tunnel
      orca server port-forward <id> 5432:localhost:5432 -b     # background
    """

    client = ctx.find_object(OrcaContext).ensure_client()

    # Resolve server
    try:
        data = client.get(f"{client.compute_url}/servers/{server_id}")
        srv = data.get("server", data)
    except Exception:
        data = client.get(f"{client.compute_url}/servers/detail",
                          params={"name": server_id})
        matches = data.get("servers", [])
        if not matches:
            raise click.ClickException(f"Server '{server_id}' not found.")
        if len(matches) > 1:
            console.print(f"[yellow]Multiple servers match '{server_id}':[/yellow]")
            for m in matches:
                console.print(f"  {m['id']}  {m.get('name', '')}")
            raise click.ClickException("Be more specific or use the server ID.")
        srv = matches[0]

    ip = _pick_ssh_ip(srv)
    if not ip:
        raise click.ClickException(
            f"No IP address found for server '{srv.get('name', server_id)}'.")

    # Validate port mapping
    parts = port_mapping.split(":")
    if len(parts) != 3:
        raise click.ClickException(
            "PORT_MAPPING must be LOCAL_PORT:REMOTE_HOST:REMOTE_PORT "
            "(e.g. 8080:localhost:80)")
    local_port, remote_host, remote_port = parts

    if not ssh_user:
        ssh_user = "root"

    # Find SSH key (same logic as server ssh)
    if not key_path:
        key_path = _find_ssh_key(srv.get("key_name"))

    # Build SSH tunnel command
    flag = "-R" if reverse else "-L"
    tunnel_spec = f"{local_port}:{remote_host}:{remote_port}"

    cmd = ["ssh", flag, tunnel_spec]
    if key_path:
        cmd.extend(["-i", key_path])
    if ssh_port != 22:
        cmd.extend(["-p", str(ssh_port)])
    if bg:
        cmd.extend(["-f", "-N"])
    else:
        cmd.append("-N")
    cmd.append(f"{ssh_user}@{ip}")

    direction = "remote → local" if reverse else "local → remote"
    console.print(
        f"[bold]Tunnel ({direction}):[/bold] "
        f"{'localhost' if not reverse else remote_host}:{local_port} → "
        f"{remote_host if not reverse else 'localhost'}:{remote_port}"
    )
    console.print(f"[dim]$ {' '.join(cmd)}[/dim]")

    if bg:
        import subprocess
        subprocess.Popen(cmd)
        console.print("[green]Tunnel started in background.[/green]")
    else:
        console.print("[dim]Press Ctrl+C to stop the tunnel.[/dim]")
        os.execvp("ssh", cmd)


# ══════════════════════════════════════════════════════════════════════════
#  migrate / live-migrate
# ══════════════════════════════════════════════════════════════════════════


@server.command("migrate")
@click.argument("server_id")
@click.option("--host", default=None, help="Target host (admin only, optional).")
@click.pass_context
def server_migrate(ctx: click.Context, server_id: str, host: str | None) -> None:
    """Cold-migrate a server to another host."""
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {}
    if host:
        body["host"] = host
    client.post(f"{client.compute_url}/servers/{server_id}/action",
                json={"migrate": body or None})
    console.print(f"[green]Migration of server {server_id} started.[/green]")
    console.print("[dim]Use 'orca server show' to track progress.[/dim]")


@server.command("live-migrate")
@click.argument("server_id")
@click.option("--host", default=None, help="Target host (admin only, optional).")
@click.option("--block-migration/--no-block-migration", "block_migration", default=False,
              show_default=True, help="Use block migration (copies disk, slower but no shared storage needed).")
@click.pass_context
def server_live_migrate(ctx: click.Context, server_id: str, host: str | None,
                        block_migration: bool) -> None:
    """Live-migrate a server without downtime."""
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {
        "host": host,
        "block_migration": block_migration,
    }
    client.post(f"{client.compute_url}/servers/{server_id}/action",
                json={"os-migrateLive": body})
    console.print(f"[green]Live migration of server {server_id} started.[/green]")
    console.print("[dim]Use 'orca server show' to track progress.[/dim]")


# ══════════════════════════════════════════════════════════════════════════
#  security-group add/remove
# ══════════════════════════════════════════════════════════════════════════


@server.command("add-security-group")
@click.argument("server_id")
@click.argument("security_group")
@click.pass_context
def server_add_security_group(ctx: click.Context, server_id: str, security_group: str) -> None:
    """Add a security group to a running server."""
    client = ctx.find_object(OrcaContext).ensure_client()
    client.post(f"{client.compute_url}/servers/{server_id}/action",
                json={"addSecurityGroup": {"name": security_group}})
    console.print(f"[green]Security group '{security_group}' added to server {server_id}.[/green]")


@server.command("remove-security-group")
@click.argument("server_id")
@click.argument("security_group")
@click.pass_context
def server_remove_security_group(ctx: click.Context, server_id: str, security_group: str) -> None:
    """Remove a security group from a running server."""
    client = ctx.find_object(OrcaContext).ensure_client()
    client.post(f"{client.compute_url}/servers/{server_id}/action",
                json={"removeSecurityGroup": {"name": security_group}})
    console.print(f"[green]Security group '{security_group}' removed from server {server_id}.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  set (metadata, tags, admin password)
# ══════════════════════════════════════════════════════════════════════════


@server.command("set")
@click.argument("server_id")
@click.option("--name", default=None, help="New display name.")
@click.option("--property", "properties", multiple=True, metavar="KEY=VALUE",
              help="Metadata key=value (repeatable).")
@click.option("--tag", "tags", multiple=True, help="Tag to set (repeatable, replaces all existing tags).")
@click.option("--admin-password", default=None, help="New admin/root password (injected via Nova).")
@click.pass_context
def server_set(ctx: click.Context, server_id: str, name: str | None,
               properties: tuple[str, ...], tags: tuple[str, ...],
               admin_password: str | None) -> None:
    """Set server properties, metadata, tags, or admin password.

    \b
    Examples:
      orca server set <id> --name new-name
      orca server set <id> --property env=prod --property team=infra
      orca server set <id> --tag web --tag frontend
      orca server set <id> --admin-password s3cr3t
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    did_something = False

    if name:
        client.put(f"{client.compute_url}/servers/{server_id}",
                   json={"server": {"name": name}})
        console.print(f"[green]Server {server_id} renamed to '{name}'.[/green]")
        did_something = True

    if properties:
        meta = {}
        for prop in properties:
            if "=" not in prop:
                raise click.UsageError(f"Invalid format '{prop}', expected KEY=VALUE.")
            k, v = prop.split("=", 1)
            meta[k] = v
        client.post(f"{client.compute_url}/servers/{server_id}/metadata",
                    json={"metadata": meta})
        console.print(f"[green]Metadata updated on server {server_id}.[/green]")
        did_something = True

    if tags:
        client.put(f"{client.compute_url}/servers/{server_id}/tags",
                   json={"tags": list(tags)})
        console.print(f"[green]Tags set on server {server_id}: {', '.join(tags)}[/green]")
        did_something = True

    if admin_password:
        client.post(f"{client.compute_url}/servers/{server_id}/action",
                    json={"changePassword": {"adminPass": admin_password}})
        console.print(f"[green]Admin password changed for server {server_id}.[/green]")
        did_something = True

    if not did_something:
        console.print("[yellow]Nothing to set.[/yellow]")


# ══════════════════════════════════════════════════════════════════════════
#  metadata / tag list
# ══════════════════════════════════════════════════════════════════════════


@server.command("metadata-list")
@click.argument("server_id")
@click.pass_context
def server_metadata_list(ctx: click.Context, server_id: str) -> None:
    """Show all metadata key/value pairs for a server."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{client.compute_url}/servers/{server_id}/metadata")
    meta = data.get("metadata", {})
    if not meta:
        console.print("[yellow]No metadata set.[/yellow]")
        return
    from rich.table import Table

    from orca_cli.core.output import console as _console
    table = Table(title="Server Metadata", show_lines=False)
    table.add_column("Key", style="bold")
    table.add_column("Value")
    for k, v in meta.items():
        table.add_row(k, str(v))
    _console.print(table)


@server.command("tag-list")
@click.argument("server_id")
@click.pass_context
def server_tag_list(ctx: click.Context, server_id: str) -> None:
    """List tags on a server."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{client.compute_url}/servers/{server_id}/tags")
    tags = data.get("tags", [])
    if not tags:
        console.print("[yellow]No tags set.[/yellow]")
    else:
        for tag in tags:
            console.print(f"  {tag}")





# ── migration-list / migration-show ───────────────────────────────────────

@server.command("migration-list")
@click.argument("server_id", callback=validate_id, shell_complete=complete_servers)
@output_options
@click.pass_context
def server_migration_list(ctx: click.Context, server_id: str,
                          output_format: str, columns: tuple[str, ...],
                          fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List migrations for a server."""
    client = ctx.find_object(OrcaContext).ensure_client()
    migrations = client.get(
        f"{client.compute_url}/servers/{server_id}/migrations"
    ).get("migrations", [])

    print_list(
        migrations,
        [
            ("ID", "id", {"style": "cyan"}),
            ("Type", "migration_type"),
            ("Status", "status", {"style": "green"}),
            ("Source", "source_compute"),
            ("Dest", "dest_compute"),
            ("Created", lambda m: (m.get("created_at") or "")[:19]),
            ("Updated", lambda m: (m.get("updated_at") or "")[:19]),
        ],
        title=f"Migrations for server {server_id}",
        output_format=output_format, fit_width=fit_width, max_width=max_width,
        noindent=noindent, columns=columns,
        empty_msg="No migrations found.",
    )


@server.command("migration-show")
@click.argument("server_id", callback=validate_id, shell_complete=complete_servers)
@click.argument("migration_id")
@output_options
@click.pass_context
def server_migration_show(ctx: click.Context, server_id: str, migration_id: str,
                          output_format: str, columns: tuple[str, ...],
                          fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show details of a specific migration."""
    client = ctx.find_object(OrcaContext).ensure_client()
    m = client.get(
        f"{client.compute_url}/servers/{server_id}/migrations/{migration_id}"
    ).get("migration", {})

    print_detail(
        [(k, str(m.get(k, "") or "")) for k in [
            "id", "migration_type", "status",
            "source_compute", "source_node",
            "dest_compute", "dest_node",
            "old_instance_type_id", "new_instance_type_id",
            "created_at", "updated_at",
        ]],
        output_format=output_format, fit_width=fit_width, max_width=max_width,
        noindent=noindent, columns=columns,
    )


@server.command("migration-abort")
@click.argument("server_id", callback=validate_id, shell_complete=complete_servers)
@click.argument("migration_id")
@click.pass_context
def server_migration_abort(ctx: click.Context, server_id: str, migration_id: str) -> None:
    """Abort an in-progress live migration."""
    client = ctx.find_object(OrcaContext).ensure_client()
    client.delete(
        f"{client.compute_url}/servers/{server_id}/migrations/{migration_id}"
    )
    console.print(f"Migration [bold]{migration_id}[/bold] aborted.")


@server.command("migration-force-complete")
@click.argument("server_id", callback=validate_id, shell_complete=complete_servers)
@click.argument("migration_id")
@click.pass_context
def server_migration_force_complete(ctx: click.Context, server_id: str, migration_id: str) -> None:
    """Force an in-progress live migration to complete."""
    client = ctx.find_object(OrcaContext).ensure_client()
    client.post(
        f"{client.compute_url}/servers/{server_id}/migrations/{migration_id}/action",
        json={"force_complete": None},
    )
    console.print(f"Migration [bold]{migration_id}[/bold] forced to complete.")


# ══════════════════════════════════════════════════════════════════════════
#  evacuate / dump-create / restore
# ══════════════════════════════════════════════════════════════════════════


@server.command("evacuate")
@click.argument("server_id")
@click.option("--host", default=None, help="Target host (admin only, optional).")
@click.option("--on-shared-storage/--no-shared-storage", "on_shared_storage",
              default=False, show_default=True,
              help="Whether server disks are on shared storage.")
@click.option("--password", "admin_pass", default=None,
              help="Admin password for the evacuated server.")
@click.pass_context
def server_evacuate(ctx: click.Context, server_id: str, host: str | None,
                    on_shared_storage: bool, admin_pass: str | None) -> None:
    """Evacuate a server from a failed host to another.

    \b
    Examples:
      orca server evacuate <id>
      orca server evacuate <id> --host compute02
      orca server evacuate <id> --on-shared-storage
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {"onSharedStorage": on_shared_storage}
    if host:
        body["host"] = host
    if admin_pass:
        body["adminPass"] = admin_pass
    client.post(f"{client.compute_url}/servers/{server_id}/action",
                json={"evacuate": body})
    console.print(f"[green]Server {server_id} evacuation started.[/green]")
    console.print("[dim]Use 'orca server show' to track status.[/dim]")


@server.command("dump-create")
@click.argument("server_id")
@click.pass_context
def server_dump_create(ctx: click.Context, server_id: str) -> None:
    """Trigger a crash dump on a server (requires Nova microversion ≥ 2.17).

    Sends an NMI to the server which causes the guest OS to generate
    a crash dump. The server must be ACTIVE.
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    client.post(f"{client.compute_url}/servers/{server_id}/action",
                json={"trigger_crash_dump": None})
    console.print(f"[green]Crash dump triggered on server {server_id}.[/green]")


@server.command("restore")
@click.argument("server_id")
@click.pass_context
def server_restore(ctx: click.Context, server_id: str) -> None:
    """Restore a soft-deleted server.

    Only valid when Nova is configured with soft-delete
    (reclaim_instance_interval > 0) and the server status is SOFT_DELETED.
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    client.post(f"{client.compute_url}/servers/{server_id}/action",
                json={"restore": None})
    console.print(f"[green]Server {server_id} restored.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  fixed-ip add/remove  (deprecated in Nova ≥ 2.44 but still supported)
# ══════════════════════════════════════════════════════════════════════════


@server.command("add-fixed-ip")
@click.argument("server_id")
@click.argument("network_id")
@click.pass_context
def server_add_fixed_ip(ctx: click.Context, server_id: str, network_id: str) -> None:
    """Add a fixed IP from a network to a server.

    \b
    Example:
      orca server add-fixed-ip <server-id> <network-id>
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    client.post(f"{client.compute_url}/servers/{server_id}/action",
                json={"addFixedIp": {"networkId": network_id}})
    console.print(f"[green]Fixed IP from network {network_id} added to server {server_id}.[/green]")


@server.command("remove-fixed-ip")
@click.argument("server_id")
@click.argument("ip_address")
@click.pass_context
def server_remove_fixed_ip(ctx: click.Context, server_id: str, ip_address: str) -> None:
    """Remove a specific fixed IP from a server.

    \b
    Example:
      orca server remove-fixed-ip <server-id> 10.0.0.5
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    client.post(f"{client.compute_url}/servers/{server_id}/action",
                json={"removeFixedIp": {"address": ip_address}})
    console.print(f"[green]Fixed IP {ip_address} removed from server {server_id}.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  port / network add/remove
# ══════════════════════════════════════════════════════════════════════════


@server.command("add-port")
@click.argument("server_id")
@click.argument("port_id")
@click.pass_context
def server_add_port(ctx: click.Context, server_id: str, port_id: str) -> None:
    """Attach an existing Neutron port to a server.

    \b
    Example:
      orca server add-port <server-id> <port-id>
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.post(
        f"{client.compute_url}/servers/{server_id}/os-interface",
        json={"interfaceAttachment": {"port_id": port_id}},
    )
    att = data.get("interfaceAttachment", data) if data else {}
    ips = ", ".join(ip.get("ip_address", "") for ip in att.get("fixed_ips", []))
    console.print(f"[green]Port {port_id} attached to server {server_id} ({ips}).[/green]")


@server.command("remove-port")
@click.argument("server_id")
@click.argument("port_id")
@click.pass_context
def server_remove_port(ctx: click.Context, server_id: str, port_id: str) -> None:
    """Detach a Neutron port from a server.

    \b
    Example:
      orca server remove-port <server-id> <port-id>
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    client.delete(f"{client.compute_url}/servers/{server_id}/os-interface/{port_id}")
    console.print(f"[green]Port {port_id} removed from server {server_id}.[/green]")


@server.command("add-network")
@click.argument("server_id")
@click.argument("network_id")
@click.pass_context
def server_add_network(ctx: click.Context, server_id: str, network_id: str) -> None:
    """Attach a network to a server (creates a new port automatically).

    \b
    Example:
      orca server add-network <server-id> <network-id>
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.post(
        f"{client.compute_url}/servers/{server_id}/os-interface",
        json={"interfaceAttachment": {"net_id": network_id}},
    )
    att = data.get("interfaceAttachment", data) if data else {}
    ips = ", ".join(ip.get("ip_address", "") for ip in att.get("fixed_ips", []))
    console.print(
        f"[green]Network {network_id} attached to server {server_id} "
        f"— port {att.get('port_id', '')} ({ips}).[/green]"
    )


@server.command("remove-network")
@click.argument("server_id")
@click.argument("network_id")
@click.pass_context
def server_remove_network(ctx: click.Context, server_id: str, network_id: str) -> None:
    """Detach all interfaces on a specific network from a server.

    Looks up interfaces by network ID and removes each one.

    \b
    Example:
      orca server remove-network <server-id> <network-id>
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{client.compute_url}/servers/{server_id}/os-interface")
    interfaces = data.get("interfaceAttachments", [])
    matching = [i for i in interfaces if i.get("net_id") == network_id]

    if not matching:
        console.print(f"[yellow]No interfaces found for network {network_id} on server {server_id}.[/yellow]")
        return

    for iface in matching:
        port_id = iface["port_id"]
        client.delete(f"{client.compute_url}/servers/{server_id}/os-interface/{port_id}")
        console.print(f"  Removed port {port_id}")

    console.print(
        f"[green]{len(matching)} interface(s) on network {network_id} removed from server {server_id}.[/green]"
    )


# ══════════════════════════════════════════════════════════════════════════
#  unset
# ══════════════════════════════════════════════════════════════════════════


@server.command("unset")
@click.argument("server_id")
@click.option("--property", "properties", multiple=True, metavar="KEY",
              help="Metadata key to remove (repeatable).")
@click.option("--tag", "tags", multiple=True,
              help="Tag to remove (repeatable).")
@click.pass_context
def server_unset(ctx: click.Context, server_id: str,
                 properties: tuple[str, ...], tags: tuple[str, ...]) -> None:
    """Remove metadata keys or tags from a server.

    \b
    Examples:
      orca server unset <id> --property env --property team
      orca server unset <id> --tag web --tag frontend
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    did_something = False

    for key in properties:
        client.delete(f"{client.compute_url}/servers/{server_id}/metadata/{key}")
        console.print(f"  Removed metadata key: {key}")
        did_something = True

    for tag in tags:
        client.delete(f"{client.compute_url}/servers/{server_id}/tags/{tag}")
        console.print(f"  Removed tag: {tag}")
        did_something = True

    if not did_something:
        console.print("[yellow]Nothing to unset — provide --property or --tag.[/yellow]")
    else:
        console.print(f"[green]Server {server_id} updated.[/green]")
