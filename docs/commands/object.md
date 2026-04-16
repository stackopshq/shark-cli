# `orca object` — object (Swift)

Manage object storage containers & objects (Swift).

---

## account-set

Set account-level metadata.

```bash
orca object account-set [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--property TEXT` | Metadata key=value pair (repeatable).  [required] |
| `--help` | Show this message and exit. |

---

## account-unset

Remove account-level metadata.

```bash
orca object account-unset [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--property TEXT` | Metadata key to remove (repeatable).  [required] |
| `--help` | Show this message and exit. |

---

## container-create

Create a container.

```bash
orca object container-create [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## container-delete

Delete a container.

```bash
orca object container-delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--recursive` | Delete all objects before deleting the container. |
| `-y, --yes` | Skip confirmation prompt. |
| `--help` | Show this message and exit. |

---

## container-list

List containers.

```bash
orca object container-list [OPTIONS]
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

## container-save

Download all objects in a container to a local directory.

```bash
orca object container-save [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--output-dir TEXT` | Local directory to save objects into.  [default: .] |
| `--help` | Show this message and exit. |

---

## container-set

Set metadata on a container.

```bash
orca object container-set [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--property TEXT` | Metadata key=value pair (repeatable).  [required] |
| `--help` | Show this message and exit. |

---

## container-show

Show container metadata.

```bash
orca object container-show [OPTIONS]
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

## delete

Delete one or more objects from a container.

```bash
orca object delete [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## download

Download an object from a container.

```bash
orca object download [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--file TEXT` | Local filename to save to (defaults to object name). |
| `--help` | Show this message and exit. |

---

## list

List objects in a container.

```bash
orca object list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--prefix TEXT` | Only list objects with this prefix. |
| `--delimiter TEXT` | Delimiter for pseudo-folder grouping. |
| `--long` | Show hash and content type. |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## set

Set metadata on an object.

```bash
orca object set [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--property TEXT` | Metadata key=value pair (repeatable).  [required] |
| `--help` | Show this message and exit. |

---

## show

Show object metadata.

```bash
orca object show [OPTIONS]
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

## stats

Show account-level storage statistics.

```bash
orca object stats [OPTIONS]
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

Show containers and objects as a tree.

```bash
orca object tree [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--delimiter TEXT` | Delimiter for pseudo-folder hierarchy.  [default: /] |
| `--help` | Show this message and exit. |

---

## unset

Remove metadata from an object.

```bash
orca object unset [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--property TEXT` | Metadata key to remove (repeatable).  [required] |
| `--help` | Show this message and exit. |

---

## upload

Upload file(s) to a container.

```bash
orca object upload [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--name TEXT` | Override the object name (only valid for single file |
| `--segment-size INTEGER` | Segment size in MB for large files (default: 4096 |
| `--help` | Show this message and exit. |

---
