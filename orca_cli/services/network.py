"""High-level operations on Neutron networking resources."""

from __future__ import annotations

from typing import Any

from orca_cli.core.client import OrcaClient
from orca_cli.models.network import (
    Agent,
    AutoAllocatedTopology,
    FloatingIp,
    Network,
    Port,
    QosPolicy,
    QosRule,
    RbacPolicy,
    Router,
    SecurityGroup,
    SecurityGroupRule,
    Segment,
    Subnet,
    SubnetPool,
    Trunk,
)


class NetworkService:
    """Typed wrapper around the Neutron ``/v2.0`` endpoints.

    Owns URL construction for networks, subnets, ports, routers,
    floating IPs, security groups + rules, subnet pools, trunks,
    QoS policies + rules, agents, RBAC policies, segments, and
    auto-allocated topology. Retry, auth, and pagination live in
    OrcaClient — the service is purely a translation layer between
    Neutron and the typed models.
    """

    def __init__(self, client: OrcaClient) -> None:
        self._client = client
        self._base = f"{client.network_url}/v2.0"

    # ── networks ───────────────────────────────────────────────────────

    def find(self, *, params: dict[str, Any] | None = None) -> list[Network]:
        data = self._client.get(f"{self._base}/networks", params=params)
        return data.get("networks", [])

    def find_all(self, page_size: int = 1000, *,
                 params: dict[str, Any] | None = None) -> list[Network]:
        return self._client.paginate(f"{self._base}/networks", "networks",
                                     page_size=page_size, params=params)

    def get(self, network_id: str) -> Network:
        data = self._client.get(f"{self._base}/networks/{network_id}")
        return data.get("network", data)

    def create(self, body: dict[str, Any]) -> Network:
        data = self._client.post(f"{self._base}/networks",
                                 json={"network": body})
        return data.get("network", data) if data else {}

    def update(self, network_id: str, body: dict[str, Any]) -> Network:
        data = self._client.put(f"{self._base}/networks/{network_id}",
                                json={"network": body})
        return data.get("network", data) if data else {}

    def delete(self, network_id: str) -> None:
        self._client.delete(f"{self._base}/networks/{network_id}")

    # ── subnets ────────────────────────────────────────────────────────

    def find_subnets(self, *,
                     params: dict[str, Any] | None = None) -> list[Subnet]:
        data = self._client.get(f"{self._base}/subnets", params=params)
        return data.get("subnets", [])

    def find_all_subnets(self, page_size: int = 1000, *,
                         params: dict[str, Any] | None = None) -> list[Subnet]:
        return self._client.paginate(f"{self._base}/subnets", "subnets",
                                     page_size=page_size, params=params)

    def get_subnet(self, subnet_id: str) -> Subnet:
        data = self._client.get(f"{self._base}/subnets/{subnet_id}")
        return data.get("subnet", data)

    def create_subnet(self, body: dict[str, Any]) -> Subnet:
        data = self._client.post(f"{self._base}/subnets",
                                 json={"subnet": body})
        return data.get("subnet", data) if data else {}

    def update_subnet(self, subnet_id: str, body: dict[str, Any]) -> Subnet:
        data = self._client.put(f"{self._base}/subnets/{subnet_id}",
                                json={"subnet": body})
        return data.get("subnet", data) if data else {}

    def delete_subnet(self, subnet_id: str) -> None:
        self._client.delete(f"{self._base}/subnets/{subnet_id}")

    # ── ports ──────────────────────────────────────────────────────────

    def find_ports(self, *,
                   params: dict[str, Any] | None = None) -> list[Port]:
        data = self._client.get(f"{self._base}/ports", params=params)
        return data.get("ports", [])

    def find_all_ports(self, page_size: int = 1000, *,
                       params: dict[str, Any] | None = None) -> list[Port]:
        return self._client.paginate(f"{self._base}/ports", "ports",
                                     page_size=page_size, params=params)

    def get_port(self, port_id: str) -> Port:
        data = self._client.get(f"{self._base}/ports/{port_id}")
        return data.get("port", data)

    def create_port(self, body: dict[str, Any]) -> Port:
        data = self._client.post(f"{self._base}/ports",
                                 json={"port": body})
        return data.get("port", data) if data else {}

    def update_port(self, port_id: str, body: dict[str, Any]) -> Port:
        data = self._client.put(f"{self._base}/ports/{port_id}",
                                json={"port": body})
        return data.get("port", data) if data else {}

    def delete_port(self, port_id: str) -> None:
        self._client.delete(f"{self._base}/ports/{port_id}")

    # ── routers ────────────────────────────────────────────────────────

    def find_routers(self, *,
                     params: dict[str, Any] | None = None) -> list[Router]:
        data = self._client.get(f"{self._base}/routers", params=params)
        return data.get("routers", [])

    def find_all_routers(self, page_size: int = 1000, *,
                         params: dict[str, Any] | None = None) -> list[Router]:
        return self._client.paginate(f"{self._base}/routers", "routers",
                                     page_size=page_size, params=params)

    def get_router(self, router_id: str) -> Router:
        data = self._client.get(f"{self._base}/routers/{router_id}")
        return data.get("router", data)

    def create_router(self, body: dict[str, Any]) -> Router:
        data = self._client.post(f"{self._base}/routers",
                                 json={"router": body})
        return data.get("router", data) if data else {}

    def update_router(self, router_id: str, body: dict[str, Any]) -> Router:
        data = self._client.put(f"{self._base}/routers/{router_id}",
                                json={"router": body})
        return data.get("router", data) if data else {}

    def delete_router(self, router_id: str) -> None:
        self._client.delete(f"{self._base}/routers/{router_id}")

    def add_router_interface(self, router_id: str,
                             body: dict[str, Any]) -> dict | None:
        return self._client.put(
            f"{self._base}/routers/{router_id}/add_router_interface",
            json=body,
        )

    def remove_router_interface(self, router_id: str,
                                body: dict[str, Any]) -> dict | None:
        return self._client.put(
            f"{self._base}/routers/{router_id}/remove_router_interface",
            json=body,
        )

    def add_router_routes(self, router_id: str,
                          routes: list[dict[str, Any]]) -> dict | None:
        return self._client.put(
            f"{self._base}/routers/{router_id}/add_extraroutes",
            json={"router": {"routes": routes}},
        )

    def remove_router_routes(self, router_id: str,
                             routes: list[dict[str, Any]]) -> dict | None:
        return self._client.put(
            f"{self._base}/routers/{router_id}/remove_extraroutes",
            json={"router": {"routes": routes}},
        )

    # ── floating IPs ───────────────────────────────────────────────────

    def find_floating_ips(self, *,
                          params: dict[str, Any] | None = None) -> list[FloatingIp]:
        data = self._client.get(f"{self._base}/floatingips", params=params)
        return data.get("floatingips", [])

    def find_all_floating_ips(
        self, page_size: int = 1000, *,
        params: dict[str, Any] | None = None,
    ) -> list[FloatingIp]:
        return self._client.paginate(f"{self._base}/floatingips", "floatingips",
                                     page_size=page_size, params=params)

    def get_floating_ip(self, fip_id: str) -> FloatingIp:
        data = self._client.get(f"{self._base}/floatingips/{fip_id}")
        return data.get("floatingip", data)

    def create_floating_ip(self, body: dict[str, Any]) -> FloatingIp:
        data = self._client.post(f"{self._base}/floatingips",
                                 json={"floatingip": body})
        return data.get("floatingip", data) if data else {}

    def update_floating_ip(self, fip_id: str,
                           body: dict[str, Any]) -> FloatingIp:
        data = self._client.put(f"{self._base}/floatingips/{fip_id}",
                                json={"floatingip": body})
        return data.get("floatingip", data) if data else {}

    def delete_floating_ip(self, fip_id: str) -> None:
        self._client.delete(f"{self._base}/floatingips/{fip_id}")

    # ── security groups ────────────────────────────────────────────────

    def find_security_groups(
        self, *, params: dict[str, Any] | None = None,
    ) -> list[SecurityGroup]:
        data = self._client.get(f"{self._base}/security-groups", params=params)
        return data.get("security_groups", [])

    def find_all_security_groups(
        self, page_size: int = 1000, *,
        params: dict[str, Any] | None = None,
    ) -> list[SecurityGroup]:
        return self._client.paginate(f"{self._base}/security-groups",
                                     "security_groups",
                                     page_size=page_size, params=params)

    def get_security_group(self, sg_id: str) -> SecurityGroup:
        data = self._client.get(f"{self._base}/security-groups/{sg_id}")
        return data.get("security_group", data)

    def create_security_group(self, body: dict[str, Any]) -> SecurityGroup:
        data = self._client.post(f"{self._base}/security-groups",
                                 json={"security_group": body})
        return data.get("security_group", data) if data else {}

    def update_security_group(self, sg_id: str,
                              body: dict[str, Any]) -> SecurityGroup:
        data = self._client.put(f"{self._base}/security-groups/{sg_id}",
                                json={"security_group": body})
        return data.get("security_group", data) if data else {}

    def delete_security_group(self, sg_id: str) -> None:
        self._client.delete(f"{self._base}/security-groups/{sg_id}")

    def create_security_group_rule(
        self, body: dict[str, Any],
    ) -> SecurityGroupRule:
        data = self._client.post(f"{self._base}/security-group-rules",
                                 json={"security_group_rule": body})
        return data.get("security_group_rule", data) if data else {}

    def delete_security_group_rule(self, rule_id: str) -> None:
        self._client.delete(f"{self._base}/security-group-rules/{rule_id}")

    # ── subnet pools ───────────────────────────────────────────────────

    def find_subnet_pools(
        self, *, params: dict[str, Any] | None = None,
    ) -> list[SubnetPool]:
        data = self._client.get(f"{self._base}/subnetpools", params=params)
        return data.get("subnetpools", [])

    def find_all_subnet_pools(
        self, page_size: int = 1000, *,
        params: dict[str, Any] | None = None,
    ) -> list[SubnetPool]:
        return self._client.paginate(f"{self._base}/subnetpools", "subnetpools",
                                     page_size=page_size, params=params)

    def get_subnet_pool(self, pool_id: str) -> SubnetPool:
        data = self._client.get(f"{self._base}/subnetpools/{pool_id}")
        return data.get("subnetpool", data)

    def create_subnet_pool(self, body: dict[str, Any]) -> SubnetPool:
        data = self._client.post(f"{self._base}/subnetpools",
                                 json={"subnetpool": body})
        return data.get("subnetpool", data) if data else {}

    def update_subnet_pool(self, pool_id: str,
                           body: dict[str, Any]) -> SubnetPool:
        data = self._client.put(f"{self._base}/subnetpools/{pool_id}",
                                json={"subnetpool": body})
        return data.get("subnetpool", data) if data else {}

    def delete_subnet_pool(self, pool_id: str) -> None:
        self._client.delete(f"{self._base}/subnetpools/{pool_id}")

    # ── trunks ─────────────────────────────────────────────────────────

    def find_trunks(self, *,
                    params: dict[str, Any] | None = None) -> list[Trunk]:
        data = self._client.get(f"{self._base}/trunks", params=params)
        return data.get("trunks", [])

    def find_all_trunks(self, page_size: int = 1000, *,
                        params: dict[str, Any] | None = None) -> list[Trunk]:
        return self._client.paginate(f"{self._base}/trunks", "trunks",
                                     page_size=page_size, params=params)

    def get_trunk(self, trunk_id: str) -> Trunk:
        data = self._client.get(f"{self._base}/trunks/{trunk_id}")
        return data.get("trunk", data)

    def create_trunk(self, body: dict[str, Any]) -> Trunk:
        data = self._client.post(f"{self._base}/trunks",
                                 json={"trunk": body})
        return data.get("trunk", data) if data else {}

    def update_trunk(self, trunk_id: str, body: dict[str, Any]) -> Trunk:
        data = self._client.put(f"{self._base}/trunks/{trunk_id}",
                                json={"trunk": body})
        return data.get("trunk", data) if data else {}

    def delete_trunk(self, trunk_id: str) -> None:
        self._client.delete(f"{self._base}/trunks/{trunk_id}")

    def get_trunk_subports(self, trunk_id: str) -> list[dict]:
        data = self._client.get(f"{self._base}/trunks/{trunk_id}/get_subports")
        return data.get("sub_ports", []) if data else []

    def add_trunk_subports(self, trunk_id: str,
                           sub_ports: list[dict[str, Any]]) -> dict | None:
        return self._client.put(
            f"{self._base}/trunks/{trunk_id}/add_subports",
            json={"sub_ports": sub_ports},
        )

    def remove_trunk_subports(self, trunk_id: str,
                              sub_ports: list[dict[str, Any]]) -> dict | None:
        return self._client.put(
            f"{self._base}/trunks/{trunk_id}/remove_subports",
            json={"sub_ports": sub_ports},
        )

    # ── QoS policies + rules ───────────────────────────────────────────

    def find_qos_policies(
        self, *, params: dict[str, Any] | None = None,
    ) -> list[QosPolicy]:
        data = self._client.get(f"{self._base}/qos/policies", params=params)
        return data.get("policies", [])

    def find_all_qos_policies(
        self, page_size: int = 1000, *,
        params: dict[str, Any] | None = None,
    ) -> list[QosPolicy]:
        return self._client.paginate(f"{self._base}/qos/policies", "policies",
                                     page_size=page_size, params=params)

    def get_qos_policy(self, policy_id: str) -> QosPolicy:
        data = self._client.get(f"{self._base}/qos/policies/{policy_id}")
        return data.get("policy", data)

    def create_qos_policy(self, body: dict[str, Any]) -> QosPolicy:
        data = self._client.post(f"{self._base}/qos/policies",
                                 json={"policy": body})
        return data.get("policy", data) if data else {}

    def update_qos_policy(self, policy_id: str,
                          body: dict[str, Any]) -> QosPolicy:
        data = self._client.put(f"{self._base}/qos/policies/{policy_id}",
                                json={"policy": body})
        return data.get("policy", data) if data else {}

    def delete_qos_policy(self, policy_id: str) -> None:
        self._client.delete(f"{self._base}/qos/policies/{policy_id}")

    def find_qos_rules(self, policy_id: str, rule_type: str) -> list[QosRule]:
        """``rule_type`` is the plural segment
        (``bandwidth_limit_rules``, ``dscp_marking_rules``,
        ``minimum_bandwidth_rules``, ``minimum_packet_rate_rules``)."""
        data = self._client.get(
            f"{self._base}/qos/policies/{policy_id}/{rule_type}"
        )
        return data.get(rule_type, [])

    def create_qos_rule(self, policy_id: str, rule_type: str,
                        body: dict[str, Any]) -> QosRule:
        singular = rule_type[:-1]  # strip plural "s"
        data = self._client.post(
            f"{self._base}/qos/policies/{policy_id}/{rule_type}",
            json={singular: body},
        )
        return data.get(singular, data) if data else {}

    def delete_qos_rule(self, policy_id: str, rule_type: str,
                        rule_id: str) -> None:
        self._client.delete(
            f"{self._base}/qos/policies/{policy_id}/{rule_type}/{rule_id}"
        )

    # ── agents (admin) ─────────────────────────────────────────────────

    def find_agents(self, *,
                    params: dict[str, Any] | None = None) -> list[Agent]:
        data = self._client.get(f"{self._base}/agents", params=params)
        return data.get("agents", [])

    def get_agent(self, agent_id: str) -> Agent:
        data = self._client.get(f"{self._base}/agents/{agent_id}")
        return data.get("agent", data)

    def update_agent(self, agent_id: str, body: dict[str, Any]) -> Agent:
        data = self._client.put(f"{self._base}/agents/{agent_id}",
                                json={"agent": body})
        return data.get("agent", data) if data else {}

    def delete_agent(self, agent_id: str) -> None:
        self._client.delete(f"{self._base}/agents/{agent_id}")

    # ── RBAC policies ──────────────────────────────────────────────────

    def find_rbac_policies(
        self, *, params: dict[str, Any] | None = None,
    ) -> list[RbacPolicy]:
        data = self._client.get(f"{self._base}/rbac-policies", params=params)
        return data.get("rbac_policies", [])

    def get_rbac_policy(self, rbac_id: str) -> RbacPolicy:
        data = self._client.get(f"{self._base}/rbac-policies/{rbac_id}")
        return data.get("rbac_policy", data)

    def create_rbac_policy(self, body: dict[str, Any]) -> RbacPolicy:
        data = self._client.post(f"{self._base}/rbac-policies",
                                 json={"rbac_policy": body})
        return data.get("rbac_policy", data) if data else {}

    def update_rbac_policy(self, rbac_id: str,
                           body: dict[str, Any]) -> RbacPolicy:
        data = self._client.put(f"{self._base}/rbac-policies/{rbac_id}",
                                json={"rbac_policy": body})
        return data.get("rbac_policy", data) if data else {}

    def delete_rbac_policy(self, rbac_id: str) -> None:
        self._client.delete(f"{self._base}/rbac-policies/{rbac_id}")

    # ── segments ───────────────────────────────────────────────────────

    def find_segments(self, *,
                      params: dict[str, Any] | None = None) -> list[Segment]:
        data = self._client.get(f"{self._base}/segments", params=params)
        return data.get("segments", [])

    def get_segment(self, segment_id: str) -> Segment:
        data = self._client.get(f"{self._base}/segments/{segment_id}")
        return data.get("segment", data)

    def create_segment(self, body: dict[str, Any]) -> Segment:
        data = self._client.post(f"{self._base}/segments",
                                 json={"segment": body})
        return data.get("segment", data) if data else {}

    def update_segment(self, segment_id: str,
                       body: dict[str, Any]) -> Segment:
        data = self._client.put(f"{self._base}/segments/{segment_id}",
                                json={"segment": body})
        return data.get("segment", data) if data else {}

    def delete_segment(self, segment_id: str) -> None:
        self._client.delete(f"{self._base}/segments/{segment_id}")

    # ── auto-allocated topology ────────────────────────────────────────

    def get_auto_allocated_topology(
        self, scope: str, *, dry_run: bool = False,
    ) -> AutoAllocatedTopology:
        """``scope`` is a project UUID or ``"null"`` for the current project.
        With ``dry_run=True`` Neutron only validates, it does not create."""
        params: dict[str, Any] = {"fields": "dry-run"} if dry_run else {}
        data = self._client.get(
            f"{self._base}/auto-allocated-topology/{scope}",
            params=params or None,
        )
        return data.get("auto_allocated_topology", data)

    def delete_auto_allocated_topology(self, scope: str) -> None:
        self._client.delete(f"{self._base}/auto-allocated-topology/{scope}")

    # ── quotas ─────────────────────────────────────────────────────────

    def find_quotas(self) -> list[dict]:
        """All quota entries visible to the caller (admin)."""
        data = self._client.get(f"{self._base}/quotas")
        q = data.get("quotas", [])
        return q if isinstance(q, list) else []

    def get_quota(self, project_id: str) -> dict:
        data = self._client.get(f"{self._base}/quotas/{project_id}")
        return data.get("quota", data)
