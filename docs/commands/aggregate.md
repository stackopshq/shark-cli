# `orca aggregate` — aggregate

Manage host aggregates (Nova).

---

## add-host

Add a host to an aggregate.

```bash
orca aggregate add-host [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## cache-image

IMAGE_IDS...

```bash
orca aggregate cache-image [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## create

Create a host aggregate.

```bash
orca aggregate create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--zone TEXT` | Availability zone name. |
| `--help` | Show this message and exit. |

---

## delete

Delete a host aggregate.

```bash
orca aggregate delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | |
| `--help` | Show this message and exit. |

---

## list

List host aggregates.

```bash
orca aggregate list [OPTIONS]
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

## remove-host

HOST

```bash
orca aggregate remove-host [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## set

Update an aggregate's name, AZ, or metadata.

```bash
orca aggregate set [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--name TEXT` | New name. |
| `--zone TEXT` | New availability zone. |
| `--property KEY=VALUE` | Metadata key=value (repeatable). |
| `--help` | Show this message and exit. |

---

## show

Show aggregate details.

```bash
orca aggregate show [OPTIONS]
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

## unset

Unset metadata properties on an aggregate.

```bash
orca aggregate unset [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--property KEY` | Metadata key to remove (repeatable). |
| `--help` | Show this message and exit. |

---
