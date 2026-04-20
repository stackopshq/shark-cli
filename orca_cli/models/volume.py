"""Typed views of Cinder resources (only the fields orca reads)."""

from __future__ import annotations

from typing import TypedDict


class VolumeAttachment(TypedDict, total=False):
    id: str
    volume_id: str
    server_id: str
    instance_uuid: str
    device: str
    host_name: str
    attached_at: str
    detached_at: str
    attach_mode: str
    status: str
    connection_info: dict


# Cinder uses a few colon-prefixed keys (os-vol-host-attr:host etc.); the
# alternative TypedDict syntax handles them.
Volume = TypedDict(
    "Volume",
    {
        "id": str,
        "name": str,
        "description": str,
        "status": str,
        "size": int,
        "volume_type": str,
        "bootable": str,            # Cinder returns "true"/"false" strings
        "encrypted": bool,
        "multiattach": bool,
        "availability_zone": str,
        "user_id": str,
        "snapshot_id": str,
        "source_volid": str,
        "metadata": dict,
        "volume_image_metadata": dict,
        "attachments": list,
        "created_at": str,
        "updated_at": str,
        "os-vol-host-attr:host": str,
        "os-vol-tenant-attr:tenant_id": str,
        "os-volume-replication:extended_status": str,
        "replication_status": str,
        "consistencygroup_id": str,
        "group_id": str,
    },
    total=False,
)


class VolumeSnapshot(TypedDict, total=False):
    id: str
    name: str
    description: str
    status: str
    size: int
    volume_id: str
    metadata: dict
    progress: str
    created_at: str
    updated_at: str


class VolumeBackup(TypedDict, total=False):
    id: str
    name: str
    description: str
    status: str
    size: int
    volume_id: str
    snapshot_id: str
    container: str
    availability_zone: str
    is_incremental: bool
    has_dependent_backups: bool
    object_count: int
    fail_reason: str
    created_at: str
    updated_at: str
