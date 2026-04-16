# `orca alarm` — alarm (Aodh)

Manage Aodh alarms.

---

## capabilities

Show Aodh API capabilities.

```bash
orca alarm capabilities [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## create

Create an alarm.

```bash
orca alarm create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--name TEXT` | Alarm name.  [required] |
| `--type [gnocchi_resources_threshold|gnocchi_aggregation_by_metrics_threshold|gnocchi_aggregation_by_resources_threshold|event|composite|loadbalancer_member_health|threshold]` | |
| `--rule JSON` | Type-specific rule as a JSON string. |
| `--description TEXT` | Alarm description. |
| `--severity [low|moderate|critical]` | |
| `--enabled / --disabled` | Enable or disable the alarm. |
| `--repeat-actions / --no-repeat-actions` | |
| `--alarm-action URL` | Webhook URL to call when entering alarm |
| `--ok-action URL` | Webhook URL to call when entering ok state. |
| `--insufficient-data-action URL` | Webhook URL to call on insufficient data. |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## delete

Delete an alarm.

```bash
orca alarm delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## history

Show the change history of an alarm.

```bash
orca alarm history [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--limit INTEGER` | Max number of history entries. |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## list

List alarms.

```bash
orca alarm list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--type TEXT` | Filter by alarm type. |
| `--state [ok|alarm|insufficient_data]` | |
| `--enabled / --disabled` | Filter by enabled status. |
| `--name TEXT` | Filter by alarm name. |
| `--limit INTEGER` | Max number of alarms to return. |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## quota-set

Set alarm quota for a project.

```bash
orca alarm quota-set [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--alarms INTEGER` | Maximum number of alarms for the project.  [required] |
| `--help` | Show this message and exit. |

---

## set

Update an alarm.

```bash
orca alarm set [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--name TEXT` | New alarm name. |
| `--description TEXT` | New description. |
| `--severity [low|moderate|critical]` | |
| `--enabled / --disabled` | Enable or disable. |
| `--repeat-actions / --no-repeat-actions` | |
| `--rule JSON` | Updated type-specific rule as JSON. |
| `--alarm-action URL` | |
| `--ok-action URL` | |
| `--insufficient-data-action URL` | |
| `--help` | Show this message and exit. |

---

## show

Show an alarm.

```bash
orca alarm show [OPTIONS]
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

## state-get

Get the current state of an alarm.

```bash
orca alarm state-get [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## state-set

{ok|alarm|insufficient_data}

```bash
orca alarm state-set [OPTIONS]
```

| Option | Description |
|--------|-------------|

---
