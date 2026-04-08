"""``shark image`` — manage images (Glance v2)."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress, BarColumn, DownloadColumn, TransferSpeedColumn, TimeRemainingColumn
from rich.table import Table

from shark_cli.core.context import SharkContext
from shark_cli.core.client import AuthenticationError, APIError

console = Console()

CHUNK_SIZE = 64 * 1024  # 64 KB


@click.group()
@click.pass_context
def image(ctx: click.Context) -> None:
    """Manage images."""
    pass


@image.command("list")
@click.pass_context
def image_list(ctx: click.Context) -> None:
    """List available images."""
    client = ctx.find_object(SharkContext).ensure_client()
    url = f"{client.image_url}/v2/images"
    data = client.get(url)

    images = data.get("images", [])

    if not images:
        console.print("[yellow]No images found.[/yellow]")
        return

    table = Table(title="Images", show_lines=True)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="bold")
    table.add_column("Status", style="green")
    table.add_column("Min Disk (GB)", justify="right")
    table.add_column("Min RAM (MB)", justify="right")
    table.add_column("Size (MB)", justify="right")

    for img in sorted(images, key=lambda x: x.get("name", "")):
        size = img.get("size")
        size_mb = str(round(size / 1024 / 1024)) if size else ""
        table.add_row(
            img.get("id", ""),
            img.get("name", ""),
            img.get("status", ""),
            str(img.get("min_disk", "")),
            str(img.get("min_ram", "")),
            size_mb,
        )

    console.print(table)


@image.command("show")
@click.argument("image_id")
@click.pass_context
def image_show(ctx: click.Context, image_id: str) -> None:
    """Show image details."""
    client = ctx.find_object(SharkContext).ensure_client()
    url = f"{client.image_url}/v2/images/{image_id}"
    img = client.get(url)

    table = Table(title=f"Image {img.get('name', image_id)}", show_lines=True)
    table.add_column("Property", style="bold")
    table.add_column("Value")

    for key in ["id", "name", "status", "visibility", "os_distro", "os_version",
                "min_disk", "min_ram", "size", "disk_format", "container_format",
                "created_at", "updated_at"]:
        val = img.get(key, "")
        if key == "size" and val:
            val = f"{round(int(val) / 1024 / 1024)} MB"
        table.add_row(key, str(val))

    console.print(table)


@image.command("create")
@click.argument("name")
@click.option("--disk-format", type=click.Choice(["raw", "qcow2", "vmdk", "vdi", "vhd", "vhdx", "iso", "aki", "ari", "ami"], case_sensitive=False), default="qcow2", show_default=True, help="Disk format.")
@click.option("--container-format", type=click.Choice(["bare", "ovf", "ova", "aki", "ari", "ami", "docker"], case_sensitive=False), default="bare", show_default=True, help="Container format.")
@click.option("--min-disk", type=int, default=0, show_default=True, help="Min disk (GB).")
@click.option("--min-ram", type=int, default=0, show_default=True, help="Min RAM (MB).")
@click.option("--visibility", type=click.Choice(["private", "shared", "community", "public"], case_sensitive=False), default="private", show_default=True, help="Visibility.")
@click.option("--file", "file_path", type=click.Path(exists=True), default=None, help="Upload image data from file immediately.")
@click.pass_context
def image_create(ctx: click.Context, name: str, disk_format: str, container_format: str,
                 min_disk: int, min_ram: int, visibility: str, file_path: str | None) -> None:
    """Create a new image (and optionally upload data).

    \b
    Examples:
      shark image create my-image
      shark image create my-image --file ubuntu.qcow2
      shark image create my-image --disk-format raw --file disk.img
    """
    client = ctx.find_object(SharkContext).ensure_client()
    url = f"{client.image_url}/v2/images"
    body = {
        "name": name,
        "disk_format": disk_format,
        "container_format": container_format,
        "min_disk": min_disk,
        "min_ram": min_ram,
        "visibility": visibility,
    }
    img = client.post(url, json=body)
    image_id = img.get("id", "")
    console.print(f"[green]Image '{name}' created: {image_id}[/green]")
    console.print(f"  Status: {img.get('status', '')}")

    if file_path:
        p = Path(file_path)
        total = p.stat().st_size
        console.print(f"  Uploading {file_path} ({total / 1024 / 1024:.1f} MB) ...")
        upload_url = f"{client.image_url}/v2/images/{image_id}/file"
        with open(p, "rb") as f:
            client.put_stream(upload_url, stream=f)
        console.print(f"  [green]Upload complete.[/green]")


@image.command("update")
@click.argument("image_id")
@click.option("--name", default=None, help="New name.")
@click.option("--min-disk", type=int, default=None, help="New min disk (GB).")
@click.option("--min-ram", type=int, default=None, help="New min RAM (MB).")
@click.option("--visibility", type=click.Choice(["private", "shared", "community", "public"], case_sensitive=False), default=None, help="New visibility.")
@click.pass_context
def image_update(ctx: click.Context, image_id: str, name: str | None,
                 min_disk: int | None, min_ram: int | None, visibility: str | None) -> None:
    """Update image properties (JSON-Patch).

    \b
    Examples:
      shark image update <id> --name new-name
      shark image update <id> --visibility shared
    """
    import json as json_mod

    ops = []
    if name is not None:
        ops.append({"op": "replace", "path": "/name", "value": name})
    if min_disk is not None:
        ops.append({"op": "replace", "path": "/min_disk", "value": min_disk})
    if min_ram is not None:
        ops.append({"op": "replace", "path": "/min_ram", "value": min_ram})
    if visibility is not None:
        ops.append({"op": "replace", "path": "/visibility", "value": visibility})

    if not ops:
        console.print("[yellow]No properties to update. Use --name, --min-disk, --min-ram, or --visibility.[/yellow]")
        return

    client = ctx.find_object(SharkContext).ensure_client()
    url = f"{client.image_url}/v2/images/{image_id}"
    data = client.patch(
        url,
        content=json_mod.dumps(ops).encode(),
        content_type="application/openstack-images-v2.1-json-patch",
    )
    console.print(f"[green]Image {image_id} updated.[/green]")
    if data:
        console.print(f"  Name: {data.get('name', '')}")
        console.print(f"  Status: {data.get('status', '')}")


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
      shark image upload <id> /path/to/ubuntu.qcow2
    """
    client = ctx.find_object(SharkContext).ensure_client()
    p = Path(file_path)
    total = p.stat().st_size
    console.print(f"Uploading {file_path} ({total / 1024 / 1024:.1f} MB) to image {image_id} ...")
    url = f"{client.image_url}/v2/images/{image_id}/file"
    with open(p, "rb") as f:
        client.put_stream(url, stream=f)
    console.print(f"[green]Upload complete.[/green]")


@image.command("download")
@click.argument("image_id")
@click.option("--output", "-o", "output_path", required=True, type=click.Path(), help="Output file path.")
@click.pass_context
def image_download(ctx: click.Context, image_id: str, output_path: str) -> None:
    """Download image data to a local file.

    \b
    Supports large files — streams to disk without loading into memory.
    Examples:
      shark image download <id> -o /tmp/my-image.qcow2
    """
    client = ctx.find_object(SharkContext).ensure_client()

    # Get image metadata first for size info
    meta_url = f"{client.image_url}/v2/images/{image_id}"
    meta = client.get(meta_url)
    total = meta.get("size") or 0
    name = meta.get("name", image_id)
    console.print(f"Downloading '{name}' ({total / 1024 / 1024:.1f} MB) ...")

    url = f"{client.image_url}/v2/images/{image_id}/file"
    out = Path(output_path)

    with client.get_stream(url) as resp:
        if resp.status_code == 204:
            console.print("[yellow]No image data available.[/yellow]")
            return
        if resp.status_code in (401, 403):
            raise AuthenticationError()
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
    client = ctx.find_object(SharkContext).ensure_client()
    url = f"{client.image_url}/v2/images/{image_id}/actions/deactivate"
    client.post(url)
    console.print(f"[green]Image {image_id} deactivated.[/green]")


@image.command("reactivate")
@click.argument("image_id")
@click.pass_context
def image_reactivate(ctx: click.Context, image_id: str) -> None:
    """Reactivate a deactivated image."""
    client = ctx.find_object(SharkContext).ensure_client()
    url = f"{client.image_url}/v2/images/{image_id}/actions/reactivate"
    client.post(url)
    console.print(f"[green]Image {image_id} reactivated.[/green]")


@image.command("tag-add")
@click.argument("image_id")
@click.argument("tag")
@click.pass_context
def image_tag_add(ctx: click.Context, image_id: str, tag: str) -> None:
    """Add a tag to an image."""
    client = ctx.find_object(SharkContext).ensure_client()
    url = f"{client.image_url}/v2/images/{image_id}/tags/{tag}"
    client.put(url)
    console.print(f"[green]Tag '{tag}' added to image {image_id}.[/green]")


@image.command("tag-delete")
@click.argument("image_id")
@click.argument("tag")
@click.pass_context
def image_tag_delete(ctx: click.Context, image_id: str, tag: str) -> None:
    """Remove a tag from an image."""
    client = ctx.find_object(SharkContext).ensure_client()
    url = f"{client.image_url}/v2/images/{image_id}/tags/{tag}"
    client.delete(url)
    console.print(f"[green]Tag '{tag}' removed from image {image_id}.[/green]")


@image.command("delete")
@click.argument("image_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def image_delete(ctx: click.Context, image_id: str, yes: bool) -> None:
    """Delete an image."""
    if not yes:
        click.confirm(f"Delete image {image_id}?", abort=True)

    client = ctx.find_object(SharkContext).ensure_client()
    url = f"{client.image_url}/v2/images/{image_id}"
    client.delete(url)
    console.print(f"[green]Image {image_id} deleted.[/green]")
