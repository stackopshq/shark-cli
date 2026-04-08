# Volumes — `shark volume`

Manage block storage volumes and snapshots (Cinder v3). Volumes are persistent block devices that can be attached to servers. Snapshots provide point-in-time copies of a volume's data.

---

## Volumes

### list

List all volumes with their size, status, type, and server attachments.

```bash
shark volume list
```

### show

Display detailed properties of a volume: type, bootable flag, encryption, multi-attach, availability zone, and attachment info.

```bash
shark volume show <volume-id>
```

### create

Create a new block storage volume. You can create an empty volume, clone from a snapshot, clone from another volume, or create from an image.

```bash
# Empty volume
shark volume create --name data-vol --size 50

# From snapshot
shark volume create --name restored --size 50 --snapshot-id <snap-id>

# From image (bootable)
shark volume create --name boot-vol --size 20 --image-id <image-id>

# With specific type
shark volume create --name fast-vol --size 100 --type ceph-ssd
```

| Option | Required | Description |
|---|---|---|
| `--name` | yes | Volume name |
| `--size` | yes | Size in GB |
| `--type` | no | Volume type |
| `--description` | no | Description |
| `--snapshot-id` | no | Create from snapshot |
| `--source-vol` | no | Clone from existing volume |
| `--image-id` | no | Create from image |

### update

Update a volume's name or description. The volume can be in any status.

```bash
shark volume update <volume-id> --name new-name
shark volume update <volume-id> --description "Production database"
```

### extend

Extend a volume to a larger size. The new size must be greater than the current size. The volume must be in `available` status (or `in-use` if the backend supports online resize).

```bash
shark volume extend <volume-id> --size 100
```

### retype

Change the volume type (e.g. from HDD to SSD). The data may be migrated depending on the migration policy.

```bash
shark volume retype <volume-id> --type ceph-ssd
shark volume retype <volume-id> --type ceph-ssd --migration-policy on-demand
```

| Option | Default | Description |
|---|---|---|
| `--type` | *required* | New volume type |
| `--migration-policy` | `never` | `never` or `on-demand` |

### set-bootable

Set or unset the bootable flag on a volume. A bootable volume can be used to boot a server.

```bash
shark volume set-bootable <volume-id> true
shark volume set-bootable <volume-id> false
```

### set-readonly

Set or unset the read-only flag on a volume to prevent writes.

```bash
shark volume set-readonly <volume-id> true
shark volume set-readonly <volume-id> false
```

### delete

Permanently delete a volume. The volume must be in `available` status (not attached). Asks for confirmation.

```bash
shark volume delete <volume-id>
shark volume delete <volume-id> -y
```

---

## Snapshots

### snapshot-list

List all volume snapshots with their source volume, size, and status.

```bash
shark volume snapshot-list
```

### snapshot-show

Display snapshot details: source volume, size, status, description, timestamps.

```bash
shark volume snapshot-show <snapshot-id>
```

### snapshot-create

Create a point-in-time snapshot of a volume. Use `--force` to snapshot an in-use volume (crash-consistent).

```bash
shark volume snapshot-create <volume-id> --name daily-backup
shark volume snapshot-create <volume-id> --name live-snap --force
shark volume snapshot-create <volume-id> --name snap --description "Before upgrade"
```

| Option | Required | Description |
|---|---|---|
| `--name` | yes | Snapshot name |
| `--description` | no | Description |
| `--force` | no | Force snapshot of in-use volume |

### snapshot-delete

Delete a volume snapshot. Asks for confirmation.

```bash
shark volume snapshot-delete <snapshot-id>
shark volume snapshot-delete <snapshot-id> -y
```

---

## Full Example: Data Volume Lifecycle

```bash
# 1. Create a data volume
shark volume create --name data-vol --size 50

# 2. Attach to a server
shark server attach-volume <server-id> <volume-id>

# 3. Snapshot before maintenance
shark volume snapshot-create <volume-id> --name pre-maintenance

# 4. Extend the volume
shark server detach-volume <server-id> <volume-id>
shark volume extend <volume-id> --size 100
shark server attach-volume <server-id> <volume-id>
```
