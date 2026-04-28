"""Typed views of Nova resources outside of ``/servers`` (only the fields
orca reads). Server-related TypedDicts live in ``orca_cli.models.server``.
"""

from __future__ import annotations

from typing import TypedDict

# Nova exposes colon-prefixed keys ("OS-FLV-EXT-DATA:ephemeral" etc.);
# the alternative TypedDict syntax handles them.
Flavor = TypedDict(
    "Flavor",
    {
        "id": str,
        "name": str,
        "description": str,
        "vcpus": int,
        "ram": int,
        "disk": int,
        "swap": int,
        "ephemeral": int,
        "rxtx_factor": float,
        "is_public": bool,
        "disabled": bool,
        "extra_specs": dict,
        "OS-FLV-DISABLED:disabled": bool,
        "OS-FLV-EXT-DATA:ephemeral": int,
        "os-flavor-access:is_public": bool,
    },
    total=False,
)


class FlavorAccess(TypedDict, total=False):
    flavor_id: str
    tenant_id: str


class Keypair(TypedDict, total=False):
    id: int
    name: str
    type: str
    fingerprint: str
    public_key: str
    private_key: str
    user_id: str
    created_at: str


class Aggregate(TypedDict, total=False):
    id: int
    name: str
    availability_zone: str
    hosts: list
    metadata: dict
    created_at: str
    updated_at: str
    deleted: bool
    deleted_at: str


class Hypervisor(TypedDict, total=False):
    id: str
    hypervisor_hostname: str
    hypervisor_type: str
    hypervisor_version: int
    host_ip: str
    state: str
    status: str
    vcpus: int
    vcpus_used: int
    memory_mb: int
    memory_mb_used: int
    local_gb: int
    local_gb_used: int
    free_ram_mb: int
    free_disk_gb: int
    running_vms: int
    current_workload: int
    disk_available_least: int
    cpu_info: dict
    service: dict
    uptime: str


class HypervisorStatistics(TypedDict, total=False):
    count: int
    vcpus: int
    vcpus_used: int
    memory_mb: int
    memory_mb_used: int
    local_gb: int
    local_gb_used: int
    free_ram_mb: int
    free_disk_gb: int
    current_workload: int
    running_vms: int
    disk_available_least: int


class AvailabilityZone(TypedDict, total=False):
    zoneName: str
    zoneState: dict
    hosts: dict


class ComputeService(TypedDict, total=False):
    id: str
    binary: str
    host: str
    zone: str
    status: str
    state: str
    disabled_reason: str
    forced_down: bool
    updated_at: str
    DEFAULT: str


class ServerGroup(TypedDict, total=False):
    id: str
    name: str
    policies: list
    policy: str
    rules: dict
    members: list
    metadata: dict
    project_id: str
    user_id: str


class TenantUsage(TypedDict, total=False):
    tenant_id: str
    start: str
    stop: str
    total_hours: float
    total_vcpus_usage: float
    total_memory_mb_usage: float
    total_local_gb_usage: float
    server_usages: list


class AbsoluteLimits(TypedDict, total=False):
    maxTotalCores: int
    maxTotalInstances: int
    maxTotalRAMSize: int
    maxTotalKeypairs: int
    maxTotalFloatingIps: int
    maxServerMeta: int
    maxImageMeta: int
    maxPersonality: int
    maxPersonalitySize: int
    maxServerGroups: int
    maxServerGroupMembers: int
    maxSecurityGroups: int
    maxSecurityGroupRules: int
    totalCoresUsed: int
    totalInstancesUsed: int
    totalRAMUsed: int
    totalFloatingIpsUsed: int
    totalSecurityGroupsUsed: int
    totalServerGroupsUsed: int
