# `orca role` — role

Manage roles and assignments (Keystone v3).

---

## add

Grant a role to a user or group on a project or domain.

```bash
orca role add [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--user TEXT` | User ID. |
| `--group TEXT` | Group ID. |
| `--project TEXT` | Project ID. |
| `--domain TEXT` | Domain ID. |
| `--help` | Show this message and exit. |

---

## assignment-list

List role assignments.

```bash
orca role assignment-list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--user TEXT` | |
| `--group TEXT` | |
| `--project TEXT` | |
| `--domain TEXT` | |
| `--role TEXT` | |
| `--effective` | Include inherited/effective assignments. |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## create

Create a role.

```bash
orca role create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--description TEXT` | |
| `--domain TEXT` | |
| `--help` | Show this message and exit. |

---

## delete

Delete a role.

```bash
orca role delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | |
| `--help` | Show this message and exit. |

---

## implied-create

IMPLIED_ROLE_ID

```bash
orca role implied-create [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## implied-delete

IMPLIED_ROLE_ID

```bash
orca role implied-delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | |
| `--help` | Show this message and exit. |

---

## implied-list

List all implied role relationships.

```bash
orca role implied-list [OPTIONS]
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

## list

List roles.

```bash
orca role list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--domain TEXT` | Filter by domain ID. |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## remove

Revoke a role from a user or group.

```bash
orca role remove [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--user TEXT` | User ID. |
| `--group TEXT` | Group ID. |
| `--project TEXT` | Project ID. |
| `--domain TEXT` | Domain ID. |
| `--help` | Show this message and exit. |

---

## set

Set role properties (rename or update description).

```bash
orca role set [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--name TEXT` | New role name. |
| `--description TEXT` | New description. |
| `--help` | Show this message and exit. |

---

## show

Show role details.

```bash
orca role show [OPTIONS]
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
