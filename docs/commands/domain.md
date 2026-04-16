# `orca domain` — domain

Manage domains (Keystone v3).

---

## create

Create a domain.

```bash
orca domain create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--description TEXT` | |
| `--enable / --disable` | |
| `--help` | Show this message and exit. |

---

## delete

Delete a domain.

```bash
orca domain delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | |
| `--help` | Show this message and exit. |

---

## list

List domains.

```bash
orca domain list [OPTIONS]
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

## set

Update a domain.

```bash
orca domain set [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--name TEXT` | |
| `--description TEXT` | |
| `--enable / --disable` | |
| `--help` | Show this message and exit. |

---

## show

Show domain details.

```bash
orca domain show [OPTIONS]
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
