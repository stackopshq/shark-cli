# `orca subnet-pool` — subnet-pool

Manage Neutron subnet pools for automatic IP allocation.

---

## create

Create a subnet pool.

```bash
orca subnet-pool create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--name TEXT` | Pool name.  [required] |
| `--pool-prefix TEXT` | CIDR prefix for the pool (repeatable). |
| `--default-prefix-length INTEGER` | |
| `--min-prefix-length INTEGER` | Minimum prefix length. |
| `--max-prefix-length INTEGER` | Maximum prefix length. |
| `--shared` | Make the pool shared. |
| `--default` | Set as the default pool. |
| `--description TEXT` | Description. |
| `--help` | Show this message and exit. |

---

## delete

Delete a subnet pool.

```bash
orca subnet-pool delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## list

List subnet pools.

```bash
orca subnet-pool list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--shared` | Show only shared pools. |
| `--default` | Show only the default pool. |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## set

Update a subnet pool.

```bash
orca subnet-pool set [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--name TEXT` | New name. |
| `--description TEXT` | New description. |
| `--default-prefix-length INTEGER` | |
| `--pool-prefix TEXT` | Add a prefix to the pool (repeatable). |
| `--default / --no-default` | Set or unset as the default pool. |
| `--help` | Show this message and exit. |

---

## show

Show subnet pool details.

```bash
orca subnet-pool show [OPTIONS]
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
