# `orca credential` — credential

Manage Keystone credentials.

---

## create

Create a credential.

```bash
orca credential create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--user TEXT` | User ID who owns this credential.  [required] |
| `--type TEXT` | Credential type (ec2, totp, cert, etc.).  [required] |
| `--blob TEXT` | Credential data (JSON string or raw value).  [required] |
| `--project TEXT` | Project ID (required for EC2 credentials). |
| `--help` | Show this message and exit. |

---

## delete

Delete a credential.

```bash
orca credential delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## list

List credentials.

```bash
orca credential list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--user TEXT` | Filter by user ID. |
| `--type TEXT` | Filter by type (ec2, totp, cert…). |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## set

Update a credential.

```bash
orca credential set [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--blob TEXT` | New credential data. |
| `--project TEXT` | New project ID. |
| `--help` | Show this message and exit. |

---

## show

Show credential details.

```bash
orca credential show [OPTIONS]
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
