"""High-level operations on Cinder block storage resources."""

from __future__ import annotations

from typing import Any

from orca_cli.core.client import OrcaClient
from orca_cli.models.volume import Volume, VolumeAttachment, VolumeBackup, VolumeSnapshot


class VolumeService:
    """Typed wrapper around the Cinder ``/volumes`` (and adjacent) endpoints.

    Owns URL construction for everything under ``client.volume_url``.
    Methods cover volumes, snapshots, backups, attachments, types,
    QoS specs, groups, group snapshots/types, transfers, messages,
    and the os-services admin endpoint.
    """

    def __init__(self, client: OrcaClient) -> None:
        self._client = client
        self._base = client.volume_url

    # ── volumes ────────────────────────────────────────────────────────

    def find(self, *, params: dict[str, Any] | None = None) -> list[Volume]:
        data = self._client.get(f"{self._base}/volumes/detail", params=params)
        return data.get("volumes", [])

    def find_all(self, page_size: int = 1000, *,
                 params: dict[str, Any] | None = None) -> list[Volume]:
        return self._client.paginate(f"{self._base}/volumes/detail", "volumes",
                                     page_size=page_size, params=params)

    def get(self, volume_id: str) -> Volume:
        data = self._client.get(f"{self._base}/volumes/{volume_id}")
        return data.get("volume", data)

    def create(self, body: dict[str, Any]) -> Volume:
        data = self._client.post(f"{self._base}/volumes", json={"volume": body})
        return data.get("volume", data) if data else {}

    def update(self, volume_id: str, body: dict[str, Any]) -> Volume:
        data = self._client.put(f"{self._base}/volumes/{volume_id}",
                                json={"volume": body})
        return data.get("volume", data) if data else {}

    def delete(self, volume_id: str, *,
               cascade: bool = False, force: bool = False) -> None:
        params: dict[str, Any] = {}
        if cascade:
            params["cascade"] = True
        if force:
            params["force"] = True
        self._client.delete(f"{self._base}/volumes/{volume_id}",
                            params=params or None)

    def action(self, volume_id: str, body: dict[str, Any]) -> dict | None:
        return self._client.post(f"{self._base}/volumes/{volume_id}/action",
                                 json=body)

    def extend(self, volume_id: str, new_size: int) -> None:
        self.action(volume_id, {"os-extend": {"new_size": new_size}})

    def retype(self, volume_id: str, new_type: str, *,
               migration_policy: str = "never") -> None:
        self.action(volume_id, {"os-retype": {
            "new_type": new_type, "migration_policy": migration_policy,
        }})

    def set_bootable(self, volume_id: str, bootable: bool) -> None:
        self.action(volume_id, {"os-set_bootable": {"bootable": bootable}})

    def set_readonly(self, volume_id: str, readonly: bool) -> None:
        self.action(volume_id, {"os-update_readonly_flag": {"readonly": readonly}})

    def revert_to_snapshot(self, volume_id: str, snapshot_id: str) -> None:
        self.action(volume_id, {"revert": {"snapshot_id": snapshot_id}})

    def migrate(self, volume_id: str, host: str, *,
                force_host_copy: bool = False,
                lock_volume: bool = False) -> None:
        self.action(volume_id, {"os-migrate_volume": {
            "host": host,
            "force_host_copy": force_host_copy,
            "lock_volume": lock_volume,
        }})

    def set_metadata(self, volume_id: str, kv: dict[str, str]) -> dict[str, str]:
        data = self._client.post(f"{self._base}/volumes/{volume_id}/metadata",
                                 json={"metadata": kv})
        return data.get("metadata", {}) if data else {}

    def delete_metadata_key(self, volume_id: str, key: str) -> None:
        self._client.delete(f"{self._base}/volumes/{volume_id}/metadata/{key}")

    def get_summary(self) -> dict:
        data = self._client.get(f"{self._base}/volumes/summary")
        return data.get("volume-summary", data) if data else {}

    # ── snapshots ──────────────────────────────────────────────────────

    def find_snapshots(self, *,
                       params: dict[str, Any] | None = None) -> list[VolumeSnapshot]:
        data = self._client.get(f"{self._base}/snapshots/detail", params=params)
        return data.get("snapshots", [])

    def get_snapshot(self, snapshot_id: str) -> VolumeSnapshot:
        data = self._client.get(f"{self._base}/snapshots/{snapshot_id}")
        return data.get("snapshot", data)

    def create_snapshot(self, body: dict[str, Any]) -> VolumeSnapshot:
        data = self._client.post(f"{self._base}/snapshots",
                                 json={"snapshot": body})
        return data.get("snapshot", data) if data else {}

    def delete_snapshot(self, snapshot_id: str) -> None:
        self._client.delete(f"{self._base}/snapshots/{snapshot_id}")

    def update_snapshot(self, snapshot_id: str, body: dict[str, Any]) -> VolumeSnapshot:
        data = self._client.put(f"{self._base}/snapshots/{snapshot_id}",
                                json={"snapshot": body})
        return data.get("snapshot", data) if data else {}

    def update_snapshot_metadata(self, snapshot_id: str, kv: dict[str, str]) -> dict:
        # Cinder uses POST for metadata merge (matches the volume metadata API).
        data = self._client.post(f"{self._base}/snapshots/{snapshot_id}/metadata",
                                 json={"metadata": kv})
        return data.get("metadata", {}) if data else {}

    # ── backups ────────────────────────────────────────────────────────

    def find_backups(self, *,
                     params: dict[str, Any] | None = None) -> list[VolumeBackup]:
        data = self._client.get(f"{self._base}/backups/detail", params=params)
        return data.get("backups", [])

    def get_backup(self, backup_id: str) -> VolumeBackup:
        data = self._client.get(f"{self._base}/backups/{backup_id}")
        return data.get("backup", data)

    def create_backup(self, body: dict[str, Any]) -> VolumeBackup:
        data = self._client.post(f"{self._base}/backups",
                                 json={"backup": body})
        return data.get("backup", data) if data else {}

    def delete_backup(self, backup_id: str, *, force: bool = False) -> None:
        params = {"force": True} if force else None
        self._client.delete(f"{self._base}/backups/{backup_id}", params=params)

    def restore_backup(self, backup_id: str, body: dict[str, Any]) -> dict:
        data = self._client.post(f"{self._base}/backups/{backup_id}/restore",
                                 json={"restore": body})
        return data.get("restore", data) if data else {}

    # ── attachments ────────────────────────────────────────────────────

    def find_attachments(self, *,
                         params: dict[str, Any] | None = None) -> list[VolumeAttachment]:
        data = self._client.get(f"{self._base}/attachments", params=params)
        return data.get("attachments", [])

    def get_attachment(self, attachment_id: str) -> VolumeAttachment:
        data = self._client.get(f"{self._base}/attachments/{attachment_id}")
        return data.get("attachment", data)

    def create_attachment(self, body: dict[str, Any]) -> VolumeAttachment:
        data = self._client.post(f"{self._base}/attachments",
                                 json={"attachment": body})
        return data.get("attachment", data) if data else {}

    def update_attachment(self, attachment_id: str, body: dict[str, Any]) -> dict:
        data = self._client.put(f"{self._base}/attachments/{attachment_id}",
                                json={"attachment": body})
        return data.get("attachment", data) if data else {}

    def delete_attachment(self, attachment_id: str) -> None:
        self._client.delete(f"{self._base}/attachments/{attachment_id}")

    def complete_attachment(self, attachment_id: str) -> None:
        self._client.post(f"{self._base}/attachments/{attachment_id}/action",
                          json={"os-complete": None})

    # ── volume types & access ──────────────────────────────────────────

    def find_types(self) -> list[dict]:
        data = self._client.get(f"{self._base}/types")
        return data.get("volume_types", [])

    def get_type(self, type_id: str) -> dict:
        data = self._client.get(f"{self._base}/types/{type_id}")
        return data.get("volume_type", data)

    def get_default_type(self) -> dict:
        data = self._client.get(f"{self._base}/types/default")
        return data.get("volume_type", data) if data else {}

    def create_type(self, body: dict[str, Any]) -> dict:
        data = self._client.post(f"{self._base}/types",
                                 json={"volume_type": body})
        return data.get("volume_type", data) if data else {}

    def update_type(self, type_id: str, body: dict[str, Any]) -> dict:
        data = self._client.put(f"{self._base}/types/{type_id}",
                                json={"volume_type": body})
        return data.get("volume_type", data) if data else {}

    def delete_type(self, type_id: str) -> None:
        self._client.delete(f"{self._base}/types/{type_id}")

    def set_type_extra_specs(self, type_id: str, kv: dict[str, str]) -> dict:
        data = self._client.post(f"{self._base}/types/{type_id}/extra_specs",
                                 json={"extra_specs": kv})
        return data.get("extra_specs", {}) if data else {}

    def list_type_access(self, type_id: str) -> list[dict]:
        data = self._client.get(
            f"{self._base}/types/{type_id}/os-volume-type-access"
        )
        return data.get("volume_type_access", [])

    def add_type_access(self, type_id: str, project_id: str) -> None:
        self._client.post(f"{self._base}/types/{type_id}/action",
                          json={"addProjectAccess": {"project": project_id}})

    def remove_type_access(self, type_id: str, project_id: str) -> None:
        self._client.post(f"{self._base}/types/{type_id}/action",
                          json={"removeProjectAccess": {"project": project_id}})

    # ── QoS specs ──────────────────────────────────────────────────────

    def find_qos(self) -> list[dict]:
        data = self._client.get(f"{self._base}/qos-specs")
        return data.get("qos_specs", [])

    def get_qos(self, qos_id: str) -> dict:
        data = self._client.get(f"{self._base}/qos-specs/{qos_id}")
        return data.get("qos_specs", data)

    def create_qos(self, body: dict[str, Any]) -> dict:
        data = self._client.post(f"{self._base}/qos-specs",
                                 json={"qos_specs": body})
        return data.get("qos_specs", data) if data else {}

    def update_qos(self, qos_id: str, body: dict[str, Any]) -> dict:
        data = self._client.put(f"{self._base}/qos-specs/{qos_id}",
                                json={"qos_specs": body})
        return data.get("qos_specs", data) if data else {}

    def delete_qos(self, qos_id: str, *, force: bool = False) -> None:
        params = {"force": True} if force else None
        self._client.delete(f"{self._base}/qos-specs/{qos_id}", params=params)

    def associate_qos(self, qos_id: str, type_id: str) -> None:
        self._client.get(f"{self._base}/qos-specs/{qos_id}/associate",
                         params={"vol_type_id": type_id})

    def disassociate_qos(self, qos_id: str, type_id: str | None = None) -> None:
        if type_id:
            self._client.get(f"{self._base}/qos-specs/{qos_id}/disassociate",
                             params={"vol_type_id": type_id})
        else:
            self._client.get(f"{self._base}/qos-specs/{qos_id}/disassociate_all")

    # ── transfers ──────────────────────────────────────────────────────

    def find_transfers(self, *,
                       params: dict[str, Any] | None = None) -> list[dict]:
        data = self._client.get(f"{self._base}/volume-transfers/detail",
                                params=params)
        return data.get("transfers", [])

    def get_transfer(self, transfer_id: str) -> dict:
        data = self._client.get(f"{self._base}/volume-transfers/{transfer_id}")
        return data.get("transfer", data)

    def create_transfer(self, body: dict[str, Any]) -> dict:
        data = self._client.post(f"{self._base}/volume-transfers",
                                 json={"transfer": body})
        return data.get("transfer", data) if data else {}

    def accept_transfer(self, transfer_id: str, auth_key: str) -> dict:
        data = self._client.post(
            f"{self._base}/volume-transfers/{transfer_id}/accept",
            json={"accept": {"auth_key": auth_key}},
        )
        return data.get("transfer", data) if data else {}

    def delete_transfer(self, transfer_id: str) -> None:
        self._client.delete(f"{self._base}/volume-transfers/{transfer_id}")

    # ── messages ───────────────────────────────────────────────────────

    def find_messages(self) -> list[dict]:
        data = self._client.get(f"{self._base}/messages")
        return data.get("messages", [])

    def get_message(self, message_id: str) -> dict:
        data = self._client.get(f"{self._base}/messages/{message_id}")
        return data.get("message", data)

    def delete_message(self, message_id: str) -> None:
        self._client.delete(f"{self._base}/messages/{message_id}")

    # ── groups ─────────────────────────────────────────────────────────

    def find_groups(self) -> list[dict]:
        data = self._client.get(f"{self._base}/groups/detail")
        return data.get("groups", [])

    def get_group(self, group_id: str) -> dict:
        data = self._client.get(f"{self._base}/groups/{group_id}")
        return data.get("group", data)

    def create_group(self, body: dict[str, Any]) -> dict:
        data = self._client.post(f"{self._base}/groups",
                                 json={"group": body})
        return data.get("group", data) if data else {}

    def update_group(self, group_id: str, body: dict[str, Any]) -> dict:
        data = self._client.put(f"{self._base}/groups/{group_id}",
                                json={"group": body})
        return data.get("group", data) if data else {}

    def delete_group(self, group_id: str, *, delete_volumes: bool = False) -> None:
        self._client.post(f"{self._base}/groups/{group_id}/action",
                          json={"delete": {"delete-volumes": delete_volumes}})

    # ── group snapshots ────────────────────────────────────────────────

    def find_group_snapshots(self) -> list[dict]:
        data = self._client.get(f"{self._base}/group_snapshots/detail")
        return data.get("group_snapshots", [])

    def get_group_snapshot(self, gs_id: str) -> dict:
        data = self._client.get(f"{self._base}/group_snapshots/{gs_id}")
        return data.get("group_snapshot", data)

    def create_group_snapshot(self, body: dict[str, Any]) -> dict:
        data = self._client.post(f"{self._base}/group_snapshots",
                                 json={"group_snapshot": body})
        return data.get("group_snapshot", data) if data else {}

    def delete_group_snapshot(self, gs_id: str) -> None:
        self._client.delete(f"{self._base}/group_snapshots/{gs_id}")

    # ── group types ────────────────────────────────────────────────────

    def find_group_types(self) -> list[dict]:
        data = self._client.get(f"{self._base}/group_types")
        return data.get("group_types", [])

    def get_group_type(self, gt_id: str) -> dict:
        data = self._client.get(f"{self._base}/group_types/{gt_id}")
        return data.get("group_type", data)

    def create_group_type(self, body: dict[str, Any]) -> dict:
        data = self._client.post(f"{self._base}/group_types",
                                 json={"group_type": body})
        return data.get("group_type", data) if data else {}

    def update_group_type(self, gt_id: str, body: dict[str, Any]) -> dict:
        data = self._client.put(f"{self._base}/group_types/{gt_id}",
                                json={"group_type": body})
        return data.get("group_type", data) if data else {}

    def delete_group_type(self, gt_id: str) -> None:
        self._client.delete(f"{self._base}/group_types/{gt_id}")

    def set_group_specs(self, gt_id: str, kv: dict[str, str]) -> dict:
        data = self._client.post(
            f"{self._base}/group_types/{gt_id}/group_specs",
            json={"group_specs": kv},
        )
        return data.get("group_specs", {}) if data else {}

    def unset_group_spec(self, gt_id: str, key: str) -> None:
        self._client.delete(
            f"{self._base}/group_types/{gt_id}/group_specs/{key}"
        )

    # ── services (admin) ───────────────────────────────────────────────

    def find_services(self, *,
                      params: dict[str, Any] | None = None) -> list[dict]:
        data = self._client.get(f"{self._base}/os-services", params=params)
        return data.get("services", [])

    def update_service(self, action: str, body: dict[str, Any]) -> dict | None:
        """``action`` is the verb path ('enable', 'disable', 'disable-log-reason').
        """
        return self._client.put(f"{self._base}/os-services/{action}", json=body)

    # ── limits ─────────────────────────────────────────────────────────

    def get_limits(self) -> dict:
        """Absolute project limits (totalVolumesUsed etc.)."""
        data = self._client.get(f"{self._base}/limits")
        return data.get("limits", {}).get("absolute", {})
