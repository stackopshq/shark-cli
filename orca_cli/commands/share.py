"""``orca share`` — manage Manila shared file systems."""

from __future__ import annotations

import click

from orca_cli.core.context import OrcaContext
from orca_cli.core.output import console, output_options, print_detail, print_list
from orca_cli.services.shared_file_system import FileShareService

SHARE_PROTOCOLS = ["NFS", "CIFS", "GLUSTERFS", "HDFS", "CEPHFS", "MAPRFS"]
ACCESS_TYPES = ["ip", "user", "cert", "cephx"]
ACCESS_LEVELS = ["rw", "ro"]


def _svc(ctx: click.Context) -> FileShareService:
    return FileShareService(ctx.find_object(OrcaContext).ensure_client())


# ══════════════════════════════════════════════════════════════════════════
#  Top-level group
# ══════════════════════════════════════════════════════════════════════════

@click.group()
@click.pass_context
def share(ctx: click.Context) -> None:
    """Manage Manila shared file systems (shares, access rules, snapshots).

    Manila is a multi-tenant NFS/CIFS/CephFS-as-a-service. Use ``orca share
    create`` to allocate a share, ``orca share access allow`` to expose it
    to a client IP, then mount the export location.
    """
    pass


# ── sub-groups (ADR-0008: noun [subnoun] verb) ──────────────────────────

@share.group("access")
def share_access() -> None:
    """Manage share access rules (NFS IP allow, CIFS user, CephFS x509)."""


@share.group("snapshot")
def share_snapshot() -> None:
    """Manage share snapshots."""


@share.group("type")
def share_type() -> None:
    """Inspect share types (admin defines, users select)."""


# ══════════════════════════════════════════════════════════════════════════
#  Shares — CRUD
# ══════════════════════════════════════════════════════════════════════════

@share.command("list")
@output_options
@click.pass_context
def share_list(ctx: click.Context, output_format: str, columns: tuple[str, ...],
               fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List shares."""
    shares = _svc(ctx).find()
    print_list(
        shares,
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Name", lambda s: s.get("name") or "—", {"style": "bold"}),
            ("Status", "status", {"style": "green"}),
            ("Size (GB)", "size", {"justify": "right"}),
            ("Proto", "share_proto"),
            ("Type", lambda s: s.get("share_type_name") or s.get("share_type") or "—"),
            ("AZ", lambda s: s.get("availability_zone") or "—"),
        ],
        title="Shares",
        output_format=output_format, fit_width=fit_width, max_width=max_width,
        noindent=noindent, columns=columns,
        empty_msg="No shares found.",
    )


@share.command("show")
@click.argument("share_id")
@output_options
@click.pass_context
def share_show(ctx: click.Context, share_id: str, output_format: str,
               columns: tuple[str, ...], fit_width: bool, max_width: int | None,
               noindent: bool) -> None:
    """Show share details + export locations."""
    data = _svc(ctx).get(share_id)
    fields = [
        ("id", data.get("id", "")),
        ("name", data.get("name", "") or "—"),
        ("description", data.get("description", "") or "—"),
        ("status", data.get("status", "")),
        ("size (GB)", str(data.get("size", ""))),
        ("share_proto", data.get("share_proto", "")),
        ("share_type", data.get("share_type_name", "") or data.get("share_type", "") or "—"),
        ("share_network_id", data.get("share_network_id", "") or "—"),
        ("host", data.get("host", "") or "—"),
        ("availability_zone", data.get("availability_zone", "") or "—"),
        ("access_rules_status", data.get("access_rules_status", "") or "—"),
        ("created_at", data.get("created_at", "")),
        ("project_id", data.get("project_id", "")),
    ]

    locations = data.get("export_locations") or []
    if locations:
        fields.append(("", ""))
        fields.append(("── Export locations ──", ""))
        for i, loc in enumerate(locations):
            path = loc.get("path", loc) if isinstance(loc, dict) else loc
            fields.append((f"  [{i}]", str(path)))
    elif data.get("export_location"):
        fields.append(("export_location", data["export_location"]))

    print_detail(fields, output_format=output_format, fit_width=fit_width,
                 max_width=max_width, noindent=noindent, columns=columns)


@share.command("create")
@click.argument("name")
@click.option("--size", type=int, required=True, help="Share size in GB.")
@click.option("--protocol", type=click.Choice(SHARE_PROTOCOLS), default="NFS",
              show_default=True, help="Share protocol.")
@click.option("--description", default=None, help="Free-text description.")
@click.option("--share-type", default=None,
              help="Share type name or ID (omit for the operator default).")
@click.option("--share-network", default=None,
              help="Share network ID for multi-tenant deployments.")
@click.option("--snapshot-id", default=None,
              help="Create from an existing snapshot.")
@click.option("--availability-zone", default=None, help="Target AZ.")
@click.option("--public/--private", "is_public", default=False,
              help="Share visibility (default: private).")
@click.pass_context
def share_create(ctx: click.Context, name: str, size: int, protocol: str,
                 description: str | None, share_type: str | None,
                 share_network: str | None, snapshot_id: str | None,
                 availability_zone: str | None, is_public: bool) -> None:
    """Create a share.

    \b
    Examples:
      orca share create my-nfs --size 50
      orca share create scratch --size 100 --protocol CEPHFS --availability-zone az1
      orca share create from-snap --size 10 --snapshot-id <snap-id>
    """
    body: dict = {
        "name": name,
        "size": size,
        "share_proto": protocol,
        "is_public": is_public,
    }
    if description:
        body["description"] = description
    if share_type:
        body["share_type"] = share_type
    if share_network:
        body["share_network_id"] = share_network
    if snapshot_id:
        body["snapshot_id"] = snapshot_id
    if availability_zone:
        body["availability_zone"] = availability_zone

    data = _svc(ctx).create(body)
    console.print(f"[green]Share '{data.get('name', name)}' created ({data.get('id', '')}).[/green]")


@share.command("set")
@click.argument("share_id")
@click.option("--name", default=None, help="New display name.")
@click.option("--description", default=None, help="New description.")
@click.option("--public/--private", "is_public", default=None,
              help="Switch visibility.")
@click.pass_context
def share_set(ctx: click.Context, share_id: str, name: str | None,
              description: str | None, is_public: bool | None) -> None:
    """Update a share's name / description / visibility."""
    body: dict = {}
    if name is not None:
        body["display_name"] = name
    if description is not None:
        body["display_description"] = description
    if is_public is not None:
        body["is_public"] = is_public
    if not body:
        console.print("[yellow]Nothing to update.[/yellow]")
        return
    _svc(ctx).update(share_id, body)
    console.print(f"[green]Share {share_id} updated.[/green]")


@share.command("delete")
@click.argument("share_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def share_delete(ctx: click.Context, share_id: str, yes: bool) -> None:
    """Delete a share."""
    if not yes:
        click.confirm(f"Delete share {share_id}?", abort=True)
    _svc(ctx).delete(share_id)
    console.print(f"[green]Share {share_id} deletion requested.[/green]")


@share.command("extend")
@click.argument("share_id")
@click.option("--size", type=int, required=True, help="New total size in GB.")
@click.pass_context
def share_extend(ctx: click.Context, share_id: str, size: int) -> None:
    """Extend a share (grow only)."""
    _svc(ctx).extend(share_id, size)
    console.print(f"[green]Share {share_id} extended to {size} GB.[/green]")


@share.command("shrink")
@click.argument("share_id")
@click.option("--size", type=int, required=True, help="New total size in GB.")
@click.pass_context
def share_shrink(ctx: click.Context, share_id: str, size: int) -> None:
    """Shrink a share (only allowed if the backend supports it)."""
    _svc(ctx).shrink(share_id, size)
    console.print(f"[green]Share {share_id} shrink requested to {size} GB.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  Access rules
# ══════════════════════════════════════════════════════════════════════════

@share_access.command("list")
@click.argument("share_id")
@output_options
@click.pass_context
def access_list(ctx: click.Context, share_id: str, output_format: str,
                columns: tuple[str, ...], fit_width: bool, max_width: int | None,
                noindent: bool) -> None:
    """List access rules attached to a share."""
    rules = _svc(ctx).find_access_rules(share_id)
    print_list(
        rules,
        [
            ("Access ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Type", "access_type"),
            ("To", "access_to", {"style": "bold"}),
            ("Level", "access_level"),
            ("State", "state", {"style": "green"}),
        ],
        title=f"Access rules for share {share_id}",
        output_format=output_format, fit_width=fit_width, max_width=max_width,
        noindent=noindent, columns=columns,
        empty_msg="No access rules.",
    )


@share_access.command("allow")
@click.argument("share_id")
@click.option("--access-type", type=click.Choice(ACCESS_TYPES), required=True,
              help="ip (NFS) | user (CIFS) | cert (CephFS) | cephx (Ceph).")
@click.option("--access-to", required=True,
              help="The principal: IP/CIDR for ip, username for user, CN for cert, client name for cephx.")
@click.option("--access-level", type=click.Choice(ACCESS_LEVELS), default="rw",
              show_default=True)
@click.pass_context
def access_allow(ctx: click.Context, share_id: str, access_type: str,
                 access_to: str, access_level: str) -> None:
    """Grant access to a share.

    \b
    Examples:
      orca share access allow <share-id> --access-type ip --access-to 10.0.0.0/24
      orca share access allow <share-id> --access-type ip --access-to 1.2.3.4 --access-level ro
      orca share access allow <share-id> --access-type cephx --access-to client.foo
    """
    rule = _svc(ctx).allow_access(share_id, access_type, access_to,
                                  access_level=access_level)
    console.print(f"[green]Access granted ({rule.get('id', '?')}).[/green]")
    if rule.get("access_key"):
        # CephFS returns a one-shot secret here — surface it.
        console.print(f"[bold yellow]access_key:[/bold yellow] {rule['access_key']}")
        console.print("[dim]Save this key now; Manila won't show it again.[/dim]")


@share_access.command("deny")
@click.argument("share_id")
@click.argument("access_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def access_deny(ctx: click.Context, share_id: str, access_id: str, yes: bool) -> None:
    """Revoke an access rule from a share."""
    if not yes:
        click.confirm(f"Revoke access {access_id} from share {share_id}?", abort=True)
    _svc(ctx).deny_access(share_id, access_id)
    console.print(f"[green]Access {access_id} revoked.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  Snapshots
# ══════════════════════════════════════════════════════════════════════════

@share_snapshot.command("list")
@output_options
@click.pass_context
def snapshot_list(ctx: click.Context, output_format: str, columns: tuple[str, ...],
                  fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List share snapshots."""
    snaps = _svc(ctx).find_snapshots()
    print_list(
        snaps,
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Name", lambda s: s.get("name") or "—", {"style": "bold"}),
            ("Status", "status", {"style": "green"}),
            ("Share", "share_id"),
            ("Size (GB)", "size", {"justify": "right"}),
            ("Created", "created_at"),
        ],
        title="Share snapshots",
        output_format=output_format, fit_width=fit_width, max_width=max_width,
        noindent=noindent, columns=columns,
        empty_msg="No snapshots found.",
    )


@share_snapshot.command("show")
@click.argument("snapshot_id")
@output_options
@click.pass_context
def snapshot_show(ctx: click.Context, snapshot_id: str, output_format: str,
                  columns: tuple[str, ...], fit_width: bool, max_width: int | None,
                  noindent: bool) -> None:
    """Show snapshot details."""
    data = _svc(ctx).get_snapshot(snapshot_id)
    fields = [(k, str(data.get(k, "") or "—")) for k in
              ["id", "name", "description", "status", "share_id",
               "share_size", "size", "created_at", "project_id"]]
    print_detail(fields, output_format=output_format, fit_width=fit_width,
                 max_width=max_width, noindent=noindent, columns=columns)


@share_snapshot.command("create")
@click.argument("share_id")
@click.option("--name", default=None, help="Snapshot name.")
@click.option("--description", default=None, help="Snapshot description.")
@click.pass_context
def snapshot_create(ctx: click.Context, share_id: str, name: str | None,
                    description: str | None) -> None:
    """Snapshot a share."""
    data = _svc(ctx).create_snapshot(share_id, name=name, description=description)
    console.print(f"[green]Snapshot created ({data.get('id', '')}).[/green]")


@share_snapshot.command("delete")
@click.argument("snapshot_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def snapshot_delete(ctx: click.Context, snapshot_id: str, yes: bool) -> None:
    """Delete a snapshot."""
    if not yes:
        click.confirm(f"Delete snapshot {snapshot_id}?", abort=True)
    _svc(ctx).delete_snapshot(snapshot_id)
    console.print(f"[green]Snapshot {snapshot_id} deletion requested.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  Types (read-only)
# ══════════════════════════════════════════════════════════════════════════

@share_type.command("list")
@output_options
@click.pass_context
def type_list(ctx: click.Context, output_format: str, columns: tuple[str, ...],
              fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List share types defined by the operator."""
    types = _svc(ctx).find_types()
    print_list(
        types,
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Name", "name", {"style": "bold"}),
            ("Default", "is_default"),
            ("Public", "is_public"),
            ("Extra specs",
             lambda t: ", ".join(f"{k}={v}" for k, v in (t.get("extra_specs") or {}).items()) or "—"),
        ],
        title="Share types",
        output_format=output_format, fit_width=fit_width, max_width=max_width,
        noindent=noindent, columns=columns,
        empty_msg="No share types found.",
    )


@share_type.command("show")
@click.argument("type_id")
@output_options
@click.pass_context
def type_show(ctx: click.Context, type_id: str, output_format: str,
              columns: tuple[str, ...], fit_width: bool, max_width: int | None,
              noindent: bool) -> None:
    """Show a share type."""
    data = _svc(ctx).get_type(type_id)
    fields = [
        ("id", data.get("id", "")),
        ("name", data.get("name", "")),
        ("description", data.get("description", "") or "—"),
        ("is_default", str(data.get("is_default", ""))),
        ("is_public", str(data.get("is_public", ""))),
    ]
    extra = data.get("extra_specs") or {}
    if extra:
        fields.append(("", ""))
        fields.append(("── Extra specs ──", ""))
        for k, v in extra.items():
            fields.append((f"  {k}", str(v)))
    req = data.get("required_extra_specs") or {}
    if req:
        fields.append(("", ""))
        fields.append(("── Required ──", ""))
        for k, v in req.items():
            fields.append((f"  {k}", str(v)))
    print_detail(fields, output_format=output_format, fit_width=fit_width,
                 max_width=max_width, noindent=noindent, columns=columns)
