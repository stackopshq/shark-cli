# `orca flavor` — flavor

Manage flavors.

---

## access-add

PROJECT_ID

```bash
orca flavor access-add [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## access-list

List projects that have access to a private flavor.

```bash
orca flavor access-list [OPTIONS]
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

## access-remove

PROJECT_ID

```bash
orca flavor access-remove [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## create

Create a flavor.

```bash
orca flavor create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--vcpus INTEGER` | Number of vCPUs.  [required] |
| `--ram INTEGER` | RAM in MB.  [required] |
| `--disk INTEGER` | Root disk size in GB.  [default: 0] |
| `--ephemeral INTEGER` | Ephemeral disk in GB.  [default: 0] |
| `--swap INTEGER` | Swap disk in MB.  [default: 0] |
| `--rxtx-factor FLOAT` | RX/TX factor.  [default: 1.0] |
| `--public / --private` | Make flavor public or private.  [default: public] |
| `--id TEXT` | Flavor ID (auto-generated if 'auto').  [default: auto] |
| `--help` | Show this message and exit. |

---

## delete

Delete a flavor.

```bash
orca flavor delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## list

List available flavors.

```bash
orca flavor list [OPTIONS]
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

## set

Set extra specs on a flavor.

```bash
orca flavor set [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--property KEY=VALUE` | Extra spec key=value (repeatable). |
| `--help` | Show this message and exit. |

---

## show

Show flavor details.

```bash
orca flavor show [OPTIONS]
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

Unset extra specs from a flavor.

```bash
orca flavor unset [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--property KEY` | Extra spec key to remove (repeatable). |
| `--help` | Show this message and exit. |

---
