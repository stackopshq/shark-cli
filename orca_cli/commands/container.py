"""``orca container`` — manage object storage containers (Swift)."""

from __future__ import annotations

import click

from orca_cli.core.context import OrcaContext
from orca_cli.core.output import console, output_options, print_detail, print_list
from orca_cli.core.validators import safe_child_path, safe_output_path
from orca_cli.services.object_store import ObjectStoreService


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


@click.group()
@click.pass_context
def container(ctx: click.Context) -> None:
    """Manage object storage containers (Swift)."""
    pass


@container.command("list")
@output_options
@click.pass_context
def container_list(ctx: click.Context, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List containers."""
    client = ctx.find_object(OrcaContext).ensure_client()
    svc = ObjectStoreService(client)
    containers = svc.find_containers()

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


@container.command("show")
@click.argument("container_name", metavar="CONTAINER")
@output_options
@click.pass_context
def container_show(ctx: click.Context, container_name: str, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show container metadata."""
    client = ctx.find_object(OrcaContext).ensure_client()
    svc = ObjectStoreService(client)
    headers = svc.head_container(container_name)

    fields: list[tuple[str, str]] = [
        ("Container", container_name),
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


@container.command("create")
@click.argument("container_name", metavar="CONTAINER")
@click.pass_context
def container_create(ctx: click.Context, container_name: str) -> None:
    """Create a container."""
    client = ctx.find_object(OrcaContext).ensure_client()
    svc = ObjectStoreService(client)
    svc.create_container(container_name)
    console.print(f"[green]Container '{container_name}' created.[/green]")


@container.command("delete")
@click.argument("container_name", metavar="CONTAINER")
@click.option("--recursive", is_flag=True, default=False, help="Delete all objects before deleting the container.")
@click.pass_context
def container_delete(ctx: click.Context, container_name: str, recursive: bool) -> None:
    """Delete a container.

    Use --recursive to delete all objects in the container first.
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    svc = ObjectStoreService(client)

    if recursive:
        # Fetch and delete all objects first
        objects = svc.find_objects(container_name)
        for obj in objects:
            obj_name = obj.get("name", "")
            if obj_name:
                svc.delete_object(container_name, obj_name)
                console.print(f"  Deleted object: {obj_name}")

    svc.delete_container(container_name)
    console.print(f"[green]Container '{container_name}' deleted.[/green]")


@container.command("set")
@click.argument("container_name", metavar="CONTAINER")
@click.option("--property", "properties", multiple=True, required=True, help="Metadata key=value pair (repeatable).")
@click.pass_context
def container_set(ctx: click.Context, container_name: str, properties: tuple[str, ...]) -> None:
    """Set metadata on a container."""
    client = ctx.find_object(OrcaContext).ensure_client()
    svc = ObjectStoreService(client)

    extra_headers: dict[str, str] = {}
    for prop in properties:
        if "=" not in prop:
            raise click.BadParameter(f"Invalid property format: '{prop}'. Expected key=value.", param_hint="--property")
        key, val = prop.split("=", 1)
        extra_headers[f"X-Container-Meta-{key}"] = val

    svc.post_container_metadata(container_name, extra_headers)
    console.print(f"[green]Metadata set on container '{container_name}'.[/green]")


@container.command("save")
@click.argument("container_name", metavar="CONTAINER")
@click.option("--output-dir", default=".", show_default=True, help="Local directory to save objects into.")
@click.pass_context
def container_save(ctx: click.Context, container_name: str, output_dir: str) -> None:
    """Download all objects in a container to a local directory."""
    client = ctx.find_object(OrcaContext).ensure_client()
    svc = ObjectStoreService(client)

    objects = svc.find_objects(container_name)

    if not objects:
        console.print("[yellow]Container is empty — nothing to download.[/yellow]")
        return

    out_path = safe_output_path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    for obj in objects:
        obj_name = obj.get("name", "")
        if not obj_name:
            continue
        try:
            dest = safe_child_path(out_path, obj_name)
        except click.BadParameter as exc:
            console.print(f"[red]Skipping '{obj_name}': {exc.message}[/red]")
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)

        url = svc.object_url(container_name, obj_name)
        resp = client._http.get(url, headers=client._headers())
        if not resp.is_success:
            console.print(f"[red]Failed to download '{obj_name}': HTTP {resp.status_code}[/red]")
            continue

        dest.write_bytes(resp.content)
        console.print(f"  Saved: {dest} ({_human_size(len(resp.content))})")

    console.print(f"[green]Downloaded {len(objects)} object(s) to '{out_path}'.[/green]")


@container.command("unset")
@click.argument("container_name", metavar="CONTAINER")
@click.option("--property", "properties", multiple=True, required=True, help="Metadata key to remove (repeatable).")
@click.pass_context
def container_unset(ctx: click.Context, container_name: str, properties: tuple[str, ...]) -> None:
    """Remove metadata from a container."""
    client = ctx.find_object(OrcaContext).ensure_client()
    svc = ObjectStoreService(client)

    extra_headers: dict[str, str] = {}
    for key in properties:
        extra_headers[f"X-Remove-Container-Meta-{key}"] = "x"

    svc.post_container_metadata(container_name, extra_headers)
    console.print(f"[green]Metadata removed from container '{container_name}'.[/green]")


@container.command("stats")
@output_options
@click.pass_context
def container_stats(ctx: click.Context, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show account-level storage statistics."""
    client = ctx.find_object(OrcaContext).ensure_client()
    svc = ObjectStoreService(client)
    headers = svc.head_account()

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
