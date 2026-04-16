# `orca region` — region

Manage Keystone regions.

---

## create

Create a region.

```bash
orca region create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--description TEXT` | Region description. |
| `--parent TEXT` | Parent region ID. |
| `--help` | Show this message and exit. |

---

## delete

Delete a region.

```bash
orca region delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## list

List regions.

```bash
orca region list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--parent TEXT` | Filter by parent region ID. |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## set

Update a region's description.

```bash
orca region set [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--description TEXT` | New description. |
| `--help` | Show this message and exit. |

---

## show

Show region details.

```bash
orca region show [OPTIONS]
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
