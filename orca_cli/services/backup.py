"""High-level operations on Freezer backup resources.

Freezer's API uses ``/v2/<collection>`` paths under ``client.backup_url``,
returns lists wrapped in ``{"<collection>": [...]}``, and exposes
event-style controls (``POST /v2/jobs/{id}/event`` with ``{"event":
"start"}``) for job lifecycle. The service collapses these patterns so
``commands/backup.py`` deals only with typed dictionaries.
"""

from __future__ import annotations

from typing import Any

from orca_cli.core.client import OrcaClient
from orca_cli.models.backup import (
    Action,
    Backup,
    FreezerClient,
    Job,
    Session,
)


class BackupService:
    """Typed wrapper around the Freezer ``/v2/*`` endpoints."""

    def __init__(self, client: OrcaClient) -> None:
        self._client = client
        self._base = f"{client.backup_url}/v2"

    # ── backups ────────────────────────────────────────────────────────

    def find_backups(
        self, *, params: dict[str, Any] | None = None,
    ) -> list[Backup]:
        data = self._client.get(f"{self._base}/backups", params=params) or {}
        if isinstance(data, list):
            return data
        return data.get("backups", [])

    def get_backup(self, backup_id: str) -> Backup:
        data = self._client.get(f"{self._base}/backups/{backup_id}")
        return data if data else {}

    def delete_backup(self, backup_id: str) -> None:
        self._client.delete(f"{self._base}/backups/{backup_id}")

    # ── jobs ───────────────────────────────────────────────────────────

    def find_jobs(
        self, *, params: dict[str, Any] | None = None,
    ) -> list[Job]:
        data = self._client.get(f"{self._base}/jobs", params=params) or {}
        if isinstance(data, list):
            return data
        return data.get("jobs", [])

    def get_job(self, job_id: str) -> Job:
        data = self._client.get(f"{self._base}/jobs/{job_id}")
        return data if data else {}

    def create_job(self, body: dict[str, Any]) -> Job:
        data = self._client.post(f"{self._base}/jobs", json=body)
        return data if data else {}

    def start_job(self, job_id: str) -> None:
        self._client.post(f"{self._base}/jobs/{job_id}/event",
                          json={"event": "start"})

    def stop_job(self, job_id: str) -> None:
        self._client.post(f"{self._base}/jobs/{job_id}/event",
                          json={"event": "stop"})

    def delete_job(self, job_id: str) -> None:
        self._client.delete(f"{self._base}/jobs/{job_id}")

    # ── sessions ───────────────────────────────────────────────────────

    def find_sessions(
        self, *, params: dict[str, Any] | None = None,
    ) -> list[Session]:
        data = self._client.get(f"{self._base}/sessions", params=params) or {}
        if isinstance(data, list):
            return data
        return data.get("sessions", [])

    def get_session(self, session_id: str) -> Session:
        data = self._client.get(f"{self._base}/sessions/{session_id}")
        return data if data else {}

    def create_session(self, body: dict[str, Any]) -> Session:
        data = self._client.post(f"{self._base}/sessions", json=body)
        return data if data else {}

    def add_job_to_session(self, session_id: str, job_id: str) -> None:
        self._client.put(
            f"{self._base}/sessions/{session_id}/jobs/{job_id}"
        )

    def remove_job_from_session(self, session_id: str, job_id: str) -> None:
        self._client.delete(
            f"{self._base}/sessions/{session_id}/jobs/{job_id}"
        )

    def start_session(self, session_id: str) -> None:
        """Trigger every job attached to the session."""
        self._client.post(
            f"{self._base}/sessions/{session_id}/action",
            json={"start": None},
        )

    def delete_session(self, session_id: str) -> None:
        self._client.delete(f"{self._base}/sessions/{session_id}")

    # ── clients (Freezer agents) ───────────────────────────────────────

    def find_clients(
        self, *, params: dict[str, Any] | None = None,
    ) -> list[FreezerClient]:
        data = self._client.get(f"{self._base}/clients", params=params) or {}
        if isinstance(data, list):
            return data
        return data.get("clients", [])

    def get_client(self, client_id: str) -> FreezerClient:
        data = self._client.get(f"{self._base}/clients/{client_id}")
        return data if data else {}

    def register_client(self, body: dict[str, Any]) -> FreezerClient:
        data = self._client.post(f"{self._base}/clients", json=body)
        return data if data else {}

    def delete_client(self, client_id: str) -> None:
        self._client.delete(f"{self._base}/clients/{client_id}")

    # ── actions (standalone) ───────────────────────────────────────────

    def find_actions(
        self, *, params: dict[str, Any] | None = None,
    ) -> list[Action]:
        data = self._client.get(f"{self._base}/actions", params=params) or {}
        if isinstance(data, list):
            return data
        return data.get("actions", [])

    def get_action(self, action_id: str) -> Action:
        data = self._client.get(f"{self._base}/actions/{action_id}")
        return data if data else {}

    def create_action(self, freezer_action: dict[str, Any]) -> Action:
        data = self._client.post(
            f"{self._base}/actions",
            json={"freezer_action": freezer_action},
        )
        return data if data else {}

    def delete_action(self, action_id: str) -> None:
        self._client.delete(f"{self._base}/actions/{action_id}")
