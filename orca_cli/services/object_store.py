"""High-level operations on Swift object-storage resources.

Swift's API is different from the rest of OpenStack: HEAD returns
metadata in headers, POST updates metadata without a JSON body,
listing uses ``?format=json`` for parseable output, and object
up/download is binary streaming. The service therefore:

* returns parsed lists for GET ``?format=json`` endpoints,
* exposes ``head_*`` methods that return the raw response headers,
* exposes ``post_metadata`` methods for metadata updates that go
  through the raw httpx client (``client._http``) — Swift requires
  no body for these, which ``OrcaClient.post`` does not support.

Binary uploads/downloads stay in the command modules for now: they
need streaming access to the underlying httpx client.
"""

from __future__ import annotations

from typing import Any

from orca_cli.core.client import OrcaClient
from orca_cli.core.exceptions import APIError, AuthenticationError, PermissionDeniedError
from orca_cli.models.object_store import Container, ObjectEntry


def _check_status(resp: Any) -> None:
    if resp.status_code == 401:
        raise AuthenticationError()
    if resp.status_code == 403:
        raise PermissionDeniedError()
    if not resp.is_success:
        raise APIError(resp.status_code, resp.text[:300])


class ObjectStoreService:
    """Typed wrapper around Swift account/container/object endpoints."""

    def __init__(self, client: OrcaClient) -> None:
        self._client = client
        self._base = client.object_store_url

    # ── account ────────────────────────────────────────────────────────

    def head_account(self) -> dict[str, str]:
        """Account-level headers (x-account-container-count etc.)."""
        resp = self._client._http.head(self._base,
                                       headers=self._client._headers())
        _check_status(resp)
        return dict(resp.headers)

    # ── containers ─────────────────────────────────────────────────────

    def find_containers(self) -> list[Container]:
        data = self._client.get(f"{self._base}?format=json")
        return data if isinstance(data, list) else []

    def head_container(self, name: str) -> dict[str, str]:
        resp = self._client._http.head(f"{self._base}/{name}",
                                       headers=self._client._headers())
        _check_status(resp)
        return dict(resp.headers)

    def create_container(
        self, name: str, *, headers: dict[str, str] | None = None,
    ) -> None:
        req_headers = self._client._headers()
        if headers:
            req_headers.update(headers)
        resp = self._client._http.put(f"{self._base}/{name}",
                                      headers=req_headers)
        _check_status(resp)

    def delete_container(self, name: str) -> None:
        self._client.delete(f"{self._base}/{name}")

    def post_container_metadata(
        self, name: str, metadata: dict[str, str],
    ) -> None:
        """Set ``X-Container-Meta-*`` headers on a container."""
        headers = self._client._headers()
        for k, v in metadata.items():
            headers[k] = v
        resp = self._client._http.post(f"{self._base}/{name}",
                                       headers=headers)
        _check_status(resp)

    # ── objects ────────────────────────────────────────────────────────

    def find_objects(
        self, container: str, *,
        prefix: str | None = None, delimiter: str | None = None,
    ) -> list[ObjectEntry]:
        params = "format=json"
        if prefix:
            params += f"&prefix={prefix}"
        if delimiter:
            params += f"&delimiter={delimiter}"
        data = self._client.get(f"{self._base}/{container}?{params}")
        return data if isinstance(data, list) else []

    def head_object(self, container: str, name: str) -> dict[str, str]:
        resp = self._client._http.head(
            f"{self._base}/{container}/{name}",
            headers=self._client._headers(),
        )
        _check_status(resp)
        return dict(resp.headers)

    def delete_object(self, container: str, name: str) -> None:
        self._client.delete(f"{self._base}/{container}/{name}")

    def post_object_metadata(
        self, container: str, name: str, metadata: dict[str, str],
    ) -> None:
        """Set ``X-Object-Meta-*`` headers on an object."""
        headers = self._client._headers()
        for k, v in metadata.items():
            headers[k] = v
        resp = self._client._http.post(
            f"{self._base}/{container}/{name}",
            headers=headers,
        )
        _check_status(resp)

    def object_url(self, container: str, name: str) -> str:
        """Return the raw URL for streaming upload/download."""
        return f"{self._base}/{container}/{name}"
