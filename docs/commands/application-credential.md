# `orca application-credential` — application-credential

[ARGS]...

---

## create

[OPTIONS] NAME

```bash
orca application-credential create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--description TEXT` | |
| `--secret TEXT` | Secret (auto-generated if omitted). |
| `--expires TEXT` | Expiry (ISO 8601, e.g. 2026-12-31T00:00:00). |
| `--unrestricted` | Allow creation of other credentials (dangerous). |
| `--user TEXT` | |
| `--help` | Show this message and exit. |

---

## delete

[OPTIONS] CREDENTIAL_ID

```bash
orca application-credential delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--user TEXT` | |
| `-y, --yes` | |
| `--help` | Show this message and exit. |

---

## list

[OPTIONS]

```bash
orca application-credential list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--user TEXT` | User ID (default: current user). |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## show

[OPTIONS] CREDENTIAL_ID

```bash
orca application-credential show [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--user TEXT` | |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---
