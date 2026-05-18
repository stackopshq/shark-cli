"""Typed views of Manila (shared file system) resources."""

from __future__ import annotations

from typing import TypedDict


class Share(TypedDict, total=False):
    id: str
    name: str
    description: str
    status: str
    size: int
    share_proto: str
    share_type: str
    share_type_name: str
    share_network_id: str
    share_group_id: str
    snapshot_id: str
    availability_zone: str
    host: str
    project_id: str
    user_id: str
    is_public: bool
    access_rules_status: str
    has_replicas: bool
    replication_type: str
    export_location: str
    export_locations: list
    created_at: str
    metadata: dict


class ShareAccessRule(TypedDict, total=False):
    id: str
    access_level: str       # "rw" | "ro"
    access_type: str        # "ip" | "user" | "cert" | "cephx"
    access_to: str
    access_key: str         # only for CephFS
    state: str              # "active" | "error" | "applying" | "denying"
    share_id: str
    created_at: str
    updated_at: str
    metadata: dict


class ShareSnapshot(TypedDict, total=False):
    id: str
    name: str
    description: str
    status: str
    share_id: str
    share_size: int
    size: int
    project_id: str
    user_id: str
    provider_location: str
    created_at: str


class ShareType(TypedDict, total=False):
    id: str
    name: str
    description: str
    is_default: bool
    is_public: bool
    extra_specs: dict
    required_extra_specs: dict
