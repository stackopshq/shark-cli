"""High-level operations on Octavia load-balancing resources."""

from __future__ import annotations

from typing import Any

from orca_cli.core.client import OrcaClient
from orca_cli.models.load_balancer import (
    Amphora,
    HealthMonitor,
    L7Policy,
    L7Rule,
    Listener,
    LoadBalancer,
    Member,
    Pool,
)


class LoadBalancerService:
    """Typed wrapper around Octavia ``/v2/lbaas`` and ``/v2/octavia``."""

    def __init__(self, client: OrcaClient) -> None:
        self._client = client
        self._base = f"{client.load_balancer_url}/v2/lbaas"
        self._admin = f"{client.load_balancer_url}/v2/octavia"

    # ── load balancers ─────────────────────────────────────────────────

    def find(self, *,
             params: dict[str, Any] | None = None) -> list[LoadBalancer]:
        data = self._client.get(f"{self._base}/loadbalancers", params=params)
        return data.get("loadbalancers", [])

    def find_all(self, page_size: int = 1000, *,
                 params: dict[str, Any] | None = None) -> list[LoadBalancer]:
        return self._client.paginate(
            f"{self._base}/loadbalancers", "loadbalancers",
            page_size=page_size, params=params,
        )

    def get(self, lb_id: str) -> LoadBalancer:
        data = self._client.get(f"{self._base}/loadbalancers/{lb_id}")
        return data.get("loadbalancer", data)

    def create(self, body: dict[str, Any]) -> LoadBalancer:
        data = self._client.post(f"{self._base}/loadbalancers",
                                 json={"loadbalancer": body})
        return data.get("loadbalancer", data) if data else {}

    def update(self, lb_id: str, body: dict[str, Any]) -> LoadBalancer:
        data = self._client.put(f"{self._base}/loadbalancers/{lb_id}",
                                json={"loadbalancer": body})
        return data.get("loadbalancer", data) if data else {}

    def delete(self, lb_id: str, *, cascade: bool = False) -> None:
        params = {"cascade": "true"} if cascade else None
        self._client.delete(f"{self._base}/loadbalancers/{lb_id}",
                            params=params)

    def get_stats(self, lb_id: str) -> dict:
        data = self._client.get(
            f"{self._base}/loadbalancers/{lb_id}/stats"
        )
        return data.get("stats", data) if data else {}

    def get_status(self, lb_id: str) -> dict:
        data = self._client.get(
            f"{self._base}/loadbalancers/{lb_id}/statuses"
        )
        return data.get("statuses", data) if data else {}

    # ── listeners ──────────────────────────────────────────────────────

    def find_listeners(self, *,
                       params: dict[str, Any] | None = None) -> list[Listener]:
        data = self._client.get(f"{self._base}/listeners", params=params)
        return data.get("listeners", [])

    def get_listener(self, listener_id: str) -> Listener:
        data = self._client.get(f"{self._base}/listeners/{listener_id}")
        return data.get("listener", data)

    def create_listener(self, body: dict[str, Any]) -> Listener:
        data = self._client.post(f"{self._base}/listeners",
                                 json={"listener": body})
        return data.get("listener", data) if data else {}

    def update_listener(self, listener_id: str,
                        body: dict[str, Any]) -> Listener:
        data = self._client.put(f"{self._base}/listeners/{listener_id}",
                                json={"listener": body})
        return data.get("listener", data) if data else {}

    def delete_listener(self, listener_id: str) -> None:
        self._client.delete(f"{self._base}/listeners/{listener_id}")

    # ── pools ──────────────────────────────────────────────────────────

    def find_pools(self, *,
                   params: dict[str, Any] | None = None) -> list[Pool]:
        data = self._client.get(f"{self._base}/pools", params=params)
        return data.get("pools", [])

    def get_pool(self, pool_id: str) -> Pool:
        data = self._client.get(f"{self._base}/pools/{pool_id}")
        return data.get("pool", data)

    def create_pool(self, body: dict[str, Any]) -> Pool:
        data = self._client.post(f"{self._base}/pools",
                                 json={"pool": body})
        return data.get("pool", data) if data else {}

    def update_pool(self, pool_id: str, body: dict[str, Any]) -> Pool:
        data = self._client.put(f"{self._base}/pools/{pool_id}",
                                json={"pool": body})
        return data.get("pool", data) if data else {}

    def delete_pool(self, pool_id: str) -> None:
        self._client.delete(f"{self._base}/pools/{pool_id}")

    # ── members ────────────────────────────────────────────────────────

    def find_members(self, pool_id: str, *,
                     params: dict[str, Any] | None = None) -> list[Member]:
        data = self._client.get(f"{self._base}/pools/{pool_id}/members",
                                params=params)
        return data.get("members", [])

    def get_member(self, pool_id: str, member_id: str) -> Member:
        data = self._client.get(
            f"{self._base}/pools/{pool_id}/members/{member_id}"
        )
        return data.get("member", data)

    def create_member(self, pool_id: str, body: dict[str, Any]) -> Member:
        data = self._client.post(f"{self._base}/pools/{pool_id}/members",
                                 json={"member": body})
        return data.get("member", data) if data else {}

    def update_member(self, pool_id: str, member_id: str,
                      body: dict[str, Any]) -> Member:
        data = self._client.put(
            f"{self._base}/pools/{pool_id}/members/{member_id}",
            json={"member": body},
        )
        return data.get("member", data) if data else {}

    def delete_member(self, pool_id: str, member_id: str) -> None:
        self._client.delete(
            f"{self._base}/pools/{pool_id}/members/{member_id}"
        )

    # ── health monitors ────────────────────────────────────────────────

    def find_health_monitors(
        self, *, params: dict[str, Any] | None = None,
    ) -> list[HealthMonitor]:
        data = self._client.get(f"{self._base}/healthmonitors",
                                params=params)
        return data.get("healthmonitors", [])

    def get_health_monitor(self, hm_id: str) -> HealthMonitor:
        data = self._client.get(f"{self._base}/healthmonitors/{hm_id}")
        return data.get("healthmonitor", data)

    def create_health_monitor(self, body: dict[str, Any]) -> HealthMonitor:
        data = self._client.post(f"{self._base}/healthmonitors",
                                 json={"healthmonitor": body})
        return data.get("healthmonitor", data) if data else {}

    def update_health_monitor(self, hm_id: str,
                              body: dict[str, Any]) -> HealthMonitor:
        data = self._client.put(f"{self._base}/healthmonitors/{hm_id}",
                                json={"healthmonitor": body})
        return data.get("healthmonitor", data) if data else {}

    def delete_health_monitor(self, hm_id: str) -> None:
        self._client.delete(f"{self._base}/healthmonitors/{hm_id}")

    # ── L7 policies ────────────────────────────────────────────────────

    def find_l7policies(
        self, *, params: dict[str, Any] | None = None,
    ) -> list[L7Policy]:
        data = self._client.get(f"{self._base}/l7policies", params=params)
        return data.get("l7policies", [])

    def get_l7policy(self, policy_id: str) -> L7Policy:
        data = self._client.get(f"{self._base}/l7policies/{policy_id}")
        return data.get("l7policy", data)

    def create_l7policy(self, body: dict[str, Any]) -> L7Policy:
        data = self._client.post(f"{self._base}/l7policies",
                                 json={"l7policy": body})
        return data.get("l7policy", data) if data else {}

    def update_l7policy(self, policy_id: str,
                        body: dict[str, Any]) -> L7Policy:
        data = self._client.put(f"{self._base}/l7policies/{policy_id}",
                                json={"l7policy": body})
        return data.get("l7policy", data) if data else {}

    def delete_l7policy(self, policy_id: str) -> None:
        self._client.delete(f"{self._base}/l7policies/{policy_id}")

    # ── L7 rules ───────────────────────────────────────────────────────

    def find_l7rules(self, policy_id: str) -> list[L7Rule]:
        data = self._client.get(
            f"{self._base}/l7policies/{policy_id}/rules"
        )
        return data.get("rules", [])

    def get_l7rule(self, policy_id: str, rule_id: str) -> L7Rule:
        data = self._client.get(
            f"{self._base}/l7policies/{policy_id}/rules/{rule_id}"
        )
        return data.get("rule", data)

    def create_l7rule(self, policy_id: str,
                      body: dict[str, Any]) -> L7Rule:
        data = self._client.post(
            f"{self._base}/l7policies/{policy_id}/rules",
            json={"rule": body},
        )
        return data.get("rule", data) if data else {}

    def update_l7rule(self, policy_id: str, rule_id: str,
                      body: dict[str, Any]) -> L7Rule:
        data = self._client.put(
            f"{self._base}/l7policies/{policy_id}/rules/{rule_id}",
            json={"rule": body},
        )
        return data.get("rule", data) if data else {}

    def delete_l7rule(self, policy_id: str, rule_id: str) -> None:
        self._client.delete(
            f"{self._base}/l7policies/{policy_id}/rules/{rule_id}"
        )

    # ── amphorae (admin) ───────────────────────────────────────────────

    def find_amphorae(self, *,
                      params: dict[str, Any] | None = None) -> list[Amphora]:
        data = self._client.get(f"{self._admin}/amphorae", params=params)
        return data.get("amphorae", [])

    def get_amphora(self, amphora_id: str) -> Amphora:
        data = self._client.get(f"{self._admin}/amphorae/{amphora_id}")
        return data.get("amphora", data)

    def failover_amphora(self, amphora_id: str) -> None:
        self._client.put(
            f"{self._admin}/amphorae/{amphora_id}/failover"
        )
