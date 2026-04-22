"""High-level operations on Designate DNS resources."""

from __future__ import annotations

from typing import Any

from orca_cli.core.client import OrcaClient
from orca_cli.models.dns import Recordset, Tld, Zone, ZoneTransferRequest


class DnsService:
    """Typed wrapper around Designate v2 endpoints."""

    def __init__(self, client: OrcaClient) -> None:
        self._client = client
        self._base = f"{client.dns_url}/v2"

    # ── zones ──────────────────────────────────────────────────────────

    def find_zones(self, *,
                   params: dict[str, Any] | None = None,
                   headers: dict[str, str] | None = None) -> list[Zone]:
        kwargs: dict[str, Any] = {}
        if params is not None:
            kwargs["params"] = params
        if headers is not None:
            kwargs["headers"] = headers
        data = self._client.get(f"{self._base}/zones", **kwargs)
        return data.get("zones", [])

    def get_zone(self, zone_id: str) -> Zone:
        data = self._client.get(f"{self._base}/zones/{zone_id}")
        return data.get("zone", data)

    def create_zone(self, body: dict[str, Any]) -> Zone:
        data = self._client.post(f"{self._base}/zones", json=body)
        return data.get("zone", data) if data else {}

    def update_zone(self, zone_id: str, body: dict[str, Any]) -> Zone:
        data = self._client.patch(f"{self._base}/zones/{zone_id}", json=body)
        return data.get("zone", data) if data else {}

    def delete_zone(self, zone_id: str) -> None:
        self._client.delete(f"{self._base}/zones/{zone_id}")

    # ── recordsets ─────────────────────────────────────────────────────

    def find_recordsets(
        self, zone_id: str, *,
        params: dict[str, Any] | None = None,
    ) -> list[Recordset]:
        data = self._client.get(
            f"{self._base}/zones/{zone_id}/recordsets",
            params=params,
        )
        return data.get("recordsets", [])

    def find_all_recordsets(self, *,
                            params: dict[str, Any] | None = None) -> list[Recordset]:
        """All recordsets across zones (no zone filter)."""
        data = self._client.get(f"{self._base}/recordsets", params=params)
        return data.get("recordsets", [])

    def get_recordset(self, zone_id: str, recordset_id: str) -> Recordset:
        data = self._client.get(
            f"{self._base}/zones/{zone_id}/recordsets/{recordset_id}"
        )
        return data.get("recordset", data)

    def create_recordset(self, zone_id: str,
                         body: dict[str, Any]) -> Recordset:
        data = self._client.post(
            f"{self._base}/zones/{zone_id}/recordsets",
            json=body,
        )
        return data.get("recordset", data) if data else {}

    def update_recordset(self, zone_id: str, recordset_id: str,
                         body: dict[str, Any]) -> Recordset:
        data = self._client.put(
            f"{self._base}/zones/{zone_id}/recordsets/{recordset_id}",
            json=body,
        )
        return data.get("recordset", data) if data else {}

    def delete_recordset(self, zone_id: str, recordset_id: str) -> None:
        self._client.delete(
            f"{self._base}/zones/{zone_id}/recordsets/{recordset_id}"
        )

    # ── zone tasks: export/import ──────────────────────────────────────

    def export_zone(self, zone_id: str) -> dict:
        return self._client.post(
            f"{self._base}/zones/{zone_id}/tasks/export",
        ) or {}

    def get_export_task(self, export_id: str) -> dict:
        return self._client.get(
            f"{self._base}/zones/tasks/exports/{export_id}"
        ) or {}

    def get_import_task(self, import_id: str) -> dict:
        return self._client.get(
            f"{self._base}/zones/tasks/imports/{import_id}"
        ) or {}

    # ── zone transfer requests ─────────────────────────────────────────

    def create_transfer_request(
        self, zone_id: str, body: dict[str, Any],
    ) -> ZoneTransferRequest:
        data = self._client.post(
            f"{self._base}/zones/{zone_id}/tasks/transfer_requests",
            json=body,
        )
        return data.get("transfer_request", data) if data else {}

    def find_transfer_requests(self) -> list[ZoneTransferRequest]:
        data = self._client.get(
            f"{self._base}/zones/tasks/transfer_requests"
        )
        return data.get("transfer_requests", [])

    def get_transfer_request(
        self, transfer_id: str,
    ) -> ZoneTransferRequest:
        data = self._client.get(
            f"{self._base}/zones/tasks/transfer_requests/{transfer_id}"
        )
        return data.get("transfer_request", data)

    def delete_transfer_request(self, transfer_id: str) -> None:
        self._client.delete(
            f"{self._base}/zones/tasks/transfer_requests/{transfer_id}"
        )

    def accept_transfer(self, body: dict[str, Any]) -> dict:
        return self._client.post(
            f"{self._base}/zones/tasks/transfer_accepts",
            json=body,
        ) or {}

    # ── reverse DNS (PTR) ──────────────────────────────────────────────

    def find_reverse_floatingips(self) -> list[dict]:
        data = self._client.get(f"{self._base}/reverse/floatingips")
        return data.get("floatingips", [])

    # ── TLDs ───────────────────────────────────────────────────────────

    def find_tlds(self) -> list[Tld]:
        data = self._client.get(f"{self._base}/tlds")
        return data.get("tlds", [])

    def create_tld(self, body: dict[str, Any]) -> Tld:
        data = self._client.post(f"{self._base}/tlds", json=body)
        return data.get("tld", data) if data else {}

    def delete_tld(self, tld_id: str) -> None:
        self._client.delete(f"{self._base}/tlds/{tld_id}")
