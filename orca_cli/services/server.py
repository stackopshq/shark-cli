"""High-level operations on Nova servers."""

from __future__ import annotations

from typing import Any

from orca_cli.core.client import OrcaClient
from orca_cli.models.server import Server


class ServerService:
    """Typed wrapper around the Nova ``/servers`` endpoints.

    Owns URL construction; commands import this service instead of
    building ``f"{client.compute_url}/servers/..."`` strings themselves.
    Retry, auth, and rate-limit handling live in OrcaClient — the
    service is purely a translation layer between the Nova API and the
    typed model.
    """

    def __init__(self, client: OrcaClient) -> None:
        self._client = client
        self._base = f"{client.compute_url}/servers"

    # ── reads ──────────────────────────────────────────────────────────

    def find(self, limit: int = 50) -> list[Server]:
        """Return up to ``limit`` servers with their detail payload.

        Named ``find`` rather than ``list`` to avoid shadowing the
        builtin within the class scope (mypy then can't resolve
        ``list[Server]`` annotations on sibling methods).
        """
        data = self._client.get(f"{self._base}/detail", params={"limit": limit})
        return data.get("servers", [])

    def find_all(self, page_size: int = 1000) -> list[Server]:
        """Paginate through every server in the project (no silent cap)."""
        return self._client.paginate(f"{self._base}/detail", "servers",
                                     page_size=page_size)

    def get(self, server_id: str) -> Server:
        """Fetch one server by ID. Raises APIError if not found."""
        data = self._client.get(f"{self._base}/{server_id}")
        return data.get("server", data)

    # ── writes ─────────────────────────────────────────────────────────

    def delete(self, server_id: str) -> None:
        """Issue an asynchronous delete; the server transitions to
        DELETED state."""
        self._client.delete(f"{self._base}/{server_id}")

    def action(self, server_id: str, body: dict[str, Any]) -> None:
        """POST a Nova action verb (e.g. ``{"reboot": {"type": "SOFT"}}``)."""
        self._client.post(f"{self._base}/{server_id}/action", json=body)

    def start(self, server_id: str) -> None:
        self.action(server_id, {"os-start": None})

    def stop(self, server_id: str) -> None:
        self.action(server_id, {"os-stop": None})

    def reboot(self, server_id: str, *, hard: bool = False) -> None:
        self.action(server_id, {"reboot": {"type": "HARD" if hard else "SOFT"}})
