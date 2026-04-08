# Volumes — `shark volume`

Manage block storage volumes & snapshots (Cinder).

## Volumes

| Command | Description |
|---|---|
| `list` | List volumes |
| `show <id>` | Show volume details |
| `create <name>` | Create a volume |
| `update <id>` | Update name or description |
| `delete <id>` | Delete a volume |
| `extend <id>` | Extend to a larger size |
| `retype <id>` | Change volume type |
| `set-bootable <id>` | Set or unset bootable flag |
| `set-readonly <id>` | Set or unset read-only flag |

## Snapshots

| Command | Description |
|---|---|
| `snapshot-list` | List volume snapshots |
| `snapshot-show <id>` | Show snapshot details |
| `snapshot-create` | Create a snapshot |
| `snapshot-delete <id>` | Delete a snapshot |

## Examples

### Create and attach a volume

```bash
shark volume create data-vol --size 50 --type ceph-ssd
# Attach via server command:
shark server attach-volume <server-id> --volume-id <volume-id>
```

### Create a snapshot

```bash
shark volume snapshot-create --volume-id <id> --name my-snapshot
```

### Extend a volume

```bash
shark volume extend <id> --new-size 100
```
