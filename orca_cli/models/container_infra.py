"""Typed views of Magnum container-infrastructure resources."""

from __future__ import annotations

from typing import TypedDict


class Cluster(TypedDict, total=False):
    uuid: str
    name: str
    status: str
    status_reason: str
    cluster_template_id: str
    master_count: int
    node_count: int
    keypair: str
    master_flavor_id: str
    flavor_id: str
    stack_id: str
    api_address: str
    master_addresses: list
    node_addresses: list
    coe_version: str
    container_version: str
    labels: dict
    health_status: str
    health_status_reason: dict
    fixed_network: str
    fixed_subnet: str
    project_id: str
    user_id: str
    created_at: str
    updated_at: str


class ClusterTemplate(TypedDict, total=False):
    uuid: str
    name: str
    image_id: str
    keypair_id: str
    external_network_id: str
    fixed_network: str
    fixed_subnet: str
    dns_nameserver: str
    master_flavor_id: str
    flavor_id: str
    coe: str
    network_driver: str
    volume_driver: str
    docker_volume_size: int
    http_proxy: str
    https_proxy: str
    no_proxy: str
    labels: dict
    tls_disabled: bool
    public: bool
    registry_enabled: bool
    server_type: str
    cluster_distro: str
    hidden: bool


class NodeGroup(TypedDict, total=False):
    uuid: str
    name: str
    cluster_id: str
    project_id: str
    docker_volume_size: int
    labels: dict
    flavor_id: str
    image_id: str
    node_addresses: list
    node_count: int
    role: str
    max_node_count: int
    min_node_count: int
    is_default: bool
    status: str
    status_reason: str
    created_at: str
    updated_at: str
