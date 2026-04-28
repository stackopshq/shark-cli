"""High-level operations on Heat orchestration resources."""

from __future__ import annotations

from typing import Any

from orca_cli.core.client import OrcaClient
from orca_cli.models.orchestration import (
    Stack,
    StackEvent,
    StackOutput,
    StackResource,
)


class OrchestrationService:
    """Typed wrapper around Heat endpoints.

    Stacks are addressed either by name or by a ``name/id`` tuple
    depending on the endpoint (Heat uses both). The service mirrors
    the API — callers pass the pieces that the endpoint needs.
    """

    def __init__(self, client: OrcaClient) -> None:
        self._client = client
        self._base = client.orchestration_url

    # ── stacks ─────────────────────────────────────────────────────────

    def find(self, *,
             params: dict[str, Any] | None = None,
             headers: dict[str, str] | None = None) -> list[Stack]:
        data = self._client.get(f"{self._base}/stacks",
                                params=params, headers=headers)
        return data.get("stacks", [])

    def find_all(self, page_size: int = 1000, *,
                 params: dict[str, Any] | None = None) -> list[Stack]:
        return self._client.paginate(f"{self._base}/stacks", "stacks",
                                     page_size=page_size, params=params)

    def get(self, name: str, stack_id: str | None = None) -> Stack:
        """Pass either the stack name (resolves canonical URL) or both
        ``name`` and ``stack_id`` (direct GET)."""
        if stack_id:
            data = self._client.get(f"{self._base}/stacks/{name}/{stack_id}")
        else:
            data = self._client.get(f"{self._base}/stacks/{name}")
        return data.get("stack", data)

    def create(self, body: dict[str, Any]) -> Stack:
        data = self._client.post(f"{self._base}/stacks", json=body)
        return data.get("stack", data) if data else {}

    def update(self, name: str, stack_id: str,
               body: dict[str, Any]) -> None:
        self._client.put(f"{self._base}/stacks/{name}/{stack_id}", json=body)

    def delete(self, name: str, stack_id: str) -> None:
        self._client.delete(f"{self._base}/stacks/{name}/{stack_id}")

    def action(self, name: str, stack_id: str,
               body: dict[str, Any]) -> dict | None:
        return self._client.post(
            f"{self._base}/stacks/{name}/{stack_id}/actions",
            json=body,
        )

    def abandon(self, name: str, stack_id: str) -> dict | None:
        return self._client.delete(
            f"{self._base}/stacks/{name}/{stack_id}/abandon"
        )

    # ── resources ──────────────────────────────────────────────────────

    def find_resources(self, name: str, stack_id: str) -> list[StackResource]:
        data = self._client.get(
            f"{self._base}/stacks/{name}/{stack_id}/resources"
        )
        return data.get("resources", [])

    def get_resource(self, name: str, stack_id: str,
                     resource_name: str) -> StackResource:
        data = self._client.get(
            f"{self._base}/stacks/{name}/{stack_id}/resources/{resource_name}"
        )
        return data.get("resource", data)

    # ── events ─────────────────────────────────────────────────────────

    def find_events(self, name: str, stack_id: str, *,
                    params: dict[str, Any] | None = None) -> list[StackEvent]:
        data = self._client.get(
            f"{self._base}/stacks/{name}/{stack_id}/events",
            params=params,
        )
        return data.get("events", [])

    def get_event(self, name: str, stack_id: str, resource_name: str,
                  event_id: str) -> StackEvent:
        data = self._client.get(
            f"{self._base}/stacks/{name}/{stack_id}"
            f"/resources/{resource_name}/events/{event_id}"
        )
        return data.get("event", data)

    # ── outputs ────────────────────────────────────────────────────────

    def find_outputs(self, name: str, stack_id: str) -> list[StackOutput]:
        data = self._client.get(
            f"{self._base}/stacks/{name}/{stack_id}/outputs"
        )
        return data.get("outputs", [])

    def get_output(self, name: str, stack_id: str, key: str) -> StackOutput:
        data = self._client.get(
            f"{self._base}/stacks/{name}/{stack_id}/outputs/{key}"
        )
        return data.get("output", data)

    # ── templates ──────────────────────────────────────────────────────

    def get_template(self, name: str, stack_id: str) -> dict:
        return self._client.get(
            f"{self._base}/stacks/{name}/{stack_id}/template"
        )

    def validate_template(self, body: dict[str, Any]) -> dict:
        return self._client.post(f"{self._base}/validate", json=body) or {}

    # ── resource types ─────────────────────────────────────────────────

    def find_resource_types(self, *,
                            params: dict[str, Any] | None = None) -> list[dict]:
        data = self._client.get(f"{self._base}/resource_types",
                                params=params)
        return data.get("resource_types", [])

    def get_resource_type_template(self, resource_type: str, *,
                                   params: dict[str, Any] | None = None) -> dict:
        return self._client.get(
            f"{self._base}/resource_types/{resource_type}/template",
            params=params,
        ) or {}

    # ── snapshots (Heat stack snapshot/restore) ────────────────────────

    def create_snapshot(self, name: str, stack_id: str,
                        snapshot_name: str | None = None) -> dict:
        body: dict = {}
        if snapshot_name:
            body["name"] = snapshot_name
        return self._client.post(
            f"{self._base}/stacks/{name}/{stack_id}/snapshots",
            json=body,
        ) or {}

    def find_snapshots(self, name: str, stack_id: str) -> list[dict]:
        data = self._client.get(
            f"{self._base}/stacks/{name}/{stack_id}/snapshots"
        )
        return data.get("snapshots", []) if isinstance(data, dict) else []

    def get_snapshot(self, name: str, stack_id: str, snapshot_id: str) -> dict:
        data = self._client.get(
            f"{self._base}/stacks/{name}/{stack_id}/snapshots/{snapshot_id}"
        )
        return data.get("snapshot", data) if isinstance(data, dict) else {}

    def delete_snapshot(self, name: str, stack_id: str,
                        snapshot_id: str) -> None:
        self._client.delete(
            f"{self._base}/stacks/{name}/{stack_id}/snapshots/{snapshot_id}"
        )

    def restore_snapshot(self, name: str, stack_id: str,
                         snapshot_id: str) -> None:
        self._client.post(
            f"{self._base}/stacks/{name}/{stack_id}"
            f"/snapshots/{snapshot_id}/restore"
        )

    # ── adopt (rebuild a stack from existing resources) ────────────────

    def adopt(self, body: dict[str, Any]) -> Stack:
        # POST /stacks with adopt_stack_data — same endpoint as create.
        data = self._client.post(f"{self._base}/stacks", json=body)
        return data.get("stack", data) if data else {}

    # ── files / environment / breakpoints ──────────────────────────────

    def get_files(self, name: str, stack_id: str) -> dict:
        return self._client.get(
            f"{self._base}/stacks/{name}/{stack_id}/files"
        ) or {}

    def get_environment(self, name: str, stack_id: str) -> dict:
        return self._client.get(
            f"{self._base}/stacks/{name}/{stack_id}/environment"
        ) or {}

    # ── resource actions: signal, mark unhealthy, get metadata ──────────

    def signal_resource(self, name: str, stack_id: str,
                        resource_name: str,
                        body: dict[str, Any] | None = None) -> None:
        self._client.post(
            f"{self._base}/stacks/{name}/{stack_id}"
            f"/resources/{resource_name}/signal",
            json=body or {},
        )

    def mark_resource_unhealthy(self, name: str, stack_id: str,
                                 resource_name: str,
                                 status_reason: str | None = None) -> None:
        body = {
            "mark_unhealthy": True,
            "resource_status_reason": status_reason or "marked unhealthy via orca",
        }
        self._client.patch(
            f"{self._base}/stacks/{name}/{stack_id}"
            f"/resources/{resource_name}",
            json=body,
        )

    def get_resource_metadata(self, name: str, stack_id: str,
                              resource_name: str) -> dict:
        data = self._client.get(
            f"{self._base}/stacks/{name}/{stack_id}"
            f"/resources/{resource_name}/metadata"
        )
        return data.get("metadata", data) if isinstance(data, dict) else {}
