"""``orca image`` — manage images (Glance v2)."""

from __future__ import annotations

import json as _json
import re
from pathlib import Path
from typing import Any

import click
from rich.progress import BarColumn, DownloadColumn, Progress, TimeRemainingColumn, TransferSpeedColumn
from rich.table import Table

from orca_cli.core.client import APIError, AuthenticationError
from orca_cli.core.context import OrcaContext
from orca_cli.core.exceptions import OrcaCLIError, PermissionDeniedError
from orca_cli.core.output import console, output_options, print_detail, print_list
from orca_cli.core.validators import safe_output_path
from orca_cli.models.image import Image
from orca_cli.services.image import ImageService
from orca_cli.services.server import ServerService

CHUNK_SIZE = 64 * 1024  # 64 KB

# Glance image-property key constraints (matches Glance schema validation).
_PROPERTY_KEY_RE = re.compile(r"^[A-Za-z0-9_:.\-]{1,255}$")

# Standard top-level Glance v2 image fields. Anything else returned by the
# API is treated as a custom image property by ``image show``.
_STANDARD_IMAGE_FIELDS: frozenset[str] = frozenset({
    "id", "name", "status", "visibility", "owner", "protected",
    "disk_format", "container_format", "size", "virtual_size",
    "min_disk", "min_ram",
    "checksum", "os_hash_algo", "os_hash_value",
    "direct_url", "stores", "file", "locations", "self", "schema",
    "created_at", "updated_at",
    "tags", "image_type",
    "os_hidden", "hidden",
})


def _validate_property_key(key: str) -> str:
    """Reject malformed property keys before any HTTP round-trip."""
    if not _PROPERTY_KEY_RE.match(key):
        raise click.BadParameter(
            f"invalid property key {key!r}: must match [A-Za-z0-9_:.-]{{1,255}}",
        )
    return key


def _parse_property(_ctx: click.Context, _param: click.Parameter,
                    values: tuple[str, ...]) -> tuple[tuple[str, str], ...]:
    """Click callback for ``--property KEY=VALUE`` (repeatable).

    Splits on the first ``=`` so values may themselves contain ``=``.
    """
    parsed: list[tuple[str, str]] = []
    for raw in values:
        if "=" not in raw:
            raise click.BadParameter(
                f"property must be in KEY=VALUE form (got {raw!r})",
            )
        key, val = raw.split("=", 1)
        _validate_property_key(key)
        parsed.append((key, val))
    return tuple(parsed)


def _parse_remove_property(_ctx: click.Context, _param: click.Parameter,
                           values: tuple[str, ...]) -> tuple[str, ...]:
    """Click callback for ``--remove-property KEY`` (repeatable)."""
    return tuple(_validate_property_key(k) for k in values)


@click.group()
@click.pass_context
def image(ctx: click.Context) -> None:
    """Manage images."""
    pass


@image.command("list")
@output_options
@click.pass_context
def image_list(ctx: click.Context, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List available images."""
    service = ImageService(ctx.find_object(OrcaContext).ensure_client())
    images = sorted(service.find(), key=lambda x: x.get("name", ""))

    column_defs = [
        ("ID", "id", {"style": "cyan", "no_wrap": True}),
        ("Name", "name", {"style": "bold"}),
        ("Status", "status", {"style": "green"}),
        ("Min Disk (GB)", "min_disk", {"justify": "right"}),
        ("Min RAM (MB)", "min_ram", {"justify": "right"}),
        ("Size (MB)", lambda img: str(round(img["size"] / 1024 / 1024)) if img.get("size") else "", {"justify": "right"}),
    ]

    print_list(
        images,
        column_defs,
        title="Images",
        output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent,
        columns=columns,
        empty_msg="No images found.",
    )


@image.command("show")
@click.argument("image_id")
@output_options
@click.pass_context
def image_show(ctx: click.Context, image_id: str, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show image details, including custom properties and integrity hashes.

    \b
    Custom properties (anything outside the Glance v2 standard schema, e.g.
    os_distro, os_version, hw_qemu_guest_agent) are surfaced separately:
      table  →  rendered as a "Properties" sub-table after the main table
      json   →  nested under a top-level "properties" key
      value  →  printed after the standard fields, one ``KEY VALUE`` per line
    """
    img = ImageService(ctx.find_object(OrcaContext).ensure_client()).get(image_id)

    standard_keys = [
        "id", "name", "status", "visibility", "owner", "protected",
        "min_disk", "min_ram", "size", "disk_format", "container_format",
        "checksum", "os_hash_algo", "os_hash_value", "direct_url",
        "tags", "created_at", "updated_at",
    ]

    # Pretty-printed view used by the ``table`` and ``value`` formats.
    fields: list[tuple[str, Any]] = []
    for key in standard_keys:
        raw: Any = img.get(key, "")
        if key == "size" and raw:
            fields.append((key, f"{round(int(raw) / 1024 / 1024)} MB"))
        elif key == "tags" and isinstance(raw, list):
            fields.append((key, ", ".join(raw)))
        else:
            fields.append((key, str(raw) if raw != "" else ""))

    # Anything Glance returns that isn't part of the standard schema is a
    # custom image property (os_distro, hw_*, cinder_img_volume_type, …).
    properties = {k: v for k, v in img.items() if k not in _STANDARD_IMAGE_FIELDS}

    if output_format == "json":
        # Preserve raw types from Glance (size as int, tags as list, …) so
        # JSON consumers can do arithmetic/jq filtering without re-parsing.
        data: dict[str, Any] = {k: img.get(k) for k in standard_keys if k in img}
        # Dual-render: every custom property is also exposed at the top level,
        # mirroring the raw Glance response shape. This preserves backward
        # compatibility with scripts doing `jq .os_distro` while the new
        # `.properties` aggregate offers a stable, sorted, schema-distinct view.
        for k, v in properties.items():
            data[k] = v
        if columns:
            wanted = {c.lower() for c in columns}
            data = {k: v for k, v in data.items() if k.lower() in wanted}
        # `properties` is always emitted, even when --column filters narrow
        # the standard fields — the brief requires it always be surfaced.
        data["properties"] = {k: properties[k] for k in sorted(properties)}
        click.echo(_json.dumps(data, default=str, indent=None if noindent else 2))
        return

    if output_format == "value":
        display = fields
        if columns:
            wanted = {c.lower() for c in columns}
            display = [(f, v) for f, v in display if f.lower() in wanted]
        for _, value in display:
            click.echo(value if value is not None else "")
        for k in sorted(properties):
            click.echo(f"{k} {properties[k]}")
        return

    # table
    print_detail(fields, output_format=output_format, fit_width=fit_width,
                 max_width=max_width, noindent=noindent, columns=columns)
    if properties:
        prop_table = Table(title="Properties", show_header=True, show_lines=False)
        prop_table.add_column("Key", style="bold cyan", no_wrap=True)
        col_kw: dict[str, Any] = {}
        if fit_width or max_width is not None:
            col_kw["overflow"] = "fold"
        prop_table.add_column("Value", **col_kw)
        for k in sorted(properties):
            prop_table.add_row(k, str(properties[k]))
        console.print(prop_table)


@image.command("create")
@click.argument("name")
@click.option("--disk-format", type=click.Choice(["raw", "qcow2", "vmdk", "vdi", "vhd", "vhdx", "iso", "aki", "ari", "ami"], case_sensitive=False), default="qcow2", show_default=True, help="Disk format.")
@click.option("--container-format", type=click.Choice(["bare", "ovf", "ova", "aki", "ari", "ami", "docker"], case_sensitive=False), default="bare", show_default=True, help="Container format.")
@click.option("--min-disk", type=int, default=0, show_default=True, help="Min disk (GB).")
@click.option("--min-ram", type=int, default=0, show_default=True, help="Min RAM (MB).")
@click.option("--visibility", type=click.Choice(["private", "shared", "community", "public"], case_sensitive=False), default="private", show_default=True, help="Visibility.")
@click.option("--file", "file_path", type=click.Path(exists=True), default=None, help="Upload image data from file immediately.")
@click.option("--property", "properties", multiple=True, callback=_parse_property,
              metavar="KEY=VALUE",
              help="Custom image property to set on creation (e.g. os_distro=ubuntu). "
                   "Repeatable. Values may contain '='; only the first '=' splits.")
@click.pass_context
def image_create(ctx: click.Context, name: str, disk_format: str, container_format: str,
                 min_disk: int, min_ram: int, visibility: str, file_path: str | None,
                 properties: tuple[tuple[str, str], ...]) -> None:
    """Create a new image (and optionally upload data).

    \b
    Examples:
      orca image create my-image
      orca image create my-image --file ubuntu.qcow2
      orca image create my-image --disk-format raw --file disk.img
      orca image create my-image --property os_distro=ubuntu \\
                                 --property os_version=24.04 \\
                                 --property hw_qemu_guest_agent=yes
    """
    service = ImageService(ctx.find_object(OrcaContext).ensure_client())
    body: dict[str, Any] = {
        "name": name,
        "disk_format": disk_format,
        "container_format": container_format,
        "min_disk": min_disk,
        "min_ram": min_ram,
        "visibility": visibility,
    }
    # Glance v2 takes custom properties as top-level keys on the create body.
    for k, v in properties:
        body[k] = v
    img = service.create(body)
    image_id = img.get("id", "")
    console.print(f"[green]Image '{name}' created: {image_id}[/green]")
    console.print(f"  Status: {img.get('status', '')}")

    if file_path:
        p = Path(file_path)
        total = p.stat().st_size
        console.print(f"  Uploading {file_path} ({total / 1024 / 1024:.1f} MB) ...")
        with open(p, "rb") as f:
            service.upload(image_id, stream=f)
        console.print("  [green]Upload complete.[/green]")


@image.command("update")
@click.argument("image_id")
@click.option("--name", default=None, help="New name.")
@click.option("--min-disk", type=int, default=None, help="New min disk (GB).")
@click.option("--min-ram", type=int, default=None, help="New min RAM (MB).")
@click.option("--visibility", type=click.Choice(["private", "shared", "community", "public"], case_sensitive=False), default=None, help="New visibility.")
@click.option("--property", "properties", multiple=True, callback=_parse_property,
              metavar="KEY=VALUE",
              help="Set or replace a custom image property (KEY=VALUE). "
                   "Repeatable. Untouched properties are preserved.")
@click.option("--remove-property", "remove_properties", multiple=True,
              callback=_parse_remove_property, metavar="KEY",
              help="Remove a custom image property by key. Repeatable. "
                   "Errors if the key is absent (use --ignore-missing for idempotent runs).")
@click.option("--ignore-missing", is_flag=True, default=False,
              help="With --remove-property: silently skip keys that aren't on the image.")
@click.pass_context
def image_update(ctx: click.Context, image_id: str, name: str | None,
                 min_disk: int | None, min_ram: int | None, visibility: str | None,
                 properties: tuple[tuple[str, str], ...],
                 remove_properties: tuple[str, ...],
                 ignore_missing: bool) -> None:
    """Update image properties (JSON-Patch).

    Builds one atomic JSON-Patch document from all flags. ``--property`` emits
    ``add`` when the key is absent and ``replace`` when it already exists, so
    untouched properties survive. ``--remove-property`` is strict by default
    and turns idempotent under ``--ignore-missing``.

    \b
    Examples:
      orca image update <id> --name new-name
      orca image update <id> --visibility shared
      orca image update <id> --property os_distro=ubuntu --property os_version=24.04
      orca image update <id> --remove-property hw_qemu_guest_agent
      orca image update <id> --remove-property foo --ignore-missing
    """
    service = ImageService(ctx.find_object(OrcaContext).ensure_client())

    ops: list[dict[str, Any]] = []
    if name is not None:
        ops.append({"op": "replace", "path": "/name", "value": name})
    if min_disk is not None:
        ops.append({"op": "replace", "path": "/min_disk", "value": min_disk})
    if min_ram is not None:
        ops.append({"op": "replace", "path": "/min_ram", "value": min_ram})
    if visibility is not None:
        ops.append({"op": "replace", "path": "/visibility", "value": visibility})

    # Need the current state to choose add-vs-replace and to validate removes.
    if properties or remove_properties:
        current = service.get(image_id)
        for k, v in properties:
            op = "replace" if k in current else "add"
            ops.append({"op": op, "path": f"/{k}", "value": v})
        for k in remove_properties:
            if k not in current:
                if ignore_missing:
                    continue
                raise OrcaCLIError(
                    f"cannot remove property '{k}': not present on image "
                    f"{image_id}. Use --ignore-missing for idempotent removal.",
                )
            ops.append({"op": "remove", "path": f"/{k}"})

    if not ops:
        console.print(
            "[yellow]No changes requested. Use --name, --min-disk, --min-ram, "
            "--visibility, --property, or --remove-property.[/yellow]",
        )
        return

    data = service.update(image_id, ops)
    console.print(f"[green]Image {image_id} updated.[/green]")
    if data:
        console.print(f"  Name: {data.get('name', '')}")
        console.print(f"  Status: {data.get('status', '')}")


def _stream_with_progress(client, *, url: str, path: Path, description: str) -> None:
    """Stream ``path`` to ``url`` via PUT with a progress bar and error mapping.

    Uses the raw httpx client because the Glance upload/stage endpoints
    need a live generator for the progress bar — ``put_stream`` consumes
    the file object straight-through without yielding progress events.
    """
    total = path.stat().st_size
    headers = client._headers()
    headers["Content-Type"] = "application/octet-stream"
    headers["Content-Length"] = str(total)

    with Progress(
        "[cyan]{task.description}",
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(description, total=total)

        def _iter(f, chunk_size=256 * 1024):
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                progress.advance(task, len(chunk))
                yield chunk

        with open(path, "rb") as f:
            resp = client._http.put(url, headers=headers, content=_iter(f))

    if resp.status_code == 401:
        raise AuthenticationError()
    if resp.status_code == 403:
        raise PermissionDeniedError()
    if not resp.is_success:
        raise APIError(resp.status_code, resp.text[:300])


@image.command("upload")
@click.argument("image_id")
@click.argument("file_path", type=click.Path(exists=True))
@click.pass_context
def image_upload(ctx: click.Context, image_id: str, file_path: str) -> None:
    """Upload image data from a local file.

    \b
    The image must already exist and be in 'queued' status.
    Supports large files — streams from disk without loading into memory.
    Examples:
      orca image upload <id> /path/to/ubuntu.qcow2
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    service = ImageService(client)
    p = Path(file_path)
    _stream_with_progress(client, url=service.upload_url(image_id), path=p,
                          description=f"Uploading {p.name}")
    console.print("[green]Upload complete.[/green]")


@image.command("stage")
@click.argument("image_id")
@click.argument("file_path", type=click.Path(exists=True))
@click.pass_context
def image_stage(ctx: click.Context, image_id: str, file_path: str) -> None:
    """Upload image data to the staging area (interruptible import).

    Uploads binary data to /v2/images/{id}/stage without activating the image.
    After staging, run:

    \b
      orca image import <id> --method glance-direct

    to complete the import. Requires Glance ≥ 16.0 (Queens) and API v2.6+.

    \b
    Example:
      orca image stage <id> /path/to/ubuntu.qcow2
      orca image import <id> --method glance-direct
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    service = ImageService(client)
    p = Path(file_path)
    _stream_with_progress(client, url=service.stage_url(image_id), path=p,
                          description=f"Staging {p.name}")
    console.print(f"[green]Staging complete for image {image_id}.[/green]")
    console.print(f"[dim]Run: orca image import {image_id} --method glance-direct[/dim]")


@image.command("download")
@click.argument("image_id")
@click.option("--output", "-o", "output_path", required=True, type=click.Path(), help="Output file path.")
@click.pass_context
def image_download(ctx: click.Context, image_id: str, output_path: str) -> None:
    """Download image data to a local file.

    \b
    Supports large files — streams to disk without loading into memory.
    Examples:
      orca image download <id> -o /tmp/my-image.qcow2
    """
    service = ImageService(ctx.find_object(OrcaContext).ensure_client())

    meta = service.get(image_id)
    total = meta.get("size") or 0
    name = meta.get("name", image_id)
    console.print(f"Downloading '{name}' ({total / 1024 / 1024:.1f} MB) ...")

    out = safe_output_path(output_path)

    with service.stream_download(image_id) as resp:
        if resp.status_code == 204:
            console.print("[yellow]No image data available.[/yellow]")
            return
        if resp.status_code == 401:
            raise AuthenticationError()
        if resp.status_code == 403:
            raise PermissionDeniedError()
        if not resp.is_success:
            raise APIError(resp.status_code, resp.text[:300] if hasattr(resp, 'text') else "Download failed")

        with open(out, "wb") as f, Progress(
            "[cyan]{task.description}",
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Downloading", total=total or None)
            for chunk in resp.iter_bytes(chunk_size=CHUNK_SIZE):
                f.write(chunk)
                progress.advance(task, len(chunk))

    console.print(f"[green]Saved to {out}.[/green]")


@image.command("deactivate")
@click.argument("image_id")
@click.pass_context
def image_deactivate(ctx: click.Context, image_id: str) -> None:
    """Deactivate an image (make data unavailable)."""
    ImageService(ctx.find_object(OrcaContext).ensure_client()).deactivate(image_id)
    console.print(f"[green]Image {image_id} deactivated.[/green]")


@image.command("reactivate")
@click.argument("image_id")
@click.pass_context
def image_reactivate(ctx: click.Context, image_id: str) -> None:
    """Reactivate a deactivated image."""
    ImageService(ctx.find_object(OrcaContext).ensure_client()).reactivate(image_id)
    console.print(f"[green]Image {image_id} reactivated.[/green]")


@image.command("tag-add")
@click.argument("image_id")
@click.argument("tag")
@click.pass_context
def image_tag_add(ctx: click.Context, image_id: str, tag: str) -> None:
    """Add a tag to an image."""
    ImageService(ctx.find_object(OrcaContext).ensure_client()).add_tag(image_id, tag)
    console.print(f"[green]Tag '{tag}' added to image {image_id}.[/green]")


@image.command("tag-delete")
@click.argument("image_id")
@click.argument("tag")
@click.pass_context
def image_tag_delete(ctx: click.Context, image_id: str, tag: str) -> None:
    """Remove a tag from an image."""
    ImageService(ctx.find_object(OrcaContext).ensure_client()).delete_tag(image_id, tag)
    console.print(f"[green]Tag '{tag}' removed from image {image_id}.[/green]")


@image.command("delete")
@click.argument("image_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def image_delete(ctx: click.Context, image_id: str, yes: bool) -> None:
    """Delete an image."""
    if not yes:
        click.confirm(f"Delete image {image_id}?", abort=True)

    ImageService(ctx.find_object(OrcaContext).ensure_client()).delete(image_id)
    console.print(f"[green]Image {image_id} deleted.[/green]")


# ── Maintenance commands ────────────────────────────────────────────────


def _human_size(size: int | None) -> str:
    """Format bytes as human-readable."""
    if not size:
        return "—"
    n: float = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


@image.command("shrink")
@click.argument("image_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def image_shrink(ctx: click.Context, image_id: str, yes: bool) -> None:
    """Convert a raw image to qcow2 with compression to save space.

    Downloads the image, converts it locally via ``qemu-img convert``,
    then uploads the compressed result as a new image. The original is
    deactivated (not deleted) so you can verify before removing it.

    Requires ``qemu-img`` to be installed locally.

    \b
    Examples:
      orca image shrink <image-id>
      orca image shrink <image-id> -y
    """
    import shutil
    import subprocess
    import tempfile

    # Check qemu-img availability
    if not shutil.which("qemu-img"):
        console.print("[red]Error: qemu-img not found. Install qemu-utils (apt) or qemu (brew).[/red]")
        raise SystemExit(1)

    client = ctx.find_object(OrcaContext).ensure_client()
    service = ImageService(client)

    meta = service.get(image_id)
    name = meta.get("name", image_id)
    fmt = meta.get("disk_format", "")
    status = meta.get("status", "")
    original_size = meta.get("size") or 0

    if status != "active":
        console.print(f"[red]Image is not active (status={status}). Cannot shrink.[/red]")
        raise SystemExit(1)

    if fmt != "raw":
        console.print(f"[yellow]Image format is '{fmt}', not raw. Shrink is most effective on raw images.[/yellow]")
        if not yes:
            click.confirm("Continue anyway?", abort=True)

    console.print(f"[bold]Image:[/bold] {name} ({image_id})")
    console.print(f"[bold]Format:[/bold] {fmt}  [bold]Size:[/bold] {_human_size(original_size)}")

    if not yes:
        click.confirm("\nDownload, convert to qcow2 (compressed), and re-upload?", abort=True)

    with tempfile.TemporaryDirectory(prefix="orca-shrink-") as tmpdir:
        raw_path = Path(tmpdir) / "original.img"
        qcow2_path = Path(tmpdir) / "compressed.qcow2"

        # Download
        console.print("\n[bold]1/3[/bold] Downloading image...")
        with service.stream_download(image_id) as resp:
            if not resp.is_success:
                raise APIError(resp.status_code, "Download failed")
            with open(raw_path, "wb") as f, Progress(
                "[cyan]{task.description}", BarColumn(), DownloadColumn(),
                TransferSpeedColumn(), TimeRemainingColumn(), console=console,
            ) as progress:
                task = progress.add_task("Downloading", total=original_size or None)
                for chunk in resp.iter_bytes(chunk_size=CHUNK_SIZE):
                    f.write(chunk)
                    progress.advance(task, len(chunk))

        # Convert
        console.print("[bold]2/3[/bold] Converting to qcow2 with compression...")
        result = subprocess.run(
            ["qemu-img", "convert", "-c", "-O", "qcow2", str(raw_path), str(qcow2_path)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            console.print(f"[red]qemu-img failed:[/red] {result.stderr.strip()}")
            raise SystemExit(1)

        new_size = qcow2_path.stat().st_size
        ratio = (1 - new_size / original_size) * 100 if original_size else 0
        console.print(f"  {_human_size(original_size)} → {_human_size(new_size)} ([green]{ratio:.1f}% smaller[/green])")

        # Upload as new image
        console.print("[bold]3/3[/bold] Uploading compressed image...")
        new_meta = service.create({
            "name": f"{name} (shrunk)",
            "disk_format": "qcow2",
            "container_format": meta.get("container_format", "bare"),
            "min_disk": meta.get("min_disk", 0),
            "min_ram": meta.get("min_ram", 0),
            "visibility": meta.get("visibility", "private"),
        })
        new_id = new_meta.get("id", "")

        with open(qcow2_path, "rb") as f:
            service.upload(new_id, stream=f)

    service.deactivate(image_id)

    console.print("\n[green]Done![/green]")
    console.print(f"  New image: {new_id} ('{name} (shrunk)')")
    console.print(f"  Original {image_id} has been deactivated (not deleted).")
    console.print(f"  Verify the new image, then run: [cyan]orca image delete {image_id} -y[/cyan]")


@image.command("unused")
@click.option("--delete", "-d", "do_delete", is_flag=True, default=False,
              help="Actually delete unused images.")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation (with --delete).")
@click.option("--include-snapshots", is_flag=True, default=False,
              help="Include snapshot images in the scan.")
@click.pass_context
def image_unused(ctx: click.Context, do_delete: bool, yes: bool, include_snapshots: bool) -> None:
    """Find images not used by any server instance.

    Cross-references Glance images with Nova servers to identify images
    that no running or stopped instance references. By default snapshots
    are excluded from the scan.

    \b
    Examples:
      orca image unused                     # dry-run
      orca image unused --delete            # interactive delete
      orca image unused --delete -y         # auto-confirm
      orca image unused --include-snapshots # include snapshot images
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    images_svc = ImageService(client)
    servers_svc = ServerService(client)

    with console.status("[bold]Scanning images and servers..."):
        images = images_svc.find()
        servers = servers_svc.find()

    # Collect image IDs in use by servers
    used_image_ids: set[str] = set()
    for srv in servers:
        ref = srv.get("image")
        if isinstance(ref, dict) and ref.get("id"):
            used_image_ids.add(ref["id"])
        elif isinstance(ref, str) and ref:
            used_image_ids.add(ref)

    # Filter unused images
    unused: list[Image] = []
    for img in images:
        if img.get("status") != "active":
            continue
        if img["id"] in used_image_ids:
            continue
        # Skip snapshots unless requested
        if not include_snapshots and img.get("image_type") == "snapshot":
            continue
        unused.append(img)

    if not unused:
        console.print("[green]All active images are in use by at least one server.[/green]")
        return

    from rich.table import Table

    table = Table(title=f"Unused Images ({len(unused)})", show_lines=False)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="bold")
    table.add_column("Format")
    table.add_column("Size", justify="right")
    table.add_column("Created")
    table.add_column("Visibility")

    total_size = 0
    for img in unused:
        sz = img.get("size") or 0
        total_size += sz
        table.add_row(
            img["id"],
            img.get("name", ""),
            img.get("disk_format", "?"),
            _human_size(sz),
            (img.get("created_at", "") or "")[:10],
            img.get("visibility", ""),
        )

    console.print()
    console.print(table)
    console.print(f"\n[bold]Total reclaimable:[/bold] {_human_size(total_size)}")

    if not do_delete:
        console.print(f"\n[yellow]{len(unused)} unused image(s). "
                       "Use --delete to remove them.[/yellow]\n")
        return

    if not yes:
        click.confirm(f"\nDelete {len(unused)} unused image(s)?", abort=True)

    deleted = 0
    errors = 0
    for img in unused:
        img_id = img["id"]
        img_name = img.get("name", "")
        try:
            images_svc.delete(img_id)
            console.print(f"  [green]Deleted[/green] {img_name} ({img_id})")
            deleted += 1
        except Exception as exc:
            console.print(f"  [red]Failed[/red] {img_name} ({img_id}): {exc}")
            errors += 1

    console.print(f"\n[green]{deleted} deleted[/green]", end="")
    if errors:
        console.print(f", [red]{errors} failed[/red]")
    else:
        console.print()
    console.print()


# ══════════════════════════════════════════════════════════════════════════
#  Image Member Sharing (Glance v2)
# ══════════════════════════════════════════════════════════════════════════

@image.command("member-list")
@click.argument("image_id")
@output_options
@click.pass_context
def image_member_list(ctx: click.Context, image_id: str, output_format: str,
                      columns: tuple[str, ...], fit_width: bool,
                      max_width: int | None, noindent: bool) -> None:
    """List all projects that have access to a shared image.

    The image must have visibility=shared.
    """
    members = ImageService(ctx.find_object(OrcaContext).ensure_client()).list_members(image_id)
    print_list(
        members,
        [
            ("Member ID (Project)", "member_id", {"style": "cyan"}),
            ("Status", "status", {"style": "green"}),
            ("Created", "created_at"),
            ("Updated", "updated_at"),
            ("Schema", "schema"),
        ],
        title=f"Members of image {image_id}",
        output_format=output_format, columns=columns,
        fit_width=fit_width, max_width=max_width, noindent=noindent,
        empty_msg="No members found. Make sure the image has visibility=shared.",
    )


@image.command("member-show")
@click.argument("image_id")
@click.argument("member_id", metavar="PROJECT_ID")
@output_options
@click.pass_context
def image_member_show(ctx: click.Context, image_id: str, member_id: str,
                      output_format: str, columns: tuple[str, ...],
                      fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show a specific project's membership status for a shared image."""
    m = ImageService(ctx.find_object(OrcaContext).ensure_client()).get_member(image_id, member_id)
    fields = [
        ("Image ID", m.get("image_id", image_id)),
        ("Member ID (Project)", m.get("member_id", member_id)),
        ("Status", m.get("status", "—")),
        ("Created", m.get("created_at", "—")),
        ("Updated", m.get("updated_at", "—")),
        ("Schema", m.get("schema", "—")),
    ]
    print_detail(fields, output_format=output_format, fit_width=fit_width,
                 max_width=max_width, noindent=noindent, columns=columns)


@image.command("member-create")
@click.argument("image_id")
@click.argument("member_id", metavar="PROJECT_ID")
@click.pass_context
def image_member_create(ctx: click.Context, image_id: str, member_id: str) -> None:
    """Share an image with a project (sets status to 'pending').

    The project must then run 'orca image member-set --status accepted'
    to confirm acceptance.

    \b
    Example:
      orca image member-create <image-id> <project-id>
    """
    m = ImageService(ctx.find_object(OrcaContext).ensure_client()).add_member(image_id, member_id)
    status = m.get("status", "pending") if isinstance(m, dict) else "pending"
    console.print(
        f"[green]Image {image_id} shared with project {member_id} (status: {status}).[/green]"
    )
    console.print(
        f"[dim]The project must run: orca image member-set {image_id} {member_id} --status accepted[/dim]"
    )


@image.command("member-delete")
@click.argument("image_id")
@click.argument("member_id", metavar="PROJECT_ID")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def image_member_delete(ctx: click.Context, image_id: str, member_id: str, yes: bool) -> None:
    """Revoke a project's access to a shared image."""
    if not yes:
        click.confirm(f"Revoke access of project {member_id} to image {image_id}?", abort=True)
    ImageService(ctx.find_object(OrcaContext).ensure_client()).delete_member(image_id, member_id)
    console.print(f"[green]Project {member_id} access to image {image_id} revoked.[/green]")


@image.command("member-set")
@click.argument("image_id")
@click.argument("member_id", metavar="PROJECT_ID")
@click.option(
    "--status", required=True,
    type=click.Choice(["accepted", "rejected", "pending"], case_sensitive=False),
    help="New membership status.",
)
@click.pass_context
def image_member_set(ctx: click.Context, image_id: str, member_id: str, status: str) -> None:
    """Accept, reject, or reset a shared image invitation.

    Run this as the receiving project to accept or reject sharing.

    \b
    Examples:
      orca image member-set <image-id> <project-id> --status accepted
      orca image member-set <image-id> <project-id> --status rejected
    """
    ImageService(ctx.find_object(OrcaContext).ensure_client()).set_member_status(
        image_id, member_id, status,
    )
    labels = {"accepted": "green", "rejected": "red", "pending": "yellow"}
    color = labels.get(status, "white")
    console.print(f"[{color}]Membership {image_id}/{member_id} set to '{status}'.[/{color}]")


@image.command("share-and-accept")
@click.argument("image_id")
@click.argument("member_id", metavar="PROJECT_ID")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def image_share_and_accept(ctx: click.Context, image_id: str, member_id: str, yes: bool) -> None:
    """Share an image with a project and immediately accept on their behalf (admin mode).

    Combines ``member-create`` + ``member-set --status accepted`` in one step.
    Requires admin credentials or the ability to act on behalf of both projects.

    \b
    Example:
      orca image share-and-accept <image-id> <project-id> --yes
    """
    if not yes:
        click.confirm(
            f"Share image {image_id} with project {member_id} and auto-accept?",
            abort=True,
        )
    service = ImageService(ctx.find_object(OrcaContext).ensure_client())

    service.add_member(image_id, member_id)
    console.print(f"[cyan]Step 1/2[/cyan] Image {image_id} shared with project {member_id}.")

    service.set_member_status(image_id, member_id, "accepted")
    console.print(
        f"[cyan]Step 2/2[/cyan] Membership accepted.\n"
        f"[bold green]Image {image_id} is now visible to project {member_id}.[/bold green]"
    )


# ══════════════════════════════════════════════════════════════════════════
#  image import  (Glance v2 import API)
# ══════════════════════════════════════════════════════════════════════════

@image.command("import")
@click.argument("image_id")
@click.option("--method", "import_method",
              type=click.Choice(["web-download", "glance-direct", "copy-image"]),
              default="web-download", show_default=True,
              help="Import method.")
@click.option("--uri", default=None,
              help="Source URI (required for web-download).")
@click.option("--store", "stores", multiple=True,
              help="Target store(s) for copy-image (repeatable).")
@click.pass_context
def image_import(ctx: click.Context, image_id: str, import_method: str,
                 uri: str | None, stores: tuple[str, ...]) -> None:
    """Import image data using the Glance v2 import API.

    \b
    Methods:
      web-download   Pull image from a public URI (requires --uri)
      glance-direct  Finalise an image whose binary was already staged
      copy-image     Copy image data across stores (requires --store)

    \b
    Examples:
      orca image import <id> --method web-download --uri https://example.com/image.img
      orca image import <id> --method glance-direct
      orca image import <id> --method copy-image --store ceph1 --store ceph2
    """
    if import_method == "web-download" and not uri:
        raise click.UsageError("--uri is required for web-download.")

    ImageService(ctx.find_object(OrcaContext).ensure_client()).import_(
        image_id, import_method, uri=uri, stores=list(stores) if stores else None,
    )
    console.print(f"[green]Import triggered for image {image_id} (method: {import_method}).[/green]")
    if import_method == "web-download":
        console.print(f"  URI: {uri}")
    console.print(f"\nUse [bold]orca image show {image_id}[/bold] to monitor status.\n")


# ══════════════════════════════════════════════════════════════════════════
#  image cache  (Glance v2 cache management — admin)
# ══════════════════════════════════════════════════════════════════════════

@image.command("cache-list")
@output_options
@click.pass_context
def image_cache_list(ctx: click.Context, output_format: str, columns: tuple[str, ...],
                     fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List cached and queued images (admin)."""
    data = ImageService(ctx.find_object(OrcaContext).ensure_client()).list_cache()

    cached = [dict(id=i, state="cached") for i in data.get("cached_images", [])]
    queued = [dict(id=i, state="queued") for i in data.get("queued_images", [])]
    items = cached + queued

    print_list(
        items,
        [
            ("Image ID", "id", {"style": "cyan", "no_wrap": True}),
            ("State", "state", {"style": "green"}),
        ],
        title="Image Cache",
        output_format=output_format, fit_width=fit_width, max_width=max_width,
        noindent=noindent, columns=columns,
        empty_msg="Cache is empty.",
    )


@image.command("cache-queue")
@click.argument("image_id")
@click.pass_context
def image_cache_queue(ctx: click.Context, image_id: str) -> None:
    """Queue an image for pre-caching (admin)."""
    ImageService(ctx.find_object(OrcaContext).ensure_client()).cache_queue(image_id)
    console.print(f"[green]Image {image_id} queued for caching.[/green]")


@image.command("cache-delete")
@click.argument("image_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def image_cache_delete(ctx: click.Context, image_id: str, yes: bool) -> None:
    """Remove a specific image from the cache (admin)."""
    if not yes:
        click.confirm(f"Remove image {image_id} from cache?", abort=True)
    ImageService(ctx.find_object(OrcaContext).ensure_client()).cache_delete(image_id)
    console.print(f"[green]Image {image_id} removed from cache.[/green]")


@image.command("cache-clear")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def image_cache_clear(ctx: click.Context, yes: bool) -> None:
    """Clear the entire image cache (admin)."""
    if not yes:
        click.confirm("Clear entire image cache?", abort=True)
    ImageService(ctx.find_object(OrcaContext).ensure_client()).cache_clear()
    console.print("[green]Image cache cleared.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  image stores-info  (Glance multi-backend)
# ══════════════════════════════════════════════════════════════════════════


@image.command("stores-info")
@click.option("--detail", is_flag=True, default=False,
              help="Show store properties (admin only, requires Glance ≥ 2.15).")
@output_options
@click.pass_context
def image_stores_info(ctx: click.Context, detail: bool, output_format: str,
                      columns: tuple[str, ...], fit_width: bool,
                      max_width: int | None, noindent: bool) -> None:
    """List available Glance storage backends (multi-store only).

    \b
    Example:
      orca image stores-info
      orca image stores-info --detail
    """
    stores = ImageService(ctx.find_object(OrcaContext).ensure_client()).list_stores(detail=detail)

    column_defs = [
        ("ID", "id", {"style": "cyan"}),
        ("Description", "description"),
        ("Default", lambda s: "yes" if s.get("is_default") else ""),
    ]
    if detail:
        column_defs.append(("Properties", lambda s: str(s.get("properties", ""))))

    print_list(
        stores,
        column_defs,
        title="Image Stores",
        output_format=output_format, fit_width=fit_width, max_width=max_width,
        noindent=noindent, columns=columns,
        empty_msg="No stores found (multi-backend may not be enabled).",
    )


# ══════════════════════════════════════════════════════════════════════════
#  image task-list / task-show  (Glance async tasks)
# ══════════════════════════════════════════════════════════════════════════


@image.command("task-list")
@click.option("--type", "task_type", default=None,
              type=click.Choice(["import", "export", "clone"], case_sensitive=False),
              help="Filter by task type.")
@click.option("--status", "task_status", default=None,
              type=click.Choice(["pending", "processing", "success", "failure"], case_sensitive=False),
              help="Filter by task status.")
@output_options
@click.pass_context
def image_task_list(ctx: click.Context, task_type: str | None, task_status: str | None,
                    output_format: str, columns: tuple[str, ...], fit_width: bool,
                    max_width: int | None, noindent: bool) -> None:
    """List Glance async tasks."""
    tasks = ImageService(ctx.find_object(OrcaContext).ensure_client()).list_tasks(
        task_type=task_type, status=task_status,
    )

    print_list(
        tasks,
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Type", "type"),
            ("Status", "status", {"style": "green"}),
            ("Owner", "owner_id", {"style": "dim"}),
            ("Created", "created_at"),
            ("Expires", "expires_at"),
        ],
        title="Image Tasks",
        output_format=output_format, fit_width=fit_width, max_width=max_width,
        noindent=noindent, columns=columns,
        empty_msg="No tasks found.",
    )


@image.command("task-show")
@click.argument("task_id")
@output_options
@click.pass_context
def image_task_show(ctx: click.Context, task_id: str, output_format: str,
                    columns: tuple[str, ...], fit_width: bool,
                    max_width: int | None, noindent: bool) -> None:
    """Show details of a Glance async task."""
    t = ImageService(ctx.find_object(OrcaContext).ensure_client()).get_task(task_id)
    fields = [
        ("ID", t.get("id", task_id)),
        ("Type", t.get("type", "—")),
        ("Status", t.get("status", "—")),
        ("Message", t.get("message", "—")),
        ("Owner", t.get("owner_id", "—")),
        ("Input", str(t.get("input", ""))),
        ("Result", str(t.get("result", ""))),
        ("Created", t.get("created_at", "—")),
        ("Updated", t.get("updated_at", "—")),
        ("Expires", t.get("expires_at", "—")),
    ]
    print_detail(fields, output_format=output_format, fit_width=fit_width,
                 max_width=max_width, noindent=noindent, columns=columns)
