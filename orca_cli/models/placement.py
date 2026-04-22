"""Typed views of OpenStack Placement resources."""

from __future__ import annotations

from typing import TypedDict


class ResourceProvider(TypedDict, total=False):
    uuid: str
    name: str
    parent_provider_uuid: str
    root_provider_uuid: str
    generation: int


class Inventory(TypedDict, total=False):
    resource_provider_generation: int
    total: int
    reserved: int
    min_unit: int
    max_unit: int
    step_size: int
    allocation_ratio: float


class ProviderUsages(TypedDict, total=False):
    resource_provider_generation: int
    usages: dict


class ResourceClass(TypedDict, total=False):
    name: str
    links: list


class Trait(TypedDict, total=False):
    name: str


class Allocation(TypedDict, total=False):
    allocations: dict
    project_id: str
    user_id: str
    consumer_generation: int


class AllocationCandidate(TypedDict, total=False):
    allocation_requests: list
    provider_summaries: dict
