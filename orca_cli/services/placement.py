"""High-level operations on OpenStack Placement resources."""

from __future__ import annotations

from typing import Any

from orca_cli.core.client import OrcaClient
from orca_cli.models.placement import (
    Allocation,
    AllocationCandidate,
    Inventory,
    ProviderUsages,
    ResourceClass,
    ResourceProvider,
    Trait,
)

_PH_HEADER = {"OpenStack-API-Version": "placement 1.6"}


def _ph(extra: dict | None = None) -> dict:
    if extra:
        merged = {**_PH_HEADER, **extra}
        return merged
    return dict(_PH_HEADER)


class PlacementService:
    """Typed wrapper around Placement endpoints."""

    def __init__(self, client: OrcaClient) -> None:
        self._client = client
        self._base = client.placement_url

    # ── resource providers ─────────────────────────────────────────────

    def find_providers(
        self, *, params: dict[str, Any] | None = None,
    ) -> list[ResourceProvider]:
        data = self._client.get(f"{self._base}/resource_providers",
                                params=params)
        return data.get("resource_providers", [])

    def get_provider(self, uuid: str, *,
                     headers: dict[str, str] | None = None) -> ResourceProvider:
        return self._client.get(f"{self._base}/resource_providers/{uuid}",
                                headers=headers)

    def create_provider(self, body: dict[str, Any]) -> ResourceProvider:
        data = self._client.post(f"{self._base}/resource_providers",
                                 json=body)
        return data if data else {}

    def update_provider(self, uuid: str,
                        body: dict[str, Any]) -> ResourceProvider:
        data = self._client.put(f"{self._base}/resource_providers/{uuid}",
                                json=body)
        return data if data else {}

    def delete_provider(self, uuid: str) -> None:
        self._client.delete(f"{self._base}/resource_providers/{uuid}")

    # ── inventories ────────────────────────────────────────────────────

    def find_inventories(self, uuid: str) -> dict:
        return self._client.get(
            f"{self._base}/resource_providers/{uuid}/inventories"
        )

    def set_inventory(self, uuid: str, resource_class: str,
                      body: dict[str, Any]) -> Inventory:
        data = self._client.put(
            f"{self._base}/resource_providers/{uuid}"
            f"/inventories/{resource_class}",
            json=body,
        )
        return data if data else {}

    def delete_inventory(self, uuid: str, resource_class: str) -> None:
        self._client.delete(
            f"{self._base}/resource_providers/{uuid}"
            f"/inventories/{resource_class}"
        )

    # ── usages ─────────────────────────────────────────────────────────

    def get_provider_usages(self, uuid: str) -> ProviderUsages:
        return self._client.get(
            f"{self._base}/resource_providers/{uuid}/usages"
        )

    def get_project_usages(
        self, *, params: dict[str, Any] | None = None,
    ) -> dict:
        return self._client.get(f"{self._base}/usages",
                                params=params, headers=_ph())

    # ── resource classes ───────────────────────────────────────────────

    def find_resource_classes(self) -> list[ResourceClass]:
        data = self._client.get(f"{self._base}/resource_classes",
                                headers=_ph())
        return data.get("resource_classes", [])

    def get_resource_class(self, name: str) -> ResourceClass:
        return self._client.get(f"{self._base}/resource_classes/{name}",
                                headers=_ph())

    def create_resource_class(self, name: str) -> None:
        self._client.put(f"{self._base}/resource_classes/{name}",
                         json={}, headers=_ph())

    def delete_resource_class(self, name: str) -> None:
        self._client.delete(f"{self._base}/resource_classes/{name}",
                            headers=_ph())

    # ── traits ─────────────────────────────────────────────────────────

    def find_traits(self, *,
                    params: dict[str, Any] | None = None) -> list[Trait]:
        data = self._client.get(f"{self._base}/traits",
                                params=params, headers=_ph())
        return data.get("traits", [])

    def create_trait(self, name: str) -> None:
        self._client.put(f"{self._base}/traits/{name}",
                         json={}, headers=_ph())

    def delete_trait(self, name: str) -> None:
        self._client.delete(f"{self._base}/traits/{name}", headers=_ph())

    def find_provider_traits(self, uuid: str) -> dict:
        return self._client.get(
            f"{self._base}/resource_providers/{uuid}/traits",
            headers=_ph(),
        )

    def set_provider_traits(self, uuid: str,
                            body: dict[str, Any]) -> dict:
        return self._client.put(
            f"{self._base}/resource_providers/{uuid}/traits",
            json=body, headers=_ph(),
        ) or {}

    def delete_provider_traits(self, uuid: str) -> None:
        self._client.delete(
            f"{self._base}/resource_providers/{uuid}/traits",
            headers=_ph(),
        )

    # ── allocations ────────────────────────────────────────────────────

    def get_allocations(self, consumer_uuid: str) -> Allocation:
        return self._client.get(
            f"{self._base}/allocations/{consumer_uuid}"
        )

    def set_allocations(self, consumer_uuid: str,
                        body: dict[str, Any]) -> None:
        self._client.put(
            f"{self._base}/allocations/{consumer_uuid}", json=body,
        )

    def delete_allocations(self, consumer_uuid: str) -> None:
        self._client.delete(f"{self._base}/allocations/{consumer_uuid}")

    # ── allocation candidates ──────────────────────────────────────────

    def find_allocation_candidates(
        self, *, params: dict[str, Any] | None = None,
    ) -> AllocationCandidate:
        return self._client.get(
            f"{self._base}/allocation_candidates", params=params,
        )

    # ── aggregates ─────────────────────────────────────────────────────

    def get_provider_aggregates(self, uuid: str) -> dict:
        return self._client.get(
            f"{self._base}/resource_providers/{uuid}/aggregates"
        )

    def set_provider_aggregates(self, uuid: str,
                                body: dict[str, Any]) -> dict:
        return self._client.put(
            f"{self._base}/resource_providers/{uuid}/aggregates",
            json=body,
        ) or {}
