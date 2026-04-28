"""``orca volume`` — manage block storage volumes & snapshots (Cinder v3)."""

from __future__ import annotations

import re
import time

import click

from orca_cli.commands.image import _parse_property
from orca_cli.core import cache
from orca_cli.core.completions import complete_volumes
from orca_cli.core.context import OrcaContext
from orca_cli.core.exceptions import OrcaCLIError
from orca_cli.core.output import console, output_options, print_detail, print_list
from orca_cli.core.validators import validate_id
from orca_cli.core.waiter import wait_for_resource
from orca_cli.models.image import Image
from orca_cli.services.image import ImageService
from orca_cli.services.server import ServerService
from orca_cli.services.volume import VolumeService

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _resolve_volume_id(service: VolumeService, value: str) -> str:
    """Return *value* if it's a UUID, otherwise look up by exact name."""
    if _UUID_RE.match(value):
        return value
    matches = service.find(params={"name": value})
    if not matches:
        raise OrcaCLIError(f"No volume found with name '{value}'.")
    if len(matches) > 1:
        raise OrcaCLIError(
            f"Multiple volumes match '{value}' — pass a UUID instead."
        )
    return matches[0]["id"]


def _vol_action(ctx: click.Context, volume_id: str, action: dict, label: str) -> None:
    service = VolumeService(ctx.find_object(OrcaContext).ensure_client())
    service.action(volume_id, action)
    console.print(f"[green]{label} request sent for {volume_id}.[/green]")


@click.group()
@click.pass_context
def volume(ctx: click.Context) -> None:
    """Manage block storage volumes & snapshots."""
    pass


# ── nested sub-groups (ADR-0008 — openstackclient-style naming) ───────────


@volume.group("attachment")
def volume_attachment() -> None:
    """Manage volume attachments (low-level)."""


@volume.group("backup")
def volume_backup() -> None:
    """Manage Cinder backups."""


@volume.group("group")
def volume_group() -> None:
    """Manage consistency / generic volume groups."""


@volume_group.group("snapshot")
def volume_group_snapshot() -> None:
    """Group snapshots — atomic snapshots across a group of volumes."""


@volume_group.group("type")
def volume_group_type() -> None:
    """Group types."""


@volume.group("message")
def volume_message() -> None:
    """User-facing Cinder messages (failures, info)."""


@volume.group("qos")
def volume_qos() -> None:
    """QoS specifications."""


@volume.group("service")
def volume_service() -> None:
    """Cinder backend services (admin)."""


@volume.group("snapshot")
def volume_snapshot() -> None:
    """Manage volume snapshots."""


@volume.group("transfer")
def volume_transfer() -> None:
    """Volume transfers between projects."""


@volume.group("type")
def volume_type() -> None:
    """Volume types."""


@volume_type.group("access")
def volume_type_access() -> None:
    """Project-level access to a volume type."""


# ── list ──────────────────────────────────────────────────────────────────

@volume.command("list")
@output_options
@click.pass_context
def volume_list(ctx: click.Context, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List volumes."""
    service = VolumeService(ctx.find_object(OrcaContext).ensure_client())
    volumes = service.find()

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
    vol = VolumeService(ctx.find_object(OrcaContext).ensure_client()).get(volume_id)

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
            raise OrcaCLIError(
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

    vol = VolumeService(client).create(body)
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

    service = VolumeService(ctx.find_object(OrcaContext).ensure_client())
    service.update(volume_id, body)
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

@volume.command("set-bootable", deprecated=True)
@click.argument("volume_id", callback=validate_id)
@click.option("--bootable/--no-bootable", default=True, show_default=True,
              help="Mark volume as bootable or non-bootable.")
@click.pass_context
def volume_set_bootable(ctx: click.Context, volume_id: str, bootable: bool) -> None:
    """Set bootable flag (deprecated — use 'volume set --bootable')."""
    flag = "--bootable" if bootable else "--no-bootable"
    click.secho(
        f"warning: 'volume set-bootable' is deprecated; use "
        f"'orca volume set {volume_id} {flag}' instead.",
        fg="yellow", err=True,
    )
    _vol_action(ctx, volume_id, {"os-set_bootable": {"bootable": bootable}},
                f"Set bootable={str(bootable).lower()}")


# ── set-readonly ──────────────────────────────────────────────────────────

@volume.command("set-readonly", deprecated=True)
@click.argument("volume_id", callback=validate_id)
@click.option("--readonly/--no-readonly", default=True, show_default=True,
              help="Mark volume as read-only or read-write.")
@click.pass_context
def volume_set_readonly(ctx: click.Context, volume_id: str, readonly: bool) -> None:
    """Set read-only flag (deprecated — use 'volume set --read-only')."""
    flag = "--read-only" if readonly else "--no-read-only"
    click.secho(
        f"warning: 'volume set-readonly' is deprecated; use "
        f"'orca volume set {volume_id} {flag}' instead.",
        fg="yellow", err=True,
    )
    _vol_action(ctx, volume_id, {"os-update_readonly_flag": {"readonly": readonly}},
                f"Set readonly={str(readonly).lower()}")


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
    service = VolumeService(client)

    if dry_run:
        vol = service.get(volume_id)
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

    service.delete(volume_id)
    cache.invalidate(orca_ctx.profile, "volumes")

    if wait:
        wait_for_resource(
            client, f"{client.volume_url}/volumes/{volume_id}", "volume", "deleted",
            label=f"Volume {volume_id}",
            delete_mode=True,
            error_status="error",
        )
    else:
        console.print(f"[green]Volume {volume_id} deleted.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  upload-to-image
# ══════════════════════════════════════════════════════════════════════════


_IMAGE_TERMINAL_OK = "active"
_IMAGE_TERMINAL_FAIL = ("killed", "deleted")


def _format_size(size: int | None) -> str:
    """Format bytes for the progress line; '—' when unknown."""
    if not size:
        return "—"
    n = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def _wait_for_image_active(service: ImageService, image_id: str,
                           *, fast_interval: int = 5,
                           slow_interval: int = 15,
                           fast_window: int = 60) -> tuple[Image, float]:
    """Poll Glance until the image reaches ``active``.

    Polls every ``fast_interval`` seconds for the first ``fast_window``
    seconds, then every ``slow_interval`` seconds. Raises ``OrcaCLIError``
    if the image transitions to a terminal failure state.
    """
    start = time.monotonic()
    last_status = ""
    last_size: int | None = None

    with console.status(f"[bold cyan]Waiting for image {image_id} → active…[/bold cyan]") as spinner:
        while True:
            elapsed = time.monotonic() - start
            img = service.get(image_id)
            status = (img.get("status") or "").lower()
            size = img.get("size")

            if status == _IMAGE_TERMINAL_OK:
                return img, elapsed

            if status in _IMAGE_TERMINAL_FAIL:
                fault = img.get("message") or img.get("fault") or ""
                msg = (
                    f"Image {image_id} entered terminal state '{status}' "
                    f"after {elapsed:.0f}s."
                )
                if fault:
                    msg += f" Details: {fault}"
                raise OrcaCLIError(msg)

            if status != last_status or size != last_size:
                last_status, last_size = status, size
                spinner.update(
                    f"[bold cyan]Image {image_id}: {status or 'pending'} "
                    f"({_format_size(size)}, {elapsed:.0f}s)…[/bold cyan]"
                )

            interval = fast_interval if elapsed < fast_window else slow_interval
            time.sleep(interval)


@volume.command("upload-to-image")
@click.argument("volume_id_or_name", shell_complete=complete_volumes)
@click.argument("image_name")
@click.option("--disk-format",
              type=click.Choice(["raw", "qcow2", "vmdk", "vdi", "vhd", "vhdx",
                                 "iso", "aki", "ari", "ami"],
                                case_sensitive=False),
              default="qcow2", show_default=True, help="Disk format.")
@click.option("--container-format",
              type=click.Choice(["bare", "ovf", "ova", "aki", "ari", "ami", "docker"],
                                case_sensitive=False),
              default="bare", show_default=True, help="Container format.")
@click.option("--visibility",
              type=click.Choice(["private", "shared", "community", "public"],
                                case_sensitive=False),
              default=None,
              help="Image visibility. Only sent to Cinder when explicit "
                   "(older microversions reject the field); otherwise "
                   "Glance applies its own default.")
@click.option("--protected/--no-protected", "protected",
              default=None,
              help="Mark the resulting image as protected (deletion-locked). "
                   "Only sent to Cinder when explicit; otherwise omitted "
                   "from the action body for older-microversion compatibility.")
@click.option("--force", is_flag=True, default=False,
              help="Required when uploading from an in-use volume.")
@click.option("--property", "properties", multiple=True, callback=_parse_property,
              metavar="KEY=VALUE",
              help="Custom Glance property to set on the resulting image. "
                   "Repeatable. Applied via JSON-Patch after the upload action.")
@click.option("--wait", is_flag=True, default=False,
              help="Poll the resulting image until it reaches 'active' "
                   "(or 'killed'/'deleted', in which case exit non-zero).")
@click.pass_context
def volume_upload_to_image(ctx: click.Context, volume_id_or_name: str,
                           image_name: str,
                           disk_format: str, container_format: str,
                           visibility: str | None, protected: bool | None,
                           force: bool,
                           properties: tuple[tuple[str, str], ...],
                           wait: bool) -> None:
    """Materialize a volume's data as a downloadable Glance image.

    \b
    Wraps Cinder's ``os-volume_upload_image`` action. The resulting image is
    a self-contained binary (unlike a server snapshot of a boot-from-volume
    instance, which is a 0-byte shell pointing at a Cinder snapshot) and can
    therefore be downloaded with ``orca image download``.

    \b
    Examples:
      orca volume upload-to-image <volume-id> my-image
      orca volume upload-to-image my-vol my-image --disk-format raw
      orca volume upload-to-image <id> img --force                # in-use volume
      orca volume upload-to-image <id> img --property os_distro=ubuntu --wait
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    vol_service = VolumeService(client)
    img_service = ImageService(client)

    volume_id = _resolve_volume_id(vol_service, volume_id_or_name)

    # Pre-flight: refuse to call Cinder when the volume is in-use without
    # --force, so the user gets an actionable message instead of an opaque
    # 400 from the back-end.
    vol = vol_service.get(volume_id)
    status = (vol.get("status") or "").lower()
    if status == "in-use" and not force:
        raise OrcaCLIError(
            f"Volume {volume_id} is in-use; pass --force to upload anyway "
            "(the resulting image may be crash-consistent only).",
        )

    response = vol_service.upload_to_image(
        volume_id,
        image_name=image_name,
        disk_format=disk_format,
        container_format=container_format,
        visibility=visibility,
        protected=protected,
        force=force,
    )
    image_id = response.get("image_id", "")
    initial_status = response.get("status", "queued")
    if not image_id:
        raise OrcaCLIError(
            "Cinder accepted the upload action but did not return an image_id; "
            "check 'orca image list' manually.",
        )

    # Glance does not accept arbitrary properties via os-volume_upload_image,
    # so we PATCH the freshly-created image instead. We still consult the
    # current state to choose add-vs-replace, mirroring 'orca image update'.
    if properties:
        current = img_service.get(image_id)
        ops = [
            {
                "op": "replace" if k in current else "add",
                "path": f"/{k}",
                "value": v,
            }
            for k, v in properties
        ]
        img_service.update(image_id, ops)

    console.print(
        f"[green]Image '{image_name}' ({image_id}) creation started "
        f"from volume {volume_id}.[/green]"
    )
    console.print(f"  Status: {initial_status}")

    if not wait:
        console.print(
            f"[dim]Use 'orca image show {image_id}' to track progress.[/dim]"
        )
        return

    img, elapsed = _wait_for_image_active(img_service, image_id)
    console.print(f"[green]Image {image_id} is active ({elapsed:.0f}s).[/green]")
    console.print(f"  Size:          {_format_size(img.get('size'))}")
    if img.get("checksum"):
        console.print(f"  Checksum:      {img['checksum']}")
    if img.get("os_hash_algo") and img.get("os_hash_value"):
        console.print(
            f"  {img['os_hash_algo']}: {img['os_hash_value']}"
        )


# ══════════════════════════════════════════════════════════════════════════
#  Snapshots
# ══════════════════════════════════════════════════════════════════════════

@volume_snapshot.command("list")
@output_options
@click.pass_context
def snapshot_list(ctx: click.Context, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List volume snapshots."""
    snaps = VolumeService(ctx.find_object(OrcaContext).ensure_client()).find_snapshots()

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


@volume_snapshot.command("show")
@click.argument("snapshot_id", callback=validate_id)
@output_options
@click.pass_context
def snapshot_show(ctx: click.Context, snapshot_id: str, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show snapshot details."""
    snap = VolumeService(ctx.find_object(OrcaContext).ensure_client()).get_snapshot(snapshot_id)

    fields: list[tuple[str, str]] = []
    for key in ["id", "name", "description", "volume_id", "size", "status", "created_at"]:
        val = snap.get(key, "")
        if key == "size" and val:
            val = f"{val} GB"
        fields.append((key, str(val) if val is not None else ""))

    print_detail(fields, output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent, columns=columns)


@volume_snapshot.command("create")
@click.argument("volume_id_or_name")
@click.option("--name", required=True, help="Snapshot name.")
@click.option("--description", default=None, help="Snapshot description.")
@click.option("--force", is_flag=True, help="Force snapshot of in-use volume.")
@click.pass_context
def snapshot_create(ctx: click.Context, volume_id_or_name: str, name: str, description: str | None, force: bool) -> None:
    """Create a snapshot of a volume (accepts UUID or name)."""
    service = VolumeService(ctx.find_object(OrcaContext).ensure_client())

    # Resolve name → UUID if needed
    import re
    _UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
    if _UUID_RE.match(volume_id_or_name):
        volume_id = volume_id_or_name
    else:
        vols = service.find(params={"name": volume_id_or_name})
        if not vols:
            raise OrcaCLIError(f"No volume found with name '{volume_id_or_name}'")
        if len(vols) > 1:
            raise OrcaCLIError(f"Multiple volumes match '{volume_id_or_name}' — use a UUID")
        volume_id = vols[0]["id"]

    body: dict = {"volume_id": volume_id, "name": name, "force": force}
    if description:
        body["description"] = description

    snap = service.create_snapshot(body)
    console.print(f"[green]Snapshot '{snap.get('name')}' ({snap.get('id')}) created from {volume_id}.[/green]")


@volume_snapshot.command("delete")
@click.argument("snapshot_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def snapshot_delete(ctx: click.Context, snapshot_id: str, yes: bool) -> None:
    """Delete a volume snapshot."""
    if not yes:
        click.confirm(f"Delete snapshot {snapshot_id}?", abort=True)

    VolumeService(ctx.find_object(OrcaContext).ensure_client()).delete_snapshot(snapshot_id)
    console.print(f"[green]Snapshot {snapshot_id} deleted.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  Tree / Map
# ══════════════════════════════════════════════════════════════════════════

@volume.command("tree")
@click.option("--volume-id", "filter_vol", default=None, help="Show only this volume and its snapshots.")
@click.pass_context
def volume_tree(ctx: click.Context, filter_vol: str | None) -> None:  # noqa: C901
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
    service = VolumeService(client)

    with console.status("[bold cyan]Building volume tree…[/bold cyan]"):
        # Fetch volumes & snapshots
        vols = service.find()
        snaps = service.find_snapshots()

        # Fetch servers for name resolution
        try:
            srv_list = ServerService(client).find_all()
            servers = {s["id"]: s.get("name", s["id"]) for s in srv_list}
        except Exception:
            servers = {}

    # Index
    vol_map = {v["id"]: v for v in vols}
    snaps_by_vol: dict[str, list] = {}
    for s in snaps:
        snaps_by_vol.setdefault(s.get("volume_id", ""), []).append(s)

    # Volumes created from a snapshot → track parent
    children_of_snap: dict[str, list] = {}
    for v in vols:
        sid = v.get("snapshot_id")
        if sid:
            children_of_snap.setdefault(sid, []).append(v)

    # Volumes cloned from another volume
    children_of_vol: dict[str, list] = {}
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

    def _add_volume(parent_node, v, seen: set) -> None:
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

@volume_backup.command("list")
@click.option("--all-projects", is_flag=True, help="List backups from all projects (admin).")
@output_options
@click.pass_context
def volume_backup_list(ctx: click.Context, all_projects: bool, output_format: str,
                       columns: tuple[str, ...], fit_width: bool,
                       max_width: int | None, noindent: bool) -> None:
    """List Cinder volume backups."""
    service = VolumeService(ctx.find_object(OrcaContext).ensure_client())
    params = {"all_tenants": 1} if all_projects else None
    backups = service.find_backups(params=params)
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


@volume_backup.command("show")
@click.argument("backup_id", callback=validate_id)
@output_options
@click.pass_context
def volume_backup_show(ctx: click.Context, backup_id: str, output_format: str,
                       columns: tuple[str, ...], fit_width: bool,
                       max_width: int | None, noindent: bool) -> None:
    """Show details of a volume backup."""
    b = VolumeService(ctx.find_object(OrcaContext).ensure_client()).get_backup(backup_id)
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


@volume_backup.command("create")
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
    service = VolumeService(client)

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

    bk = service.create_backup(body)
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


@volume_backup.command("delete")
@click.argument("backup_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.option("--force", is_flag=True, help="Force deletion even if backup is not available.")
@click.pass_context
def volume_backup_delete(ctx: click.Context, backup_id: str, yes: bool, force: bool) -> None:
    """Delete a volume backup."""
    if not yes:
        click.confirm(f"Delete backup {backup_id}?", abort=True)
    VolumeService(ctx.find_object(OrcaContext).ensure_client()).delete_backup(backup_id, force=force)
    console.print(f"[green]Backup {backup_id} deleted.[/green]")


@volume_backup.command("restore")
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
    service = VolumeService(client)
    body: dict = {}
    if volume_id:
        body["volume_id"] = volume_id
    if name:
        body["name"] = name

    restore = service.restore_backup(backup_id, body)
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
@click.option("--bootable/--no-bootable", "bootable", default=None,
              help="Mark volume as bootable or non-bootable.")
@click.option("--read-only/--no-read-only", "read_only", default=None,
              help="Mark volume as read-only or read-write.")
@click.pass_context
def volume_set(ctx: click.Context, volume_id: str, properties: tuple[str, ...],
               name: str | None, description: str | None,
               bootable: bool | None, read_only: bool | None) -> None:
    """Set volume properties, metadata, or flags.

    \b
    Examples:
      orca volume set <id> --name new-name
      orca volume set <id> --property env=prod --property team=infra
      orca volume set <id> --bootable
      orca volume set <id> --read-only
    """
    service = VolumeService(ctx.find_object(OrcaContext).ensure_client())
    body: dict = {}
    if name is not None:
        body["name"] = name
    if description is not None:
        body["description"] = description
    if body:
        service.update(volume_id, body)
    if properties:
        meta: dict = {}
        for prop in properties:
            if "=" not in prop:
                raise OrcaCLIError(f"Invalid property format '{prop}', expected KEY=VALUE.")
            k, v = prop.split("=", 1)
            meta[k] = v
        service.set_metadata(volume_id, meta)
    if bootable is not None:
        _vol_action(ctx, volume_id, {"os-set_bootable": {"bootable": bootable}},
                    f"Set bootable={str(bootable).lower()}")
    if read_only is not None:
        _vol_action(ctx, volume_id, {"os-update_readonly_flag": {"readonly": read_only}},
                    f"Set readonly={str(read_only).lower()}")
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
    service = VolumeService(ctx.find_object(OrcaContext).ensure_client())
    for key in properties:
        service.delete_metadata_key(volume_id, key)
    console.print(f"[green]Metadata removed from volume {volume_id}.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  Snapshot update
# ══════════════════════════════════════════════════════════════════════════

@volume_snapshot.command("set")
@click.argument("snapshot_id", callback=validate_id)
@click.option("--name", default=None, help="New name.")
@click.option("--description", default=None, help="New description.")
@click.option("--property", "properties", multiple=True, metavar="KEY=VALUE",
              help="Metadata key=value (repeatable).")
@click.pass_context
def snapshot_set(ctx: click.Context, snapshot_id: str, name: str | None,
                 description: str | None, properties: tuple[str, ...]) -> None:
    """Update a snapshot's name, description, or metadata."""
    service = VolumeService(ctx.find_object(OrcaContext).ensure_client())
    body: dict = {}
    if name is not None:
        body["name"] = name
    if description is not None:
        body["description"] = description
    if body:
        service.update_snapshot(snapshot_id, body)
    if properties:
        meta: dict = {}
        for prop in properties:
            if "=" not in prop:
                raise OrcaCLIError(f"Invalid property format '{prop}', expected KEY=VALUE.")
            k, v = prop.split("=", 1)
            meta[k] = v
        service.update_snapshot_metadata(snapshot_id, meta)
    if not body and not properties:
        console.print("[yellow]Nothing to update.[/yellow]")
        return
    console.print(f"[green]Snapshot {snapshot_id} updated.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  Volume Types
# ══════════════════════════════════════════════════════════════════════════

@volume_type.command("list")
@click.option("--default", "show_default", is_flag=True, help="Show the default type only.")
@output_options
@click.pass_context
def volume_type_list(ctx: click.Context, show_default: bool,
                     output_format: str, columns: tuple[str, ...],
                     fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List volume types."""
    service = VolumeService(ctx.find_object(OrcaContext).ensure_client())
    types = [service.get_default_type()] if show_default else service.find_types()
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


@volume_type.command("show")
@click.argument("type_id")
@output_options
@click.pass_context
def volume_type_show(ctx: click.Context, type_id: str,
                     output_format: str, columns: tuple[str, ...],
                     fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show volume type details."""
    client = ctx.find_object(OrcaContext).ensure_client()
    t = VolumeService(client).get_type(type_id)
    extra = t.get("extra_specs") or {}
    fields = [(k, str(t.get(k, "") or "")) for k in
              ["id", "name", "description", "is_public"]]
    for k, v in extra.items():
        fields.append((f"  {k}", str(v)))
    print_detail(fields, output_format=output_format, fit_width=fit_width,
                 max_width=max_width, noindent=noindent, columns=columns)


@volume_type.command("create")
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
    service = VolumeService(ctx.find_object(OrcaContext).ensure_client())
    body: dict = {"name": name, "os-volume-type-access:is_public": is_public}
    if description:
        body["description"] = description
    t = service.create_type(body)
    if properties:
        specs: dict = {}
        for prop in properties:
            if "=" not in prop:
                raise OrcaCLIError(f"Invalid format '{prop}', expected KEY=VALUE.")
            k, v = prop.split("=", 1)
            specs[k] = v
        service.set_type_extra_specs(t["id"], specs)
    console.print(f"[green]Volume type '{name}' created: {t.get('id', '?')}[/green]")


@volume_type.command("set")
@click.argument("type_id")
@click.option("--name", default=None, help="New name.")
@click.option("--description", default=None, help="New description.")
@click.option("--property", "properties", multiple=True, metavar="KEY=VALUE",
              help="Extra spec to add or update (repeatable).")
@click.pass_context
def volume_type_set(ctx: click.Context, type_id: str, name: str | None,
                    description: str | None, properties: tuple[str, ...]) -> None:
    """Update a volume type."""
    service = VolumeService(ctx.find_object(OrcaContext).ensure_client())
    body: dict = {}
    if name is not None:
        body["name"] = name
    if description is not None:
        body["description"] = description
    if body:
        service.update_type(type_id, body)
    if properties:
        specs: dict = {}
        for prop in properties:
            if "=" not in prop:
                raise OrcaCLIError(f"Invalid format '{prop}', expected KEY=VALUE.")
            k, v = prop.split("=", 1)
            specs[k] = v
        service.set_type_extra_specs(type_id, specs)
    if not body and not properties:
        console.print("[yellow]Nothing to update.[/yellow]")
        return
    console.print(f"[green]Volume type {type_id} updated.[/green]")


@volume_type.command("delete")
@click.argument("type_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def volume_type_delete(ctx: click.Context, type_id: str, yes: bool) -> None:
    """Delete a volume type."""
    if not yes:
        click.confirm(f"Delete volume type {type_id}?", abort=True)
    VolumeService(ctx.find_object(OrcaContext).ensure_client()).delete_type(type_id)
    console.print(f"[green]Volume type {type_id} deleted.[/green]")


@volume_type_access.command("list")
@click.argument("type_id")
@output_options
@click.pass_context
def volume_type_access_list(ctx: click.Context, type_id: str,
                             output_format: str, columns: tuple[str, ...],
                             fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List projects that have access to a private volume type."""
    accesses = VolumeService(ctx.find_object(OrcaContext).ensure_client()).list_type_access(type_id)
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


@volume_type_access.command("add")
@click.argument("type_id")
@click.argument("project_id", callback=validate_id)
@click.pass_context
def volume_type_access_add(ctx: click.Context, type_id: str, project_id: str) -> None:
    """Grant a project access to a private volume type."""
    VolumeService(ctx.find_object(OrcaContext).ensure_client()).add_type_access(type_id, project_id)
    console.print(f"[green]Project {project_id} granted access to type {type_id}.[/green]")


@volume_type_access.command("remove")
@click.argument("type_id")
@click.argument("project_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def volume_type_access_remove(ctx: click.Context, type_id: str, project_id: str,
                               yes: bool) -> None:
    """Revoke a project's access to a private volume type."""
    if not yes:
        click.confirm(f"Remove project {project_id} from type {type_id}?", abort=True)
    VolumeService(ctx.find_object(OrcaContext).ensure_client()).remove_type_access(type_id, project_id)
    console.print(f"[green]Project {project_id} access to type {type_id} revoked.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  Volume Transfers
# ══════════════════════════════════════════════════════════════════════════

@volume_transfer.command("create")
@click.argument("volume_id", callback=validate_id)
@click.option("--name", default=None, help="Transfer name.")
@click.pass_context
def volume_transfer_create(ctx: click.Context, volume_id: str, name: str | None) -> None:
    """Create a volume transfer request."""
    service = VolumeService(ctx.find_object(OrcaContext).ensure_client())
    body: dict = {"volume_id": volume_id}
    if name:
        body["name"] = name
    t = service.create_transfer(body)
    console.print(f"[green]Transfer created: {t.get('id', '?')}[/green]")
    console.print(f"  Auth key: [bold cyan]{t.get('auth_key', '?')}[/bold cyan]")
    console.print("  [yellow]Save the auth key — it will not be shown again.[/yellow]")


@volume_transfer.command("list")
@click.option("--all-projects", is_flag=True, help="List transfers from all projects (admin).")
@output_options
@click.pass_context
def volume_transfer_list(ctx: click.Context, all_projects: bool,
                         output_format: str, columns: tuple[str, ...],
                         fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List volume transfer requests."""
    params = {"all_tenants": 1} if all_projects else None
    transfers = VolumeService(ctx.find_object(OrcaContext).ensure_client()).find_transfers(params=params)
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


@volume_transfer.command("show")
@click.argument("transfer_id", callback=validate_id)
@output_options
@click.pass_context
def volume_transfer_show(ctx: click.Context, transfer_id: str,
                         output_format: str, columns: tuple[str, ...],
                         fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show a volume transfer request."""
    t = VolumeService(ctx.find_object(OrcaContext).ensure_client()).get_transfer(transfer_id)
    print_detail(
        [(k, str(t.get(k, "") or "")) for k in
         ["id", "name", "volume_id", "created_at"]],
        output_format=output_format, fit_width=fit_width, max_width=max_width,
        noindent=noindent, columns=columns,
    )


@volume_transfer.command("accept")
@click.argument("transfer_id", callback=validate_id)
@click.argument("auth_key")
@click.pass_context
def volume_transfer_accept(ctx: click.Context, transfer_id: str, auth_key: str) -> None:
    """Accept a volume transfer request."""
    VolumeService(ctx.find_object(OrcaContext).ensure_client()).accept_transfer(transfer_id, auth_key)
    console.print(f"[green]Transfer {transfer_id} accepted.[/green]")


@volume_transfer.command("delete")
@click.argument("transfer_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def volume_transfer_delete(ctx: click.Context, transfer_id: str, yes: bool) -> None:
    """Delete a volume transfer request."""
    if not yes:
        click.confirm(f"Delete transfer {transfer_id}?", abort=True)
    VolumeService(ctx.find_object(OrcaContext).ensure_client()).delete_transfer(transfer_id)
    console.print(f"[green]Transfer {transfer_id} deleted.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  Volume QoS Specs
# ══════════════════════════════════════════════════════════════════════════

@volume_qos.command("list")
@output_options
@click.pass_context
def volume_qos_list(ctx: click.Context, output_format: str, columns: tuple[str, ...],
                    fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List volume QoS specs."""
    specs = VolumeService(ctx.find_object(OrcaContext).ensure_client()).find_qos()
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


@volume_qos.command("show")
@click.argument("qos_id", callback=validate_id)
@output_options
@click.pass_context
def volume_qos_show(ctx: click.Context, qos_id: str,
                    output_format: str, columns: tuple[str, ...],
                    fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show volume QoS spec details."""
    s = VolumeService(ctx.find_object(OrcaContext).ensure_client()).get_qos(qos_id)
    fields = [
        ("ID", str(s.get("id", ""))),
        ("Name", str(s.get("name", ""))),
        ("Consumer", str(s.get("consumer", ""))),
    ]
    for k, v in (s.get("specs") or {}).items():
        fields.append((f"  {k}", str(v)))
    print_detail(fields, output_format=output_format, fit_width=fit_width,
                 max_width=max_width, noindent=noindent, columns=columns)


@volume_qos.command("create")
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
    service = VolumeService(ctx.find_object(OrcaContext).ensure_client())
    specs: dict = {}
    for prop in properties:
        if "=" not in prop:
            raise OrcaCLIError(f"Invalid format '{prop}', expected KEY=VALUE.")
        k, v = prop.split("=", 1)
        specs[k] = v
    # Cinder expects spec keys at the top level of qos_specs alongside
    # name/consumer; not nested under a "specs" sub-key.
    body: dict = {"name": name, "consumer": consumer, **specs}
    s = service.create_qos(body)
    console.print(f"[green]QoS spec '{name}' created: {s.get('id', '?')}[/green]")


@volume_qos.command("set")
@click.argument("qos_id", callback=validate_id)
@click.option("--property", "properties", multiple=True, metavar="KEY=VALUE",
              help="QoS spec key=value to add or update (repeatable).")
@click.pass_context
def volume_qos_set(ctx: click.Context, qos_id: str, properties: tuple[str, ...]) -> None:
    """Add or update keys on a volume QoS spec."""
    if not properties:
        console.print("[yellow]No properties specified.[/yellow]")
        return
    service = VolumeService(ctx.find_object(OrcaContext).ensure_client())
    specs: dict = {}
    for prop in properties:
        if "=" not in prop:
            raise OrcaCLIError(f"Invalid format '{prop}', expected KEY=VALUE.")
        k, v = prop.split("=", 1)
        specs[k] = v
    # Cinder expects the spec keys at the top of qos_specs, not nested
    # under a "specs" sub-key. Pass the flat dict directly.
    service.update_qos(qos_id, specs)
    console.print(f"[green]QoS spec {qos_id} updated.[/green]")


@volume_qos.command("delete")
@click.argument("qos_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.option("--force", is_flag=True, help="Delete even if associated with a volume type.")
@click.pass_context
def volume_qos_delete(ctx: click.Context, qos_id: str, yes: bool, force: bool) -> None:
    """Delete a volume QoS spec."""
    if not yes:
        click.confirm(f"Delete QoS spec {qos_id}?", abort=True)
    VolumeService(ctx.find_object(OrcaContext).ensure_client()).delete_qos(qos_id, force=force)
    console.print(f"[green]QoS spec {qos_id} deleted.[/green]")


@volume_qos.command("associate")
@click.argument("qos_id", callback=validate_id)
@click.argument("type_id")
@click.pass_context
def volume_qos_associate(ctx: click.Context, qos_id: str, type_id: str) -> None:
    """Associate a QoS spec with a volume type."""
    VolumeService(ctx.find_object(OrcaContext).ensure_client()).associate_qos(qos_id, type_id)
    console.print(f"[green]QoS spec {qos_id} associated with type {type_id}.[/green]")


@volume_qos.command("disassociate")
@click.argument("qos_id", callback=validate_id)
@click.argument("type_id")
@click.option("--all", "disassociate_all", is_flag=True,
              help="Disassociate from all volume types.")
@click.pass_context
def volume_qos_disassociate(ctx: click.Context, qos_id: str, type_id: str,
                             disassociate_all: bool) -> None:
    """Disassociate a QoS spec from a volume type."""
    service = VolumeService(ctx.find_object(OrcaContext).ensure_client())
    service.disassociate_qos(qos_id, None if disassociate_all else type_id)
    console.print(f"[green]QoS spec {qos_id} disassociated.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  Volume Service (Cinder service management)
# ══════════════════════════════════════════════════════════════════════════

@volume_service.command("list")
@click.option("--host", default=None, help="Filter by host.")
@click.option("--binary", default=None, help="Filter by binary (e.g. cinder-volume).")
@output_options
@click.pass_context
def volume_service_list(ctx: click.Context, host: str | None, binary: str | None,
                        output_format: str, columns: tuple[str, ...],
                        fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List Cinder services."""
    params: dict = {}
    if host:
        params["host"] = host
    if binary:
        params["binary"] = binary
    services = VolumeService(ctx.find_object(OrcaContext).ensure_client()).find_services(
        params=params or None,
    )
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


@volume_service.command("set")
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
        raise OrcaCLIError("Specify --enable or --disable.")
    service = VolumeService(ctx.find_object(OrcaContext).ensure_client())
    body: dict = {"host": host, "binary": binary}
    if action == "disable":
        verb = "disable"
        if disabled_reason:
            body["disabled_reason"] = disabled_reason
            verb = "disable-log-reason"
    else:
        verb = "enable"
    service.update_service(verb, body)
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


@volume_snapshot.command("revert")
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
    s = VolumeService(ctx.find_object(OrcaContext).ensure_client()).get_summary()
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


@volume_message.command("list")
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
    # find_messages has no built-in filters; apply client-side.
    messages = VolumeService(ctx.find_object(OrcaContext).ensure_client()).find_messages()
    if resource_id:
        messages = [m for m in messages if m.get("resource_uuid") == resource_id]
    if resource_type:
        rt = resource_type.upper()
        messages = [m for m in messages if m.get("resource_type") == rt]
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


@volume_message.command("show")
@click.argument("message_id", callback=validate_id)
@output_options
@click.pass_context
def volume_message_show(ctx: click.Context, message_id: str,
                        output_format: str, columns: tuple[str, ...],
                        fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show a Cinder error message."""
    m = VolumeService(ctx.find_object(OrcaContext).ensure_client()).get_message(message_id)
    fields = [(k, str(m.get(k, "") or "")) for k in
              ["id", "resource_type", "resource_uuid", "event_id",
               "user_message", "message_level", "created_at", "expires_at"]]
    print_detail(fields, output_format=output_format, fit_width=fit_width,
                 max_width=max_width, noindent=noindent, columns=columns)


@volume_message.command("delete")
@click.argument("message_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def volume_message_delete(ctx: click.Context, message_id: str, yes: bool) -> None:
    """Delete a Cinder error message."""
    if not yes:
        click.confirm(f"Delete message {message_id}?", abort=True)
    VolumeService(ctx.find_object(OrcaContext).ensure_client()).delete_message(message_id)
    console.print(f"[green]Message {message_id} deleted.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  volume attachments (Cinder v3 attachment API)
# ══════════════════════════════════════════════════════════════════════════


@volume_attachment.command("list")
@click.option("--volume-id", "vol_filter", default=None,
              help="Filter by volume ID.")
@output_options
@click.pass_context
def volume_attachment_list(ctx: click.Context, vol_filter: str | None,
                           output_format: str, columns: tuple[str, ...],
                           fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List volume attachments (Cinder v3 attachment API)."""
    params = {"volume_id": vol_filter} if vol_filter else None
    attachments = VolumeService(ctx.find_object(OrcaContext).ensure_client()).find_attachments(params=params)
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


@volume_attachment.command("show")
@click.argument("attachment_id", callback=validate_id)
@output_options
@click.pass_context
def volume_attachment_show(ctx: click.Context, attachment_id: str,
                           output_format: str, columns: tuple[str, ...],
                           fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show a volume attachment."""
    a = VolumeService(ctx.find_object(OrcaContext).ensure_client()).get_attachment(attachment_id)
    fields = [(k, str(a.get(k, "") or "")) for k in
              ["id", "volume_id", "instance_uuid", "status",
               "attach_mode", "attached_at", "detached_at"]]
    if a.get("connection_info"):
        fields.append(("Connection Info", str(a["connection_info"])))
    print_detail(fields, output_format=output_format, fit_width=fit_width,
                 max_width=max_width, noindent=noindent, columns=columns)


@volume_attachment.command("delete")
@click.argument("attachment_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def volume_attachment_delete(ctx: click.Context, attachment_id: str, yes: bool) -> None:
    """Delete a volume attachment."""
    if not yes:
        click.confirm(f"Delete attachment {attachment_id}?", abort=True)
    VolumeService(ctx.find_object(OrcaContext).ensure_client()).delete_attachment(attachment_id)
    console.print(f"[green]Attachment {attachment_id} deleted.[/green]")


@volume_attachment.command("create")
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
    service = VolumeService(ctx.find_object(OrcaContext).ensure_client())
    body: dict = {
        "volume_id": volume_id,
        "instance_uuid": instance_id,
        "attach_mode": attach_mode,
    }
    if connector_json:
        try:
            body["connector"] = _json.loads(connector_json)
        except _json.JSONDecodeError as exc:
            raise click.BadParameter(f"Invalid JSON: {exc}", param_hint="--connector") from exc
    a = service.create_attachment(body)
    print_detail(
        [(k, str(a.get(k, "") or "")) for k in
         ("id", "volume_id", "instance_uuid", "status", "attach_mode", "attached_at")],
        output_format=output_format, columns=columns,
        fit_width=fit_width, max_width=max_width, noindent=noindent,
    )


@volume_attachment.command("set")
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
    service = VolumeService(ctx.find_object(OrcaContext).ensure_client())
    try:
        connector = _json.loads(connector_json)
    except _json.JSONDecodeError as exc:
        raise click.BadParameter(f"Invalid JSON: {exc}", param_hint="--connector") from exc
    a = service.update_attachment(attachment_id, {"connector": connector})
    if a:
        print_detail(
            [(k, str(a.get(k, "") or "")) for k in
             ("id", "volume_id", "instance_uuid", "status", "attach_mode")],
            output_format=output_format, columns=columns,
            fit_width=fit_width, max_width=max_width, noindent=noindent,
        )
    else:
        console.print(f"[green]Attachment {attachment_id} updated.[/green]")


@volume_attachment.command("complete")
@click.argument("attachment_id", callback=validate_id)
@click.pass_context
def volume_attachment_complete(ctx: click.Context, attachment_id: str) -> None:
    """Mark a volume attachment as complete (os-complete action)."""
    VolumeService(ctx.find_object(OrcaContext).ensure_client()).complete_attachment(attachment_id)
    console.print(f"[green]Attachment {attachment_id} marked as complete.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  volume groups (Cinder consistency groups v3)
# ══════════════════════════════════════════════════════════════════════════


@volume_group.command("list")
@output_options
@click.pass_context
def volume_group_list(ctx: click.Context, output_format: str, columns: tuple[str, ...],
                      fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List volume groups."""
    groups = VolumeService(ctx.find_object(OrcaContext).ensure_client()).find_groups()
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


@volume_group.command("show")
@click.argument("group_id", callback=validate_id)
@output_options
@click.pass_context
def volume_group_show(ctx: click.Context, group_id: str,
                      output_format: str, columns: tuple[str, ...],
                      fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show a volume group."""
    g = VolumeService(ctx.find_object(OrcaContext).ensure_client()).get_group(group_id)
    fields = [(k, str(g.get(k, "") or "")) for k in
              ["id", "name", "status", "group_type",
               "volume_types", "availability_zone",
               "description", "created_at"]]
    print_detail(fields, output_format=output_format, fit_width=fit_width,
                 max_width=max_width, noindent=noindent, columns=columns)


@volume_group.command("create")
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
    service = VolumeService(ctx.find_object(OrcaContext).ensure_client())
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
    g = service.create_group(body)
    console.print(f"[green]Group '{g.get('name', name)}' ({g.get('id')}) created.[/green]")


@volume_group.command("update")
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
    service = VolumeService(ctx.find_object(OrcaContext).ensure_client())
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
    service.update_group(group_id, body)
    console.print(f"[green]Group {group_id} updated.[/green]")


@volume_group.command("delete")
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
    VolumeService(ctx.find_object(OrcaContext).ensure_client()).delete_group(group_id, delete_volumes=delete_volumes)
    console.print(f"[green]Group {group_id} deletion started.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  volume group-snapshot (Cinder v3)
# ══════════════════════════════════════════════════════════════════════════

@volume_group_snapshot.command("list")
@output_options
@click.pass_context
def volume_group_snapshot_list(ctx: click.Context, output_format: str,
                               columns: tuple[str, ...], fit_width: bool,
                               max_width: int | None, noindent: bool) -> None:
    """List volume group snapshots."""
    gs = VolumeService(ctx.find_object(OrcaContext).ensure_client()).find_group_snapshots()
    print_list(
        gs,
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


@volume_group_snapshot.command("show")
@click.argument("group_snapshot_id", callback=validate_id)
@output_options
@click.pass_context
def volume_group_snapshot_show(ctx: click.Context, group_snapshot_id: str,
                               output_format: str, columns: tuple[str, ...],
                               fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show a volume group snapshot."""
    gs = VolumeService(ctx.find_object(OrcaContext).ensure_client()).get_group_snapshot(group_snapshot_id)
    print_detail(
        [(k, str(gs.get(k, "") or "")) for k in
         ("id", "name", "status", "group_id", "group_type_id",
          "description", "created_at")],
        output_format=output_format, columns=columns,
        fit_width=fit_width, max_width=max_width, noindent=noindent,
    )


@volume_group_snapshot.command("create")
@click.argument("group_id", callback=validate_id)
@click.option("--name", default=None, help="Snapshot name.")
@click.option("--description", default=None, help="Snapshot description.")
@click.pass_context
def volume_group_snapshot_create(ctx: click.Context, group_id: str,
                                 name: str | None, description: str | None) -> None:
    """Create a snapshot of a volume group."""
    service = VolumeService(ctx.find_object(OrcaContext).ensure_client())
    body: dict = {"group_id": group_id}
    if name:
        body["name"] = name
    if description:
        body["description"] = description
    gs = service.create_group_snapshot(body)
    console.print(
        f"[green]Group snapshot '{gs.get('name', '')}' ({gs.get('id')}) created.[/green]"
    )


@volume_group_snapshot.command("delete")
@click.argument("group_snapshot_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def volume_group_snapshot_delete(ctx: click.Context, group_snapshot_id: str,
                                 yes: bool) -> None:
    """Delete a volume group snapshot."""
    if not yes:
        click.confirm(f"Delete group snapshot {group_snapshot_id}?", abort=True)
    VolumeService(ctx.find_object(OrcaContext).ensure_client()).delete_group_snapshot(group_snapshot_id)
    console.print(f"[green]Group snapshot {group_snapshot_id} deleted.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  volume group-type (Cinder v3)
# ══════════════════════════════════════════════════════════════════════════

@volume_group_type.command("list")
@output_options
@click.pass_context
def volume_group_type_list(ctx: click.Context, output_format: str,
                           columns: tuple[str, ...], fit_width: bool,
                           max_width: int | None, noindent: bool) -> None:
    """List volume group types."""
    gt = VolumeService(ctx.find_object(OrcaContext).ensure_client()).find_group_types()
    print_list(
        gt,
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


@volume_group_type.command("show")
@click.argument("group_type_id")
@output_options
@click.pass_context
def volume_group_type_show(ctx: click.Context, group_type_id: str,
                           output_format: str, columns: tuple[str, ...],
                           fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show a volume group type."""
    gt = VolumeService(ctx.find_object(OrcaContext).ensure_client()).get_group_type(group_type_id)
    print_detail(
        [(k, str(gt.get(k, "") or "")) for k in
         ("id", "name", "is_public", "description")],
        output_format=output_format, columns=columns,
        fit_width=fit_width, max_width=max_width, noindent=noindent,
    )


@volume_group_type.command("create")
@click.argument("name")
@click.option("--description", default=None, help="Group type description.")
@click.option("--public/--private", default=True, help="Public or private group type.")
@click.pass_context
def volume_group_type_create(ctx: click.Context, name: str,
                             description: str | None, public: bool) -> None:
    """Create a volume group type."""
    service = VolumeService(ctx.find_object(OrcaContext).ensure_client())
    body: dict = {"name": name, "is_public": public}
    if description:
        body["description"] = description
    gt = service.create_group_type(body)
    console.print(f"[green]Group type '{gt.get('name')}' ({gt.get('id')}) created.[/green]")


@volume_group_type.command("set")
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
    service = VolumeService(client)
    body: dict = {}
    if name is not None:
        body["name"] = name
    if description is not None:
        body["description"] = description
    if public is not None:
        body["is_public"] = public
    if body:
        service.update_group_type(group_type_id, body)
    if properties:
        specs: dict = {}
        for p in properties:
            if "=" not in p:
                raise OrcaCLIError(f"Invalid format '{p}', expected KEY=VALUE.")
            k, v = p.split("=", 1)
            specs[k] = v
        service.set_group_specs(group_type_id, specs)
    if not body and not properties:
        console.print("[yellow]Nothing to update.[/yellow]")
        return
    console.print(f"[green]Group type {group_type_id} updated.[/green]")


@volume_group_type.command("unset")
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
    service = VolumeService(ctx.find_object(OrcaContext).ensure_client())
    for key in properties:
        service.unset_group_spec(group_type_id, key)
    console.print(f"[green]Group type {group_type_id} properties removed.[/green]")


@volume_group_type.command("delete")
@click.argument("group_type_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def volume_group_type_delete(ctx: click.Context, group_type_id: str, yes: bool) -> None:
    """Delete a volume group type."""
    if not yes:
        click.confirm(f"Delete group type {group_type_id}?", abort=True)
    VolumeService(ctx.find_object(OrcaContext).ensure_client()).delete_group_type(group_type_id)
    console.print(f"[green]Group type {group_type_id} deleted.[/green]")


# ── Deprecated aliases (ADR-0008) ─────────────────────────────────────────
#
# Each former hyphenated subcommand is re-exposed under its old name
# so existing scripts keep working. Marked ``deprecated`` in --help and
# emit a stderr warning. Targeted for removal in v2.0.



@volume.group("pool")
def volume_pool() -> None:
    """Inspect Cinder scheduler backend pools (admin)."""


@volume_pool.command("list")
@click.option("--detail", is_flag=True, default=False,
              help="Include detailed capabilities per pool.")
@output_options
@click.pass_context
def volume_pool_list(ctx: click.Context, detail,
                      output_format, columns, fit_width, max_width, noindent):
    """List Cinder scheduler backend pools."""
    svc = VolumeService(ctx.find_object(OrcaContext).ensure_client())
    pools = svc.find_pools(detail=detail)
    if not pools:
        console.print("No backend pools found.")
        return
    col_defs: list[tuple] = [("Name", "name")]
    if detail:
        col_defs += [
            ("Total (GB)",
             lambda p: p.get("capabilities", {}).get("total_capacity_gb", "")),
            ("Free (GB)",
             lambda p: p.get("capabilities", {}).get("free_capacity_gb", "")),
            ("Backend",
             lambda p: p.get("capabilities", {}).get("volume_backend_name", "")),
        ]
    print_list(pools, col_defs, title="Cinder Backend Pools",
               output_format=output_format, columns=columns,
               fit_width=fit_width, max_width=max_width, noindent=noindent)


@volume.group("host")
def volume_host() -> None:
    """Inspect Cinder hosts (admin)."""


@volume_host.command("list")
@click.option("--zone", default=None, help="Filter by availability zone.")
@output_options
@click.pass_context
def volume_host_list(ctx: click.Context, zone,
                      output_format, columns, fit_width, max_width, noindent):
    """List Cinder hosts."""
    svc = VolumeService(ctx.find_object(OrcaContext).ensure_client())
    hosts = svc.find_hosts(zone=zone)
    if not hosts:
        console.print("No hosts found.")
        return
    print_list(
        hosts,
        [("Host", "host_name"), ("Service", "service"),
         ("Zone", "zone")],
        title="Cinder Hosts",
        output_format=output_format, columns=columns,
        fit_width=fit_width, max_width=max_width, noindent=noindent,
    )
