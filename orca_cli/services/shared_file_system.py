"""High-level operations on Manila (shared file system) resources.

Manila uses a microversion header to opt into newer API features —
orca pins ``X-OpenStack-Manila-API-Version: 2.51`` (OpenStack Train),
which is old enough to be supported everywhere Manila ships, and new
enough to expose the unified ``/share-access-rules`` endpoint instead
of the legacy per-share action API.
"""

from __future__ import annotations

from typing import Any

from orca_cli.core.client import OrcaClient
from orca_cli.models.shared_file_system import (
    Share,
    ShareAccessRule,
    ShareSnapshot,
    ShareType,
)

# Microversion floor. Bump only with a clear reason: it directly
# affects the response shape that orca's models assume.
MANILA_MICROVERSION = "2.51"


class FileShareService:
    """Typed wrapper around Manila v2 endpoints."""

    def __init__(self, client: OrcaClient) -> None:
        self._client = client
        self._base = client.share_url

    # ── header injection ───────────────────────────────────────────────

    def _h(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        h = {"X-OpenStack-Manila-API-Version": MANILA_MICROVERSION}
        if extra:
            h.update(extra)
        return h

    # ── shares ─────────────────────────────────────────────────────────

    def find(self, *, detail: bool = True,
             params: dict[str, Any] | None = None) -> list[Share]:
        suffix = "/shares/detail" if detail else "/shares"
        data = self._client.get(f"{self._base}{suffix}",
                                params=params, headers=self._h())
        return data.get("shares", [])

    def get(self, share_id: str) -> Share:
        data = self._client.get(f"{self._base}/shares/{share_id}",
                                headers=self._h())
        return data.get("share", data)

    def create(self, body: dict[str, Any]) -> Share:
        # Manila wraps the body under "share".
        data = self._client.post(f"{self._base}/shares",
                                 json={"share": body}, headers=self._h())
        return data.get("share", data) if data else {}

    def update(self, share_id: str, body: dict[str, Any]) -> Share:
        data = self._client.put(f"{self._base}/shares/{share_id}",
                                json={"share": body}, headers=self._h())
        return data.get("share", data) if data else {}

    def delete(self, share_id: str) -> None:
        self._client.delete(f"{self._base}/shares/{share_id}",
                            headers=self._h())

    def extend(self, share_id: str, new_size: int) -> None:
        """Grow a share to *new_size* GB."""
        self._client.post(f"{self._base}/shares/{share_id}/action",
                          json={"extend": {"new_size": new_size}},
                          headers=self._h())

    def shrink(self, share_id: str, new_size: int) -> None:
        self._client.post(f"{self._base}/shares/{share_id}/action",
                          json={"shrink": {"new_size": new_size}},
                          headers=self._h())

    # ── access rules (unified API, microversion ≥ 2.45) ────────────────

    def find_access_rules(self, share_id: str) -> list[ShareAccessRule]:
        data = self._client.get(
            f"{self._base}/share-access-rules",
            params={"share_id": share_id}, headers=self._h(),
        )
        return data.get("access_list", [])

    def get_access_rule(self, access_id: str) -> ShareAccessRule:
        data = self._client.get(
            f"{self._base}/share-access-rules/{access_id}",
            headers=self._h(),
        )
        return data.get("access", data)

    def allow_access(self, share_id: str, access_type: str,
                     access_to: str, *, access_level: str = "rw",
                     metadata: dict | None = None) -> ShareAccessRule:
        body: dict[str, Any] = {
            "allow_access": {
                "access_type": access_type,
                "access_to": access_to,
                "access_level": access_level,
            }
        }
        if metadata:
            body["allow_access"]["metadata"] = metadata
        data = self._client.post(f"{self._base}/shares/{share_id}/action",
                                 json=body, headers=self._h())
        return data.get("access", data) if data else {}

    def deny_access(self, share_id: str, access_id: str) -> None:
        self._client.post(
            f"{self._base}/shares/{share_id}/action",
            json={"deny_access": {"access_id": access_id}},
            headers=self._h(),
        )

    # ── snapshots ──────────────────────────────────────────────────────

    def find_snapshots(self, *, detail: bool = True,
                       params: dict[str, Any] | None = None) -> list[ShareSnapshot]:
        suffix = "/snapshots/detail" if detail else "/snapshots"
        data = self._client.get(f"{self._base}{suffix}",
                                params=params, headers=self._h())
        return data.get("snapshots", [])

    def get_snapshot(self, snapshot_id: str) -> ShareSnapshot:
        data = self._client.get(f"{self._base}/snapshots/{snapshot_id}",
                                headers=self._h())
        return data.get("snapshot", data)

    def create_snapshot(self, share_id: str, *,
                        name: str | None = None,
                        description: str | None = None) -> ShareSnapshot:
        body: dict[str, Any] = {"share_id": share_id}
        if name:
            body["name"] = name
        if description:
            body["description"] = description
        data = self._client.post(f"{self._base}/snapshots",
                                 json={"snapshot": body}, headers=self._h())
        return data.get("snapshot", data) if data else {}

    def delete_snapshot(self, snapshot_id: str) -> None:
        self._client.delete(f"{self._base}/snapshots/{snapshot_id}",
                            headers=self._h())

    # ── types (read-only here; admin create lives in lot 2) ────────────

    def find_types(self) -> list[ShareType]:
        data = self._client.get(f"{self._base}/types", headers=self._h())
        return data.get("share_types", [])

    def get_type(self, type_id: str) -> ShareType:
        data = self._client.get(f"{self._base}/types/{type_id}",
                                headers=self._h())
        return data.get("share_type", data)


__all__ = ["FileShareService", "MANILA_MICROVERSION"]
