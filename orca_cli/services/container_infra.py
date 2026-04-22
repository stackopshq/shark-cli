"""High-level operations on Magnum container-infrastructure resources."""

from __future__ import annotations

from typing import Any

from orca_cli.core.client import OrcaClient
from orca_cli.models.container_infra import Cluster, ClusterTemplate, NodeGroup


class ContainerInfraService:
    """Typed wrapper around Magnum endpoints."""

    def __init__(self, client: OrcaClient) -> None:
        self._client = client
        self._base = client.container_infra_url

    # ── clusters ───────────────────────────────────────────────────────

    def find(self, *, params: dict[str, Any] | None = None) -> list[Cluster]:
        data = self._client.get(f"{self._base}/clusters", params=params)
        return data.get("clusters", [])

    def get(self, cluster_id: str) -> Cluster:
        return self._client.get(f"{self._base}/clusters/{cluster_id}")

    def create(self, body: dict[str, Any]) -> Cluster:
        data = self._client.post(f"{self._base}/clusters", json=body)
        return data if data else {}

    def update(self, cluster_id: str, body: list[dict[str, Any]]) -> Cluster:
        """Magnum's cluster PATCH expects a JSON Patch array."""
        data = self._client.patch(f"{self._base}/clusters/{cluster_id}",
                                  json=body)
        return data if data else {}

    def delete(self, cluster_id: str) -> None:
        self._client.delete(f"{self._base}/clusters/{cluster_id}")

    def upgrade(self, cluster_id: str, body: dict[str, Any]) -> None:
        self._client.post(
            f"{self._base}/clusters/{cluster_id}/actions/upgrade",
            json=body,
        )

    # ── cluster templates ──────────────────────────────────────────────

    def find_templates(
        self, *, params: dict[str, Any] | None = None,
    ) -> list[ClusterTemplate]:
        data = self._client.get(f"{self._base}/clustertemplates",
                                params=params)
        return data.get("clustertemplates", [])

    def get_template(self, template_id: str) -> ClusterTemplate:
        return self._client.get(
            f"{self._base}/clustertemplates/{template_id}"
        )

    def create_template(self, body: dict[str, Any]) -> ClusterTemplate:
        data = self._client.post(f"{self._base}/clustertemplates",
                                 json=body)
        return data if data else {}

    def delete_template(self, template_id: str) -> None:
        self._client.delete(f"{self._base}/clustertemplates/{template_id}")

    # ── node groups (per-cluster) ──────────────────────────────────────

    def find_nodegroups(self, cluster_id: str) -> list[NodeGroup]:
        data = self._client.get(
            f"{self._base}/clusters/{cluster_id}/nodegroups"
        )
        return data.get("nodegroups", [])

    def get_nodegroup(self, cluster_id: str, nodegroup_id: str) -> NodeGroup:
        return self._client.get(
            f"{self._base}/clusters/{cluster_id}/nodegroups/{nodegroup_id}"
        )

    def create_nodegroup(
        self, cluster_id: str, body: dict[str, Any],
    ) -> NodeGroup:
        data = self._client.post(
            f"{self._base}/clusters/{cluster_id}/nodegroups",
            json=body,
        )
        return data if data else {}

    def update_nodegroup(
        self, cluster_id: str, nodegroup_id: str,
        body: list[dict[str, Any]],
    ) -> NodeGroup:
        """JSON Patch array, same as cluster update."""
        data = self._client.patch(
            f"{self._base}/clusters/{cluster_id}/nodegroups/{nodegroup_id}",
            json=body,
        )
        return data if data else {}

    def delete_nodegroup(self, cluster_id: str, nodegroup_id: str) -> None:
        self._client.delete(
            f"{self._base}/clusters/{cluster_id}/nodegroups/{nodegroup_id}"
        )
