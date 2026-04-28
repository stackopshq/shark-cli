"""High-level operations on Nova compute resources outside ``/servers``.

Servers themselves live in :class:`orca_cli.services.server.ServerService`;
ComputeService covers flavors (+ extra-specs + access), keypairs,
aggregates (+ hosts + metadata + image cache), hypervisors, availability
zones, the ``os-services`` admin endpoint, server groups, tenant usage
and absolute limits.
"""

from __future__ import annotations

from typing import Any

from orca_cli.core.client import OrcaClient
from orca_cli.models.compute import (
    AbsoluteLimits,
    Aggregate,
    AvailabilityZone,
    Flavor,
    FlavorAccess,
    Hypervisor,
    HypervisorStatistics,
    Keypair,
    ServerGroup,
    TenantUsage,
)
from orca_cli.models.compute import (
    ComputeService as ComputeServiceModel,
)


class ComputeService:
    """Typed wrapper around Nova endpoints other than ``/servers``."""

    def __init__(self, client: OrcaClient) -> None:
        self._client = client
        self._base = client.compute_url

    # ── flavors ────────────────────────────────────────────────────────

    def find_flavors(self, *,
                     params: dict[str, Any] | None = None) -> list[Flavor]:
        data = self._client.get(f"{self._base}/flavors/detail", params=params)
        return data.get("flavors", [])

    def find_all_flavors(self, page_size: int = 1000, *,
                         params: dict[str, Any] | None = None) -> list[Flavor]:
        return self._client.paginate(f"{self._base}/flavors/detail", "flavors",
                                     page_size=page_size, params=params)

    def get_flavor(self, flavor_id: str) -> Flavor:
        data = self._client.get(f"{self._base}/flavors/{flavor_id}")
        return data.get("flavor", data)

    def create_flavor(self, body: dict[str, Any]) -> Flavor:
        data = self._client.post(f"{self._base}/flavors",
                                 json={"flavor": body})
        return data.get("flavor", data) if data else {}

    def delete_flavor(self, flavor_id: str) -> None:
        self._client.delete(f"{self._base}/flavors/{flavor_id}")

    def set_flavor_extra_specs(self, flavor_id: str,
                               specs: dict[str, str]) -> dict[str, str]:
        data = self._client.post(
            f"{self._base}/flavors/{flavor_id}/os-extra_specs",
            json={"extra_specs": specs},
        )
        return data.get("extra_specs", {}) if data else {}

    def unset_flavor_extra_spec(self, flavor_id: str, key: str) -> None:
        self._client.delete(
            f"{self._base}/flavors/{flavor_id}/os-extra_specs/{key}"
        )

    def list_flavor_access(self, flavor_id: str) -> list[FlavorAccess]:
        data = self._client.get(
            f"{self._base}/flavors/{flavor_id}/os-flavor-access"
        )
        return data.get("flavor_access", [])

    def add_flavor_access(self, flavor_id: str, tenant_id: str) -> None:
        self._client.post(f"{self._base}/flavors/{flavor_id}/action",
                          json={"addTenantAccess": {"tenant": tenant_id}})

    def remove_flavor_access(self, flavor_id: str, tenant_id: str) -> None:
        self._client.post(f"{self._base}/flavors/{flavor_id}/action",
                          json={"removeTenantAccess": {"tenant": tenant_id}})

    # ── keypairs ───────────────────────────────────────────────────────

    def find_keypairs(self) -> list[dict]:
        """Raw keypair wrappers ({"keypair": {...}}); call ``get_keypair``
        for the unwrapped form."""
        data = self._client.get(f"{self._base}/os-keypairs")
        return data.get("keypairs", [])

    def get_keypair(self, name: str) -> Keypair:
        data = self._client.get(f"{self._base}/os-keypairs/{name}")
        return data.get("keypair", data)

    def create_keypair(self, body: dict[str, Any]) -> Keypair:
        data = self._client.post(f"{self._base}/os-keypairs",
                                 json={"keypair": body})
        return data.get("keypair", data) if data else {}

    def delete_keypair(self, name: str) -> None:
        self._client.delete(f"{self._base}/os-keypairs/{name}")

    # ── aggregates ─────────────────────────────────────────────────────

    def find_aggregates(self) -> list[Aggregate]:
        data = self._client.get(f"{self._base}/os-aggregates")
        return data.get("aggregates", [])

    def get_aggregate(self, agg_id: str) -> Aggregate:
        data = self._client.get(f"{self._base}/os-aggregates/{agg_id}")
        return data.get("aggregate", data)

    def create_aggregate(self, body: dict[str, Any]) -> Aggregate:
        data = self._client.post(f"{self._base}/os-aggregates",
                                 json={"aggregate": body})
        return data.get("aggregate", data) if data else {}

    def update_aggregate(self, agg_id: str,
                         body: dict[str, Any]) -> Aggregate:
        data = self._client.put(f"{self._base}/os-aggregates/{agg_id}",
                                json={"aggregate": body})
        return data.get("aggregate", data) if data else {}

    def delete_aggregate(self, agg_id: str) -> None:
        self._client.delete(f"{self._base}/os-aggregates/{agg_id}")

    def add_aggregate_host(self, agg_id: str, host: str) -> Aggregate:
        data = self._client.post(f"{self._base}/os-aggregates/{agg_id}/action",
                                 json={"add_host": {"host": host}})
        return data.get("aggregate", data) if data else {}

    def remove_aggregate_host(self, agg_id: str, host: str) -> Aggregate:
        data = self._client.post(f"{self._base}/os-aggregates/{agg_id}/action",
                                 json={"remove_host": {"host": host}})
        return data.get("aggregate", data) if data else {}

    def set_aggregate_metadata(self, agg_id: str,
                               metadata: dict[str, Any]) -> Aggregate:
        data = self._client.post(
            f"{self._base}/os-aggregates/{agg_id}/action",
            json={"set_metadata": {"metadata": metadata}},
        )
        return data.get("aggregate", data) if data else {}

    def cache_aggregate_images(self, agg_id: str,
                               images: list[dict[str, str]]) -> None:
        self._client.post(f"{self._base}/os-aggregates/{agg_id}/images",
                          json={"cache": images})

    # ── hypervisors ────────────────────────────────────────────────────

    def find_hypervisors(self) -> list[Hypervisor]:
        data = self._client.get(f"{self._base}/os-hypervisors/detail")
        return data.get("hypervisors", [])

    def get_hypervisor(self, hyper_id: str) -> Hypervisor:
        data = self._client.get(f"{self._base}/os-hypervisors/{hyper_id}")
        return data.get("hypervisor", data)

    def hypervisor_statistics(self) -> HypervisorStatistics:
        data = self._client.get(f"{self._base}/os-hypervisors/statistics")
        return data.get("hypervisor_statistics", data)

    # ── availability zones ─────────────────────────────────────────────

    def find_availability_zones(self, *,
                                detail: bool = False) -> list[AvailabilityZone]:
        url = f"{self._base}/os-availability-zone"
        if detail:
            url += "/detail"
        data = self._client.get(url)
        return data.get("availabilityZoneInfo", [])

    # ── compute services (os-services) ─────────────────────────────────

    def find_services(
        self, *, params: dict[str, Any] | None = None,
    ) -> list[ComputeServiceModel]:
        data = self._client.get(f"{self._base}/os-services", params=params)
        return data.get("services", [])

    def update_service(self, service_id: str,
                       body: dict[str, Any]) -> ComputeServiceModel:
        data = self._client.put(f"{self._base}/os-services/{service_id}",
                                json=body)
        return data.get("service", data) if data else {}

    def delete_service(self, service_id: str) -> None:
        self._client.delete(f"{self._base}/os-services/{service_id}")

    # ── server groups ──────────────────────────────────────────────────

    def find_server_groups(
        self, *, params: dict[str, Any] | None = None,
    ) -> list[ServerGroup]:
        data = self._client.get(f"{self._base}/os-server-groups",
                                params=params)
        return data.get("server_groups", [])

    def get_server_group(self, group_id: str) -> ServerGroup:
        data = self._client.get(f"{self._base}/os-server-groups/{group_id}")
        return data.get("server_group", data)

    def create_server_group(self, body: dict[str, Any]) -> ServerGroup:
        data = self._client.post(f"{self._base}/os-server-groups",
                                 json={"server_group": body})
        return data.get("server_group", data) if data else {}

    def delete_server_group(self, group_id: str) -> None:
        self._client.delete(f"{self._base}/os-server-groups/{group_id}")

    # ── usage & limits ─────────────────────────────────────────────────

    def find_tenant_usages(
        self, *, params: dict[str, Any] | None = None,
    ) -> list[TenantUsage]:
        """All tenants usage (admin). Pass start/end/detailed in params."""
        data = self._client.get(
            f"{self._base}/os-simple-tenant-usage",
            params=params,
        )
        return data.get("tenant_usages", [])

    def get_tenant_usage(
        self, tenant_id: str, *,
        params: dict[str, Any] | None = None,
    ) -> TenantUsage:
        data = self._client.get(
            f"{self._base}/os-simple-tenant-usage/{tenant_id}",
            params=params,
        )
        return data.get("tenant_usage", data)

    def get_limits(self, *,
                   params: dict[str, Any] | None = None) -> AbsoluteLimits:
        data = self._client.get(f"{self._base}/limits", params=params)
        return data.get("limits", {}).get("absolute", {})
