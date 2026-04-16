# `orca user` — user

Manage users (Keystone v3).

---

## create

Create a user.

```bash
orca user create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--password TEXT` | User password. |
| `--email TEXT` | Email address. |
| `--description TEXT` | Description. |
| `--domain TEXT` | Domain ID. |
| `--project TEXT` | Default project ID. |
| `--enable / --disable` | Enable or disable the user.  [default: enable] |
| `--help` | Show this message and exit. |

---

## delete

Delete a user.

```bash
orca user delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## list

List users.

```bash
orca user list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--domain TEXT` | Filter by domain name or ID. |
| `--project TEXT` | Filter by project ID. |
| `--enabled / --disabled` | Filter by enabled state. |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## set

Update a user.

```bash
orca user set [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--name TEXT` | New name. |
| `--email TEXT` | New email. |
| `--description TEXT` | New description. |
| `--password TEXT` | New password. |
| `--enable / --disable` | Enable or disable. |
| `--help` | Show this message and exit. |

---

## set-password

Set a user's password (admin).

```bash
orca user set-password [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--password TEXT` | New password. |
| `--help` | Show this message and exit. |

---

## show

Show user details.

```bash
orca user show [OPTIONS]
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
