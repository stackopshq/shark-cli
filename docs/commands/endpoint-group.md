# `orca endpoint-group` — endpoint-group

Manage Keystone endpoint groups.

---

## add-project

ENDPOINT_GROUP_ID
PROJECT_ID

```bash
orca endpoint-group add-project [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## create

Create an endpoint group.

```bash
orca endpoint-group create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--name TEXT` | Endpoint group name.  [required] |
| `--filter KEY=VALUE` | Filter criterion (e.g. service_id=xxx). |
| `--description TEXT` | Description. |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## delete

ENDPOINT_GROUP_ID

```bash
orca endpoint-group delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | |
| `--help` | Show this message and exit. |

---

## list

List endpoint groups.

```bash
orca endpoint-group list [OPTIONS]
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

## remove-project

[OPTIONS] ENDPOINT_GROUP_ID PROJECT_ID

```bash
orca endpoint-group remove-project [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | |
| `--help` | Show this message and exit. |

---

## set

Update an endpoint group.

```bash
orca endpoint-group set [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--name TEXT` | |
| `--description TEXT` | |
| `--filter KEY=VALUE` | |
| `--help` | Show this message and exit. |

---

## show

Show an endpoint group.

```bash
orca endpoint-group show [OPTIONS]
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
