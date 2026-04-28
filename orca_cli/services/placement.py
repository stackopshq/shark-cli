"""High-level operations on OpenStack Placement resources."""

from __future__ import annotations

from typing import Any

from orca_cli.core.client import OrcaClient
from orca_cli.core.exceptions import APIError
from orca_cli.models.placement import (
    Allocation,
    AllocationCandidate,
    Inventory,
    ProviderUsages,
    ResourceClass,
    ResourceProvider,
    Trait,
)

# Placement microversion 1.20 (Stein, 2019) makes POST /resource_providers
# return the full provider object in the body — earlier versions returned
# 201 with an empty body, forcing a GET round-trip to fetch the UUID.
_PH_HEADER = {"OpenStack-API-Version": "placement 1.20"}


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
                                params=params, headers=_ph())
        return data.get("resource_providers", [])

    def get_provider(self, uuid: str, *,
                     headers: dict[str, str] | None = None) -> ResourceProvider:
        return self._client.get(f"{self._base}/resource_providers/{uuid}",
                                headers=_ph(headers))

    def create_provider(self, body: dict[str, Any]) -> ResourceProvider:
        data = self._client.post(f"{self._base}/resource_providers",
                                 json=body, headers=_ph())
        return data if data else {}

    def update_provider(self, uuid: str,
                        body: dict[str, Any]) -> ResourceProvider:
        data = self._client.put(f"{self._base}/resource_providers/{uuid}",
                                json=body, headers=_ph())
        return data if data else {}

    def delete_provider(self, uuid: str) -> None:
        self._client.delete(f"{self._base}/resource_providers/{uuid}",
                            headers=_ph())

    # ── inventories ────────────────────────────────────────────────────

    def find_inventories(self, uuid: str) -> dict:
        return self._client.get(
            f"{self._base}/resource_providers/{uuid}/inventories",
            headers=_ph(),
        )

    def get_inventory(self, uuid: str, resource_class: str) -> Inventory:
        return self._client.get(
            f"{self._base}/resource_providers/{uuid}"
            f"/inventories/{resource_class}",
            headers=_ph(),
        )

    def set_inventory(self, uuid: str, resource_class: str,
                      body: dict[str, Any]) -> Inventory:
        # PUT /inventories/{rc} requires the inventory to already exist
        # (Placement returns 400 "No inventory of class X found" otherwise).
        # POST /inventories creates a new one. Try POST first, then fall
        # back to PUT for updates.
        post_body = {**body, "resource_class": resource_class}
        try:
            data = self._client.post(
                f"{self._base}/resource_providers/{uuid}/inventories",
                json=post_body, headers=_ph(),
            )
            return data if data else {}
        except APIError as exc:
            # 409 Conflict means the inventory already exists → use PUT.
            if exc.status_code != 409:
                raise
            data = self._client.put(
                f"{self._base}/resource_providers/{uuid}"
                f"/inventories/{resource_class}",
                json=body, headers=_ph(),
            )
            return data if data else {}

    def delete_inventory(self, uuid: str, resource_class: str) -> None:
        self._client.delete(
            f"{self._base}/resource_providers/{uuid}"
            f"/inventories/{resource_class}",
            headers=_ph(),
        )

    def delete_all_inventories(self, uuid: str) -> None:
        self._client.delete(
            f"{self._base}/resource_providers/{uuid}/inventories",
            headers=_ph(),
        )

    # ── usages ─────────────────────────────────────────────────────────

    def get_provider_usages(self, uuid: str) -> ProviderUsages:
        return self._client.get(
            f"{self._base}/resource_providers/{uuid}/usages",
            headers=_ph(),
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
        # Placement API requires {"name": "..."} in the body. Using POST
        # to /resource_classes (microversion 1.2+) is the canonical path;
        # PUT /resource_classes/{name} requires the same body shape, not
        # an empty {}.
        self._client.post(f"{self._base}/resource_classes",
                          json={"name": name}, headers=_ph())

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
            f"{self._base}/allocations/{consumer_uuid}",
            headers=_ph(),
        )

    def set_allocations(self, consumer_uuid: str,
                        body: dict[str, Any]) -> None:
        self._client.put(
            f"{self._base}/allocations/{consumer_uuid}", json=body,
            headers=_ph(),
        )

    def delete_allocations(self, consumer_uuid: str) -> None:
        self._client.delete(f"{self._base}/allocations/{consumer_uuid}",
                            headers=_ph())

    # ── allocation candidates ──────────────────────────────────────────

    def find_allocation_candidates(
        self, *, params: dict[str, Any] | None = None,
    ) -> AllocationCandidate:
        return self._client.get(
            f"{self._base}/allocation_candidates", params=params,
            headers=_ph(),
        )

    # ── aggregates ─────────────────────────────────────────────────────

    def get_provider_aggregates(self, uuid: str) -> dict:
        return self._client.get(
            f"{self._base}/resource_providers/{uuid}/aggregates",
            headers=_ph(),
        )

    def set_provider_aggregates(self, uuid: str,
                                body: dict[str, Any]) -> dict:
        return self._client.put(
            f"{self._base}/resource_providers/{uuid}/aggregates",
            json=body, headers=_ph(),
        ) or {}
