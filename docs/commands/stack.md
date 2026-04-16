# `orca stack` — stack (Heat)

Manage Heat stacks (orchestration).

---

## abandon

Abandon a stack (delete without destroying resources).

```bash
orca stack abandon [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--output-file TEXT` | Save abandoned stack data to a JSON file. |
| `--help` | Show this message and exit. |

---

## cancel

Cancel an in-progress stack update.

```bash
orca stack cancel [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## check

Check a stack (verify resource states).

```bash
orca stack check [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## create

Create a stack.

```bash
orca stack create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-t, --template TEXT` | Template file path or URL.  [required] |
| `-e, --environment TEXT` | Environment file path. |
| `--parameter TEXT` | Parameter key=value (repeatable). |
| `--timeout INTEGER` | Timeout in minutes. |
| `--wait` | Wait for stack to reach terminal state. |
| `--help` | Show this message and exit. |

---

## delete

Delete a stack.

```bash
orca stack delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--wait` | Wait for stack deletion to complete. |
| `--help` | Show this message and exit. |

---

## diff

Compare a local template with a deployed stack's template.

```bash
orca stack diff [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-t, --template PATH` | Local template file to compare against.  [required] |
| `--help` | Show this message and exit. |

---

## event-list

List stack events.

```bash
orca stack event-list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--resource TEXT` | Filter by resource name. |
| `--limit INTEGER` | Limit number of events. |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## event-show

RESOURCE_NAME EVENT_ID

```bash
orca stack event-show [OPTIONS]
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

## list

List stacks.

```bash
orca stack list [OPTIONS]
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

## output-list

List stack outputs.

```bash
orca stack output-list [OPTIONS]
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

## output-show

KEY

```bash
orca stack output-show [OPTIONS]
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

## resource-list

List resources in a stack.

```bash
orca stack resource-list [OPTIONS]
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

## resource-show

RESOURCE_NAME

```bash
orca stack resource-show [OPTIONS]
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

## resource-type-list

List available Heat resource types.

```bash
orca stack resource-type-list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--filter TEXT` | Filter resource types by name substring. |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## resource-type-show

RESOURCE_TYPE

```bash
orca stack resource-type-show [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--template-type [cfn|hot]` | Template format for the resource schema. |
| `--help` | Show this message and exit. |

---

## resume

Resume a suspended stack.

```bash
orca stack resume [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## show

Show stack details.

```bash
orca stack show [OPTIONS]
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

## suspend

Suspend a stack.

```bash
orca stack suspend [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## template-show

Show the stack template (YAML output).

```bash
orca stack template-show [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## template-validate

Validate a Heat template.

```bash
orca stack template-validate [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-t, --template TEXT` | Template file path or URL.  [required] |
| `-e, --environment TEXT` | Environment file path. |
| `--parameter TEXT` | Parameter key=value (repeatable). |
| `--help` | Show this message and exit. |

---

## topology

Show stack resource topology as a tree.

```bash
orca stack topology [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## update

Update a stack.

```bash
orca stack update [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-t, --template TEXT` | Template file path or URL.  [required] |
| `-e, --environment TEXT` | Environment file path. |
| `--parameter TEXT` | Parameter key=value (repeatable). |
| `--timeout INTEGER` | Timeout in minutes. |
| `--wait` | Wait for stack to reach terminal state. |
| `--help` | Show this message and exit. |

---
