# `orca access-rule` — access-rule

Manage application credential access rules (Keystone).

---

## delete

Delete an access rule.

```bash
orca access-rule delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--user-id TEXT` | User ID (defaults to current user). |
| `-y, --yes` | |
| `--help` | Show this message and exit. |

---

## list

List access rules.

```bash
orca access-rule list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--user-id TEXT` | User ID (defaults to current user). |
| `--service TEXT` | Filter by service type (e.g. compute). |
| `--method TEXT` | Filter by HTTP method. |
| `--path TEXT` | Filter by API path. |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## show

Show an access rule.

```bash
orca access-rule show [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--user-id TEXT` | User ID (defaults to current user). |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---
