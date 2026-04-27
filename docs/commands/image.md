# `orca image` — image

Manage images.

---

## cache-clear

Clear the entire image cache (admin).

```bash
orca image cache-clear [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## cache-delete

Remove a specific image from the cache (admin).

```bash
orca image cache-delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## cache-list

List cached and queued images (admin).

```bash
orca image cache-list [OPTIONS]
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

## cache-queue

Queue an image for pre-caching (admin).

```bash
orca image cache-queue [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## create

Create a new image (and optionally upload data).

```bash
orca image create [OPTIONS] NAME
```

| Option | Description |
|--------|-------------|
| `--disk-format [raw|qcow2|vmdk|vdi|vhd|vhdx|iso|aki|ari|ami]` | |
| `--container-format [bare|ovf|ova|aki|ari|ami|docker]` | |
| `--min-disk INTEGER` | Min disk (GB).  [default: 0] |
| `--min-ram INTEGER` | Min RAM (MB).  [default: 0] |
| `--visibility [private|shared|community|public]` | |
| `--file PATH` | Upload image data from file immediately. |
| `--property KEY=VALUE` | Custom image property to set on creation (repeatable). Values may contain `=` — only the first `=` splits. Keys must match `^[A-Za-z0-9_:.\-]{1,255}$`. |
| `--help` | Show this message and exit. |

```bash
orca image create ubuntu-24.04 --file ubuntu.qcow2 \
    --property os_distro=ubuntu \
    --property os_version=24.04 \
    --property hw_qemu_guest_agent=yes
```

---

## deactivate

Deactivate an image (make data unavailable).

```bash
orca image deactivate [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## delete

Delete an image.

```bash
orca image delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## download

Download image data to a local file.

```bash
orca image download [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-o, --output PATH` | Output file path.  [required] |
| `--help` | Show this message and exit. |

---

## import

Import image data using the Glance v2 import API.

```bash
orca image import [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--method [web-download|glance-direct|copy-image]` | |
| `--uri TEXT` | Source URI (required for web-download). |
| `--store TEXT` | Target store(s) for copy-image (repeatable). |
| `--help` | Show this message and exit. |

---

## list

List available images.

```bash
orca image list [OPTIONS]
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

## member-create

PROJECT_ID

```bash
orca image member-create [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## member-delete

PROJECT_ID

```bash
orca image member-delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## member-list

List all projects that have access to a shared image.

```bash
orca image member-list [OPTIONS]
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

## member-set

Accept, reject, or reset a shared image invitation.

```bash
orca image member-set [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--status [accepted|rejected|pending]` | |
| `--help` | Show this message and exit. |

---

## member-show

Show a specific project's membership status for a shared image.

```bash
orca image member-show [OPTIONS]
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

## reactivate

Reactivate a deactivated image.

```bash
orca image reactivate [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## share-and-accept

PROJECT_ID

```bash
orca image share-and-accept [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## show

Show image details, including custom properties and integrity hashes.

```bash
orca image show [OPTIONS] IMAGE_ID
```

Custom properties (anything outside the Glance v2 standard schema, e.g.
`os_distro`, `os_version`, `hw_qemu_guest_agent`, `cinder_img_volume_type`)
are surfaced separately:

- **table** — rendered as a `Properties` sub-table after the main table,
  sorted by key.
- **json** — exposed both at the top level (mirroring the raw Glance
  response shape, so existing scripts using `jq .os_distro` keep working)
  and under a new top-level `"properties"` aggregate so callers can also
  do `orca image show <id> -f json | jq .properties`.
- **value** — printed after the standard fields, one `KEY VALUE` per line.

Integrity fields (`checksum`, `os_hash_algo`, `os_hash_value`, `direct_url`)
and `tags` are always included as standard fields when Glance returns them.

| Option | Description |
|--------|-------------|
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if omitted. |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## shrink

Convert a raw image to qcow2 with compression to save space.

```bash
orca image shrink [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## stage

Upload image data to the staging area (interruptible import).

```bash
orca image stage [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## stores-info

List available Glance storage backends (multi-store only).

```bash
orca image stores-info [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--detail` | Show store properties (admin only, requires |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## tag-add

Add a tag to an image.

```bash
orca image tag-add [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## tag-delete

Remove a tag from an image.

```bash
orca image tag-delete [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## task-list

List Glance async tasks.

```bash
orca image task-list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--type [import|export|clone]` | Filter by task type. |
| `--status [pending|processing|success|failure]` | |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## task-show

Show details of a Glance async task.

```bash
orca image task-show [OPTIONS]
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

## unused

Find images not used by any server instance.

```bash
orca image unused [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-d, --delete` | Actually delete unused images. |
| `-y, --yes` | Skip confirmation (with --delete). |
| `--include-snapshots` | Include snapshot images in the scan. |
| `--help` | Show this message and exit. |

---

## update

Update image properties (JSON-Patch).

```bash
orca image update [OPTIONS] IMAGE_ID
```

All flags compose into a single atomic JSON-Patch document.
`--property` emits `add` when the key is absent on the image and `replace` when
it already exists, so untouched properties survive. `--remove-property` is
strict by default (errors if the key is absent) and turns idempotent under
`--ignore-missing`.

| Option | Description |
|--------|-------------|
| `--name TEXT` | New name. |
| `--min-disk INTEGER` | New min disk (GB). |
| `--min-ram INTEGER` | New min RAM (MB). |
| `--visibility [private|shared|community|public]` | |
| `--property KEY=VALUE` | Set or replace a custom image property. Repeatable. |
| `--remove-property KEY` | Remove a custom image property by key. Repeatable. |
| `--ignore-missing` | With `--remove-property`: silently skip keys that are not present on the image. |
| `--help` | Show this message and exit. |

```bash
orca image update <id> --property os_distro=ubuntu --property os_version=24.04
orca image update <id> --remove-property hw_qemu_guest_agent
orca image update <id> --remove-property foo --ignore-missing
```

---

## upload

Upload image data from a local file.

```bash
orca image upload [OPTIONS]
```

| Option | Description |
|--------|-------------|

---
