"""TypedDict shapes for Freezer backup resources.

All fields are ``total=False`` because Freezer API responses are
sparse and version-dependent — only fields actually consumed by the
CLI are typed; unknown extras pass through as ``Any``.
"""

from __future__ import annotations

from typing import Any, TypedDict


class FreezerAction(TypedDict, total=False):
    action: str
    mode: str
    storage: str
    path_to_backup: str
    restore_abs_path: str
    container: str
    backup_name: str
    max_level: int
    max_retries: int
    no_incremental: bool
    engine_name: str
    log_file: str
    hostname_dir_to_backup: str


class Backup(TypedDict, total=False):
    backup_id: str
    backup_name: str
    container: str
    status: str
    curr_backup_level: int
    storage: str
    mode: str
    engine_name: str
    time_stamp: int
    path_to_backup: str
    hostname: str
    os_auth_version: str
    project_id: str
    backup_metadata: dict[str, Any]


class JobSchedule(TypedDict, total=False):
    status: str
    event: str
    time: str
    schedule_interval: str


class Job(TypedDict, total=False):
    job_id: str
    description: str
    client_id: str
    user_id: str
    project_id: str
    session_id: str
    job_schedule: JobSchedule
    job_actions: list[dict[str, FreezerAction]]


class Session(TypedDict, total=False):
    session_id: str
    description: str
    status: str
    user_id: str
    project_id: str
    time_start: int
    time_end: int
    schedule: dict[str, Any]
    jobs: dict[str, Any]


class FreezerClient(TypedDict, total=False):
    client_id: str
    hostname: str
    description: str
    uuid: str
    user_id: str
    project_id: str


class Action(TypedDict, total=False):
    action_id: str
    user_id: str
    project_id: str
    freezer_action: FreezerAction
