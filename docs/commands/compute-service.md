# `orca compute-service` — compute-service

Manage Nova compute services (nova-compute, nova-conductor, …).

---

## delete

Force-delete a compute service record.

```bash
orca compute-service delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## list

List compute services.

```bash
orca compute-service list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--host TEXT` | Filter by hostname. |
| `--binary TEXT` | Filter by binary (e.g. nova-compute). |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## set

Enable, disable, or force-down a compute service.

```bash
orca compute-service set [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--enable / --disable` | Enable or disable the service. |
| `--disabled-reason TEXT` | Reason for disabling (used with --disable). |
| `--force-down / --no-force-down` | Force the service down (for evacuate |
| `--help` | Show this message and exit. |

---
