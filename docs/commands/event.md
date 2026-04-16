# `orca event` — event

Browse instance actions and events (Nova).

---

## all

List recent instance actions across ALL servers.

```bash
orca event all [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--limit INTEGER` | Max number of events to display.  [default: |
| `--action TEXT` | Filter by action type (e.g. create, delete). |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## list

List instance actions for a server.

```bash
orca event list [OPTIONS]
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

Show details for a single instance action, including sub-events.

```bash
orca event show [OPTIONS]
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

## timeline

Show a chronological timeline of all actions for a server.

```bash
orca event timeline [OPTIONS]
```

| Option | Description |
|--------|-------------|

---
