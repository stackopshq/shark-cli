"""Typed views of Keystone v3 identity resources (only the fields orca reads)."""

from __future__ import annotations

from typing import TypedDict


class Project(TypedDict, total=False):
    id: str
    name: str
    description: str
    domain_id: str
    parent_id: str
    enabled: bool
    is_domain: bool
    tags: list
    options: dict


class User(TypedDict, total=False):
    id: str
    name: str
    email: str
    description: str
    enabled: bool
    domain_id: str
    default_project_id: str
    password_expires_at: str
    options: dict


class Role(TypedDict, total=False):
    id: str
    name: str
    description: str
    domain_id: str
    options: dict


class RoleAssignment(TypedDict, total=False):
    user: dict
    group: dict
    role: dict
    scope: dict


class RoleInference(TypedDict, total=False):
    prior_role: dict
    implies: list


class Domain(TypedDict, total=False):
    id: str
    name: str
    description: str
    enabled: bool
    options: dict


class Group(TypedDict, total=False):
    id: str
    name: str
    description: str
    domain_id: str


class Credential(TypedDict, total=False):
    id: str
    user_id: str
    project_id: str
    type: str
    blob: str


class ApplicationCredential(TypedDict, total=False):
    id: str
    name: str
    description: str
    project_id: str
    user_id: str
    secret: str
    roles: list
    expires_at: str
    unrestricted: bool
    access_rules: list


class Endpoint(TypedDict, total=False):
    id: str
    service_id: str
    region_id: str
    region: str
    interface: str
    url: str
    enabled: bool


class EndpointGroup(TypedDict, total=False):
    id: str
    name: str
    description: str
    filters: dict


class Service(TypedDict, total=False):
    id: str
    name: str
    type: str
    description: str
    enabled: bool


class Region(TypedDict, total=False):
    id: str
    description: str
    parent_region_id: str


class Policy(TypedDict, total=False):
    id: str
    type: str
    blob: str


class IdentityProvider(TypedDict, total=False):
    id: str
    description: str
    enabled: bool
    remote_ids: list
    domain_id: str
    authorization_ttl: int


class FederationProtocol(TypedDict, total=False):
    id: str
    mapping_id: str


class Mapping(TypedDict, total=False):
    id: str
    rules: list
    schema_version: str


class ServiceProvider(TypedDict, total=False):
    id: str
    description: str
    enabled: bool
    auth_url: str
    sp_url: str
    relay_state_prefix: str


class Trust(TypedDict, total=False):
    id: str
    trustor_user_id: str
    trustee_user_id: str
    project_id: str
    impersonation: bool
    roles: list
    expires_at: str
    remaining_uses: int


class AccessRule(TypedDict, total=False):
    id: str
    service: str
    method: str
    path: str


class RegisteredLimit(TypedDict, total=False):
    id: str
    service_id: str
    region_id: str
    resource_name: str
    default_limit: int
    description: str


class Limit(TypedDict, total=False):
    id: str
    service_id: str
    region_id: str
    resource_name: str
    resource_limit: int
    description: str
    project_id: str
    domain_id: str
