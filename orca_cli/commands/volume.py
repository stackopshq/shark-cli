"""``orca volume`` — manage block storage volumes & snapshots (Cinder v3)."""

from __future__ import annotations

import click

from orca_cli.core import cache
from orca_cli.core.completions import complete_volumes
from orca_cli.core.context import OrcaContext
from orca_cli.core.output import console, output_options, print_detail, print_list
from orca_cli.core.validators import validate_id
from orca_cli.core.waiter import wait_for_resource


def _vol_action(ctx: click.Context, volume_id: str, action: dict, label: str) -> None:
    client = ctx.find_object(OrcaContext).ensure_client()
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
@output_options
@click.pass_context
def volume_list(ctx: click.Context, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List volumes."""
    client = ctx.find_object(OrcaContext).ensure_client()
    url = f"{client.volume_url}/volumes/detail"
    data = client.get(url)

    volumes = data.get("volumes", [])

    print_list(
        volumes,
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Name", lambda v: v.get("name", "") or "—", {"style": "bold"}),
            ("Size (GB)", lambda v: str(v.get("size", "")), {"justify": "right"}),
            ("Status", "status", {"style": "green"}),
            ("Bootable", "bootable"),
            ("Type", lambda v: v.get("volume_type", "") or "—"),
            ("Attached To", lambda v: ", ".join(
                a.get("server_id", "") for a in v.get("attachments", [])
            ) or "—"),
        ],
        title="Volumes",
        output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent,
        columns=columns,
        empty_msg="No volumes found.",
    )


# ── show ──────────────────────────────────────────────────────────────────

@volume.command("show")
@click.argument("volume_id", callback=validate_id)
@output_options
@click.pass_context
def volume_show(ctx: click.Context, volume_id: str, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show volume details."""
    client = ctx.find_object(OrcaContext).ensure_client()
    url = f"{client.volume_url}/volumes/{volume_id}"
    data = client.get(url)

    vol = data.get("volume", data)

    display_keys = [
        "id", "name", "status", "size", "volume_type", "bootable",
        "encrypted", "multiattach", "availability_zone",
        "snapshot_id", "source_volid", "description",
        "created_at", "updated_at",
    ]

    fields: list[tuple[str, str]] = []
    for key in display_keys:
        val = vol.get(key, "")
        if key == "size" and val:
            val = f"{val} GB"
        fields.append((key, str(val) if val is not None else ""))

    attachments = vol.get("attachments", [])
    if attachments:
        for a in attachments:
            fields.append(("attached_to", f"{a.get('server_id', '')} @ {a.get('device', '')}"))

    print_detail(fields, output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent, columns=columns)


# ── create ────────────────────────────────────────────────────────────────

@volume.command("create")
@click.option("--name", default=None, help="Volume name.")
@click.option("--size", default=None, type=int, help="Size in GB.")
@click.option("--type", "volume_type", default=None, help="Volume type.")
@click.option("--description", default=None, help="Volume description.")
@click.option("--snapshot-id", default=None, help="Create from snapshot.")
@click.option("--source-vol", default=None, help="Create from existing volume (clone).")
@click.option("--image-id", default=None, help="Create from image.")
@click.option("--wait", is_flag=True, help="Wait until the volume reaches 'available' status.")
@click.option("--interactive", "-i", is_flag=True,
              help="Step-by-step wizard — choose name, size, and type interactively.")
@click.pass_context
def volume_create(ctx: click.Context, name: str | None, size: int | None,
                  volume_type: str | None, description: str | None,
                  snapshot_id: str | None, source_vol: str | None,
                  image_id: str | None, wait: bool, interactive: bool) -> None:
    """Create a volume.

    \b
    Interactive wizard:
      orca volume create -i
    """
    from orca_cli.core import wizard as wiz

    orca_ctx = ctx.find_object(OrcaContext)
    client = orca_ctx.ensure_client()

    if interactive:
        console.print("\n[bold cyan]orca volume create — interactive wizard[/bold cyan]\n")

        if not name:
            name = click.prompt("  Volume name", prompt_suffix=" > ")

        if not size:
            size = click.prompt("  Size (GB)", type=click.IntRange(1), prompt_suffix=" > ")

        if not volume_type:
            try:
                volume_type = wiz.select_volume_type(client)
                if volume_type:
                    console.print(f"  [green]✓[/green] Type: {volume_type}")
            except Exception:
                pass  # types endpoint not available on all clusters

        if not description:
            raw = click.prompt("  Description (optional)", default="", prompt_suffix=" > ")
            description = raw.strip() or None

        console.print()
        if not click.confirm("  Create volume?", default=True):
            console.print("[yellow]Aborted.[/yellow]")
            return
    else:
        missing = []
        if not name:
            missing.append("--name")
        if not size:
            missing.append("--size")
        if missing:
            raise click.UsageError(
                f"Missing required option(s): {', '.join(missing)}. "
                "Use -i / --interactive for the guided wizard."
            )

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
    vol_id = vol.get("id", "?")
    cache.invalidate(orca_ctx.profile, "volumes")
    console.print(f"[green]Volume '{vol.get('name')}' ({vol_id}) created — {size} GB.[/green]")

    if wait:
        wait_for_resource(
            client,
            url=f"{client.volume_url}/volumes/{vol_id}",
            resource_key="volume",
            target_status="available",
            label=f"Volume {name} ({vol_id})",
            error_status="error",
        )


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

    client = ctx.find_object(OrcaContext).ensure_client()
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
@click.option("--bootable/--no-bootable", default=True, show_default=True,
              help="Mark volume as bootable or non-bootable.")
@click.pass_context
def volume_set_bootable(ctx: click.Context, volume_id: str, bootable: bool) -> None:
    """Set or unset bootable flag on a volume."""
    _vol_action(ctx, volume_id, {"os-set_bootable": {"bootable": bootable}}, f"Set bootable={str(bootable).lower()}")


# ── set-readonly ──────────────────────────────────────────────────────────

@volume.command("set-readonly")
@click.argument("volume_id", callback=validate_id)
@click.option("--readonly/--no-readonly", default=True, show_default=True,
              help="Mark volume as read-only or read-write.")
@click.pass_context
def volume_set_readonly(ctx: click.Context, volume_id: str, readonly: bool) -> None:
    """Set or unset read-only flag on a volume."""
    _vol_action(ctx, volume_id, {"os-update_readonly_flag": {"readonly": readonly}}, f"Set readonly={str(readonly).lower()}")


# ── delete ────────────────────────────────────────────────────────────────

@volume.command("delete")
@click.argument("volume_id", callback=validate_id, shell_complete=complete_volumes)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.option("--dry-run", is_flag=True, help="Show what would be deleted without deleting.")
@click.option("--wait", is_flag=True, help="Wait until the volume is fully deleted.")
@click.pass_context
def volume_delete(ctx: click.Context, volume_id: str, yes: bool, dry_run: bool, wait: bool) -> None:
    """Delete a volume."""
    orca_ctx = ctx.find_object(OrcaContext)
    client = orca_ctx.ensure_client()
    url = f"{client.volume_url}/volumes/{volume_id}"

    if dry_run:
        data = client.get(url)
        vol = data.get("volume", data)
        console.print("[yellow]Would delete volume:[/yellow]")
        console.print(f"  ID:     {vol.get('id', volume_id)}")
        console.print(f"  Name:   {vol.get('name', '—')}")
        console.print(f"  Size:   {vol.get('size', '—')} GB")
        console.print(f"  Status: {vol.get('status', '—')}")
        attachments = vol.get("attachments", [])
        if attachments:
            console.print(f"  [red]Warning: volume is attached to {len(attachments)} server(s)[/red]")
        return

    if not yes:
        click.confirm(f"Delete volume {volume_id}?", abort=True)

    client.delete(url)
    cache.invalidate(orca_ctx.profile, "volumes")

    if wait:
        wait_for_resource(
            client, url, "volume", "deleted",
            label=f"Volume {volume_id}",
            delete_mode=True,
            error_status="error",
        )
    else:
        console.print(f"[green]Volume {volume_id} deleted.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  Snapshots
# ══════════════════════════════════════════════════════════════════════════

@volume.command("snapshot-list")
@output_options
@click.pass_context
def snapshot_list(ctx: click.Context, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List volume snapshots."""
    client = ctx.find_object(OrcaContext).ensure_client()
    url = f"{client.volume_url}/snapshots/detail"
    data = client.get(url)

    snaps = data.get("snapshots", [])

    print_list(
        snaps,
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Name", lambda s: s.get("name", "") or "—", {"style": "bold"}),
            ("Volume ID", "volume_id"),
            ("Size (GB)", lambda s: str(s.get("size", "")), {"justify": "right"}),
            ("Status", "status", {"style": "green"}),
            ("Created", "created_at"),
        ],
        title="Volume Snapshots",
        output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent,
        columns=columns,
        empty_msg="No snapshots found.",
    )


@volume.command("snapshot-show")
@click.argument("snapshot_id", callback=validate_id)
@output_options
@click.pass_context
def snapshot_show(ctx: click.Context, snapshot_id: str, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show snapshot details."""
    client = ctx.find_object(OrcaContext).ensure_client()
    url = f"{client.volume_url}/snapshots/{snapshot_id}"
    data = client.get(url)

    snap = data.get("snapshot", data)

    fields: list[tuple[str, str]] = []
    for key in ["id", "name", "description", "volume_id", "size", "status", "created_at"]:
        val = snap.get(key, "")
        if key == "size" and val:
            val = f"{val} GB"
        fields.append((key, str(val) if val is not None else ""))

    print_detail(fields, output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent, columns=columns)


@volume.command("snapshot-create")
@click.argument("volume_id_or_name")
@click.option("--name", required=True, help="Snapshot name.")
@click.option("--description", default=None, help="Snapshot description.")
@click.option("--force", is_flag=True, help="Force snapshot of in-use volume.")
@click.pass_context
def snapshot_create(ctx: click.Context, volume_id_or_name: str, name: str, description: str | None, force: bool) -> None:
    """Create a snapshot of a volume (accepts UUID or name)."""
    client = ctx.find_object(OrcaContext).ensure_client()

    # Resolve name → UUID if needed
    import re
    _UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
    if _UUID_RE.match(volume_id_or_name):
        volume_id = volume_id_or_name
    else:
        data = client.get(f"{client.volume_url}/volumes", params={"name": volume_id_or_name})
        vols = data.get("volumes", [])
        if not vols:
            raise click.ClickException(f"No volume found with name '{volume_id_or_name}'")
        if len(vols) > 1:
            raise click.ClickException(f"Multiple volumes match '{volume_id_or_name}' — use a UUID")
        volume_id = vols[0]["id"]

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

    client = ctx.find_object(OrcaContext).ensure_client()
    url = f"{client.volume_url}/snapshots/{snapshot_id}"
    client.delete(url)
    console.print(f"[green]Snapshot {snapshot_id} deleted.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  Tree / Map
# ══════════════════════════════════════════════════════════════════════════

@volume.command("tree")
@click.option("--volume-id", "filter_vol", default=None, help="Show only this volume and its snapshots.")
@click.pass_context
def volume_tree(ctx: click.Context, filter_vol: str | None) -> None:
    """Display a volume / snapshot dependency tree.

    Shows every volume with its snapshots, child volumes (clones),
    and server attachments — making it easy to debug chains and
    see what depends on what.

    \b
    Examples:
      orca volume tree
      orca volume tree --volume-id <id>
    """
    from rich.tree import Tree

    client = ctx.find_object(OrcaContext).ensure_client()

    with console.status("[bold cyan]Building volume tree…[/bold cyan]"):
        # Fetch volumes & snapshots
        vols = client.get(f"{client.volume_url}/volumes/detail").get("volumes", [])
        snaps = client.get(f"{client.volume_url}/snapshots/detail").get("snapshots", [])

        # Fetch servers for name resolution
        try:
            srv_data = client.get(f"{client.compute_url}/servers/detail", params={"limit": 1000})
            servers = {s["id"]: s.get("name", s["id"]) for s in srv_data.get("servers", [])}
        except Exception:
            servers = {}

    # Index
    vol_map = {v["id"]: v for v in vols}
    snaps_by_vol: dict[str, list[dict]] = {}
    for s in snaps:
        snaps_by_vol.setdefault(s.get("volume_id", ""), []).append(s)

    # Volumes created from a snapshot → track parent
    children_of_snap: dict[str, list[dict]] = {}
    for v in vols:
        sid = v.get("snapshot_id")
        if sid:
            children_of_snap.setdefault(sid, []).append(v)

    # Volumes cloned from another volume
    children_of_vol: dict[str, list[dict]] = {}
    for v in vols:
        src = v.get("source_volid")
        if src:
            children_of_vol.setdefault(src, []).append(v)

    # Filter
    if filter_vol:
        root_vols = [vol_map[filter_vol]] if filter_vol in vol_map else []
        if not root_vols:
            console.print(f"[yellow]Volume {filter_vol} not found.[/yellow]")
            return
    else:
        # Show root volumes (not created from snapshot or clone)
        root_ids = {v["id"] for v in vols if not v.get("snapshot_id") and not v.get("source_volid")}
        # Also include orphaned volumes whose parent is gone
        for v in vols:
            sid = v.get("snapshot_id")
            src = v.get("source_volid")
            if sid and not any(s["id"] == sid for s in snaps):
                root_ids.add(v["id"])
            if src and src not in vol_map:
                root_ids.add(v["id"])
        root_vols = [v for v in vols if v["id"] in root_ids]

    root = Tree("[bold]Volume Tree[/bold]")

    def _status_color(status: str) -> str:
        s = status.lower()
        if s in ("available", "in-use"):
            return "green"
        if s in ("creating", "downloading"):
            return "yellow"
        if "error" in s:
            return "red"
        return "white"

    def _vol_label(v: dict) -> str:
        vid = v["id"]
        name = v.get("name") or "—"
        size = v.get("size", "?")
        status = v.get("status", "?")
        bootable = " [dim]boot[/dim]" if v.get("bootable") == "true" else ""
        vtype = v.get("volume_type", "") or ""
        sc = _status_color(status)

        # Attachments
        att_parts = []
        for a in v.get("attachments", []):
            srv_id = a.get("server_id", "")
            srv_name = servers.get(srv_id, srv_id[:8])
            dev = a.get("device", "?")
            att_parts.append(f"{srv_name} ({dev})")
        att = f"  → [magenta]{', '.join(att_parts)}[/magenta]" if att_parts else ""

        return (
            f"[bold]{name}[/bold]  [cyan]{vid}[/cyan]  "
            f"{size} GB  [{sc}]{status}[/{sc}]{bootable}"
            f"  [dim]{vtype}[/dim]{att}"
        )

    def _snap_label(s: dict) -> str:
        sid = s["id"]
        name = s.get("name") or "—"
        size = s.get("size", "?")
        status = s.get("status", "?")
        sc = _status_color(status)
        created = str(s.get("created_at", ""))[:19]
        return (
            f"[yellow]⊙[/yellow] [bold]{name}[/bold]  [cyan]{sid}[/cyan]  "
            f"{size} GB  [{sc}]{status}[/{sc}]  [dim]{created}[/dim]"
        )

    def _add_volume(parent_node, v: dict, seen: set) -> None:
        vid = v["id"]
        if vid in seen:
            parent_node.add(f"[dim](cycle → {vid})[/dim]")
            return
        seen.add(vid)

        vol_node = parent_node.add(_vol_label(v))

        # Snapshots of this volume
        vol_snaps = sorted(
            snaps_by_vol.get(vid, []),
            key=lambda s: s.get("created_at", ""),
        )
        for s in vol_snaps:
            snap_node = vol_node.add(_snap_label(s))
            # Volumes created from this snapshot
            for child in children_of_snap.get(s["id"], []):
                _add_volume(snap_node, child, seen)

        # Volumes cloned directly from this volume
        for child in children_of_vol.get(vid, []):
            _add_volume(vol_node, child, seen)

    seen: set[str] = set()
    for v in sorted(root_vols, key=lambda x: x.get("name") or ""):
        _add_volume(root, v, seen)

    # Show orphaned (not in any tree) if no filter
    if not filter_vol:
        orphaned = [v for v in vols if v["id"] not in seen]
        if orphaned:
            orphan_node = root.add("[dim]── Orphaned / unreachable ──[/dim]")
            for v in orphaned:
                _add_volume(orphan_node, v, seen)

    console.print()
    console.print(root)

    # Summary
    total_gb = sum(v.get("size", 0) for v in vols)
    console.print(
        f"\n[dim]{len(vols)} volumes ({total_gb} GB), "
        f"{len(snaps)} snapshots[/dim]\n"
    )


# ══════════════════════════════════════════════════════════════════════════
#  Cinder Native Backups
# ══════════════════════════════════════════════════════════════════════════

@volume.command("backup-list")
@click.option("--all-projects", is_flag=True, help="List backups from all projects (admin).")
@output_options
@click.pass_context
def volume_backup_list(ctx: click.Context, all_projects: bool, output_format: str,
                       columns: tuple[str, ...], fit_width: bool,
                       max_width: int | None, noindent: bool) -> None:
    """List Cinder volume backups."""
    client = ctx.find_object(OrcaContext).ensure_client()
    params = {}
    if all_projects:
        params["all_tenants"] = 1
    data = client.get(f"{client.volume_url}/backups/detail", params=params)
    backups = data.get("backups", [])
    print_list(
        backups,
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Name", "name", {"style": "bold"}),
            ("Volume ID", "volume_id"),
            ("Status", "status", {"style": "green"}),
            ("Size (GB)", "size", {"justify": "right"}),
            ("Incremental", lambda b: "yes" if b.get("is_incremental") else "no"),
            ("Created", "created_at"),
        ],
        title="Volume Backups",
        output_format=output_format, columns=columns,
        fit_width=fit_width, max_width=max_width, noindent=noindent,
        empty_msg="No backups found.",
    )


@volume.command("backup-show")
@click.argument("backup_id", callback=validate_id)
@output_options
@click.pass_context
def volume_backup_show(ctx: click.Context, backup_id: str, output_format: str,
                       columns: tuple[str, ...], fit_width: bool,
                       max_width: int | None, noindent: bool) -> None:
    """Show details of a volume backup."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{client.volume_url}/backups/{backup_id}")
    b = data.get("backup", data)
    print_detail(
        [
            ("ID", b.get("id", "")),
            ("Name", b.get("name", "") or "—"),
            ("Volume ID", b.get("volume_id", "")),
            ("Snapshot ID", b.get("snapshot_id", "") or "—"),
            ("Status", b.get("status", "")),
            ("Size (GB)", str(b.get("size", ""))),
            ("Incremental", "yes" if b.get("is_incremental") else "no"),
            ("Has Dependent Backups", "yes" if b.get("has_dependent_backups") else "no"),
            ("Container", b.get("container", "") or "—"),
            ("Availability Zone", b.get("availability_zone", "") or "—"),
            ("Created", b.get("created_at", "")),
            ("Updated", b.get("updated_at", "")),
            ("Description", b.get("description", "") or "—"),
        ],
        output_format=output_format, columns=columns,
        fit_width=fit_width, max_width=max_width, noindent=noindent,
    )


@volume.command("backup-create")
@click.argument("volume_id", callback=validate_id)
@click.option("--name", default=None, help="Backup name.")
@click.option("--description", default=None, help="Backup description.")
@click.option("--container", default=None, help="Swift container for the backup.")
@click.option("--incremental", is_flag=True, help="Create an incremental backup.")
@click.option("--force", is_flag=True,
              help="Backup even if the volume is attached (may create inconsistent backup).")
@click.option("--snapshot-id", default=None,
              help="Create backup from a specific snapshot instead of the volume.")
@click.option("--wait", is_flag=True, help="Wait until the backup reaches 'available' status.")
@click.pass_context
def volume_backup_create(ctx: click.Context, volume_id: str, name: str | None,
                          description: str | None, container: str | None,
                          incremental: bool, force: bool, snapshot_id: str | None,
                          wait: bool) -> None:
    """Create a Cinder backup of a volume.

    \b
    Examples:
      orca volume backup-create <volume-id> --name my-backup
      orca volume backup-create <volume-id> --incremental --wait
      orca volume backup-create <volume-id> --force  # while attached
    """
    client = ctx.find_object(OrcaContext).ensure_client()

    body: dict = {"volume_id": volume_id}
    if name:
        body["name"] = name
    if description:
        body["description"] = description
    if container:
        body["container"] = container
    if incremental:
        body["incremental"] = True
    if force:
        body["force"] = True
    if snapshot_id:
        body["snapshot_id"] = snapshot_id

    data = client.post(f"{client.volume_url}/backups", json={"backup": body})
    bk = data.get("backup", data)
    bk_id = bk.get("id", "?")
    console.print(f"[green]Backup '{bk.get('name', bk_id)}' ({bk_id}) creation started.[/green]")

    if wait:
        wait_for_resource(
            client,
            url=f"{client.volume_url}/backups/{bk_id}",
            resource_key="backup",
            target_status="available",
            label=f"Backup {bk_id}",
            error_status="error",
        )


@volume.command("backup-delete")
@click.argument("backup_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.option("--force", is_flag=True, help="Force deletion even if backup is not available.")
@click.pass_context
def volume_backup_delete(ctx: click.Context, backup_id: str, yes: bool, force: bool) -> None:
    """Delete a volume backup."""
    if not yes:
        click.confirm(f"Delete backup {backup_id}?", abort=True)
    client = ctx.find_object(OrcaContext).ensure_client()
    params = {}
    if force:
        params["force"] = True
    client.delete(f"{client.volume_url}/backups/{backup_id}", params=params if params else None)
    console.print(f"[green]Backup {backup_id} deleted.[/green]")


@volume.command("backup-restore")
@click.argument("backup_id", callback=validate_id)
@click.option("--volume-id", "volume_id", default=None,
              help="Restore to an existing volume ID (must be same size).")
@click.option("--name", default=None, help="Name for the new restored volume.")
@click.option("--wait", is_flag=True, help="Wait until the restored volume is available.")
@click.pass_context
def volume_backup_restore(ctx: click.Context, backup_id: str, volume_id: str | None,
                           name: str | None, wait: bool) -> None:
    """Restore a Cinder backup to a volume.

    If --volume-id is not specified, a new volume is created.

    \b
    Examples:
      orca volume backup-restore <backup-id>
      orca volume backup-restore <backup-id> --name restored-vol --wait
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {}
    if volume_id:
        body["volume_id"] = volume_id
    if name:
        body["name"] = name

    data = client.post(
        f"{client.volume_url}/backups/{backup_id}/restore",
        json={"restore": body},
    )
    restore = data.get("restore", data)
    vol_id = restore.get("volume_id", "?")
    console.print(f"[green]Backup {backup_id} restore started → Volume {vol_id}.[/green]")

    if wait:
        wait_for_resource(
            client,
            url=f"{client.volume_url}/volumes/{vol_id}",
            resource_key="volume",
            target_status="available",
            label=f"Restored volume {vol_id}",
            error_status="error",
        )


# ══════════════════════════════════════════════════════════════════════════
#  Volume metadata (set / unset)
# ══════════════════════════════════════════════════════════════════════════

@volume.command("set")
@click.argument("volume_id", callback=validate_id)
@click.option("--property", "properties", multiple=True, metavar="KEY=VALUE",
              help="Metadata key=value pair (repeatable).")
@click.option("--name", default=None, help="New name.")
@click.option("--description", default=None, help="New description.")
@click.pass_context
def volume_set(ctx: click.Context, volume_id: str, properties: tuple[str, ...],
               name: str | None, description: str | None) -> None:
    """Set volume properties or metadata.

    \b
    Examples:
      orca volume set <id> --name new-name
      orca volume set <id> --property env=prod --property team=infra
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {}
    if name is not None:
        body["name"] = name
    if description is not None:
        body["description"] = description
    if body:
        client.put(f"{client.volume_url}/volumes/{volume_id}", json={"volume": body})
    if properties:
        meta: dict = {}
        for prop in properties:
            if "=" not in prop:
                raise click.UsageError(f"Invalid property format '{prop}', expected KEY=VALUE.")
            k, v = prop.split("=", 1)
            meta[k] = v
        client.post(f"{client.volume_url}/volumes/{volume_id}/metadata",
                    json={"metadata": meta})
    if not body and not properties:
        console.print("[yellow]Nothing to set. Use --name, --description, or --property.[/yellow]")
        return
    console.print(f"[green]Volume {volume_id} updated.[/green]")


@volume.command("unset")
@click.argument("volume_id", callback=validate_id)
@click.option("--property", "properties", multiple=True, metavar="KEY",
              help="Metadata key to remove (repeatable).")
@click.pass_context
def volume_unset(ctx: click.Context, volume_id: str, properties: tuple[str, ...]) -> None:
    """Unset volume metadata keys."""
    if not properties:
        console.print("[yellow]No properties specified.[/yellow]")
        return
    client = ctx.find_object(OrcaContext).ensure_client()
    for key in properties:
        client.delete(f"{client.volume_url}/volumes/{volume_id}/metadata/{key}")
    console.print(f"[green]Metadata removed from volume {volume_id}.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  Snapshot update
# ══════════════════════════════════════════════════════════════════════════

@volume.command("snapshot-set")
@click.argument("snapshot_id", callback=validate_id)
@click.option("--name", default=None, help="New name.")
@click.option("--description", default=None, help="New description.")
@click.option("--property", "properties", multiple=True, metavar="KEY=VALUE",
              help="Metadata key=value (repeatable).")
@click.pass_context
def snapshot_set(ctx: click.Context, snapshot_id: str, name: str | None,
                 description: str | None, properties: tuple[str, ...]) -> None:
    """Update a snapshot's name, description, or metadata."""
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {}
    if name is not None:
        body["name"] = name
    if description is not None:
        body["description"] = description
    if body:
        client.put(f"{client.volume_url}/snapshots/{snapshot_id}", json={"snapshot": body})
    if properties:
        meta: dict = {}
        for prop in properties:
            if "=" not in prop:
                raise click.UsageError(f"Invalid property format '{prop}', expected KEY=VALUE.")
            k, v = prop.split("=", 1)
            meta[k] = v
        client.post(f"{client.volume_url}/snapshots/{snapshot_id}/metadata",
                    json={"metadata": meta})
    if not body and not properties:
        console.print("[yellow]Nothing to update.[/yellow]")
        return
    console.print(f"[green]Snapshot {snapshot_id} updated.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  Volume Types
# ══════════════════════════════════════════════════════════════════════════

@volume.command("type-list")
@click.option("--default", "show_default", is_flag=True, help="Show the default type only.")
@output_options
@click.pass_context
def volume_type_list(ctx: click.Context, show_default: bool,
                     output_format: str, columns: tuple[str, ...],
                     fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List volume types."""
    client = ctx.find_object(OrcaContext).ensure_client()
    if show_default:
        types = [client.get(f"{client.volume_url}/types/default").get("volume_type", {})]
    else:
        types = client.get(f"{client.volume_url}/types").get("volume_types", [])
    print_list(
        types,
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Name", "name", {"style": "bold"}),
            ("Description", lambda t: (t.get("description") or "")[:40]),
            ("Public", lambda t: "Yes" if t.get("is_public", True) else "No"),
        ],
        title="Volume Types",
        output_format=output_format, fit_width=fit_width, max_width=max_width,
        noindent=noindent, columns=columns,
        empty_msg="No volume types found.",
    )


@volume.command("type-show")
@click.argument("type_id")
@output_options
@click.pass_context
def volume_type_show(ctx: click.Context, type_id: str,
                     output_format: str, columns: tuple[str, ...],
                     fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show volume type details."""
    client = ctx.find_object(OrcaContext).ensure_client()
    t = client.get(f"{client.volume_url}/types/{type_id}").get("volume_type", {})
    extra = t.get("extra_specs") or {}
    fields = [(k, str(t.get(k, "") or "")) for k in
              ["id", "name", "description", "is_public"]]
    for k, v in extra.items():
        fields.append((f"  {k}", str(v)))
    print_detail(fields, output_format=output_format, fit_width=fit_width,
                 max_width=max_width, noindent=noindent, columns=columns)


@volume.command("type-create")
@click.argument("name")
@click.option("--description", default=None, help="Description.")
@click.option("--public/--private", "is_public", default=True, show_default=True,
              help="Make type public or private.")
@click.option("--property", "properties", multiple=True, metavar="KEY=VALUE",
              help="Extra spec (repeatable).")
@click.pass_context
def volume_type_create(ctx: click.Context, name: str, description: str | None,
                       is_public: bool, properties: tuple[str, ...]) -> None:
    """Create a volume type."""
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {"name": name, "os-volume-type-access:is_public": is_public}
    if description:
        body["description"] = description
    t = client.post(f"{client.volume_url}/types", json={"volume_type": body}).get("volume_type", {})
    if properties:
        specs: dict = {}
        for prop in properties:
            if "=" not in prop:
                raise click.UsageError(f"Invalid format '{prop}', expected KEY=VALUE.")
            k, v = prop.split("=", 1)
            specs[k] = v
        client.post(f"{client.volume_url}/types/{t['id']}/extra_specs",
                    json={"extra_specs": specs})
    console.print(f"[green]Volume type '{name}' created: {t.get('id', '?')}[/green]")


@volume.command("type-set")
@click.argument("type_id")
@click.option("--name", default=None, help="New name.")
@click.option("--description", default=None, help="New description.")
@click.option("--property", "properties", multiple=True, metavar="KEY=VALUE",
              help="Extra spec to add or update (repeatable).")
@click.pass_context
def volume_type_set(ctx: click.Context, type_id: str, name: str | None,
                    description: str | None, properties: tuple[str, ...]) -> None:
    """Update a volume type."""
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {}
    if name is not None:
        body["name"] = name
    if description is not None:
        body["description"] = description
    if body:
        client.put(f"{client.volume_url}/types/{type_id}", json={"volume_type": body})
    if properties:
        specs: dict = {}
        for prop in properties:
            if "=" not in prop:
                raise click.UsageError(f"Invalid format '{prop}', expected KEY=VALUE.")
            k, v = prop.split("=", 1)
            specs[k] = v
        client.post(f"{client.volume_url}/types/{type_id}/extra_specs",
                    json={"extra_specs": specs})
    if not body and not properties:
        console.print("[yellow]Nothing to update.[/yellow]")
        return
    console.print(f"[green]Volume type {type_id} updated.[/green]")


@volume.command("type-delete")
@click.argument("type_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def volume_type_delete(ctx: click.Context, type_id: str, yes: bool) -> None:
    """Delete a volume type."""
    if not yes:
        click.confirm(f"Delete volume type {type_id}?", abort=True)
    client = ctx.find_object(OrcaContext).ensure_client()
    client.delete(f"{client.volume_url}/types/{type_id}")
    console.print(f"[green]Volume type {type_id} deleted.[/green]")


@volume.command("type-access-list")
@click.argument("type_id")
@output_options
@click.pass_context
def volume_type_access_list(ctx: click.Context, type_id: str,
                             output_format: str, columns: tuple[str, ...],
                             fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List projects that have access to a private volume type."""
    client = ctx.find_object(OrcaContext).ensure_client()
    accesses = client.get(
        f"{client.volume_url}/types/{type_id}/os-volume-type-access"
    ).get("volume_type_access", [])
    print_list(
        accesses,
        [
            ("Volume Type ID", "volume_type_id", {"style": "cyan"}),
            ("Project ID", "project_id", {"style": "bold"}),
        ],
        title=f"Access for type {type_id}",
        output_format=output_format, fit_width=fit_width, max_width=max_width,
        noindent=noindent, columns=columns,
        empty_msg="No access entries (type may be public).",
    )


@volume.command("type-access-add")
@click.argument("type_id")
@click.argument("project_id", callback=validate_id)
@click.pass_context
def volume_type_access_add(ctx: click.Context, type_id: str, project_id: str) -> None:
    """Grant a project access to a private volume type."""
    client = ctx.find_object(OrcaContext).ensure_client()
    client.post(f"{client.volume_url}/types/{type_id}/action",
                json={"addProjectAccess": {"project": project_id}})
    console.print(f"[green]Project {project_id} granted access to type {type_id}.[/green]")


@volume.command("type-access-remove")
@click.argument("type_id")
@click.argument("project_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def volume_type_access_remove(ctx: click.Context, type_id: str, project_id: str,
                               yes: bool) -> None:
    """Revoke a project's access to a private volume type."""
    if not yes:
        click.confirm(f"Remove project {project_id} from type {type_id}?", abort=True)
    client = ctx.find_object(OrcaContext).ensure_client()
    client.post(f"{client.volume_url}/types/{type_id}/action",
                json={"removeProjectAccess": {"project": project_id}})
    console.print(f"[green]Project {project_id} access to type {type_id} revoked.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  Volume Transfers
# ══════════════════════════════════════════════════════════════════════════

@volume.command("transfer-create")
@click.argument("volume_id", callback=validate_id)
@click.option("--name", default=None, help="Transfer name.")
@click.pass_context
def volume_transfer_create(ctx: click.Context, volume_id: str, name: str | None) -> None:
    """Create a volume transfer request."""
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {"volume_id": volume_id}
    if name:
        body["name"] = name
    t = client.post(f"{client.volume_url}/volume-transfers",
                    json={"transfer": body}).get("transfer", {})
    console.print(f"[green]Transfer created: {t.get('id', '?')}[/green]")
    console.print(f"  Auth key: [bold cyan]{t.get('auth_key', '?')}[/bold cyan]")
    console.print("  [yellow]Save the auth key — it will not be shown again.[/yellow]")


@volume.command("transfer-list")
@click.option("--all-projects", is_flag=True, help="List transfers from all projects (admin).")
@output_options
@click.pass_context
def volume_transfer_list(ctx: click.Context, all_projects: bool,
                         output_format: str, columns: tuple[str, ...],
                         fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List volume transfer requests."""
    client = ctx.find_object(OrcaContext).ensure_client()
    params = {"all_tenants": 1} if all_projects else {}
    transfers = client.get(f"{client.volume_url}/volume-transfers/detail",
                           params=params).get("transfers", [])
    print_list(
        transfers,
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Name", lambda t: t.get("name") or "—", {"style": "bold"}),
            ("Volume ID", "volume_id"),
            ("Created", "created_at"),
        ],
        title="Volume Transfers",
        output_format=output_format, fit_width=fit_width, max_width=max_width,
        noindent=noindent, columns=columns,
        empty_msg="No transfers found.",
    )


@volume.command("transfer-show")
@click.argument("transfer_id", callback=validate_id)
@output_options
@click.pass_context
def volume_transfer_show(ctx: click.Context, transfer_id: str,
                         output_format: str, columns: tuple[str, ...],
                         fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show a volume transfer request."""
    client = ctx.find_object(OrcaContext).ensure_client()
    t = client.get(f"{client.volume_url}/volume-transfers/{transfer_id}").get("transfer", {})
    print_detail(
        [(k, str(t.get(k, "") or "")) for k in
         ["id", "name", "volume_id", "created_at"]],
        output_format=output_format, fit_width=fit_width, max_width=max_width,
        noindent=noindent, columns=columns,
    )


@volume.command("transfer-accept")
@click.argument("transfer_id", callback=validate_id)
@click.argument("auth_key")
@click.pass_context
def volume_transfer_accept(ctx: click.Context, transfer_id: str, auth_key: str) -> None:
    """Accept a volume transfer request."""
    client = ctx.find_object(OrcaContext).ensure_client()
    client.post(f"{client.volume_url}/volume-transfers/{transfer_id}/accept",
                json={"accept": {"auth_key": auth_key}})
    console.print(f"[green]Transfer {transfer_id} accepted.[/green]")


@volume.command("transfer-delete")
@click.argument("transfer_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def volume_transfer_delete(ctx: click.Context, transfer_id: str, yes: bool) -> None:
    """Delete a volume transfer request."""
    if not yes:
        click.confirm(f"Delete transfer {transfer_id}?", abort=True)
    client = ctx.find_object(OrcaContext).ensure_client()
    client.delete(f"{client.volume_url}/volume-transfers/{transfer_id}")
    console.print(f"[green]Transfer {transfer_id} deleted.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  Volume QoS Specs
# ══════════════════════════════════════════════════════════════════════════

@volume.command("qos-list")
@output_options
@click.pass_context
def volume_qos_list(ctx: click.Context, output_format: str, columns: tuple[str, ...],
                    fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List volume QoS specs."""
    client = ctx.find_object(OrcaContext).ensure_client()
    specs = client.get(f"{client.volume_url}/qos-specs").get("qos_specs", [])
    print_list(
        specs,
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Name", "name", {"style": "bold"}),
            ("Consumer", lambda s: s.get("consumer", "—")),
            ("Specs", lambda s: str(s.get("specs", {}))),
        ],
        title="Volume QoS Specs",
        output_format=output_format, fit_width=fit_width, max_width=max_width,
        noindent=noindent, columns=columns,
        empty_msg="No QoS specs found.",
    )


@volume.command("qos-show")
@click.argument("qos_id", callback=validate_id)
@output_options
@click.pass_context
def volume_qos_show(ctx: click.Context, qos_id: str,
                    output_format: str, columns: tuple[str, ...],
                    fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show volume QoS spec details."""
    client = ctx.find_object(OrcaContext).ensure_client()
    s = client.get(f"{client.volume_url}/qos-specs/{qos_id}").get("qos_specs", {})
    fields = [
        ("ID", str(s.get("id", ""))),
        ("Name", str(s.get("name", ""))),
        ("Consumer", str(s.get("consumer", ""))),
    ]
    for k, v in (s.get("specs") or {}).items():
        fields.append((f"  {k}", str(v)))
    print_detail(fields, output_format=output_format, fit_width=fit_width,
                 max_width=max_width, noindent=noindent, columns=columns)


@volume.command("qos-create")
@click.argument("name")
@click.option("--consumer", type=click.Choice(["front-end", "back-end", "both"]),
              default="both", show_default=True, help="Consumer of the QoS.")
@click.option("--property", "properties", multiple=True, metavar="KEY=VALUE",
              help="QoS spec key=value (repeatable).")
@click.pass_context
def volume_qos_create(ctx: click.Context, name: str, consumer: str,
                      properties: tuple[str, ...]) -> None:
    """Create a volume QoS spec.

    \b
    Example:
      orca volume qos-create my-qos --consumer back-end \\
        --property total_iops_sec=1000
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    specs: dict = {}
    for prop in properties:
        if "=" not in prop:
            raise click.UsageError(f"Invalid format '{prop}', expected KEY=VALUE.")
        k, v = prop.split("=", 1)
        specs[k] = v
    body: dict = {"name": name, "consumer": consumer}
    if specs:
        body["specs"] = specs
    s = client.post(f"{client.volume_url}/qos-specs",
                    json={"qos_specs": body}).get("qos_specs", {})
    console.print(f"[green]QoS spec '{name}' created: {s.get('id', '?')}[/green]")


@volume.command("qos-set")
@click.argument("qos_id", callback=validate_id)
@click.option("--property", "properties", multiple=True, metavar="KEY=VALUE",
              help="QoS spec key=value to add or update (repeatable).")
@click.pass_context
def volume_qos_set(ctx: click.Context, qos_id: str, properties: tuple[str, ...]) -> None:
    """Add or update keys on a volume QoS spec."""
    if not properties:
        console.print("[yellow]No properties specified.[/yellow]")
        return
    client = ctx.find_object(OrcaContext).ensure_client()
    specs: dict = {}
    for prop in properties:
        if "=" not in prop:
            raise click.UsageError(f"Invalid format '{prop}', expected KEY=VALUE.")
        k, v = prop.split("=", 1)
        specs[k] = v
    client.put(f"{client.volume_url}/qos-specs/{qos_id}", json={"qos_specs": {"specs": specs}})
    console.print(f"[green]QoS spec {qos_id} updated.[/green]")


@volume.command("qos-delete")
@click.argument("qos_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.option("--force", is_flag=True, help="Delete even if associated with a volume type.")
@click.pass_context
def volume_qos_delete(ctx: click.Context, qos_id: str, yes: bool, force: bool) -> None:
    """Delete a volume QoS spec."""
    if not yes:
        click.confirm(f"Delete QoS spec {qos_id}?", abort=True)
    client = ctx.find_object(OrcaContext).ensure_client()
    params = {"force": True} if force else {}
    client.delete(f"{client.volume_url}/qos-specs/{qos_id}",
                  params=params if params else None)
    console.print(f"[green]QoS spec {qos_id} deleted.[/green]")


@volume.command("qos-associate")
@click.argument("qos_id", callback=validate_id)
@click.argument("type_id")
@click.pass_context
def volume_qos_associate(ctx: click.Context, qos_id: str, type_id: str) -> None:
    """Associate a QoS spec with a volume type."""
    client = ctx.find_object(OrcaContext).ensure_client()
    client.get(f"{client.volume_url}/qos-specs/{qos_id}/associate",
               params={"vol_type_id": type_id})
    console.print(f"[green]QoS spec {qos_id} associated with type {type_id}.[/green]")


@volume.command("qos-disassociate")
@click.argument("qos_id", callback=validate_id)
@click.argument("type_id")
@click.option("--all", "disassociate_all", is_flag=True,
              help="Disassociate from all volume types.")
@click.pass_context
def volume_qos_disassociate(ctx: click.Context, qos_id: str, type_id: str,
                             disassociate_all: bool) -> None:
    """Disassociate a QoS spec from a volume type."""
    client = ctx.find_object(OrcaContext).ensure_client()
    if disassociate_all:
        client.get(f"{client.volume_url}/qos-specs/{qos_id}/disassociate_all")
    else:
        client.get(f"{client.volume_url}/qos-specs/{qos_id}/disassociate",
                   params={"vol_type_id": type_id})
    console.print(f"[green]QoS spec {qos_id} disassociated.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  Volume Service (Cinder service management)
# ══════════════════════════════════════════════════════════════════════════

@volume.command("service-list")
@click.option("--host", default=None, help="Filter by host.")
@click.option("--binary", default=None, help="Filter by binary (e.g. cinder-volume).")
@output_options
@click.pass_context
def volume_service_list(ctx: click.Context, host: str | None, binary: str | None,
                        output_format: str, columns: tuple[str, ...],
                        fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List Cinder services."""
    client = ctx.find_object(OrcaContext).ensure_client()
    params: dict = {}
    if host:
        params["host"] = host
    if binary:
        params["binary"] = binary
    services = client.get(f"{client.volume_url}/os-services",
                          params=params).get("services", [])
    print_list(
        services,
        [
            ("Binary", "binary", {"style": "bold"}),
            ("Host", "host"),
            ("Zone", "zone"),
            ("Status", "status"),
            ("State", "state"),
            ("Updated At", "updated_at"),
            ("Disabled Reason", lambda s: s.get("disabled_reason") or "—"),
        ],
        title="Cinder Services",
        output_format=output_format, fit_width=fit_width, max_width=max_width,
        noindent=noindent, columns=columns,
        empty_msg="No Cinder services found.",
    )


@volume.command("service-set")
@click.argument("host")
@click.argument("binary")
@click.option("--enable", "action", flag_value="enable", help="Enable the service.")
@click.option("--disable", "action", flag_value="disable", help="Disable the service.")
@click.option("--disabled-reason", default=None, help="Reason for disabling.")
@click.pass_context
def volume_service_set(ctx: click.Context, host: str, binary: str,
                       action: str | None, disabled_reason: str | None) -> None:
    """Enable or disable a Cinder service."""
    if not action:
        raise click.UsageError("Specify --enable or --disable.")
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {"host": host, "binary": binary}
    if action == "disable":
        url = f"{client.volume_url}/os-services/disable"
        if disabled_reason:
            body["disabled_reason"] = disabled_reason
            url = f"{client.volume_url}/os-services/disable-log-reason"
    else:
        url = f"{client.volume_url}/os-services/enable"
    client.put(url, json=body)
    console.print(f"[green]Service {binary} on {host} {action}d.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  migrate / revert-to-snapshot / summary
# ══════════════════════════════════════════════════════════════════════════


@volume.command("migrate")
@click.argument("volume_id", callback=validate_id)
@click.option("--host", required=True,
              help="Destination host (e.g. cinder@lvm#LVM).")
@click.option("--force-host-copy", is_flag=True, default=False,
              help="Bypass the driver, force host-level copy.")
@click.option("--lock-volume", is_flag=True, default=False,
              help="Lock the volume during migration.")
@click.pass_context
def volume_migrate(ctx: click.Context, volume_id: str, host: str,
                   force_host_copy: bool, lock_volume: bool) -> None:
    """Migrate a volume to a different Cinder host/backend.

    \b
    Example:
      orca volume migrate <id> --host cinder@lvm2#LVM2
    """
    _vol_action(ctx, volume_id, {
        "os-migrateVolume": {
            "host": host,
            "force_host_copy": force_host_copy,
            "lock_volume": lock_volume,
        }
    }, f"Migrate to {host}")


@volume.command("revert-to-snapshot")
@click.argument("volume_id", callback=validate_id)
@click.argument("snapshot_id", callback=validate_id)
@click.pass_context
def volume_revert_to_snapshot(ctx: click.Context, volume_id: str, snapshot_id: str) -> None:
    """Revert a volume to a previous snapshot.

    The volume must be in 'available' status and the snapshot must be
    the most recent one for this volume.

    \b
    Example:
      orca volume revert-to-snapshot <volume-id> <snapshot-id>
    """
    _vol_action(ctx, volume_id, {"revert": {"snapshot_id": snapshot_id}},
                f"Revert to snapshot {snapshot_id}")


@volume.command("summary")
@output_options
@click.pass_context
def volume_summary(ctx: click.Context, output_format: str, columns: tuple[str, ...],
                   fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show aggregated volume count and total size for the project."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{client.volume_url}/volumes/summary")
    s = data.get("volume-summary", data)
    fields = [
        ("Total Count", str(s.get("total_count", 0))),
        ("Total Size (GB)", str(s.get("total_size", 0))),
    ]
    if s.get("metadata"):
        fields.append(("Metadata", str(s["metadata"])))
    print_detail(fields, output_format=output_format, fit_width=fit_width,
                 max_width=max_width, noindent=noindent, columns=columns)


# ══════════════════════════════════════════════════════════════════════════
#  volume messages
# ══════════════════════════════════════════════════════════════════════════


@volume.command("message-list")
@click.option("--resource-id", default=None, help="Filter by resource UUID.")
@click.option("--resource-type", default=None,
              type=click.Choice(["VOLUME", "SNAPSHOT", "BACKUP", "GROUP"], case_sensitive=False),
              help="Filter by resource type.")
@output_options
@click.pass_context
def volume_message_list(ctx: click.Context, resource_id: str | None,
                        resource_type: str | None,
                        output_format: str, columns: tuple[str, ...],
                        fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List Cinder error messages."""
    client = ctx.find_object(OrcaContext).ensure_client()
    params: dict = {}
    if resource_id:
        params["resource_uuid"] = resource_id
    if resource_type:
        params["resource_type"] = resource_type.upper()
    data = client.get(f"{client.volume_url}/messages", params=params or None)
    messages = data.get("messages", [])
    print_list(
        messages,
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Resource Type", "resource_type"),
            ("Resource ID", "resource_uuid"),
            ("Event ID", "event_id"),
            ("Message", "user_message"),
            ("Created", "created_at"),
        ],
        title="Volume Messages",
        output_format=output_format, fit_width=fit_width, max_width=max_width,
        noindent=noindent, columns=columns,
        empty_msg="No messages found.",
    )


@volume.command("message-show")
@click.argument("message_id", callback=validate_id)
@output_options
@click.pass_context
def volume_message_show(ctx: click.Context, message_id: str,
                        output_format: str, columns: tuple[str, ...],
                        fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show a Cinder error message."""
    client = ctx.find_object(OrcaContext).ensure_client()
    m = client.get(f"{client.volume_url}/messages/{message_id}").get("message", {})
    fields = [(k, str(m.get(k, "") or "")) for k in
              ["id", "resource_type", "resource_uuid", "event_id",
               "user_message", "message_level", "created_at", "expires_at"]]
    print_detail(fields, output_format=output_format, fit_width=fit_width,
                 max_width=max_width, noindent=noindent, columns=columns)


@volume.command("message-delete")
@click.argument("message_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def volume_message_delete(ctx: click.Context, message_id: str, yes: bool) -> None:
    """Delete a Cinder error message."""
    if not yes:
        click.confirm(f"Delete message {message_id}?", abort=True)
    client = ctx.find_object(OrcaContext).ensure_client()
    client.delete(f"{client.volume_url}/messages/{message_id}")
    console.print(f"[green]Message {message_id} deleted.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  volume attachments (Cinder v3 attachment API)
# ══════════════════════════════════════════════════════════════════════════


@volume.command("attachment-list")
@click.option("--volume-id", "vol_filter", default=None,
              help="Filter by volume ID.")
@output_options
@click.pass_context
def volume_attachment_list(ctx: click.Context, vol_filter: str | None,
                           output_format: str, columns: tuple[str, ...],
                           fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List volume attachments (Cinder v3 attachment API)."""
    client = ctx.find_object(OrcaContext).ensure_client()
    params = {"volume_id": vol_filter} if vol_filter else None
    data = client.get(f"{client.volume_url}/attachments", params=params)
    attachments = data.get("attachments", [])
    print_list(
        attachments,
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Volume ID", "volume_id"),
            ("Instance ID", "instance_uuid"),
            ("Status", "status", {"style": "green"}),
            ("Attach Mode", "attach_mode"),
            ("Attached At", "attached_at"),
        ],
        title="Volume Attachments",
        output_format=output_format, fit_width=fit_width, max_width=max_width,
        noindent=noindent, columns=columns,
        empty_msg="No attachments found.",
    )


@volume.command("attachment-show")
@click.argument("attachment_id", callback=validate_id)
@output_options
@click.pass_context
def volume_attachment_show(ctx: click.Context, attachment_id: str,
                           output_format: str, columns: tuple[str, ...],
                           fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show a volume attachment."""
    client = ctx.find_object(OrcaContext).ensure_client()
    a = client.get(f"{client.volume_url}/attachments/{attachment_id}").get("attachment", {})
    fields = [(k, str(a.get(k, "") or "")) for k in
              ["id", "volume_id", "instance_uuid", "status",
               "attach_mode", "attached_at", "detached_at"]]
    if a.get("connection_info"):
        fields.append(("Connection Info", str(a["connection_info"])))
    print_detail(fields, output_format=output_format, fit_width=fit_width,
                 max_width=max_width, noindent=noindent, columns=columns)


@volume.command("attachment-delete")
@click.argument("attachment_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def volume_attachment_delete(ctx: click.Context, attachment_id: str, yes: bool) -> None:
    """Delete a volume attachment."""
    if not yes:
        click.confirm(f"Delete attachment {attachment_id}?", abort=True)
    client = ctx.find_object(OrcaContext).ensure_client()
    client.delete(f"{client.volume_url}/attachments/{attachment_id}")
    console.print(f"[green]Attachment {attachment_id} deleted.[/green]")


@volume.command("attachment-create")
@click.argument("volume_id", callback=validate_id)
@click.argument("instance_id", callback=validate_id)
@click.option("--mode", "attach_mode",
              type=click.Choice(["rw", "ro"]), default="rw", show_default=True,
              help="Attach mode: read-write or read-only.")
@click.option("--connector", "connector_json", default=None, metavar="JSON",
              help="Connector info as JSON (host, initiator, etc.).")
@output_options
@click.pass_context
def volume_attachment_create(ctx: click.Context, volume_id: str, instance_id: str,
                             attach_mode: str, connector_json: str | None,
                             output_format: str, columns: tuple[str, ...],
                             fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Create a volume attachment (Cinder v3 attachment API).

    \b
    Examples:
      orca volume attachment-create <vol-id> <instance-id>
      orca volume attachment-create <vol-id> <instance-id> --mode ro
      orca volume attachment-create <vol-id> <instance-id> --connector '{"host": "myhost"}'
    """
    import json as _json
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {
        "volume_id": volume_id,
        "instance_uuid": instance_id,
        "attach_mode": attach_mode,
    }
    if connector_json:
        try:
            body["connector"] = _json.loads(connector_json)
        except _json.JSONDecodeError as exc:
            raise click.BadParameter(f"Invalid JSON: {exc}", param_hint="--connector")
    data = client.post(f"{client.volume_url}/attachments", json={"attachment": body})
    a = data.get("attachment", data)
    print_detail(
        [(k, str(a.get(k, "") or "")) for k in
         ("id", "volume_id", "instance_uuid", "status", "attach_mode", "attached_at")],
        output_format=output_format, columns=columns,
        fit_width=fit_width, max_width=max_width, noindent=noindent,
    )


@volume.command("attachment-set")
@click.argument("attachment_id", callback=validate_id)
@click.option("--connector", "connector_json", required=True, metavar="JSON",
              help="Updated connector info as JSON.")
@output_options
@click.pass_context
def volume_attachment_set(ctx: click.Context, attachment_id: str, connector_json: str,
                          output_format: str, columns: tuple[str, ...],
                          fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Update (finalize) a volume attachment with connector info."""
    import json as _json
    client = ctx.find_object(OrcaContext).ensure_client()
    try:
        connector = _json.loads(connector_json)
    except _json.JSONDecodeError as exc:
        raise click.BadParameter(f"Invalid JSON: {exc}", param_hint="--connector")
    data = client.put(
        f"{client.volume_url}/attachments/{attachment_id}",
        json={"attachment": {"connector": connector}},
    )
    a = data.get("attachment", data) if data else {}
    if a:
        print_detail(
            [(k, str(a.get(k, "") or "")) for k in
             ("id", "volume_id", "instance_uuid", "status", "attach_mode")],
            output_format=output_format, columns=columns,
            fit_width=fit_width, max_width=max_width, noindent=noindent,
        )
    else:
        console.print(f"[green]Attachment {attachment_id} updated.[/green]")


@volume.command("attachment-complete")
@click.argument("attachment_id", callback=validate_id)
@click.pass_context
def volume_attachment_complete(ctx: click.Context, attachment_id: str) -> None:
    """Mark a volume attachment as complete (os-complete action)."""
    client = ctx.find_object(OrcaContext).ensure_client()
    client.post(
        f"{client.volume_url}/attachments/{attachment_id}/action",
        json={"os-complete": None},
    )
    console.print(f"[green]Attachment {attachment_id} marked as complete.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  volume groups (Cinder consistency groups v3)
# ══════════════════════════════════════════════════════════════════════════


@volume.command("group-list")
@output_options
@click.pass_context
def volume_group_list(ctx: click.Context, output_format: str, columns: tuple[str, ...],
                      fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List volume groups."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{client.volume_url}/groups/detail")
    groups = data.get("groups", [])
    print_list(
        groups,
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Name", "name", {"style": "bold"}),
            ("Status", "status", {"style": "green"}),
            ("Group Type", "group_type"),
            ("Volume Types", lambda g: ", ".join(g.get("volume_types", []))),
            ("Created", "created_at"),
        ],
        title="Volume Groups",
        output_format=output_format, fit_width=fit_width, max_width=max_width,
        noindent=noindent, columns=columns,
        empty_msg="No groups found.",
    )


@volume.command("group-show")
@click.argument("group_id", callback=validate_id)
@output_options
@click.pass_context
def volume_group_show(ctx: click.Context, group_id: str,
                      output_format: str, columns: tuple[str, ...],
                      fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show a volume group."""
    client = ctx.find_object(OrcaContext).ensure_client()
    g = client.get(f"{client.volume_url}/groups/{group_id}").get("group", {})
    fields = [(k, str(g.get(k, "") or "")) for k in
              ["id", "name", "status", "group_type",
               "volume_types", "availability_zone",
               "description", "created_at"]]
    print_detail(fields, output_format=output_format, fit_width=fit_width,
                 max_width=max_width, noindent=noindent, columns=columns)


@volume.command("group-create")
@click.argument("name", default=None, required=False)
@click.option("--group-type", required=True, help="Group type ID.")
@click.option("--volume-type", "volume_types", multiple=True, required=True,
              help="Volume type ID (repeatable).")
@click.option("--description", default=None, help="Description.")
@click.option("--availability-zone", default=None, help="Availability zone.")
@click.pass_context
def volume_group_create(ctx: click.Context, name: str | None,
                        group_type: str, volume_types: tuple[str, ...],
                        description: str | None, availability_zone: str | None) -> None:
    """Create a volume group.

    \b
    Example:
      orca volume group-create my-group \\
        --group-type <group-type-id> \\
        --volume-type <vol-type-id>
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {
        "group_type": group_type,
        "volume_types": list(volume_types),
    }
    if name:
        body["name"] = name
    if description:
        body["description"] = description
    if availability_zone:
        body["availability_zone"] = availability_zone
    g = client.post(f"{client.volume_url}/groups", json={"group": body}).get("group", {})
    console.print(f"[green]Group '{g.get('name', name)}' ({g.get('id')}) created.[/green]")


@volume.command("group-update")
@click.argument("group_id", callback=validate_id)
@click.option("--name", default=None, help="New name.")
@click.option("--description", default=None, help="New description.")
@click.option("--add-volume", "add_volumes", multiple=True,
              help="Volume ID to add to the group (repeatable).")
@click.option("--remove-volume", "remove_volumes", multiple=True,
              help="Volume ID to remove from the group (repeatable).")
@click.pass_context
def volume_group_update(ctx: click.Context, group_id: str, name: str | None,
                        description: str | None,
                        add_volumes: tuple[str, ...],
                        remove_volumes: tuple[str, ...]) -> None:
    """Update a volume group — rename or add/remove volumes.

    \b
    Examples:
      orca volume group-update <id> --name new-name
      orca volume group-update <id> --add-volume <vol-id>
      orca volume group-update <id> --remove-volume <vol-id>
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {}
    if name is not None:
        body["name"] = name
    if description is not None:
        body["description"] = description
    if add_volumes:
        body["add_volumes"] = ",".join(add_volumes)
    if remove_volumes:
        body["remove_volumes"] = ",".join(remove_volumes)
    if not body:
        console.print("[yellow]Nothing to update.[/yellow]")
        return
    client.put(f"{client.volume_url}/groups/{group_id}", json={"group": body})
    console.print(f"[green]Group {group_id} updated.[/green]")


@volume.command("group-delete")
@click.argument("group_id", callback=validate_id)
@click.option("--delete-volumes", is_flag=True, default=False,
              help="Also delete all volumes in the group.")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def volume_group_delete(ctx: click.Context, group_id: str,
                        delete_volumes: bool, yes: bool) -> None:
    """Delete a volume group.

    \b
    Example:
      orca volume group-delete <id>
      orca volume group-delete <id> --delete-volumes
    """
    if not yes:
        click.confirm(f"Delete group {group_id}?", abort=True)
    client = ctx.find_object(OrcaContext).ensure_client()
    client.post(
        f"{client.volume_url}/groups/{group_id}/action",
        json={"delete": {"delete-volumes": delete_volumes}},
    )
    console.print(f"[green]Group {group_id} deletion started.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  volume group-snapshot (Cinder v3)
# ══════════════════════════════════════════════════════════════════════════

@volume.command("group-snapshot-list")
@output_options
@click.pass_context
def volume_group_snapshot_list(ctx: click.Context, output_format: str,
                               columns: tuple[str, ...], fit_width: bool,
                               max_width: int | None, noindent: bool) -> None:
    """List volume group snapshots."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{client.volume_url}/group_snapshots/detail")
    print_list(
        data.get("group_snapshots", []),
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Name", "name", {"style": "bold"}),
            ("Status", "status"),
            ("Group ID", "group_id"),
            ("Created", lambda g: (g.get("created_at") or "")[:19]),
        ],
        title="Group Snapshots",
        output_format=output_format, columns=columns,
        fit_width=fit_width, max_width=max_width, noindent=noindent,
        empty_msg="No group snapshots found.",
    )


@volume.command("group-snapshot-show")
@click.argument("group_snapshot_id", callback=validate_id)
@output_options
@click.pass_context
def volume_group_snapshot_show(ctx: click.Context, group_snapshot_id: str,
                               output_format: str, columns: tuple[str, ...],
                               fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show a volume group snapshot."""
    client = ctx.find_object(OrcaContext).ensure_client()
    gs = client.get(
        f"{client.volume_url}/group_snapshots/{group_snapshot_id}"
    ).get("group_snapshot", {})
    print_detail(
        [(k, str(gs.get(k, "") or "")) for k in
         ("id", "name", "status", "group_id", "group_type_id",
          "description", "created_at")],
        output_format=output_format, columns=columns,
        fit_width=fit_width, max_width=max_width, noindent=noindent,
    )


@volume.command("group-snapshot-create")
@click.argument("group_id", callback=validate_id)
@click.option("--name", default=None, help="Snapshot name.")
@click.option("--description", default=None, help="Snapshot description.")
@click.pass_context
def volume_group_snapshot_create(ctx: click.Context, group_id: str,
                                 name: str | None, description: str | None) -> None:
    """Create a snapshot of a volume group."""
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {"group_id": group_id}
    if name:
        body["name"] = name
    if description:
        body["description"] = description
    data = client.post(f"{client.volume_url}/group_snapshots",
                       json={"group_snapshot": body})
    gs = data.get("group_snapshot", data)
    console.print(
        f"[green]Group snapshot '{gs.get('name', '')}' ({gs.get('id')}) created.[/green]"
    )


@volume.command("group-snapshot-delete")
@click.argument("group_snapshot_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def volume_group_snapshot_delete(ctx: click.Context, group_snapshot_id: str,
                                 yes: bool) -> None:
    """Delete a volume group snapshot."""
    if not yes:
        click.confirm(f"Delete group snapshot {group_snapshot_id}?", abort=True)
    client = ctx.find_object(OrcaContext).ensure_client()
    client.delete(f"{client.volume_url}/group_snapshots/{group_snapshot_id}")
    console.print(f"[green]Group snapshot {group_snapshot_id} deleted.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  volume group-type (Cinder v3)
# ══════════════════════════════════════════════════════════════════════════

@volume.command("group-type-list")
@output_options
@click.pass_context
def volume_group_type_list(ctx: click.Context, output_format: str,
                           columns: tuple[str, ...], fit_width: bool,
                           max_width: int | None, noindent: bool) -> None:
    """List volume group types."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{client.volume_url}/group_types")
    print_list(
        data.get("group_types", []),
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Name", "name", {"style": "bold"}),
            ("Is Public", "is_public"),
            ("Description", lambda g: (g.get("description") or "")[:50]),
        ],
        title="Group Types",
        output_format=output_format, columns=columns,
        fit_width=fit_width, max_width=max_width, noindent=noindent,
        empty_msg="No group types found.",
    )


@volume.command("group-type-show")
@click.argument("group_type_id")
@output_options
@click.pass_context
def volume_group_type_show(ctx: click.Context, group_type_id: str,
                           output_format: str, columns: tuple[str, ...],
                           fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show a volume group type."""
    client = ctx.find_object(OrcaContext).ensure_client()
    gt = client.get(
        f"{client.volume_url}/group_types/{group_type_id}"
    ).get("group_type", {})
    print_detail(
        [(k, str(gt.get(k, "") or "")) for k in
         ("id", "name", "is_public", "description")],
        output_format=output_format, columns=columns,
        fit_width=fit_width, max_width=max_width, noindent=noindent,
    )


@volume.command("group-type-create")
@click.argument("name")
@click.option("--description", default=None, help="Group type description.")
@click.option("--public/--private", default=True, help="Public or private group type.")
@click.pass_context
def volume_group_type_create(ctx: click.Context, name: str,
                             description: str | None, public: bool) -> None:
    """Create a volume group type."""
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {"name": name, "is_public": public}
    if description:
        body["description"] = description
    data = client.post(f"{client.volume_url}/group_types",
                       json={"group_type": body})
    gt = data.get("group_type", data)
    console.print(f"[green]Group type '{gt.get('name')}' ({gt.get('id')}) created.[/green]")


@volume.command("group-type-set")
@click.argument("group_type_id")
@click.option("--name", default=None, help="New name.")
@click.option("--description", default=None, help="New description.")
@click.option("--public/--private", default=None, help="Change visibility.")
@click.option("--property", "properties", multiple=True, metavar="KEY=VALUE",
              help="Group spec key=value (repeatable).")
@click.pass_context
def volume_group_type_set(ctx: click.Context, group_type_id: str,
                          name: str | None, description: str | None,
                          public: bool | None, properties: tuple[str, ...]) -> None:
    """Update a volume group type."""
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {}
    if name is not None:
        body["name"] = name
    if description is not None:
        body["description"] = description
    if public is not None:
        body["is_public"] = public
    if body:
        client.put(f"{client.volume_url}/group_types/{group_type_id}",
                   json={"group_type": body})
    if properties:
        specs: dict = {}
        for p in properties:
            if "=" not in p:
                raise click.UsageError(f"Invalid format '{p}', expected KEY=VALUE.")
            k, v = p.split("=", 1)
            specs[k] = v
        client.post(f"{client.volume_url}/group_types/{group_type_id}/group_specs",
                    json={"group_specs": specs})
    if not body and not properties:
        console.print("[yellow]Nothing to update.[/yellow]")
        return
    console.print(f"[green]Group type {group_type_id} updated.[/green]")


@volume.command("group-type-unset")
@click.argument("group_type_id")
@click.option("--property", "properties", multiple=True, metavar="KEY",
              help="Group spec key to remove (repeatable).")
@click.pass_context
def volume_group_type_unset(ctx: click.Context, group_type_id: str,
                            properties: tuple[str, ...]) -> None:
    """Unset group spec properties on a group type."""
    if not properties:
        console.print("[yellow]Nothing to unset.[/yellow]")
        return
    client = ctx.find_object(OrcaContext).ensure_client()
    for key in properties:
        client.delete(
            f"{client.volume_url}/group_types/{group_type_id}/group_specs/{key}"
        )
    console.print(f"[green]Group type {group_type_id} properties removed.[/green]")


@volume.command("group-type-delete")
@click.argument("group_type_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def volume_group_type_delete(ctx: click.Context, group_type_id: str, yes: bool) -> None:
    """Delete a volume group type."""
    if not yes:
        click.confirm(f"Delete group type {group_type_id}?", abort=True)
    client = ctx.find_object(OrcaContext).ensure_client()
    client.delete(f"{client.volume_url}/group_types/{group_type_id}")
    console.print(f"[green]Group type {group_type_id} deleted.[/green]")
