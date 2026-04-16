# `orca trust` — trust

Manage Keystone trusts (token delegation).

---

## create

Create a trust (delegation from trustor to trustee).

```bash
orca trust create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--trustor TEXT` | Trustor user ID (delegating identity). |
| `--trustee TEXT` | Trustee user ID (receiving delegation). |
| `--project TEXT` | Project ID for the trust scope. |
| `--role TEXT` | Role name to delegate (repeatable). |
| `--impersonate / --no-impersonate` | |
| `--expires-at TEXT` | Expiry datetime in ISO 8601 (e.g. |
| `--uses INTEGER` | Maximum number of times the trust can be |
| `--help` | Show this message and exit. |

---

## delete

Delete a trust.

```bash
orca trust delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## list

List trusts.

```bash
orca trust list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--trustor TEXT` | Filter by trustor user ID. |
| `--trustee TEXT` | Filter by trustee user ID. |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## show

Show trust details.

```bash
orca trust show [OPTIONS]
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
