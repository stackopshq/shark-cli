"""High-level operations on Barbican key-manager resources."""

from __future__ import annotations

from typing import Any

from orca_cli.core.client import OrcaClient
from orca_cli.models.key_manager import Acl, Order, Secret, SecretContainer


class KeyManagerService:
    """Typed wrapper around Barbican ``/v1`` endpoints."""

    def __init__(self, client: OrcaClient) -> None:
        self._client = client
        self._base = f"{client.key_manager_url}/v1"

    # ── secrets ────────────────────────────────────────────────────────

    def find_secrets(self, *,
                     params: dict[str, Any] | None = None) -> list[Secret]:
        data = self._client.get(f"{self._base}/secrets", params=params)
        return data.get("secrets", [])

    def get_secret(self, secret_id: str) -> Secret:
        return self._client.get(f"{self._base}/secrets/{secret_id}")

    def create_secret(self, body: dict[str, Any]) -> Secret:
        data = self._client.post(f"{self._base}/secrets", json=body)
        return data if data else {}

    def delete_secret(self, secret_id: str) -> None:
        self._client.delete(f"{self._base}/secrets/{secret_id}")

    # ── secret ACL ─────────────────────────────────────────────────────

    def get_secret_acl(self, secret_id: str) -> Acl:
        return self._client.get(f"{self._base}/secrets/{secret_id}/acl")

    def update_secret_acl(self, secret_id: str,
                          body: dict[str, Any]) -> dict:
        return self._client.put(
            f"{self._base}/secrets/{secret_id}/acl", json=body,
        ) or {}

    def delete_secret_acl(self, secret_id: str) -> None:
        self._client.delete(f"{self._base}/secrets/{secret_id}/acl")

    # ── containers ─────────────────────────────────────────────────────

    def find_containers(
        self, *, params: dict[str, Any] | None = None,
    ) -> list[SecretContainer]:
        data = self._client.get(f"{self._base}/containers", params=params)
        return data.get("containers", [])

    def get_container(self, container_id: str) -> SecretContainer:
        return self._client.get(f"{self._base}/containers/{container_id}")

    def create_container(self, body: dict[str, Any]) -> SecretContainer:
        data = self._client.post(f"{self._base}/containers", json=body)
        return data if data else {}

    def delete_container(self, container_id: str) -> None:
        self._client.delete(f"{self._base}/containers/{container_id}")

    # ── orders ─────────────────────────────────────────────────────────

    def find_orders(self, *,
                    params: dict[str, Any] | None = None) -> list[Order]:
        data = self._client.get(f"{self._base}/orders", params=params)
        return data.get("orders", [])

    def get_order(self, order_id: str) -> Order:
        return self._client.get(f"{self._base}/orders/{order_id}")

    def create_order(self, body: dict[str, Any]) -> Order:
        data = self._client.post(f"{self._base}/orders", json=body)
        return data if data else {}

    def delete_order(self, order_id: str) -> None:
        self._client.delete(f"{self._base}/orders/{order_id}")
