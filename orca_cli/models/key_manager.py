"""Typed views of Barbican key-manager resources (only the fields orca reads)."""

from __future__ import annotations

from typing import TypedDict


class Secret(TypedDict, total=False):
    secret_ref: str
    name: str
    secret_type: str
    algorithm: str
    bit_length: int
    mode: str
    payload_content_type: str
    payload_content_encoding: str
    status: str
    expiration: str
    creator_id: str
    created: str
    updated: str
    content_types: dict


class SecretContainer(TypedDict, total=False):
    container_ref: str
    name: str
    type: str
    secret_refs: list
    creator_id: str
    status: str
    created: str
    updated: str


class Order(TypedDict, total=False):
    order_ref: str
    type: str
    status: str
    secret_ref: str
    container_ref: str
    meta: dict
    creator_id: str
    created: str
    updated: str
    sub_status: str
    sub_status_message: str


class Acl(TypedDict, total=False):
    read: dict
    users: list
    project_access: bool
    created: str
    updated: str
