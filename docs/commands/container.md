# `orca container` — container (Swift)

Manage object storage containers (Swift).

---

## create

Create a container.

```bash
orca container create [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## delete

Delete a container.

```bash
orca container delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--recursive` | Delete all objects before deleting the container. |
| `--help` | Show this message and exit. |

---

## list

List containers.

```bash
orca container list [OPTIONS]
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

## save

Download all objects in a container to a local directory.

```bash
orca container save [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--output-dir TEXT` | Local directory to save objects into.  [default: .] |
| `--help` | Show this message and exit. |

---

## set

Set metadata on a container.

```bash
orca container set [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--property TEXT` | Metadata key=value pair (repeatable).  [required] |
| `--help` | Show this message and exit. |

---

## show

Show container metadata.

```bash
orca container show [OPTIONS]
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
orca container stats [OPTIONS]
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

Remove metadata from a container.

```bash
orca container unset [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--property TEXT` | Metadata key to remove (repeatable).  [required] |
| `--help` | Show this message and exit. |

---
