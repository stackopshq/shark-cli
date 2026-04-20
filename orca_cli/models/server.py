"""Typed view of the Nova server resource (only the fields orca reads)."""

from __future__ import annotations

from typing import TypedDict


class ServerFlavor(TypedDict, total=False):
    id: str
    original_name: str
    vcpus: int
    ram: int
    disk: int


class ServerAddress(TypedDict, total=False):
    addr: str
    version: int


# Server uses the alternative TypedDict syntax because Nova exposes a
# handful of OS-EXT-* fields whose names contain colons — those can't
# be expressed as Python identifiers in the class form.
Server = TypedDict(
    "Server",
    {
        "id": str,
        "name": str,
        "status": str,
        "flavor": ServerFlavor,
        "image": dict,
        "addresses": dict,
        "key_name": str,
        "created": str,
        "updated": str,
        "user_id": str,
        "tenant_id": str,
        "hostId": str,
        "accessIPv4": str,
        "accessIPv6": str,
        "config_drive": str,
        "progress": int,
        "metadata": dict,
        "tags": list,
        "security_groups": list,
        "os-extended-volumes:volumes_attached": list,
        "OS-EXT-STS:vm_state": str,
        "OS-EXT-STS:task_state": str,
        "OS-EXT-STS:power_state": int,
        "OS-EXT-AZ:availability_zone": str,
        "OS-EXT-SRV-ATTR:host": str,
        "OS-EXT-SRV-ATTR:hypervisor_hostname": str,
        "OS-EXT-SRV-ATTR:instance_name": str,
        "OS-DCF:diskConfig": str,
        "OS-SRV-USG:launched_at": str,
        "OS-SRV-USG:terminated_at": str,
    },
    total=False,
)
