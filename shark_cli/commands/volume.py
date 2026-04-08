"""``shark volume`` — manage block storage volumes & snapshots (Cinder v3)."""

from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from shark_cli.core.context import SharkContext
from shark_cli.core.validators import validate_id

console = Console()


def _vol_action(ctx: click.Context, volume_id: str, action: dict, label: str) -> None:
    client = ctx.find_object(SharkContext).ensure_client()
    url = f"{client.volume_url}/volumes/{volume_id}/action"
    client.post(url, json=action)
    console.print(f"[green]{label} request sent for {volume_id}.[/green]")


@click.group()
@click.pass_context
def volume(ctx: click.Context) -> None:
    """Manage block storage volumes & snapshots."""
    pass


# ── list ──────────────────────────────────────────────────────────────────

@volume.command("list")
@click.pass_context
def volume_list(ctx: click.Context) -> None:
    """List volumes."""
    client = ctx.find_object(SharkContext).ensure_client()
    url = f"{client.volume_url}/volumes/detail"
    data = client.get(url)

    volumes = data.get("volumes", [])

    if not volumes:
        console.print("[yellow]No volumes found.[/yellow]")
        return

    table = Table(title="Volumes", show_lines=True)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="bold")
    table.add_column("Size (GB)", justify="right")
    table.add_column("Status", style="green")
    table.add_column("Bootable")
    table.add_column("Type")
    table.add_column("Attached To")

    for vol in volumes:
        attachments = vol.get("attachments", [])
        attached = ", ".join(a.get("server_id", "") for a in attachments) or "—"
        table.add_row(
            vol.get("id", ""),
            vol.get("name", "") or "—",
            str(vol.get("size", "")),
            vol.get("status", ""),
            vol.get("bootable", ""),
            vol.get("volume_type", "") or "—",
            attached,
        )

    console.print(table)


# ── show ──────────────────────────────────────────────────────────────────

@volume.command("show")
@click.argument("volume_id", callback=validate_id)
@click.pass_context
def volume_show(ctx: click.Context, volume_id: str) -> None:
    """Show volume details."""
    client = ctx.find_object(SharkContext).ensure_client()
    url = f"{client.volume_url}/volumes/{volume_id}"
    data = client.get(url)

    vol = data.get("volume", data)

    table = Table(title=f"Volume {vol.get('name') or volume_id}", show_lines=True)
    table.add_column("Property", style="bold cyan")
    table.add_column("Value")

    display_keys = [
        "id", "name", "status", "size", "volume_type", "bootable",
        "encrypted", "multiattach", "availability_zone",
        "snapshot_id", "source_volid", "description",
        "created_at", "updated_at",
    ]
    for key in display_keys:
        val = vol.get(key, "")
        if key == "size" and val:
            val = f"{val} GB"
        table.add_row(key, str(val) if val is not None else "")

    attachments = vol.get("attachments", [])
    if attachments:
        for a in attachments:
            table.add_row("attached_to", f"{a.get('server_id', '')} @ {a.get('device', '')}")

    console.print(table)


# ── create ────────────────────────────────────────────────────────────────

@volume.command("create")
@click.option("--name", required=True, help="Volume name.")
@click.option("--size", required=True, type=int, help="Size in GB.")
@click.option("--type", "volume_type", default=None, help="Volume type.")
@click.option("--description", default=None, help="Volume description.")
@click.option("--snapshot-id", default=None, help="Create from snapshot.")
@click.option("--source-vol", default=None, help="Create from existing volume (clone).")
@click.option("--image-id", default=None, help="Create from image.")
@click.pass_context
def volume_create(ctx: click.Context, name: str, size: int, volume_type: str | None,
                  description: str | None, snapshot_id: str | None,
                  source_vol: str | None, image_id: str | None) -> None:
    """Create a volume."""
    client = ctx.find_object(SharkContext).ensure_client()

    body: dict = {"name": name, "size": size}
    if volume_type:
        body["volume_type"] = volume_type
    if description:
        body["description"] = description
    if snapshot_id:
        body["snapshot_id"] = snapshot_id
    if source_vol:
        body["source_volid"] = source_vol
    if image_id:
        body["imageRef"] = image_id

    url = f"{client.volume_url}/volumes"
    data = client.post(url, json={"volume": body})

    vol = data.get("volume", data)
    console.print(f"[green]Volume '{vol.get('name')}' ({vol.get('id')}) created — {size} GB.[/green]")


# ── update (rename / description) ─────────────────────────────────────────

@volume.command("update")
@click.argument("volume_id", callback=validate_id)
@click.option("--name", default=None, help="New name.")
@click.option("--description", default=None, help="New description.")
@click.pass_context
def volume_update(ctx: click.Context, volume_id: str, name: str | None, description: str | None) -> None:
    """Update volume name or description."""
    body: dict = {}
    if name is not None:
        body["name"] = name
    if description is not None:
        body["description"] = description
    if not body:
        console.print("[yellow]Nothing to update. Use --name or --description.[/yellow]")
        return

    client = ctx.find_object(SharkContext).ensure_client()
    url = f"{client.volume_url}/volumes/{volume_id}"
    client.put(url, json={"volume": body})
    console.print(f"[green]Volume {volume_id} updated.[/green]")


# ── extend ────────────────────────────────────────────────────────────────

@volume.command("extend")
@click.argument("volume_id", callback=validate_id)
@click.option("--size", required=True, type=int, help="New size in GB (must be larger).")
@click.pass_context
def volume_extend(ctx: click.Context, volume_id: str, size: int) -> None:
    """Extend a volume to a larger size."""
    _vol_action(ctx, volume_id, {"os-extend": {"new_size": size}}, f"Extend to {size} GB")


# ── retype ────────────────────────────────────────────────────────────────

@volume.command("retype")
@click.argument("volume_id", callback=validate_id)
@click.option("--type", "new_type", required=True, help="New volume type.")
@click.option("--migration-policy", type=click.Choice(["never", "on-demand"]), default="never", show_default=True, help="Migration policy.")
@click.pass_context
def volume_retype(ctx: click.Context, volume_id: str, new_type: str, migration_policy: str) -> None:
    """Change volume type."""
    _vol_action(ctx, volume_id, {"os-retype": {"new_type": new_type, "migration_policy": migration_policy}}, f"Retype to '{new_type}'")


# ── set-bootable ──────────────────────────────────────────────────────────

@volume.command("set-bootable")
@click.argument("volume_id", callback=validate_id)
@click.argument("bootable", type=click.Choice(["true", "false"]))
@click.pass_context
def volume_set_bootable(ctx: click.Context, volume_id: str, bootable: str) -> None:
    """Set or unset bootable flag on a volume."""
    _vol_action(ctx, volume_id, {"os-set_bootable": {"bootable": bootable == "true"}}, f"Set bootable={bootable}")


# ── set-readonly ──────────────────────────────────────────────────────────

@volume.command("set-readonly")
@click.argument("volume_id", callback=validate_id)
@click.argument("readonly", type=click.Choice(["true", "false"]))
@click.pass_context
def volume_set_readonly(ctx: click.Context, volume_id: str, readonly: str) -> None:
    """Set or unset read-only flag on a volume."""
    _vol_action(ctx, volume_id, {"os-update_readonly_flag": {"readonly": readonly == "true"}}, f"Set readonly={readonly}")


# ── delete ────────────────────────────────────────────────────────────────

@volume.command("delete")
@click.argument("volume_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def volume_delete(ctx: click.Context, volume_id: str, yes: bool) -> None:
    """Delete a volume."""
    if not yes:
        click.confirm(f"Delete volume {volume_id}?", abort=True)

    client = ctx.find_object(SharkContext).ensure_client()
    url = f"{client.volume_url}/volumes/{volume_id}"
    client.delete(url)
    console.print(f"[green]Volume {volume_id} deleted.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  Snapshots
# ══════════════════════════════════════════════════════════════════════════

@volume.command("snapshot-list")
@click.pass_context
def snapshot_list(ctx: click.Context) -> None:
    """List volume snapshots."""
    client = ctx.find_object(SharkContext).ensure_client()
    url = f"{client.volume_url}/snapshots/detail"
    data = client.get(url)

    snaps = data.get("snapshots", [])
    if not snaps:
        console.print("[yellow]No snapshots found.[/yellow]")
        return

    table = Table(title="Volume Snapshots", show_lines=True)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="bold")
    table.add_column("Volume ID")
    table.add_column("Size (GB)", justify="right")
    table.add_column("Status", style="green")
    table.add_column("Created")

    for s in snaps:
        table.add_row(
            s.get("id", ""),
            s.get("name", "") or "—",
            s.get("volume_id", ""),
            str(s.get("size", "")),
            s.get("status", ""),
            s.get("created_at", ""),
        )

    console.print(table)


@volume.command("snapshot-show")
@click.argument("snapshot_id", callback=validate_id)
@click.pass_context
def snapshot_show(ctx: click.Context, snapshot_id: str) -> None:
    """Show snapshot details."""
    client = ctx.find_object(SharkContext).ensure_client()
    url = f"{client.volume_url}/snapshots/{snapshot_id}"
    data = client.get(url)

    snap = data.get("snapshot", data)

    table = Table(title=f"Snapshot {snap.get('name') or snapshot_id}", show_lines=True)
    table.add_column("Property", style="bold cyan")
    table.add_column("Value")

    for key in ["id", "name", "description", "volume_id", "size", "status", "created_at"]:
        val = snap.get(key, "")
        if key == "size" and val:
            val = f"{val} GB"
        table.add_row(key, str(val) if val is not None else "")

    console.print(table)


@volume.command("snapshot-create")
@click.argument("volume_id", callback=validate_id)
@click.option("--name", required=True, help="Snapshot name.")
@click.option("--description", default=None, help="Snapshot description.")
@click.option("--force", is_flag=True, help="Force snapshot of in-use volume.")
@click.pass_context
def snapshot_create(ctx: click.Context, volume_id: str, name: str, description: str | None, force: bool) -> None:
    """Create a snapshot of a volume."""
    client = ctx.find_object(SharkContext).ensure_client()

    body: dict = {"volume_id": volume_id, "name": name, "force": force}
    if description:
        body["description"] = description

    url = f"{client.volume_url}/snapshots"
    data = client.post(url, json={"snapshot": body})

    snap = data.get("snapshot", data)
    console.print(f"[green]Snapshot '{snap.get('name')}' ({snap.get('id')}) created from {volume_id}.[/green]")


@volume.command("snapshot-delete")
@click.argument("snapshot_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def snapshot_delete(ctx: click.Context, snapshot_id: str, yes: bool) -> None:
    """Delete a volume snapshot."""
    if not yes:
        click.confirm(f"Delete snapshot {snapshot_id}?", abort=True)

    client = ctx.find_object(SharkContext).ensure_client()
    url = f"{client.volume_url}/snapshots/{snapshot_id}"
    client.delete(url)
    console.print(f"[green]Snapshot {snapshot_id} deleted.[/green]")
