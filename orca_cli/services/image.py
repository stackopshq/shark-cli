"""High-level operations on Glance images."""

from __future__ import annotations

import json as _json
from typing import Any

from orca_cli.core.client import OrcaClient
from orca_cli.models.image import Image, ImageMember, ImageStore, ImageTask


class ImageService:
    """Typed wrapper around the Glance ``/v2`` endpoints.

    Owns URL construction for images, members, tags, cache, tasks, stores
    and the v2 import API. Retry, auth and streaming live in OrcaClient —
    the service is purely a translation layer between Glance and the typed
    model.
    """

    def __init__(self, client: OrcaClient) -> None:
        self._client = client
        self._base = f"{client.image_url}/v2"

    # ── images: reads ──────────────────────────────────────────────────

    def find(self, *, params: dict[str, Any] | None = None) -> list[Image]:
        data = self._client.get(f"{self._base}/images", params=params)
        return data.get("images", [])

    def find_all(self, page_size: int = 1000, *,
                 params: dict[str, Any] | None = None) -> list[Image]:
        """Paginate through every image (no silent cap)."""
        return self._client.paginate(f"{self._base}/images", "images",
                                     page_size=page_size, params=params)

    def get(self, image_id: str) -> Image:
        return self._client.get(f"{self._base}/images/{image_id}")

    # ── images: writes ─────────────────────────────────────────────────

    def create(self, body: dict[str, Any]) -> Image:
        """POST /v2/images — Glance returns the image body directly (no wrapper)."""
        data = self._client.post(f"{self._base}/images", json=body)
        return data if data else {}

    def update(self, image_id: str, ops: list[dict[str, Any]]) -> Image:
        """Apply a JSON-Patch document (RFC 6902, Glance media type)."""
        data = self._client.patch(
            f"{self._base}/images/{image_id}",
            content=_json.dumps(ops).encode(),
            content_type="application/openstack-images-v2.1-json-patch",
        )
        return data if data else {}

    def delete(self, image_id: str) -> None:
        self._client.delete(f"{self._base}/images/{image_id}")

    def deactivate(self, image_id: str) -> None:
        self._client.post(f"{self._base}/images/{image_id}/actions/deactivate")

    def reactivate(self, image_id: str) -> None:
        self._client.post(f"{self._base}/images/{image_id}/actions/reactivate")

    # ── image data: file / stage / download ────────────────────────────

    def upload(self, image_id: str, *,
               content: Any, content_length: int | None = None) -> None:
        """Upload image binary (PUT /v2/images/{id}/file).

        ``content`` may be a file-like object or an iterable yielding bytes
        (the latter lets callers wrap the stream with a progress bar).
        Raises :class:`APIError` / :class:`AuthenticationError` /
        :class:`PermissionDeniedError` on non-2xx.
        """
        self._stream_put(f"{self._base}/images/{image_id}/file",
                         content=content, content_length=content_length)

    def stage(self, image_id: str, *,
              content: Any, content_length: int | None = None) -> None:
        """Upload binary into the staging area (PUT /v2/images/{id}/stage)."""
        self._stream_put(f"{self._base}/images/{image_id}/stage",
                         content=content, content_length=content_length)

    def _stream_put(self, url: str, *,
                    content: Any, content_length: int | None) -> None:
        from orca_cli.core.exceptions import APIError, AuthenticationError, PermissionDeniedError
        resp = self._client.put_stream(
            url, content=content,
            content_type="application/octet-stream",
            content_length=content_length,
        )
        if resp.status_code == 401:
            raise AuthenticationError()
        if resp.status_code == 403:
            raise PermissionDeniedError()
        if not resp.is_success:
            raise APIError(resp.status_code, resp.text[:300])

    def download_url(self, image_id: str) -> str:
        """Return the URL to stream image binary from. Use ``client.get_stream``."""
        return f"{self._base}/images/{image_id}/file"

    def upload_url(self, image_id: str) -> str:
        return f"{self._base}/images/{image_id}/file"

    def stage_url(self, image_id: str) -> str:
        return f"{self._base}/images/{image_id}/stage"

    def import_(self, image_id: str, method: str, *,
                uri: str | None = None,
                stores: list[str] | None = None) -> None:
        """Trigger the Glance v2 import workflow."""
        method_body: dict[str, Any] = {"name": method}
        if uri:
            method_body["uri"] = uri
        body: dict[str, Any] = {"method": method_body}
        if stores:
            body["stores"] = list(stores)
        self._client.post(f"{self._base}/images/{image_id}/import", json=body)

    # ── tags ───────────────────────────────────────────────────────────

    def add_tag(self, image_id: str, tag: str) -> None:
        self._client.put(f"{self._base}/images/{image_id}/tags/{tag}")

    def delete_tag(self, image_id: str, tag: str) -> None:
        self._client.delete(f"{self._base}/images/{image_id}/tags/{tag}")

    # ── members (sharing) ──────────────────────────────────────────────

    def list_members(self, image_id: str) -> list[ImageMember]:
        data = self._client.get(f"{self._base}/images/{image_id}/members")
        return data.get("members", []) if data else []

    def get_member(self, image_id: str, member_id: str) -> ImageMember:
        return self._client.get(f"{self._base}/images/{image_id}/members/{member_id}")

    def add_member(self, image_id: str, member_id: str) -> ImageMember:
        data = self._client.post(
            f"{self._base}/images/{image_id}/members",
            json={"member": member_id},
        )
        return data if data else {}

    def delete_member(self, image_id: str, member_id: str) -> None:
        self._client.delete(f"{self._base}/images/{image_id}/members/{member_id}")

    def set_member_status(self, image_id: str, member_id: str,
                          status: str) -> ImageMember:
        data = self._client.put(
            f"{self._base}/images/{image_id}/members/{member_id}",
            json={"status": status},
        )
        return data if data else {}

    # ── cache (admin) ──────────────────────────────────────────────────

    def list_cache(self) -> dict[str, list[str]]:
        """Return ``{"cached_images": [...], "queued_images": [...]}``."""
        data = self._client.get(f"{self._base}/cache")
        return data if data else {}

    def cache_queue(self, image_id: str) -> None:
        self._client.put(f"{self._base}/cache/{image_id}")

    def cache_delete(self, image_id: str) -> None:
        self._client.delete(f"{self._base}/cache/{image_id}")

    def cache_clear(self) -> None:
        self._client.delete(f"{self._base}/cache")

    # ── stores (multi-backend) ─────────────────────────────────────────

    def list_stores(self, *, detail: bool = False) -> list[ImageStore]:
        suffix = "/info/stores/detail" if detail else "/info/stores"
        data = self._client.get(f"{self._base}{suffix}")
        return data.get("stores", []) if data else []

    # ── async tasks ────────────────────────────────────────────────────

    def list_tasks(self, *, task_type: str | None = None,
                   status: str | None = None) -> list[ImageTask]:
        params: dict[str, Any] = {}
        if task_type:
            params["type"] = task_type
        if status:
            params["status"] = status
        data = self._client.get(f"{self._base}/tasks", params=params or None)
        return data.get("tasks", []) if isinstance(data, dict) else []

    def get_task(self, task_id: str) -> ImageTask:
        return self._client.get(f"{self._base}/tasks/{task_id}")

    # ── convenience: os_distro for cross-service SSH user detection ────

    def get_distro(self, image_id: str) -> str:
        """Return ``os_distro`` for *image_id*, lower-cased. Never raises."""
        try:
            data = self.get(image_id)
        except Exception:
            return ""
        return (data.get("os_distro") or "").lower()

    # ── streaming download (returns a context-managed response) ────────

    def stream_download(self, image_id: str) -> Any:
        """Open a streaming download for image binary data.

        The caller is expected to use the returned object as a context
        manager (``with service.stream_download(id) as resp: ...``).
        """
        return self._client.get_stream(f"{self._base}/images/{image_id}/file")


__all__ = ["ImageService"]
