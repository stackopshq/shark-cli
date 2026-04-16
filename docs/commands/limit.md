# `orca limit` — limit

Manage Keystone project-level resource limits.

---

## create

Create a project-level limit.

```bash
orca limit create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--project-id TEXT` | Project ID.  [required] |
| `--service-id TEXT` | Service ID.  [required] |
| `--resource-name TEXT` | Resource name.  [required] |
| `--resource-limit INTEGER` | Limit value.  [required] |
| `--region-id TEXT` | Region ID. |
| `--description TEXT` | Description. |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## delete

Delete a project-level limit.

```bash
orca limit delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | |
| `--help` | Show this message and exit. |

---

## list

List limits.

```bash
orca limit list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--service-id TEXT` | Filter by service ID. |
| `--region-id TEXT` | Filter by region ID. |
| `--resource-name TEXT` | Filter by resource name. |
| `--project-id TEXT` | Filter by project ID. |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## set

Update a project-level limit.

```bash
orca limit set [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--resource-limit INTEGER` | New limit value. |
| `--description TEXT` | |
| `--help` | Show this message and exit. |

---

## show

Show a limit.

```bash
orca limit show [OPTIONS]
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
