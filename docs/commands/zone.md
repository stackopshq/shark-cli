# `orca zone` — zone (DNS)

Manage DNS zones (Designate).

---

## create

Create a DNS zone.

```bash
orca zone create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--email TEXT` | Zone administrator email.  [required] |
| `--ttl INTEGER` | Default TTL in seconds. |
| `--description TEXT` | Zone description. |
| `--type [primary|secondary]` | Zone type.  [default: PRIMARY] |
| `--masters TEXT` | Master servers (for SECONDARY zones, |
| `--help` | Show this message and exit. |

---

## delete

Delete a DNS zone.

```bash
orca zone delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## export

Export a zone as a BIND-format zone file.

```bash
orca zone export [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--file PATH` | Write zone file to this path (default: stdout). |
| `--help` | Show this message and exit. |

---

## import

Import a zone from a BIND-format zone file.

```bash
orca zone import [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--file PATH` | BIND-format zone file to import.  [required] |
| `--help` | Show this message and exit. |

---

## list

List DNS zones.

```bash
orca zone list [OPTIONS]
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

## reverse-lookup

Find PTR records for an IP address.

```bash
orca zone reverse-lookup [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## set

Update a DNS zone.

```bash
orca zone set [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--email TEXT` | Zone administrator email. |
| `--ttl INTEGER` | Default TTL in seconds. |
| `--description TEXT` | Zone description. |
| `--help` | Show this message and exit. |

---

## show

Show DNS zone details.

```bash
orca zone show [OPTIONS]
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

## tld-create

Create a TLD (admin).

```bash
orca zone tld-create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--description TEXT` | Description. |
| `--help` | Show this message and exit. |

---

## tld-delete

Delete a TLD (admin).

```bash
orca zone tld-delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## tld-list

List allowed TLDs (admin).

```bash
orca zone tld-list [OPTIONS]
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

## transfer-accept

Accept a zone transfer request.

```bash
orca zone transfer-accept [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## transfer-request-create

[OPTIONS] ZONE_ID

```bash
orca zone transfer-request-create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--target-project-id TEXT` | Restrict transfer to a specific project ID. |
| `--description TEXT` | Description. |
| `--help` | Show this message and exit. |

---

## transfer-request-delete

[OPTIONS] TRANSFER_ID

```bash
orca zone transfer-request-delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## transfer-request-list

List zone transfer requests.

```bash
orca zone transfer-request-list [OPTIONS]
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

## transfer-request-show

TRANSFER_ID

```bash
orca zone transfer-request-show [OPTIONS]
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

## tree

Show a zone as a Rich tree grouped by record type.

```bash
orca zone tree [OPTIONS]
```

| Option | Description |
|--------|-------------|

---
