# `orca server-group` — server-group

Manage server groups (Nova).

---

## create

Create a server group.

```bash
orca server-group create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--policy [anti-affinity|affinity|soft-anti-affinity|soft-affinity]` | |
| `--help` | Show this message and exit. |

---

## delete

Delete a server group.

```bash
orca server-group delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | |
| `--help` | Show this message and exit. |

---

## list

List server groups.

```bash
orca server-group list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--all` | List server groups for all projects (admin). |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## show

Show server group details.

```bash
orca server-group show [OPTIONS]
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
