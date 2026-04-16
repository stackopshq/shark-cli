# `orca secret` — secret (Barbican)

Manage secrets & containers (Barbican key-manager).

---

## acl-delete

Delete the ACL on a secret (revert to project-wide access).

```bash
orca secret acl-delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## acl-get

Get the ACL for a secret.

```bash
orca secret acl-get [OPTIONS]
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

## acl-set

Set the ACL on a secret.

```bash
orca secret acl-set [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--user TEXT` | User ID to grant read access to |
| `--project-access / --no-project-access` | |
| `--help` | Show this message and exit. |

---

## container-create

Create a secret container.

```bash
orca secret container-create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--name TEXT` | Container name. |
| `--type [generic|rsa|certificate]` | |
| `--secret NAME=SECRET_REF` | Secret reference (repeatable): name=<secret- |
| `--help` | Show this message and exit. |

---

## container-delete

Delete a secret container.

```bash
orca secret container-delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## container-list

List secret containers.

```bash
orca secret container-list [OPTIONS]
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

## container-show

Show secret container details.

```bash
orca secret container-show [OPTIONS]
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

## create

Create a secret.

```bash
orca secret create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--payload TEXT` | Secret payload (inline). |
| `--payload-content-type TEXT` | MIME type of payload.  [default: text/plain] |
| `--secret-type [symmetric|public|private|passphrase|certificate|opaque]` | |
| `--algorithm TEXT` | Algorithm (e.g. AES, RSA). |
| `--bit-length INTEGER` | Bit length. |
| `--expiration TEXT` | Expiration datetime (ISO 8601). |
| `--help` | Show this message and exit. |

---

## delete

Delete a secret.

```bash
orca secret delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## get-payload

Retrieve secret payload.

```bash
orca secret get-payload [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## list

List secrets.

```bash
orca secret list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--limit INTEGER` | Max results. |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## order-create

Create a secret order (async key/certificate generation).

```bash
orca secret order-create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--type [key|asymmetric|certificate]` | |
| `--name TEXT` | Secret name for the resulting secret. |
| `--algorithm TEXT` | Key algorithm (e.g. aes, rsa). |
| `--bit-length INTEGER` | Key bit length. |
| `--mode TEXT` | Encryption mode (e.g. cbc). |
| `--help` | Show this message and exit. |

---

## order-delete

Delete a secret order.

```bash
orca secret order-delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## order-list

List secret orders.

```bash
orca secret order-list [OPTIONS]
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

## order-show

Show an order's details.

```bash
orca secret order-show [OPTIONS]
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

## show

Show secret metadata.

```bash
orca secret show [OPTIONS]
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
