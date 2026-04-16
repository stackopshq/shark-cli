# `orca group` — group

Manage groups (Keystone v3).

---

## add-user

Add a user to a group.

```bash
orca group add-user [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## create

Create a group.

```bash
orca group create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--description TEXT` | |
| `--domain TEXT` | |
| `--help` | Show this message and exit. |

---

## delete

Delete a group.

```bash
orca group delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | |
| `--help` | Show this message and exit. |

---

## list

List groups.

```bash
orca group list [OPTIONS]
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

## member-list

List users in a group.

```bash
orca group member-list [OPTIONS]
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

## remove-user

Remove a user from a group.

```bash
orca group remove-user [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## set

Update a group.

```bash
orca group set [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--name TEXT` | |
| `--description TEXT` | |
| `--help` | Show this message and exit. |

---

## show

Show group details.

```bash
orca group show [OPTIONS]
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
