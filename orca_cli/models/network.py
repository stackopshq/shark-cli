"""Typed views of Neutron resources (only the fields orca reads)."""

from __future__ import annotations

from typing import TypedDict

# Neutron exposes a few colon-prefixed keys ("router:external",
# "provider:network_type", …); the alternative TypedDict syntax handles them.
Network = TypedDict(
    "Network",
    {
        "id": str,
        "name": str,
        "description": str,
        "status": str,
        "admin_state_up": bool,
        "shared": bool,
        "mtu": int,
        "subnets": list,
        "tenant_id": str,
        "project_id": str,
        "availability_zones": list,
        "availability_zone_hints": list,
        "tags": list,
        "created_at": str,
        "updated_at": str,
        "router:external": bool,
        "provider:network_type": str,
        "provider:physical_network": str,
        "provider:segmentation_id": int,
        "qos_policy_id": str,
        "port_security_enabled": bool,
        "is_default": bool,
        "dns_domain": str,
    },
    total=False,
)


class Subnet(TypedDict, total=False):
    id: str
    name: str
    description: str
    network_id: str
    cidr: str
    ip_version: int
    gateway_ip: str
    enable_dhcp: bool
    dns_nameservers: list
    host_routes: list
    allocation_pools: list
    subnetpool_id: str
    ipv6_address_mode: str
    ipv6_ra_mode: str
    tenant_id: str
    project_id: str
    tags: list
    created_at: str
    updated_at: str


class FixedIp(TypedDict, total=False):
    ip_address: str
    subnet_id: str


class AllowedAddressPair(TypedDict, total=False):
    ip_address: str
    mac_address: str


class BindingProfile(TypedDict, total=False):
    pass


# binding:* keys need the alternative syntax.
Port = TypedDict(
    "Port",
    {
        "id": str,
        "name": str,
        "description": str,
        "status": str,
        "admin_state_up": bool,
        "mac_address": str,
        "fixed_ips": list,
        "network_id": str,
        "device_id": str,
        "device_owner": str,
        "security_groups": list,
        "security_group_ids": list,
        "allowed_address_pairs": list,
        "tenant_id": str,
        "project_id": str,
        "dns_name": str,
        "dns_assignment": list,
        "port_security_enabled": bool,
        "qos_policy_id": str,
        "tags": list,
        "created_at": str,
        "updated_at": str,
        "binding:vif_type": str,
        "binding:vnic_type": str,
        "binding:host_id": str,
        "binding:profile": dict,
        "binding:vif_details": dict,
    },
    total=False,
)


class ExternalGatewayInfo(TypedDict, total=False):
    network_id: str
    enable_snat: bool
    external_fixed_ips: list


class Router(TypedDict, total=False):
    id: str
    name: str
    description: str
    status: str
    admin_state_up: bool
    distributed: bool
    ha: bool
    external_gateway_info: dict
    routes: list
    tenant_id: str
    project_id: str
    availability_zones: list
    availability_zone_hints: list
    flavor_id: str
    tags: list
    created_at: str
    updated_at: str


class FloatingIp(TypedDict, total=False):
    id: str
    description: str
    status: str
    floating_ip_address: str
    floating_network_id: str
    fixed_ip_address: str
    port_id: str
    router_id: str
    qos_policy_id: str
    tenant_id: str
    project_id: str
    dns_name: str
    dns_domain: str
    tags: list
    created_at: str
    updated_at: str


class SecurityGroupRule(TypedDict, total=False):
    id: str
    security_group_id: str
    direction: str
    ethertype: str
    protocol: str
    port_range_min: int
    port_range_max: int
    remote_ip_prefix: str
    remote_group_id: str
    description: str
    tenant_id: str
    project_id: str


class SecurityGroup(TypedDict, total=False):
    id: str
    name: str
    description: str
    security_group_rules: list
    stateful: bool
    tenant_id: str
    project_id: str
    tags: list
    created_at: str
    updated_at: str


class SubnetPool(TypedDict, total=False):
    id: str
    name: str
    description: str
    default_prefixlen: int
    min_prefixlen: int
    max_prefixlen: int
    default_quota: int
    ip_version: int
    prefixes: list
    shared: bool
    is_default: bool
    address_scope_id: str
    tenant_id: str
    project_id: str
    tags: list
    created_at: str
    updated_at: str


class Trunk(TypedDict, total=False):
    id: str
    name: str
    description: str
    status: str
    admin_state_up: bool
    port_id: str
    sub_ports: list
    tenant_id: str
    project_id: str
    tags: list
    created_at: str
    updated_at: str


class TrunkSubPort(TypedDict, total=False):
    port_id: str
    segmentation_type: str
    segmentation_id: int


class QosPolicy(TypedDict, total=False):
    id: str
    name: str
    description: str
    shared: bool
    is_default: bool
    rules: list
    tenant_id: str
    project_id: str
    tags: list
    created_at: str
    updated_at: str


class QosRule(TypedDict, total=False):
    id: str
    qos_policy_id: str
    max_kbps: int
    max_burst_kbps: int
    min_kbps: int
    min_kpps: int
    direction: str
    dscp_mark: int


Agent = TypedDict(
    "Agent",
    {
        "id": str,
        "agent_type": str,
        "binary": str,
        "host": str,
        "topic": str,
        "admin_state_up": bool,
        "alive": bool,
        "availability_zone": str,
        "description": str,
        "resources_synced": bool,
        "configurations": dict,
        "created_at": str,
        "started_at": str,
        "heartbeat_timestamp": str,
    },
    total=False,
)


class RbacPolicy(TypedDict, total=False):
    id: str
    object_id: str
    object_type: str
    action: str
    target_tenant: str
    target_project: str
    tenant_id: str
    project_id: str


class Segment(TypedDict, total=False):
    id: str
    name: str
    description: str
    network_id: str
    network_type: str
    physical_network: str
    segmentation_id: int


class AutoAllocatedTopology(TypedDict, total=False):
    id: str
    project_id: str
    tenant_id: str
