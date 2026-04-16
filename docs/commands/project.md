# `orca project` — project

Manage projects (Keystone v3).

---

## cleanup

Delete ALL resources in a project in dependency order.

```bash
orca project cleanup [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--project TEXT` | Project name or ID to clean up (default: |
| `--dry-run` | List resources that would be deleted without |
| `-y, --yes` | Skip confirmation prompt. |
| `--created-before YYYY-MM-DDTHH:MM:SS` | |
| `--skip [stack|loadbalancer|server|floating-ip|dns-zone|router|network|security-group|backup|volume|snapshot|image|secret|container]` | |
| `--help` | Show this message and exit. |

---

## create

Create a project.

```bash
orca project create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--domain TEXT` | Domain ID. |
| `--description TEXT` | Description. |
| `--enable / --disable` | [default: enable] |
| `--tag TEXT` | Tag (repeatable). |
| `--help` | Show this message and exit. |

---

## delete

Delete a project.

```bash
orca project delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | |
| `--help` | Show this message and exit. |

---

## list

List projects.

```bash
orca project list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--domain TEXT` | Filter by domain ID. |
| `--user TEXT` | Filter by user ID. |
| `--enabled / --disabled` | Filter by enabled state. |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## set

Update a project.

```bash
orca project set [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--name TEXT` | |
| `--description TEXT` | |
| `--enable / --disable` | |
| `--help` | Show this message and exit. |

---

## show

Show project details.

```bash
orca project show [OPTIONS]
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
