# `orca recordset` — recordset (DNS)

Manage DNS recordsets (Designate).

---

## create

Create a recordset in a zone.

```bash
orca recordset create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--type TEXT` | Record type (A, AAAA, CNAME, MX, TXT, …).  [required] |
| `--record TEXT` | Record value (repeatable for multiple values). |
| `--ttl INTEGER` | TTL in seconds. |
| `--description TEXT` | Recordset description. |
| `--help` | Show this message and exit. |

---

## delete

Delete a recordset.

```bash
orca recordset delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## list

List recordsets in a zone.

```bash
orca recordset list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--type TEXT` | Filter by record type (A, AAAA, CNAME, MX, |
| `--name TEXT` | Filter by record name. |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## set

Update a recordset in a zone.

```bash
orca recordset set [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--record TEXT` | Record value (repeatable — replaces all existing |
| `--ttl INTEGER` | TTL in seconds. |
| `--description TEXT` | Recordset description. |
| `--help` | Show this message and exit. |

---

## show

Show recordset details.

```bash
orca recordset show [OPTIONS]
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
