# `orca placement` — placement

Manage Placement resources (resource providers, classes, traits, etc.).

---

## allocation-candidate-list

[OPTIONS]

```bash
orca placement allocation-candidate-list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--resource CLASS=AMOUNT` | Requested resource, e.g. VCPU=4. Repeatable. |
| `--required TRAIT` | Required trait. Repeatable. |
| `--forbidden TRAIT` | Forbidden trait. Repeatable. |
| `--limit INTEGER` | Max number of candidates. |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## allocation-delete

[OPTIONS] CONSUMER_UUID

```bash
orca placement allocation-delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## allocation-set

CONSUMER_UUID

```bash
orca placement allocation-set [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--resource-provider TEXT` | Resource provider UUID.  [required] |
| `--resource CLASS=AMOUNT` | Resource class and amount, e.g. VCPU=4. |
| `--project-id TEXT` | Consumer project UUID.  [required] |
| `--user-id TEXT` | Consumer user UUID.  [required] |
| `--help` | Show this message and exit. |

---

## allocation-show

CONSUMER_UUID

```bash
orca placement allocation-show [OPTIONS]
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

## resource-class-create

[OPTIONS] NAME

```bash
orca placement resource-class-create [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## resource-class-delete

[OPTIONS] NAME

```bash
orca placement resource-class-delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## resource-class-list

[OPTIONS]

```bash
orca placement resource-class-list [OPTIONS]
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

## resource-class-show

[OPTIONS] NAME

```bash
orca placement resource-class-show [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## resource-provider-create

[OPTIONS] NAME

```bash
orca placement resource-provider-create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--uuid TEXT` | Explicit UUID for the new provider. |
| `--parent-uuid TEXT` | UUID of the parent provider. |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## resource-provider-delete

[OPTIONS] UUID

```bash
orca placement resource-provider-delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## resource-provider-list

[OPTIONS]

```bash
orca placement resource-provider-list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--name TEXT` | Filter by name. |
| `--uuid TEXT` | Filter by UUID. |
| `--in-tree UUID` | Limit to providers in this tree. |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## resource-provider-set

[OPTIONS] UUID

```bash
orca placement resource-provider-set [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--name TEXT` | New name. |
| `--parent-uuid TEXT` | New parent provider UUID. |
| `--help` | Show this message and exit. |

---

## resource-provider-show

[OPTIONS] UUID

```bash
orca placement resource-provider-show [OPTIONS]
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

## resource-provider-trait-delete

[OPTIONS] UUID

```bash
orca placement resource-provider-trait-delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## resource-provider-trait-list

[OPTIONS] UUID

```bash
orca placement resource-provider-trait-list [OPTIONS]
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

## resource-provider-trait-set

[OPTIONS] UUID TRAITS...

```bash
orca placement resource-provider-trait-set [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## resource-provider-usage

[OPTIONS] UUID

```bash
orca placement resource-provider-usage [OPTIONS]
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

## trait-create

Create a custom trait (must start with CUSTOM_).

```bash
orca placement trait-create [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## trait-delete

Delete a custom trait.

```bash
orca placement trait-delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## trait-list

List traits.

```bash
orca placement trait-list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--name TEXT` | Filter traits by name prefix. |
| `--associated` | Only traits associated with a resource |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## usage-list

Show aggregated usages by project/user.

```bash
orca placement usage-list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--project-id TEXT` | Filter by project UUID. |
| `--user-id TEXT` | Filter by user UUID. |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---
