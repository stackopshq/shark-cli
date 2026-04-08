# Images — `shark image`

Manage Glance images.

## Commands

| Command | Description |
|---|---|
| `list` | List images |
| `show <id>` | Show image details |
| `create <name>` | Create an image (and optionally upload data) |
| `upload <id>` | Upload image data from a local file |
| `download <id>` | Download image data to a local file |
| `update <id>` | Update image properties (JSON-Patch) |
| `delete <id>` | Delete an image |
| `deactivate <id>` | Deactivate an image |
| `reactivate <id>` | Reactivate a deactivated image |
| `tag-add <id> <tag>` | Add a tag to an image |
| `tag-delete <id> <tag>` | Remove a tag from an image |

## Examples

### Upload an image

```bash
shark image create "Ubuntu 24.04" \
  --disk-format qcow2 \
  --container-format bare \
  --file ubuntu-24.04.qcow2
```

### Download an image

```bash
shark image download <id> --output ./my-image.qcow2
```

### Update properties

```bash
shark image update <id> --property os_distro=ubuntu
```
