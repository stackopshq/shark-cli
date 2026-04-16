# `orca service` — service

Manage Keystone services (service catalog).

---

## create

Create a Keystone service.

```bash
orca service create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--name TEXT` | Service name.  [required] |
| `--type TEXT` | Service type (e.g. identity, compute).  [required] |
| `--description TEXT` | Service description. |
| `--enable / --disable` | Enable or disable the service. |
| `--help` | Show this message and exit. |

---

## delete

Delete a Keystone service.

```bash
orca service delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## list

List Keystone services.

```bash
orca service list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--type TEXT` | Filter by service type. |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## set

Update a Keystone service.

```bash
orca service set [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--name TEXT` | New name. |
| `--type TEXT` | New type. |
| `--description TEXT` | New description. |
| `--enable / --disable` | Enable or disable. |
| `--help` | Show this message and exit. |

---

## show

Show service details.

```bash
orca service show [OPTIONS]
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
