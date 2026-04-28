"""High-level operations on Keystone v3 identity resources.

All Keystone v3 routes (projects, users, services, endpoints, regions,
credentials, OS-TRUST trusts, ...) live under ``/v3``. ``with_version``
ensures the prefix is present whether the catalogue advertises Keystone
versionless (e.g. DevStack ``http://host/identity``) or already
versioned (e.g. ``http://host/identity/v3``).
"""

from __future__ import annotations

from typing import Any

from orca_cli.core.client import OrcaClient, with_version
from orca_cli.models.identity import (
    AccessRule,
    ApplicationCredential,
    Credential,
    Domain,
    Endpoint,
    EndpointGroup,
    FederationProtocol,
    Group,
    IdentityProvider,
    Limit,
    Mapping,
    Policy,
    Project,
    Region,
    RegisteredLimit,
    Role,
    RoleAssignment,
    RoleInference,
    Service,
    ServiceProvider,
    Trust,
    User,
)


class IdentityService:
    """Typed wrapper around Keystone v3 endpoints."""

    def __init__(self, client: OrcaClient) -> None:
        self._client = client
        self._v3 = with_version(client.identity_url, "v3")
        self._base = self._v3

    # ── projects ───────────────────────────────────────────────────────

    def find_projects(self, *,
                      params: dict[str, Any] | None = None) -> list[Project]:
        data = self._client.get(f"{self._v3}/projects", params=params)
        return data.get("projects", [])

    def get_project(self, project_id: str) -> Project:
        data = self._client.get(f"{self._v3}/projects/{project_id}")
        return data.get("project", data)

    def create_project(self, body: dict[str, Any]) -> Project:
        data = self._client.post(f"{self._v3}/projects",
                                 json={"project": body})
        return data.get("project", data) if data else {}

    def update_project(self, project_id: str,
                       body: dict[str, Any]) -> Project:
        data = self._client.patch(f"{self._v3}/projects/{project_id}",
                                  json={"project": body})
        return data.get("project", data) if data else {}

    def delete_project(self, project_id: str) -> None:
        self._client.delete(f"{self._v3}/projects/{project_id}")

    # ── users ──────────────────────────────────────────────────────────

    def find_users(self, *,
                   params: dict[str, Any] | None = None) -> list[User]:
        data = self._client.get(f"{self._v3}/users", params=params)
        return data.get("users", [])

    def get_user(self, user_id: str) -> User:
        data = self._client.get(f"{self._v3}/users/{user_id}")
        return data.get("user", data)

    def create_user(self, body: dict[str, Any]) -> User:
        data = self._client.post(f"{self._v3}/users",
                                 json={"user": body})
        return data.get("user", data) if data else {}

    def update_user(self, user_id: str, body: dict[str, Any]) -> User:
        data = self._client.patch(f"{self._v3}/users/{user_id}",
                                  json={"user": body})
        return data.get("user", data) if data else {}

    def delete_user(self, user_id: str) -> None:
        self._client.delete(f"{self._v3}/users/{user_id}")

    def list_user_groups(self, user_id: str) -> list[Group]:
        data = self._client.get(f"{self._v3}/users/{user_id}/groups")
        return data.get("groups", [])

    def list_user_projects(self, user_id: str) -> list[Project]:
        data = self._client.get(f"{self._v3}/users/{user_id}/projects")
        return data.get("projects", [])

    # ── roles ──────────────────────────────────────────────────────────

    def find_roles(self, *,
                   params: dict[str, Any] | None = None) -> list[Role]:
        data = self._client.get(f"{self._v3}/roles", params=params)
        return data.get("roles", [])

    def get_role(self, role_id: str) -> Role:
        data = self._client.get(f"{self._v3}/roles/{role_id}")
        return data.get("role", data)

    def create_role(self, body: dict[str, Any]) -> Role:
        data = self._client.post(f"{self._v3}/roles",
                                 json={"role": body})
        return data.get("role", data) if data else {}

    def update_role(self, role_id: str, body: dict[str, Any]) -> Role:
        data = self._client.patch(f"{self._v3}/roles/{role_id}",
                                  json={"role": body})
        return data.get("role", data) if data else {}

    def delete_role(self, role_id: str) -> None:
        self._client.delete(f"{self._v3}/roles/{role_id}")

    def grant_role(self, *, scope_type: str, scope_id: str,
                   actor_type: str, actor_id: str, role_id: str) -> None:
        """``scope_type`` is ``projects`` or ``domains``,
        ``actor_type`` is ``users`` or ``groups``."""
        self._client.put(
            f"{self._v3}/{scope_type}/{scope_id}/"
            f"{actor_type}/{actor_id}/roles/{role_id}"
        )

    def revoke_role(self, *, scope_type: str, scope_id: str,
                    actor_type: str, actor_id: str, role_id: str) -> None:
        self._client.delete(
            f"{self._v3}/{scope_type}/{scope_id}/"
            f"{actor_type}/{actor_id}/roles/{role_id}"
        )

    def find_role_assignments(
        self, *, params: dict[str, Any] | None = None,
    ) -> list[RoleAssignment]:
        data = self._client.get(f"{self._v3}/role_assignments",
                                params=params)
        return data.get("role_assignments", [])

    def find_role_inferences(self) -> list[RoleInference]:
        data = self._client.get(f"{self._v3}/role_inferences")
        return data.get("role_inferences", [])

    def create_role_inference(self, prior_id: str, implied_id: str) -> None:
        self._client.put(
            f"{self._v3}/role_inferences/{prior_id}/implies/{implied_id}"
        )

    def delete_role_inference(self, prior_id: str, implied_id: str) -> None:
        self._client.delete(
            f"{self._v3}/role_inferences/{prior_id}/implies/{implied_id}"
        )

    # ── domains ────────────────────────────────────────────────────────

    def find_domains(self, *,
                     params: dict[str, Any] | None = None) -> list[Domain]:
        data = self._client.get(f"{self._v3}/domains", params=params)
        return data.get("domains", [])

    def get_domain(self, domain_id: str) -> Domain:
        data = self._client.get(f"{self._v3}/domains/{domain_id}")
        return data.get("domain", data)

    def create_domain(self, body: dict[str, Any]) -> Domain:
        data = self._client.post(f"{self._v3}/domains",
                                 json={"domain": body})
        return data.get("domain", data) if data else {}

    def update_domain(self, domain_id: str, body: dict[str, Any]) -> Domain:
        data = self._client.patch(f"{self._v3}/domains/{domain_id}",
                                  json={"domain": body})
        return data.get("domain", data) if data else {}

    def delete_domain(self, domain_id: str) -> None:
        self._client.delete(f"{self._v3}/domains/{domain_id}")

    # ── groups ─────────────────────────────────────────────────────────

    def find_groups(self, *,
                    params: dict[str, Any] | None = None) -> list[Group]:
        data = self._client.get(f"{self._v3}/groups", params=params)
        return data.get("groups", [])

    def get_group(self, group_id: str) -> Group:
        data = self._client.get(f"{self._v3}/groups/{group_id}")
        return data.get("group", data)

    def create_group(self, body: dict[str, Any]) -> Group:
        data = self._client.post(f"{self._v3}/groups",
                                 json={"group": body})
        return data.get("group", data) if data else {}

    def update_group(self, group_id: str, body: dict[str, Any]) -> Group:
        data = self._client.patch(f"{self._v3}/groups/{group_id}",
                                  json={"group": body})
        return data.get("group", data) if data else {}

    def delete_group(self, group_id: str) -> None:
        self._client.delete(f"{self._v3}/groups/{group_id}")

    def add_group_user(self, group_id: str, user_id: str) -> None:
        self._client.put(
            f"{self._v3}/groups/{group_id}/users/{user_id}"
        )

    def remove_group_user(self, group_id: str, user_id: str) -> None:
        self._client.delete(
            f"{self._v3}/groups/{group_id}/users/{user_id}"
        )

    def list_group_users(self, group_id: str) -> list[User]:
        data = self._client.get(f"{self._v3}/groups/{group_id}/users")
        return data.get("users", [])

    # ── credentials (no /v3) ───────────────────────────────────────────

    def find_credentials(
        self, *, params: dict[str, Any] | None = None,
    ) -> list[Credential]:
        data = self._client.get(f"{self._base}/credentials", params=params)
        return data.get("credentials", [])

    def get_credential(self, cred_id: str) -> Credential:
        data = self._client.get(f"{self._base}/credentials/{cred_id}")
        return data.get("credential", data)

    def create_credential(self, body: dict[str, Any]) -> Credential:
        data = self._client.post(f"{self._base}/credentials",
                                 json={"credential": body})
        return data.get("credential", data) if data else {}

    def update_credential(self, cred_id: str,
                          body: dict[str, Any]) -> Credential:
        data = self._client.patch(f"{self._base}/credentials/{cred_id}",
                                  json={"credential": body})
        return data.get("credential", data) if data else {}

    def delete_credential(self, cred_id: str) -> None:
        self._client.delete(f"{self._base}/credentials/{cred_id}")

    # ── application credentials (/v3, per-user) ────────────────────────

    def find_application_credentials(
        self, user_id: str,
    ) -> list[ApplicationCredential]:
        data = self._client.get(
            f"{self._v3}/users/{user_id}/application_credentials"
        )
        return data.get("application_credentials", [])

    def get_application_credential(
        self, user_id: str, cred_id: str,
    ) -> ApplicationCredential:
        data = self._client.get(
            f"{self._v3}/users/{user_id}/application_credentials/{cred_id}"
        )
        return data.get("application_credential", data)

    def create_application_credential(
        self, user_id: str, body: dict[str, Any],
    ) -> ApplicationCredential:
        data = self._client.post(
            f"{self._v3}/users/{user_id}/application_credentials",
            json={"application_credential": body},
        )
        return data.get("application_credential", data) if data else {}

    def delete_application_credential(
        self, user_id: str, cred_id: str,
    ) -> None:
        self._client.delete(
            f"{self._v3}/users/{user_id}/application_credentials/{cred_id}"
        )

    # ── endpoints (no /v3) ─────────────────────────────────────────────

    def find_endpoints(
        self, *, params: dict[str, Any] | None = None,
    ) -> list[Endpoint]:
        data = self._client.get(f"{self._base}/endpoints", params=params)
        return data.get("endpoints", [])

    def get_endpoint(self, endpoint_id: str) -> Endpoint:
        data = self._client.get(f"{self._base}/endpoints/{endpoint_id}")
        return data.get("endpoint", data)

    def create_endpoint(self, body: dict[str, Any]) -> Endpoint:
        data = self._client.post(f"{self._base}/endpoints",
                                 json={"endpoint": body})
        return data.get("endpoint", data) if data else {}

    def update_endpoint(self, endpoint_id: str,
                        body: dict[str, Any]) -> Endpoint:
        data = self._client.patch(f"{self._base}/endpoints/{endpoint_id}",
                                  json={"endpoint": body})
        return data.get("endpoint", data) if data else {}

    def delete_endpoint(self, endpoint_id: str) -> None:
        self._client.delete(f"{self._base}/endpoints/{endpoint_id}")

    # ── endpoint groups (/v3) ──────────────────────────────────────────

    def find_endpoint_groups(
        self, *, params: dict[str, Any] | None = None,
    ) -> list[EndpointGroup]:
        data = self._client.get(f"{self._v3}/endpoint_groups", params=params)
        return data.get("endpoint_groups", [])

    def get_endpoint_group(self, eg_id: str) -> EndpointGroup:
        data = self._client.get(f"{self._v3}/endpoint_groups/{eg_id}")
        return data.get("endpoint_group", data)

    def create_endpoint_group(self, body: dict[str, Any]) -> EndpointGroup:
        data = self._client.post(f"{self._v3}/endpoint_groups",
                                 json={"endpoint_group": body})
        return data.get("endpoint_group", data) if data else {}

    def update_endpoint_group(self, eg_id: str,
                              body: dict[str, Any]) -> EndpointGroup:
        data = self._client.patch(f"{self._v3}/endpoint_groups/{eg_id}",
                                  json={"endpoint_group": body})
        return data.get("endpoint_group", data) if data else {}

    def delete_endpoint_group(self, eg_id: str) -> None:
        self._client.delete(f"{self._v3}/endpoint_groups/{eg_id}")

    def add_endpoint_group_project(self, eg_id: str, project_id: str) -> None:
        self._client.put(
            f"{self._v3}/endpoint_groups/{eg_id}/projects/{project_id}"
        )

    def remove_endpoint_group_project(self, eg_id: str,
                                      project_id: str) -> None:
        self._client.delete(
            f"{self._v3}/endpoint_groups/{eg_id}/projects/{project_id}"
        )

    # ── services (no /v3) ──────────────────────────────────────────────

    def find_services(
        self, *, params: dict[str, Any] | None = None,
    ) -> list[Service]:
        data = self._client.get(f"{self._base}/services", params=params)
        return data.get("services", [])

    def get_service(self, service_id: str) -> Service:
        data = self._client.get(f"{self._base}/services/{service_id}")
        return data.get("service", data)

    def create_service(self, body: dict[str, Any]) -> Service:
        data = self._client.post(f"{self._base}/services",
                                 json={"service": body})
        return data.get("service", data) if data else {}

    def update_service(self, service_id: str,
                       body: dict[str, Any]) -> Service:
        data = self._client.patch(f"{self._base}/services/{service_id}",
                                  json={"service": body})
        return data.get("service", data) if data else {}

    def delete_service(self, service_id: str) -> None:
        self._client.delete(f"{self._base}/services/{service_id}")

    # ── regions (no /v3) ───────────────────────────────────────────────

    def find_regions(
        self, *, params: dict[str, Any] | None = None,
    ) -> list[Region]:
        data = self._client.get(f"{self._base}/regions", params=params)
        return data.get("regions", [])

    def get_region(self, region_id: str) -> Region:
        data = self._client.get(f"{self._base}/regions/{region_id}")
        return data.get("region", data)

    def create_region(self, body: dict[str, Any]) -> Region:
        data = self._client.post(f"{self._base}/regions",
                                 json={"region": body})
        return data.get("region", data) if data else {}

    def update_region(self, region_id: str, body: dict[str, Any]) -> Region:
        data = self._client.patch(f"{self._base}/regions/{region_id}",
                                  json={"region": body})
        return data.get("region", data) if data else {}

    def delete_region(self, region_id: str) -> None:
        self._client.delete(f"{self._base}/regions/{region_id}")

    # ── policies (/v3) ─────────────────────────────────────────────────

    def find_policies(
        self, *, params: dict[str, Any] | None = None,
    ) -> list[Policy]:
        data = self._client.get(f"{self._v3}/policies", params=params)
        return data.get("policies", [])

    def get_policy(self, policy_id: str) -> Policy:
        data = self._client.get(f"{self._v3}/policies/{policy_id}")
        return data.get("policy", data)

    def create_policy(self, body: dict[str, Any]) -> Policy:
        data = self._client.post(f"{self._v3}/policies",
                                 json={"policy": body})
        return data.get("policy", data) if data else {}

    def update_policy(self, policy_id: str, body: dict[str, Any]) -> Policy:
        data = self._client.patch(f"{self._v3}/policies/{policy_id}",
                                  json={"policy": body})
        return data.get("policy", data) if data else {}

    def delete_policy(self, policy_id: str) -> None:
        self._client.delete(f"{self._v3}/policies/{policy_id}")

    # ── federation: identity providers ─────────────────────────────────

    def find_identity_providers(self) -> list[IdentityProvider]:
        data = self._client.get(f"{self._v3}/identity_providers")
        return data.get("identity_providers", [])

    def get_identity_provider(self, idp_id: str) -> IdentityProvider:
        data = self._client.get(f"{self._v3}/identity_providers/{idp_id}")
        return data.get("identity_provider", data)

    def create_identity_provider(
        self, idp_id: str, body: dict[str, Any],
    ) -> IdentityProvider:
        # Keystone federation uses PUT for upsert creation.
        data = self._client.put(
            f"{self._v3}/identity_providers/{idp_id}",
            json={"identity_provider": body},
        )
        return data.get("identity_provider", data) if data else {}

    def update_identity_provider(
        self, idp_id: str, body: dict[str, Any],
    ) -> IdentityProvider:
        data = self._client.patch(
            f"{self._v3}/identity_providers/{idp_id}",
            json={"identity_provider": body},
        )
        return data.get("identity_provider", data) if data else {}

    def delete_identity_provider(self, idp_id: str) -> None:
        self._client.delete(f"{self._v3}/identity_providers/{idp_id}")

    # ── federation: protocols ──────────────────────────────────────────

    def find_federation_protocols(self, idp_id: str) -> list[FederationProtocol]:
        data = self._client.get(
            f"{self._v3}/identity_providers/{idp_id}/protocols"
        )
        return data.get("protocols", [])

    def get_federation_protocol(
        self, idp_id: str, proto_id: str,
    ) -> FederationProtocol:
        data = self._client.get(
            f"{self._v3}/identity_providers/{idp_id}/protocols/{proto_id}"
        )
        return data.get("protocol", data)

    def create_federation_protocol(
        self, idp_id: str, proto_id: str, body: dict[str, Any],
    ) -> FederationProtocol:
        data = self._client.put(
            f"{self._v3}/identity_providers/{idp_id}/protocols/{proto_id}",
            json={"protocol": body},
        )
        return data.get("protocol", data) if data else {}

    def update_federation_protocol(
        self, idp_id: str, proto_id: str, body: dict[str, Any],
    ) -> FederationProtocol:
        data = self._client.patch(
            f"{self._v3}/identity_providers/{idp_id}/protocols/{proto_id}",
            json={"protocol": body},
        )
        return data.get("protocol", data) if data else {}

    def delete_federation_protocol(
        self, idp_id: str, proto_id: str,
    ) -> None:
        self._client.delete(
            f"{self._v3}/identity_providers/{idp_id}/protocols/{proto_id}"
        )

    # ── federation: mappings ───────────────────────────────────────────

    def find_mappings(self) -> list[Mapping]:
        data = self._client.get(f"{self._v3}/mappings")
        return data.get("mappings", [])

    def get_mapping(self, mapping_id: str) -> Mapping:
        data = self._client.get(f"{self._v3}/mappings/{mapping_id}")
        return data.get("mapping", data)

    def create_mapping(self, mapping_id: str,
                       body: dict[str, Any]) -> Mapping:
        data = self._client.put(f"{self._v3}/mappings/{mapping_id}",
                                json={"mapping": body})
        return data.get("mapping", data) if data else {}

    def update_mapping(self, mapping_id: str,
                       body: dict[str, Any]) -> Mapping:
        data = self._client.patch(f"{self._v3}/mappings/{mapping_id}",
                                  json={"mapping": body})
        return data.get("mapping", data) if data else {}

    def delete_mapping(self, mapping_id: str) -> None:
        self._client.delete(f"{self._v3}/mappings/{mapping_id}")

    # ── federation: service providers ──────────────────────────────────

    def find_service_providers(self) -> list[ServiceProvider]:
        data = self._client.get(f"{self._v3}/service_providers")
        return data.get("service_providers", [])

    def get_service_provider(self, sp_id: str) -> ServiceProvider:
        data = self._client.get(f"{self._v3}/service_providers/{sp_id}")
        return data.get("service_provider", data)

    def create_service_provider(
        self, sp_id: str, body: dict[str, Any],
    ) -> ServiceProvider:
        data = self._client.put(
            f"{self._v3}/service_providers/{sp_id}",
            json={"service_provider": body},
        )
        return data.get("service_provider", data) if data else {}

    def update_service_provider(
        self, sp_id: str, body: dict[str, Any],
    ) -> ServiceProvider:
        data = self._client.patch(
            f"{self._v3}/service_providers/{sp_id}",
            json={"service_provider": body},
        )
        return data.get("service_provider", data) if data else {}

    def delete_service_provider(self, sp_id: str) -> None:
        self._client.delete(f"{self._v3}/service_providers/{sp_id}")

    # ── trusts (OS-TRUST extension) ────────────────────────────────────

    def find_trusts(self, *,
                    params: dict[str, Any] | None = None) -> list[Trust]:
        data = self._client.get(f"{self._base}/OS-TRUST/trusts",
                                params=params)
        return data.get("trusts", [])

    def get_trust(self, trust_id: str) -> Trust:
        data = self._client.get(f"{self._base}/OS-TRUST/trusts/{trust_id}")
        return data.get("trust", data)

    def create_trust(self, body: dict[str, Any]) -> Trust:
        data = self._client.post(f"{self._base}/OS-TRUST/trusts",
                                 json={"trust": body})
        return data.get("trust", data) if data else {}

    def delete_trust(self, trust_id: str) -> None:
        self._client.delete(f"{self._base}/OS-TRUST/trusts/{trust_id}")

    # ── tokens ─────────────────────────────────────────────────────────

    def revoke_token(self, subject_token: str) -> None:
        """Revoke a token (DELETE with X-Subject-Token header)."""
        self._client.delete(
            f"{self._v3}/auth/tokens",
            headers={"X-Subject-Token": subject_token},
        )

    # ── access rules (/v3, per-user) ───────────────────────────────────

    def find_access_rules(self, user_id: str) -> list[AccessRule]:
        data = self._client.get(f"{self._v3}/users/{user_id}/access_rules")
        return data.get("access_rules", [])

    def get_access_rule(self, user_id: str, rule_id: str) -> AccessRule:
        data = self._client.get(
            f"{self._v3}/users/{user_id}/access_rules/{rule_id}"
        )
        return data.get("access_rule", data)

    def delete_access_rule(self, user_id: str, rule_id: str) -> None:
        self._client.delete(
            f"{self._v3}/users/{user_id}/access_rules/{rule_id}"
        )

    # ── registered limits (Keystone enforcement defaults) ──────────────

    def find_registered_limits(
        self, *, params: dict[str, Any] | None = None,
    ) -> list[RegisteredLimit]:
        data = self._client.get(f"{self._v3}/registered_limits",
                                params=params)
        return data.get("registered_limits", [])

    def get_registered_limit(self, limit_id: str) -> RegisteredLimit:
        data = self._client.get(f"{self._v3}/registered_limits/{limit_id}")
        return data.get("registered_limit", data)

    def create_registered_limits(
        self, items: list[dict[str, Any]],
    ) -> list[RegisteredLimit]:
        """Keystone POST accepts a list of registered limits at once."""
        data = self._client.post(
            f"{self._v3}/registered_limits",
            json={"registered_limits": items},
        )
        return data.get("registered_limits", []) if data else []

    def update_registered_limit(
        self, limit_id: str, body: dict[str, Any],
    ) -> RegisteredLimit:
        data = self._client.patch(
            f"{self._v3}/registered_limits/{limit_id}",
            json={"registered_limit": body},
        )
        return data.get("registered_limit", data) if data else {}

    def delete_registered_limit(self, limit_id: str) -> None:
        self._client.delete(f"{self._v3}/registered_limits/{limit_id}")

    # ── project-scoped limits (overrides) ──────────────────────────────

    def find_limits(
        self, *, params: dict[str, Any] | None = None,
    ) -> list[Limit]:
        data = self._client.get(f"{self._v3}/limits", params=params)
        return data.get("limits", [])

    def get_limit(self, limit_id: str) -> Limit:
        data = self._client.get(f"{self._v3}/limits/{limit_id}")
        return data.get("limit", data)

    def create_limits(
        self, items: list[dict[str, Any]],
    ) -> list[Limit]:
        """Keystone POST accepts a list of limits at once."""
        data = self._client.post(
            f"{self._v3}/limits", json={"limits": items},
        )
        return data.get("limits", []) if data else []

    def update_limit(
        self, limit_id: str, body: dict[str, Any],
    ) -> Limit:
        data = self._client.patch(
            f"{self._v3}/limits/{limit_id}", json={"limit": body},
        )
        return data.get("limit", data) if data else {}

    def delete_limit(self, limit_id: str) -> None:
        self._client.delete(f"{self._v3}/limits/{limit_id}")
