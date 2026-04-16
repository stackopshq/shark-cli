"""``orca object`` — manage object storage containers & objects (Swift)."""

from __future__ import annotations

import hashlib
import json
import mimetypes
import os
from pathlib import Path

import click
from rich.tree import Tree

from orca_cli.core.context import OrcaContext
from orca_cli.core.output import console, output_options, print_detail, print_list


# ── Helpers ──────────────────────────────────────────────────────────────────


def _human_size(num_bytes: int | float | str | None) -> str:
    """Format a byte count as a human-readable string (KB/MB/GB/TB)."""
    if num_bytes is None or num_bytes == "":
        return "—"
    n = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024.0:
            if unit == "B":
                return f"{int(n)} {unit}"
            return f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} PB"


def _head(client, url: str) -> dict[str, str]:
    """Perform a HEAD request and return the response headers as a dict."""
    resp = client._http.head(url, headers=client._headers())
    if resp.status_code in (401, 403):
        from orca_cli.core.exceptions import AuthenticationError
        raise AuthenticationError()
    if not resp.is_success:
        from orca_cli.core.exceptions import APIError
        raise APIError(resp.status_code, resp.text[:300])
    return dict(resp.headers)


def _post_no_body(client, url: str, extra_headers: dict[str, str] | None = None) -> dict[str, str]:
    """Perform a POST request with optional extra headers and no JSON body."""
    headers = client._headers()
    if extra_headers:
        headers.update(extra_headers)
    resp = client._http.post(url, headers=headers)
    if resp.status_code in (401, 403):
        from orca_cli.core.exceptions import AuthenticationError
        raise AuthenticationError()
    if not resp.is_success:
        from orca_cli.core.exceptions import APIError
        raise APIError(resp.status_code, resp.text[:300])
    return dict(resp.headers)


# ── Group ────────────────────────────────────────────────────────────────────


@click.group(name="object")
@click.pass_context
def object_store(ctx: click.Context) -> None:
    """Manage object storage containers & objects (Swift)."""
    pass


# ── stats ────────────────────────────────────────────────────────────────────


@object_store.command("stats")
@output_options
@click.pass_context
def object_stats(ctx: click.Context, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show account-level storage statistics."""
    client = ctx.find_object(OrcaContext).ensure_client()
    base = client.object_store_url
    headers = _head(client, base)

    containers = headers.get("x-account-container-count", "0")
    objects = headers.get("x-account-object-count", "0")
    bytes_used = headers.get("x-account-bytes-used", "0")

    fields: list[tuple[str, str]] = [
        ("Account", headers.get("x-account-project-domain-id", "—")),
        ("Containers", containers),
        ("Objects", objects),
        ("Bytes Used", bytes_used),
        ("Bytes Used (Human)", _human_size(bytes_used)),
    ]

    # Include any X-Account-Meta-* headers
    for key, val in sorted(headers.items()):
        if key.lower().startswith("x-account-meta-"):
            meta_name = key[len("x-account-meta-"):]
            fields.append((f"Meta: {meta_name}", val))

    print_detail(fields, output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent, columns=columns)


# ── container-list ───────────────────────────────────────────────────────────


@object_store.command("container-list")
@output_options
@click.pass_context
def container_list(ctx: click.Context, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List containers."""
    client = ctx.find_object(OrcaContext).ensure_client()
    base = client.object_store_url
    data = client.get(f"{base}?format=json")

    containers = data if isinstance(data, list) else []

    column_defs = [
        ("Name", "name", {"style": "bold"}),
        ("Objects", "count", {"justify": "right"}),
        ("Bytes", lambda c: str(c.get("bytes", 0)), {"justify": "right"}),
        ("Size", lambda c: _human_size(c.get("bytes")), {"justify": "right"}),
    ]

    print_list(
        containers,
        column_defs,
        title="Containers",
        output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent,
        columns=columns,
        empty_msg="No containers found.",
    )


# ── container-show ───────────────────────────────────────────────────────────


@object_store.command("container-show")
@click.argument("container")
@output_options
@click.pass_context
def container_show(ctx: click.Context, container: str, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show container metadata."""
    client = ctx.find_object(OrcaContext).ensure_client()
    base = client.object_store_url
    headers = _head(client, f"{base}/{container}")

    fields: list[tuple[str, str]] = [
        ("Container", container),
        ("Object Count", headers.get("x-container-object-count", "—")),
        ("Bytes Used", headers.get("x-container-bytes-used", "—")),
        ("Size", _human_size(headers.get("x-container-bytes-used"))),
        ("Read ACL", headers.get("x-container-read", "—")),
        ("Write ACL", headers.get("x-container-write", "—")),
        ("Storage Policy", headers.get("x-storage-policy", "—")),
    ]

    # Include any X-Container-Meta-* headers
    for key, val in sorted(headers.items()):
        if key.lower().startswith("x-container-meta-"):
            meta_name = key[len("x-container-meta-"):]
            fields.append((f"Meta: {meta_name}", val))

    print_detail(fields, output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent, columns=columns)


# ── container-create ─────────────────────────────────────────────────────────


@object_store.command("container-create")
@click.argument("container")
@click.pass_context
def container_create(ctx: click.Context, container: str) -> None:
    """Create a container."""
    client = ctx.find_object(OrcaContext).ensure_client()
    base = client.object_store_url
    url = f"{base}/{container}"
    headers = client._headers()
    resp = client._http.put(url, headers=headers)
    if resp.status_code in (401, 403):
        from orca_cli.core.exceptions import AuthenticationError
        raise AuthenticationError()
    if not resp.is_success:
        from orca_cli.core.exceptions import APIError
        raise APIError(resp.status_code, resp.text[:300])
    console.print(f"[green]Container '{container}' created.[/green]")


# ── container-delete ─────────────────────────────────────────────────────────


@object_store.command("container-delete")
@click.argument("container")
@click.option("--recursive", is_flag=True, default=False, help="Delete all objects before deleting the container.")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
@click.pass_context
def container_delete(ctx: click.Context, container: str, recursive: bool, yes: bool) -> None:
    """Delete a container.

    Use --recursive to delete all objects in the container first.
    """
    if not yes:
        click.confirm(f"Delete container '{container}'?", abort=True)
    client = ctx.find_object(OrcaContext).ensure_client()
    base = client.object_store_url

    if recursive:
        # Fetch and delete all objects first
        data = client.get(f"{base}/{container}?format=json")
        objects = data if isinstance(data, list) else []
        for obj in objects:
            obj_name = obj.get("name", "")
            if obj_name:
                client.delete(f"{base}/{container}/{obj_name}")
                console.print(f"  Deleted object: {obj_name}")

    client.delete(f"{base}/{container}")
    console.print(f"[green]Container '{container}' deleted.[/green]")


# ── container-set ────────────────────────────────────────────────────────────


@object_store.command("container-set")
@click.argument("container")
@click.option("--property", "properties", multiple=True, required=True, help="Metadata key=value pair (repeatable).")
@click.pass_context
def container_set(ctx: click.Context, container: str, properties: tuple[str, ...]) -> None:
    """Set metadata on a container."""
    client = ctx.find_object(OrcaContext).ensure_client()
    base = client.object_store_url

    extra_headers: dict[str, str] = {}
    for prop in properties:
        if "=" not in prop:
            raise click.BadParameter(f"Invalid property format: '{prop}'. Expected key=value.", param_hint="--property")
        key, val = prop.split("=", 1)
        extra_headers[f"X-Container-Meta-{key}"] = val

    _post_no_body(client, f"{base}/{container}", extra_headers=extra_headers)
    console.print(f"[green]Metadata set on container '{container}'.[/green]")


# ── container-save ───────────────────────────────────────────────────────────


@object_store.command("container-save")
@click.argument("container")
@click.option("--output-dir", default=".", show_default=True, help="Local directory to save objects into.")
@click.pass_context
def container_save(ctx: click.Context, container: str, output_dir: str) -> None:
    """Download all objects in a container to a local directory."""
    client = ctx.find_object(OrcaContext).ensure_client()
    base = client.object_store_url

    data = client.get(f"{base}/{container}?format=json")
    objects = data if isinstance(data, list) else []

    if not objects:
        console.print("[yellow]Container is empty — nothing to download.[/yellow]")
        return

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    for obj in objects:
        obj_name = obj.get("name", "")
        if not obj_name:
            continue
        dest = out_path / obj_name
        dest.parent.mkdir(parents=True, exist_ok=True)

        url = f"{base}/{container}/{obj_name}"
        resp = client._http.get(url, headers=client._headers())
        if not resp.is_success:
            console.print(f"[red]Failed to download '{obj_name}': HTTP {resp.status_code}[/red]")
            continue

        dest.write_bytes(resp.content)
        console.print(f"  Saved: {dest} ({_human_size(len(resp.content))})")

    console.print(f"[green]Downloaded {len(objects)} object(s) to '{out_path}'.[/green]")


# ── list (objects) ───────────────────────────────────────────────────────────


@object_store.command("list")
@click.argument("container")
@click.option("--prefix", default=None, help="Only list objects with this prefix.")
@click.option("--delimiter", default=None, help="Delimiter for pseudo-folder grouping.")
@click.option("--long", "long_format", is_flag=True, default=False, help="Show hash and content type.")
@output_options
@click.pass_context
def object_list(ctx: click.Context, container: str, prefix: str | None, delimiter: str | None, long_format: bool,
                output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List objects in a container."""
    client = ctx.find_object(OrcaContext).ensure_client()
    base = client.object_store_url

    params = "format=json"
    if prefix:
        params += f"&prefix={prefix}"
    if delimiter:
        params += f"&delimiter={delimiter}"

    data = client.get(f"{base}/{container}?{params}")
    objects = data if isinstance(data, list) else []

    column_defs: list[tuple] = [
        ("Name", "name", {"style": "bold"}),
        ("Bytes", lambda o: str(o.get("bytes", 0)), {"justify": "right"}),
        ("Size", lambda o: _human_size(o.get("bytes")), {"justify": "right"}),
        ("Last Modified", "last_modified"),
    ]

    if long_format:
        column_defs.extend([
            ("Content Type", "content_type"),
            ("Hash", "hash", {"style": "dim"}),
        ])

    # Include pseudo-directories from subdir entries
    for obj in objects:
        if "subdir" in obj and "name" not in obj:
            obj["name"] = obj["subdir"]
            obj["bytes"] = ""
            obj["last_modified"] = ""
            obj["content_type"] = "directory"
            obj["hash"] = ""

    print_list(
        objects,
        column_defs,
        title=f"Objects in '{container}'",
        output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent,
        columns=columns,
        empty_msg=f"No objects found in '{container}'.",
    )


# ── show (object) ───────────────────────────────────────────────────────────


@object_store.command("show")
@click.argument("container")
@click.argument("object_name", metavar="OBJECT")
@output_options
@click.pass_context
def object_show(ctx: click.Context, container: str, object_name: str, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show object metadata."""
    client = ctx.find_object(OrcaContext).ensure_client()
    base = client.object_store_url
    headers = _head(client, f"{base}/{container}/{object_name}")

    content_length = headers.get("content-length", "0")

    fields: list[tuple[str, str]] = [
        ("Container", container),
        ("Object", object_name),
        ("Content Type", headers.get("content-type", "—")),
        ("Content Length", content_length),
        ("Size", _human_size(content_length)),
        ("ETag", headers.get("etag", "—")),
        ("Last Modified", headers.get("last-modified", "—")),
        ("Accept-Ranges", headers.get("accept-ranges", "—")),
    ]

    # Include any X-Object-Meta-* headers
    for key, val in sorted(headers.items()):
        if key.lower().startswith("x-object-meta-"):
            meta_name = key[len("x-object-meta-"):]
            fields.append((f"Meta: {meta_name}", val))

    print_detail(fields, output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent, columns=columns)


# ── upload ───────────────────────────────────────────────────────────────────


SLO_SEGMENT_SIZE = 4 * 1024 * 1024 * 1024  # 4 GB per segment
SLO_THRESHOLD = 5 * 1024 * 1024 * 1024     # use SLO above 5 GB


def _upload_simple(client, base, container, obj_name, path, content_type, file_size, progress, task):
    """Single-PUT upload for files <= 5 GB."""
    headers = client._headers()
    headers["Content-Type"] = content_type
    headers["Content-Length"] = str(file_size)

    def _iter(f, chunk_size=256 * 1024):
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            progress.advance(task, len(chunk))
            yield chunk

    with open(path, "rb") as f:
        resp = client._http.put(
            f"{base}/{container}/{obj_name}",
            headers=headers,
            content=_iter(f),
        )

    if resp.status_code in (401, 403):
        from orca_cli.core.exceptions import AuthenticationError
        raise AuthenticationError()
    if not resp.is_success:
        from orca_cli.core.exceptions import APIError
        raise APIError(resp.status_code, resp.text[:300])


def _upload_slo(client, base, container, obj_name, path, content_type, file_size, progress, task):
    """Segmented upload (SLO) for files > 5 GB."""
    seg_container = f"{container}_segments"
    # Ensure segments container exists
    headers = client._headers()
    headers["Content-Length"] = "0"
    client._http.put(f"{base}/{seg_container}", headers=headers)

    manifest = []
    seg_num = 0
    uploaded = 0
    chunk_size = 256 * 1024  # read chunk for progress

    with open(path, "rb") as f:
        while uploaded < file_size:
            seg_num += 1
            seg_name = f"{obj_name}/slo/{seg_num:08d}"
            seg_size = min(SLO_SEGMENT_SIZE, file_size - uploaded)

            seg_hash = hashlib.md5()
            seg_uploaded = 0

            def _seg_iter():
                nonlocal seg_uploaded
                while seg_uploaded < seg_size:
                    to_read = min(chunk_size, seg_size - seg_uploaded)
                    data = f.read(to_read)
                    if not data:
                        break
                    seg_hash.update(data)
                    seg_uploaded += len(data)
                    progress.advance(task, len(data))
                    yield data

            seg_headers = client._headers()
            seg_headers["Content-Type"] = "application/octet-stream"
            seg_headers["Content-Length"] = str(seg_size)

            resp = client._http.put(
                f"{base}/{seg_container}/{seg_name}",
                headers=seg_headers,
                content=_seg_iter(),
            )

            if resp.status_code in (401, 403):
                from orca_cli.core.exceptions import AuthenticationError
                raise AuthenticationError()
            if not resp.is_success:
                from orca_cli.core.exceptions import APIError
                raise APIError(resp.status_code, resp.text[:300])

            uploaded += seg_uploaded
            manifest.append({
                "path": f"/{seg_container}/{seg_name}",
                "etag": seg_hash.hexdigest(),
                "size_bytes": seg_uploaded,
            })

    # Upload the SLO manifest
    manifest_headers = client._headers()
    manifest_headers["Content-Type"] = content_type
    manifest_body = json.dumps(manifest).encode()
    manifest_headers["Content-Length"] = str(len(manifest_body))

    resp = client._http.put(
        f"{base}/{container}/{obj_name}?multipart-manifest=put",
        headers=manifest_headers,
        content=manifest_body,
    )

    if resp.status_code in (401, 403):
        from orca_cli.core.exceptions import AuthenticationError
        raise AuthenticationError()
    if not resp.is_success:
        from orca_cli.core.exceptions import APIError
        raise APIError(resp.status_code, resp.text[:300])


@object_store.command("upload")
@click.argument("container")
@click.argument("files", nargs=-1, required=True, type=click.Path(exists=True))
@click.option("--name", "override_name", default=None, help="Override the object name (only valid for single file upload).")
@click.option("--segment-size", type=int, default=None, help="Segment size in MB for large files (default: 4096 MB).")
@click.pass_context
def object_upload(ctx: click.Context, container: str, files: tuple[str, ...],
                  override_name: str | None, segment_size: int | None) -> None:
    """Upload file(s) to a container.

    Files larger than 5 GB are automatically split into segments
    using Swift SLO (Static Large Object).
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    base = client.object_store_url

    if override_name and len(files) > 1:
        raise click.UsageError("--name can only be used when uploading a single file.")

    if segment_size:
        global SLO_SEGMENT_SIZE
        SLO_SEGMENT_SIZE = segment_size * 1024 * 1024

    from rich.progress import Progress, BarColumn, DownloadColumn, TransferSpeedColumn, TimeRemainingColumn

    for filepath in files:
        path = Path(filepath)
        obj_name = override_name if override_name else path.name
        content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        file_size = path.stat().st_size

        with Progress(
            "[progress.description]{task.description}",
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            if file_size > SLO_THRESHOLD:
                n_segments = (file_size + SLO_SEGMENT_SIZE - 1) // SLO_SEGMENT_SIZE
                task = progress.add_task(
                    f"Uploading {path.name} ({n_segments} segments)", total=file_size)
                _upload_slo(client, base, container, obj_name, path,
                            content_type, file_size, progress, task)
            else:
                task = progress.add_task(f"Uploading {path.name}", total=file_size)
                _upload_simple(client, base, container, obj_name, path,
                               content_type, file_size, progress, task)

        console.print(f"[green]Uploaded '{path.name}' -> '{container}/{obj_name}' ({_human_size(file_size)})[/green]")


# ── download ─────────────────────────────────────────────────────────────────


@object_store.command("download")
@click.argument("container")
@click.argument("object_name", metavar="OBJECT")
@click.option("--file", "output_file", default=None, help="Local filename to save to (defaults to object name).")
@click.pass_context
def object_download(ctx: click.Context, container: str, object_name: str, output_file: str | None) -> None:
    """Download an object from a container."""
    from rich.progress import Progress, BarColumn, DownloadColumn, TransferSpeedColumn, TimeRemainingColumn

    client = ctx.find_object(OrcaContext).ensure_client()
    base = client.object_store_url
    url = f"{base}/{container}/{object_name}"
    dest = Path(output_file if output_file else object_name.split("/")[-1])
    dest.parent.mkdir(parents=True, exist_ok=True)

    with client._http.stream("GET", url, headers=client._headers()) as resp:
        if resp.status_code in (401, 403):
            from orca_cli.core.exceptions import AuthenticationError
            raise AuthenticationError()
        if not resp.is_success:
            resp.read()
            from orca_cli.core.exceptions import APIError
            raise APIError(resp.status_code, resp.text[:300])

        total = int(resp.headers.get("Content-Length", 0))
        with Progress(
            "[progress.description]{task.description}",
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(f"Downloading {dest.name}", total=total or None)
            downloaded = 0
            with open(dest, "wb") as f:
                for chunk in resp.iter_bytes(chunk_size=256 * 1024):
                    f.write(chunk)
                    downloaded += len(chunk)
                    progress.advance(task, len(chunk))

    console.print(f"[green]Downloaded '{object_name}' -> '{dest}' ({_human_size(downloaded)})[/green]")


# ── delete (object) ─────────────────────────────────────────────────────────


@object_store.command("delete")
@click.argument("container")
@click.argument("objects", nargs=-1, required=True, metavar="OBJECT...")
@click.pass_context
def object_delete(ctx: click.Context, container: str, objects: tuple[str, ...]) -> None:
    """Delete one or more objects from a container."""
    client = ctx.find_object(OrcaContext).ensure_client()
    base = client.object_store_url

    for obj_name in objects:
        client.delete(f"{base}/{container}/{obj_name}")
        console.print(f"  Deleted: {container}/{obj_name}")

    console.print(f"[green]Deleted {len(objects)} object(s) from '{container}'.[/green]")


# ── set (object metadata) ───────────────────────────────────────────────────


@object_store.command("set")
@click.argument("container")
@click.argument("object_name", metavar="OBJECT")
@click.option("--property", "properties", multiple=True, required=True, help="Metadata key=value pair (repeatable).")
@click.pass_context
def object_set(ctx: click.Context, container: str, object_name: str, properties: tuple[str, ...]) -> None:
    """Set metadata on an object."""
    client = ctx.find_object(OrcaContext).ensure_client()
    base = client.object_store_url

    extra_headers: dict[str, str] = {}
    for prop in properties:
        if "=" not in prop:
            raise click.BadParameter(f"Invalid property format: '{prop}'. Expected key=value.", param_hint="--property")
        key, val = prop.split("=", 1)
        extra_headers[f"X-Object-Meta-{key}"] = val

    _post_no_body(client, f"{base}/{container}/{object_name}", extra_headers=extra_headers)
    console.print(f"[green]Metadata set on '{container}/{object_name}'.[/green]")


# ── unset (object metadata) ─────────────────────────────────────────────────


@object_store.command("unset")
@click.argument("container")
@click.argument("object_name", metavar="OBJECT")
@click.option("--property", "properties", multiple=True, required=True, help="Metadata key to remove (repeatable).")
@click.pass_context
def object_unset(ctx: click.Context, container: str, object_name: str, properties: tuple[str, ...]) -> None:
    """Remove metadata from an object."""
    client = ctx.find_object(OrcaContext).ensure_client()
    base = client.object_store_url

    extra_headers: dict[str, str] = {}
    for key in properties:
        extra_headers[f"X-Remove-Object-Meta-{key}"] = "x"

    _post_no_body(client, f"{base}/{container}/{object_name}", extra_headers=extra_headers)
    console.print(f"[green]Metadata removed from '{container}/{object_name}'.[/green]")


# ── account-set ───────────────────────────────────────────────────────────────


@object_store.command("account-set")
@click.option("--property", "properties", multiple=True, required=True, help="Metadata key=value pair (repeatable).")
@click.pass_context
def object_account_set(ctx: click.Context, properties: tuple[str, ...]) -> None:
    """Set account-level metadata."""
    client = ctx.find_object(OrcaContext).ensure_client()
    base = client.object_store_url

    extra_headers: dict[str, str] = {}
    for prop in properties:
        if "=" not in prop:
            raise click.BadParameter(f"Invalid property format: '{prop}'. Expected key=value.", param_hint="--property")
        key, val = prop.split("=", 1)
        extra_headers[f"X-Account-Meta-{key}"] = val

    _post_no_body(client, base, extra_headers=extra_headers)
    console.print("[green]Account metadata set.[/green]")


# ── account-unset ─────────────────────────────────────────────────────────────


@object_store.command("account-unset")
@click.option("--property", "properties", multiple=True, required=True, help="Metadata key to remove (repeatable).")
@click.pass_context
def object_account_unset(ctx: click.Context, properties: tuple[str, ...]) -> None:
    """Remove account-level metadata."""
    client = ctx.find_object(OrcaContext).ensure_client()
    base = client.object_store_url

    extra_headers: dict[str, str] = {}
    for key in properties:
        extra_headers[f"X-Remove-Account-Meta-{key}"] = "x"

    _post_no_body(client, base, extra_headers=extra_headers)
    console.print("[green]Account metadata removed.[/green]")


# ── tree ─────────────────────────────────────────────────────────────────────


@object_store.command("tree")
@click.argument("container", required=False, default=None)
@click.option("--delimiter", default="/", show_default=True, help="Delimiter for pseudo-folder hierarchy.")
@click.pass_context
def object_tree(ctx: click.Context, container: str | None, delimiter: str) -> None:
    """Show containers and objects as a tree.

    Without a container argument, shows all containers. With a container,
    shows the pseudo-folder structure of objects within it.
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    base = client.object_store_url

    if container is None:
        # Show all containers as top-level tree
        data = client.get(f"{base}?format=json")
        containers = data if isinstance(data, list) else []

        tree = Tree(f"[bold]Account[/bold]")
        for c in containers:
            name = c.get("name", "")
            count = c.get("count", 0)
            size = _human_size(c.get("bytes"))
            tree.add(f"[bold]{name}[/bold]  [dim]({count} objects, {size})[/dim]")

        console.print(tree)
    else:
        # Show pseudo-folder structure for a single container
        data = client.get(f"{base}/{container}?format=json")
        objects = data if isinstance(data, list) else []

        tree = Tree(f"[bold]{container}[/bold]")

        # Build a nested dict representing the folder hierarchy
        folder_tree: dict = {}
        for obj in objects:
            name = obj.get("name", "")
            size = obj.get("bytes", 0)
            parts = name.split(delimiter) if delimiter else [name]
            node = folder_tree
            for part in parts[:-1]:
                if part not in node:
                    node[part] = {}
                node = node[part]
            # Leaf node stores the size
            leaf_name = parts[-1] if parts[-1] else parts[-2] + delimiter if len(parts) > 1 else name
            node[leaf_name] = {"__size__": size}

        def _add_nodes(parent_tree: Tree, subtree: dict) -> None:
            for key in sorted(subtree.keys()):
                val = subtree[key]
                if isinstance(val, dict) and "__size__" in val and len(val) == 1:
                    # Leaf file
                    parent_tree.add(f"{key}  [dim]({_human_size(val['__size__'])})[/dim]")
                elif isinstance(val, dict):
                    # Directory node (may also have __size__)
                    branch = parent_tree.add(f"[bold blue]{key}/[/bold blue]")
                    child = {k: v for k, v in val.items() if k != "__size__"}
                    _add_nodes(branch, child)

        _add_nodes(tree, folder_tree)
        console.print(tree)
