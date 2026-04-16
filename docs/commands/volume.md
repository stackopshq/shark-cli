# `orca volume` — volume

Manage block storage volumes & snapshots.

---

## attachment-complete

ATTACHMENT_ID

```bash
orca volume attachment-complete [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## attachment-create

INSTANCE_ID

```bash
orca volume attachment-create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--mode [rw|ro]` | Attach mode: read-write or read-only. |
| `--connector JSON` | Connector info as JSON (host, initiator, |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## attachment-delete

ATTACHMENT_ID

```bash
orca volume attachment-delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## attachment-list

List volume attachments (Cinder v3 attachment API).

```bash
orca volume attachment-list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--volume-id TEXT` | Filter by volume ID. |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## attachment-set

Update (finalize) a volume attachment with connector info.

```bash
orca volume attachment-set [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--connector JSON` | Updated connector info as JSON.  [required] |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## attachment-show

Show a volume attachment.

```bash
orca volume attachment-show [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## backup-create

Create a Cinder volume backup.

```bash
orca volume backup-create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--name TEXT` | Backup name. |
| `--description TEXT` | Backup description. |
| `--container TEXT` | Optional backup container name. |
| `--snapshot-id TEXT` | Snapshot ID to backup instead of full volume. |
| `--force` | Allow backing up an in-use volume. |
| `--incremental` | Perform an incremental backup. |
| `--wait` | Wait for backup to reach 'available'. |
| `--help` | Show this message and exit. |

---

## backup-delete

Delete a Cinder volume backup.

```bash
orca volume backup-delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--force` | Force delete even if backup is in error. |
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## backup-list

List Cinder volume backups.

```bash
orca volume backup-list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--all-projects` | Include all projects (admin). |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## backup-restore

Restore a Cinder volume backup.

```bash
orca volume backup-restore [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--volume-id TEXT` | Restore to this existing volume ID. |
| `--name TEXT` | Name for the new volume (if not restoring to existing). |
| `--wait` | Wait for restored volume to become 'available'. |
| `--help` | Show this message and exit. |

---

## backup-show

Show Cinder volume backup details.

```bash
orca volume backup-show [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## create

Create a volume.

```bash
orca volume create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--name TEXT` | Volume name. |
| `--size INTEGER` | Size in GB. |
| `--type TEXT` | Volume type. |
| `--description TEXT` | Volume description. |
| `--snapshot-id TEXT` | Create from snapshot. |
| `--source-vol TEXT` | Create from existing volume (clone). |
| `--image-id TEXT` | Create from image. |
| `--wait` | Wait until the volume reaches 'available' status. |
| `-i, --interactive` | Step-by-step wizard — choose name, size, and type |
| `--help` | Show this message and exit. |

---

## delete

Delete a volume.

```bash
orca volume delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--dry-run` | Show what would be deleted without deleting. |
| `--wait` | Wait until the volume is fully deleted. |
| `--help` | Show this message and exit. |

---

## extend

Extend a volume to a larger size.

```bash
orca volume extend [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--size INTEGER` | New size in GB (must be larger).  [required] |
| `--help` | Show this message and exit. |

---

## group-create

Create a volume group.

```bash
orca volume group-create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--group-type TEXT` | Group type ID.  [required] |
| `--volume-type TEXT` | Volume type ID (repeatable).  [required] |
| `--description TEXT` | Description. |
| `--availability-zone TEXT` | Availability zone. |
| `--help` | Show this message and exit. |

---

## group-delete

Delete a volume group.

```bash
orca volume group-delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--delete-volumes` | Also delete all volumes in the group. |
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## group-list

List volume groups.

```bash
orca volume group-list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## group-show

Show a volume group.

```bash
orca volume group-show [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## group-snapshot-create

[OPTIONS] GROUP_ID

```bash
orca volume group-snapshot-create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--name TEXT` | Snapshot name. |
| `--description TEXT` | Snapshot description. |
| `--help` | Show this message and exit. |

---

## group-snapshot-delete

[OPTIONS] GROUP_SNAPSHOT_ID

```bash
orca volume group-snapshot-delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## group-snapshot-list

List volume group snapshots.

```bash
orca volume group-snapshot-list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## group-snapshot-show

GROUP_SNAPSHOT_ID

```bash
orca volume group-snapshot-show [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## group-type-create

Create a volume group type.

```bash
orca volume group-type-create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--description TEXT` | Group type description. |
| `--public / --private` | Public or private group type. |
| `--help` | Show this message and exit. |

---

## group-type-delete

GROUP_TYPE_ID

```bash
orca volume group-type-delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## group-type-list

List volume group types.

```bash
orca volume group-type-list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## group-type-set

Update a volume group type.

```bash
orca volume group-type-set [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--name TEXT` | New name. |
| `--description TEXT` | New description. |
| `--public / --private` | Change visibility. |
| `--property KEY=VALUE` | Group spec key=value (repeatable). |
| `--help` | Show this message and exit. |

---

## group-type-show

Show a volume group type.

```bash
orca volume group-type-show [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## group-type-unset

Unset group spec properties on a group type.

```bash
orca volume group-type-unset [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--property KEY` | Group spec key to remove (repeatable). |
| `--help` | Show this message and exit. |

---

## group-update

Update a volume group — rename or add/remove volumes.

```bash
orca volume group-update [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--name TEXT` | New name. |
| `--description TEXT` | New description. |
| `--add-volume TEXT` | Volume ID to add to the group (repeatable). |
| `--remove-volume TEXT` | Volume ID to remove from the group (repeatable). |
| `--help` | Show this message and exit. |

---

## list

List volumes.

```bash
orca volume list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## message-delete

Delete a Cinder error message.

```bash
orca volume message-delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## message-list

List Cinder error messages.

```bash
orca volume message-list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--resource-id TEXT` | Filter by resource UUID. |
| `--resource-type [volume|snapshot|backup|group]` | |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## message-show

Show a Cinder error message.

```bash
orca volume message-show [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## migrate

Migrate a volume to a different Cinder host/backend.

```bash
orca volume migrate [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--host TEXT` | Destination host (e.g. cinder@lvm#LVM).  [required] |
| `--force-host-copy` | Bypass the driver, force host-level copy. |
| `--lock-volume` | Lock the volume during migration. |
| `--help` | Show this message and exit. |

---

## qos-associate

Associate a QoS spec with a volume type.

```bash
orca volume qos-associate [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## qos-create

Create a volume QoS spec.

```bash
orca volume qos-create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--consumer [front-end|back-end|both]` | |
| `--property KEY=VALUE` | QoS spec key=value (repeatable). |
| `--help` | Show this message and exit. |

---

## qos-delete

Delete a volume QoS spec.

```bash
orca volume qos-delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--force` | Delete even if associated with a volume type. |
| `--help` | Show this message and exit. |

---

## qos-disassociate

TYPE_ID

```bash
orca volume qos-disassociate [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--all` | Disassociate from all volume types. |

---

## qos-list

List volume QoS specs.

```bash
orca volume qos-list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## qos-set

Add or update keys on a volume QoS spec.

```bash
orca volume qos-set [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--property KEY=VALUE` | QoS spec key=value to add or update (repeatable). |
| `--help` | Show this message and exit. |

---

## qos-show

Show volume QoS spec details.

```bash
orca volume qos-show [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## retype

Change volume type.

```bash
orca volume retype [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--type TEXT` | New volume type.  [required] |
| `--migration-policy [never|on-demand]` | |
| `--help` | Show this message and exit. |

---

## revert-to-snapshot

SNAPSHOT_ID

```bash
orca volume revert-to-snapshot [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## service-list

List Cinder services.

```bash
orca volume service-list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--host TEXT` | Filter by host. |
| `--binary TEXT` | Filter by binary (e.g. cinder-volume). |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## service-set

Enable or disable a Cinder service.

```bash
orca volume service-set [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--enable` | Enable the service. |
| `--disable` | Disable the service. |
| `--disabled-reason TEXT` | Reason for disabling. |
| `--help` | Show this message and exit. |

---

## set

Set volume properties or metadata.

```bash
orca volume set [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--property KEY=VALUE` | Metadata key=value pair (repeatable). |
| `--name TEXT` | New name. |
| `--description TEXT` | New description. |
| `--help` | Show this message and exit. |

---

## set-bootable

Set or unset bootable flag on a volume.

```bash
orca volume set-bootable [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--bootable / --no-bootable` | Mark volume as bootable or non-bootable. |
| `--help` | Show this message and exit. |

---

## set-readonly

Set or unset read-only flag on a volume.

```bash
orca volume set-readonly [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--readonly / --no-readonly` | Mark volume as read-only or read-write. |
| `--help` | Show this message and exit. |

---

## show

Show volume details.

```bash
orca volume show [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## snapshot-create

VOLUME_ID_OR_NAME

```bash
orca volume snapshot-create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--name TEXT` | Snapshot name.  [required] |
| `--description TEXT` | Snapshot description. |
| `--force` | Force snapshot of in-use volume. |
| `--help` | Show this message and exit. |

---

## snapshot-delete

Delete a volume snapshot.

```bash
orca volume snapshot-delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## snapshot-list

List volume snapshots.

```bash
orca volume snapshot-list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## snapshot-set

Update a snapshot's name, description, or metadata.

```bash
orca volume snapshot-set [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--name TEXT` | New name. |
| `--description TEXT` | New description. |
| `--property KEY=VALUE` | Metadata key=value (repeatable). |
| `--help` | Show this message and exit. |

---

## snapshot-show

Show snapshot details.

```bash
orca volume snapshot-show [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## summary

Show aggregated volume count and total size for the project.

```bash
orca volume summary [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## transfer-accept

AUTH_KEY

```bash
orca volume transfer-accept [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## transfer-create

Create a volume transfer request.

```bash
orca volume transfer-create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--name TEXT` | Transfer name. |
| `--help` | Show this message and exit. |

---

## transfer-delete

Delete a volume transfer request.

```bash
orca volume transfer-delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## transfer-list

List volume transfer requests.

```bash
orca volume transfer-list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--all-projects` | List transfers from all projects (admin). |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## transfer-show

Show a volume transfer request.

```bash
orca volume transfer-show [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## tree

Display a volume / snapshot dependency tree.

```bash
orca volume tree [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--volume-id TEXT` | Show only this volume and its snapshots. |
| `--help` | Show this message and exit. |

---

## type-access-add

PROJECT_ID

```bash
orca volume type-access-add [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## type-access-list

List projects that have access to a private volume type.

```bash
orca volume type-access-list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## type-access-remove

PROJECT_ID

```bash
orca volume type-access-remove [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## type-create

Create a volume type.

```bash
orca volume type-create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--description TEXT` | Description. |
| `--public / --private` | Make type public or private.  [default: public] |
| `--property KEY=VALUE` | Extra spec (repeatable). |
| `--help` | Show this message and exit. |

---

## type-delete

Delete a volume type.

```bash
orca volume type-delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## type-list

List volume types.

```bash
orca volume type-list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--default` | Show the default type only. |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## type-set

Update a volume type.

```bash
orca volume type-set [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--name TEXT` | New name. |
| `--description TEXT` | New description. |
| `--property KEY=VALUE` | Extra spec to add or update (repeatable). |
| `--help` | Show this message and exit. |

---

## type-show

Show volume type details.

```bash
orca volume type-show [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## unset

Unset volume metadata keys.

```bash
orca volume unset [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--property KEY` | Metadata key to remove (repeatable). |
| `--help` | Show this message and exit. |

---

## update

Update volume name or description.

```bash
orca volume update [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--name TEXT` | New name. |
| `--description TEXT` | New description. |
| `--help` | Show this message and exit. |

---
