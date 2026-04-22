"""Typed views of Swift object-storage resources (only the fields orca reads)."""

from __future__ import annotations

from typing import TypedDict


class Container(TypedDict, total=False):
    name: str
    count: int
    bytes: int
    last_modified: str


class ObjectEntry(TypedDict, total=False):
    name: str
    subdir: str
    bytes: int
    hash: str
    last_modified: str
    content_type: str
