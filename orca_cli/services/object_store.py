"""High-level operations on Swift object-storage resources.

Swift's API is unlike the rest of OpenStack:

* HEAD returns metadata in headers (no JSON body).
* POST updates metadata via ``X-*-Meta-*`` headers and *must* have an
  empty body.
* Listing uses ``?format=json`` for parseable output.
* Object up/download is binary streaming with explicit
  ``Content-Length``.

Streaming I/O therefore goes through the public streaming helpers on
``OrcaClient`` (``put_stream``, ``get_stream``, ``post_no_body``,
``head_request``) so command modules never reach into the private
``client._http`` / ``client._headers()`` surface.
"""

from __future__ import annotations

from typing import Any

from orca_cli.core.client import OrcaClient
from orca_cli.core.exceptions import APIError, AuthenticationError, PermissionDeniedError
from orca_cli.models.object_store import Container, ObjectEntry


def _check_status(resp: Any) -> None:
    """Map Swift response status to the project's exception hierarchy."""
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
        resp = self._client.head_request(self._base)
        _check_status(resp)
        return dict(resp.headers)

    def post_account_metadata(self, metadata: dict[str, str]) -> None:
        """Set/remove account metadata via ``X-Account-Meta-*`` /
        ``X-Remove-Account-Meta-*`` headers.
        """
        resp = self._client.post_no_body(self._base, extra_headers=metadata)
        _check_status(resp)

    # ── containers ─────────────────────────────────────────────────────

    def find_containers(self) -> list[Container]:
        data = self._client.get(f"{self._base}?format=json")
        return data if isinstance(data, list) else []

    def head_container(self, name: str) -> dict[str, str]:
        resp = self._client.head_request(f"{self._base}/{name}")
        _check_status(resp)
        return dict(resp.headers)

    def create_container(
        self, name: str, *, headers: dict[str, str] | None = None,
    ) -> None:
        # PUT with empty body — use the streaming helper with content=b"".
        resp = self._client.put_stream(
            f"{self._base}/{name}",
            content=b"",
            content_length=0,
            extra_headers=headers,
        )
        _check_status(resp)

    def delete_container(self, name: str) -> None:
        self._client.delete(f"{self._base}/{name}")

    def post_container_metadata(
        self, name: str, metadata: dict[str, str],
    ) -> None:
        """Set ``X-Container-Meta-*`` headers on a container."""
        resp = self._client.post_no_body(
            f"{self._base}/{name}", extra_headers=metadata,
        )
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
        resp = self._client.head_request(f"{self._base}/{container}/{name}")
        _check_status(resp)
        return dict(resp.headers)

    def delete_object(self, container: str, name: str) -> None:
        self._client.delete(f"{self._base}/{container}/{name}")

    def post_object_metadata(
        self, container: str, name: str, metadata: dict[str, str],
    ) -> None:
        """Set ``X-Object-Meta-*`` headers on an object."""
        resp = self._client.post_no_body(
            f"{self._base}/{container}/{name}", extra_headers=metadata,
        )
        _check_status(resp)

    # ── streaming I/O ──────────────────────────────────────────────────

    def upload_object(
        self, container: str, name: str, *,
        content: Any,
        content_type: str = "application/octet-stream",
        content_length: int | None = None,
        query: str = "",
    ) -> None:
        """PUT object data from a file-like or iterable. Raises on non-2xx.

        ``query`` is appended verbatim after ``?`` — used for SLO manifest
        uploads (``multipart-manifest=put``).
        """
        url = f"{self._base}/{container}/{name}"
        if query:
            url = f"{url}?{query}"
        resp = self._client.put_stream(
            url,
            content=content,
            content_type=content_type,
            content_length=content_length,
        )
        _check_status(resp)

    def download_object(self, container: str, name: str):
        """Open a streaming GET on an object — caller uses it as a context
        manager and iterates ``resp.iter_bytes(...)``. Status checking is
        the caller's responsibility (so the chunked stream stays open while
        the body is consumed).
        """
        return self._client.get_stream(f"{self._base}/{container}/{name}")

    def fetch_object_bytes(self, container: str, name: str) -> bytes:
        """Read a small object fully into memory and return its bytes.

        Raises on non-2xx. For large objects use :meth:`download_object`.
        """
        with self.download_object(container, name) as resp:
            if not resp.is_success:
                resp.read()
                _check_status(resp)
            resp.read()
            return resp.content

    def object_url(self, container: str, name: str) -> str:
        """Return the raw URL for an object — kept for callers that build
        their own progress-tracked streams (SLO segment uploads).
        """
        return f"{self._base}/{container}/{name}"
