"""Typed views of Heat orchestration resources (only the fields orca reads)."""

from __future__ import annotations

from typing import TypedDict


class Stack(TypedDict, total=False):
    id: str
    stack_name: str
    description: str
    stack_status: str
    stack_status_reason: str
    creation_time: str
    updated_time: str
    deletion_time: str
    parent: str
    outputs: list
    parameters: dict
    capabilities: list
    notification_topics: list
    template_description: str
    timeout_mins: int
    tags: list
    disable_rollback: bool


class StackResource(TypedDict, total=False):
    resource_name: str
    physical_resource_id: str
    resource_type: str
    resource_status: str
    resource_status_reason: str
    updated_time: str
    required_by: list
    links: list


class StackEvent(TypedDict, total=False):
    id: str
    resource_name: str
    resource_status: str
    resource_status_reason: str
    event_time: str
    logical_resource_id: str
    physical_resource_id: str
    resource_type: str


class StackOutput(TypedDict, total=False):
    output_key: str
    output_value: str
    description: str
    output_error: str
