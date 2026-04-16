# `orca backup` — backup (Freezer)

Manage backups, jobs, sessions & clients (Freezer).

---

## action-create

Create a standalone backup action.

```bash
orca backup action-create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--action [backup|restore|admin]` | |
| `--path TEXT` | Path to back up or restore.  [required] |
| `--container TEXT` | Swift container name. |
| `--storage [swift|local|ssh|s3]` | [default: swift] |
| `--mode [fs|mysql|mongo|mssql|cinder|nova]` | |
| `--backup-name TEXT` | Name for the backup. |
| `--max-level INTEGER` | Max incremental backup level. |
| `--help` | Show this message and exit. |

---

## action-delete

Delete a backup action.

```bash
orca backup action-delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## action-list

List backup actions.

```bash
orca backup action-list [OPTIONS]
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

## action-show

Show backup action details.

```bash
orca backup action-show [OPTIONS]
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

## client-delete

Unregister a backup client.

```bash
orca backup client-delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## client-list

List registered backup clients (agents).

```bash
orca backup client-list [OPTIONS]
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

## client-register

Register a new backup client.

```bash
orca backup client-register [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--description TEXT` | Client description. |
| `--help` | Show this message and exit. |

---

## client-show

Show backup client details.

```bash
orca backup client-show [OPTIONS]
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

## delete

Delete a backup.

```bash
orca backup delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## job-create

Create a backup job.

```bash
orca backup job-create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--description TEXT` | Job description. |
| `--client-id TEXT` | Freezer client ID.  [required] |
| `--action [backup|restore|admin]` | |
| `--path TEXT` | Path to back up or restore.  [required] |
| `--container TEXT` | Swift container name for storage. |
| `--storage [swift|local|ssh|s3]` | Storage backend.  [default: swift] |
| `--mode [fs|mysql|mongo|mssql|cinder|nova]` | |
| `--schedule-interval TEXT` | Schedule interval (e.g. '24 hours', '7 |
| `--help` | Show this message and exit. |

---

## job-delete

Delete a backup job.

```bash
orca backup job-delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## job-list

List backup jobs.

```bash
orca backup job-list [OPTIONS]
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

## job-show

Show backup job details.

```bash
orca backup job-show [OPTIONS]
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

## job-start

Start (trigger) a backup job.

```bash
orca backup job-start [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## job-stop

Stop a running backup job.

```bash
orca backup job-stop [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## list

List backups.

```bash
orca backup list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--limit INTEGER` | Max results. |
| `--offset INTEGER` | Offset for pagination. |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## session-add-job

JOB_ID

```bash
orca backup session-add-job [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## session-create

Create a backup session.

```bash
orca backup session-create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--description TEXT` | Session description. |
| `--schedule-interval TEXT` | Schedule interval (e.g. '24 hours'). |
| `--help` | Show this message and exit. |

---

## session-delete

Delete a backup session.

```bash
orca backup session-delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## session-list

List backup sessions.

```bash
orca backup session-list [OPTIONS]
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

## session-remove-job

JOB_ID

```bash
orca backup session-remove-job [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## session-show

Show backup session details.

```bash
orca backup session-show [OPTIONS]
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

## session-start

Start a backup session (triggers all its jobs).

```bash
orca backup session-start [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## show

Show backup details.

```bash
orca backup show [OPTIONS]
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
