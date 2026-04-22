"""Typed views of Glance resources (only the fields orca reads)."""

from __future__ import annotations

from typing import TypedDict


class Image(TypedDict, total=False):
    id: str
    name: str
    status: str
    visibility: str
    owner: str
    protected: bool
    disk_format: str
    container_format: str
    size: int
    virtual_size: int
    checksum: str
    min_disk: int
    min_ram: int
    os_distro: str
    os_version: str
    architecture: str
    hw_scsi_model: str
    created_at: str
    updated_at: str
    image_type: str         # "snapshot" when produced by nova createImage
    file: str               # path portion of the data endpoint
    schema: str
    tags: list
    stores: str
    direct_url: str
    self: str


class ImageMember(TypedDict, total=False):
    image_id: str
    member_id: str
    status: str             # "pending" | "accepted" | "rejected"
    created_at: str
    updated_at: str
    schema: str


class ImageTask(TypedDict, total=False):
    id: str
    type: str               # "import" | "export" | "clone"
    status: str             # "pending" | "processing" | "success" | "failure"
    owner_id: str
    message: str
    input: dict
    result: dict
    created_at: str
    updated_at: str
    expires_at: str
    schema: str


class ImageStore(TypedDict, total=False):
    id: str
    description: str
    is_default: bool
    properties: dict
