"""High-level operations on Designate DNS resources."""

from __future__ import annotations

from typing import Any

from orca_cli.core.client import OrcaClient, with_version
from orca_cli.models.dns import Recordset, Tld, Zone, ZoneTransferRequest


class DnsService:
    """Typed wrapper around Designate v2 endpoints."""

    def __init__(self, client: OrcaClient) -> None:
        self._client = client
        self._base = with_version(client.dns_url, "v2")

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

    def fetch_export_text(self, export_id: str) -> str:
        """Download the BIND-format zone body for a completed export task.

        The Designate ``/export`` endpoint returns ``text/dns`` rather than
        JSON, so the standard ``client.get`` helper would mis-parse it. The
        service uses ``client.get_stream`` and reads the response body.
        """
        url = f"{self._base}/zones/tasks/exports/{export_id}/export"
        with self._client.get_stream(
            url, extra_headers={"Accept": "text/dns"},
        ) as resp:
            if resp.status_code != 200:
                resp.read()
                from orca_cli.core.exceptions import APIError
                raise APIError(resp.status_code, resp.text[:300])
            resp.read()
            return resp.text

    def import_zone_text(self, content: str) -> dict:
        """Submit a BIND-format zone body to the Designate import endpoint.

        Designate expects ``Content-Type: text/dns`` and a raw zone-file body
        (no JSON envelope). Returns the parsed JSON task descriptor.
        """
        url = f"{self._base}/zones/tasks/imports"
        resp = self._client.post_stream(
            url,
            content=content.encode() if isinstance(content, str) else content,
            content_type="text/dns",
        )
        if resp.status_code not in (200, 201, 202):
            from orca_cli.core.exceptions import APIError
            raise APIError(resp.status_code, resp.text[:300])
        try:
            return resp.json() or {}
        except ValueError:
            return {}

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

    # ── zone abandon / move (admin) ────────────────────────────────────

    def abandon_zone(self, zone_id: str) -> None:
        """Drop a zone from Designate without notifying the backend.

        Use only after manual cleanup of the underlying nameservers.
        """
        self._client.post(f"{self._base}/zones/{zone_id}/tasks/abandon")

    def axfr_zone(self, zone_id: str) -> None:
        """Trigger an AXFR zone transfer from the master servers."""
        self._client.post(f"{self._base}/zones/{zone_id}/tasks/xfr")

    # ── zone shares (Designate share API) ──────────────────────────────

    def find_shares(self, zone_id: str) -> list[dict]:
        data = self._client.get(f"{self._base}/zones/{zone_id}/shares")
        return data.get("shared_zones", [])

    def get_share(self, zone_id: str, share_id: str) -> dict:
        data = self._client.get(
            f"{self._base}/zones/{zone_id}/shares/{share_id}"
        )
        return data.get("shared_zone", data) if isinstance(data, dict) else {}

    def create_share(self, zone_id: str, target_project_id: str) -> dict:
        data = self._client.post(
            f"{self._base}/zones/{zone_id}/shares",
            json={"target_project_id": target_project_id},
        )
        return data.get("shared_zone", data) if data else {}

    def delete_share(self, zone_id: str, share_id: str) -> None:
        self._client.delete(
            f"{self._base}/zones/{zone_id}/shares/{share_id}"
        )

    # ── zone blacklists (admin: forbid certain domain patterns) ────────

    def find_blacklists(self) -> list[dict]:
        data = self._client.get(f"{self._base}/blacklists")
        return data.get("blacklists", [])

    def get_blacklist(self, blacklist_id: str) -> dict:
        data = self._client.get(f"{self._base}/blacklists/{blacklist_id}")
        return data.get("blacklist", data) if isinstance(data, dict) else {}

    def create_blacklist(self, body: dict[str, Any]) -> dict:
        data = self._client.post(f"{self._base}/blacklists", json=body)
        return data.get("blacklist", data) if data else {}

    def update_blacklist(self, blacklist_id: str,
                         body: dict[str, Any]) -> dict:
        data = self._client.patch(
            f"{self._base}/blacklists/{blacklist_id}", json=body,
        )
        return data.get("blacklist", data) if data else {}

    def delete_blacklist(self, blacklist_id: str) -> None:
        self._client.delete(f"{self._base}/blacklists/{blacklist_id}")

    # ── export / import detail helpers (per-task) ──────────────────────

    def find_exports(self) -> list[dict]:
        data = self._client.get(f"{self._base}/zones/tasks/exports")
        return data.get("exports", [])

    def delete_export(self, export_id: str) -> None:
        self._client.delete(
            f"{self._base}/zones/tasks/exports/{export_id}"
        )

    def find_imports(self) -> list[dict]:
        data = self._client.get(f"{self._base}/zones/tasks/imports")
        return data.get("imports", [])

    def delete_import(self, import_id: str) -> None:
        self._client.delete(
            f"{self._base}/zones/tasks/imports/{import_id}"
        )
