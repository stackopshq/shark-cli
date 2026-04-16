# `orca endpoint` — endpoint

Manage Keystone service endpoints.

---

## create

Create an endpoint.

```bash
orca endpoint create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--service TEXT` | Service ID.  [required] |
| `--interface [public|internal|admin]` | |
| `--url TEXT` | Endpoint URL.  [required] |
| `--region TEXT` | Region ID. |
| `--enable / --disable` | Enable or disable the endpoint. |
| `--help` | Show this message and exit. |

---

## delete

Delete an endpoint.

```bash
orca endpoint delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## list

List endpoints.

```bash
orca endpoint list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--service TEXT` | Filter by service ID or name. |
| `--interface [public|internal|admin]` | |
| `--region TEXT` | Filter by region ID. |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## set

Update an endpoint.

```bash
orca endpoint set [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--url TEXT` | New URL. |
| `--interface [public|internal|admin]` | |
| `--region TEXT` | New region ID. |
| `--enable / --disable` | Enable or disable. |
| `--help` | Show this message and exit. |

---

## show

Show endpoint details.

```bash
orca endpoint show [OPTIONS]
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
