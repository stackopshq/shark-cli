# Images — `shark image`

Manage Glance images. Images are the base OS templates used to create servers. You can list available images, upload custom images, download them, and manage their metadata and tags.

---

## list

List all images in the project, sorted by name. Shows ID, name, status, min disk/RAM, and size.

```bash
shark image list
```

---

## show

Display detailed metadata for an image: format, visibility, OS info, size, and timestamps.

```bash
shark image show <image-id>
```

---

## create

Create a new image record in Glance. Optionally upload image data from a local file in the same step.

```bash
# Create metadata only
shark image create "Ubuntu 24.04"

# Create and upload in one step
shark image create "Ubuntu 24.04" --file ubuntu-24.04.qcow2

# With custom format
shark image create "Flatcar" --disk-format raw --file flatcar.img
```

| Option | Default | Description |
|---|---|---|
| `--disk-format` | `qcow2` | `raw`, `qcow2`, `vmdk`, `vdi`, `vhd`, `vhdx`, `iso`, `aki`, `ari`, `ami` |
| `--container-format` | `bare` | `bare`, `ovf`, `ova`, `aki`, `ari`, `ami`, `docker` |
| `--min-disk` | `0` | Minimum disk size in GB |
| `--min-ram` | `0` | Minimum RAM in MB |
| `--visibility` | `private` | `private`, `shared`, `community`, `public` |
| `--file` | — | Upload image data from this file |

---

## upload

Upload image data to an existing image (must be in `queued` status). Streams from disk without loading into memory — supports large files.

```bash
shark image upload <image-id> /path/to/ubuntu.qcow2
```

---

## download

Download image data to a local file. Streams to disk with a progress bar.

```bash
shark image download <image-id> -o /tmp/my-image.qcow2
```

| Option | Required | Description |
|---|---|---|
| `-o` / `--output` | yes | Output file path |

---

## update

Update image properties using JSON-Patch. Useful for changing name, visibility, or min disk/RAM requirements.

```bash
shark image update <image-id> --name "New Name"
shark image update <image-id> --visibility shared
shark image update <image-id> --min-disk 10 --min-ram 512
```

| Option | Description |
|---|---|
| `--name` | New name |
| `--min-disk` | New minimum disk (GB) |
| `--min-ram` | New minimum RAM (MB) |
| `--visibility` | `private`, `shared`, `community`, `public` |

---

## delete

Permanently delete an image and its data. Asks for confirmation.

```bash
shark image delete <image-id>
shark image delete <image-id> -y
```

---

## deactivate

Deactivate an image — the metadata stays visible but the image data becomes unavailable for download or server creation.

```bash
shark image deactivate <image-id>
```

---

## reactivate

Reactivate a deactivated image, making its data available again.

```bash
shark image reactivate <image-id>
```

---

## tag-add

Add a tag to an image. Tags are arbitrary strings useful for filtering and organisation.

```bash
shark image tag-add <image-id> production
```

---

## tag-delete

Remove a tag from an image.

```bash
shark image tag-delete <image-id> production
```
