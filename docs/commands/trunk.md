# `orca trunk` — trunk

Manage Neutron trunks (VLAN trunk ports).

---

## add-subport

Add a sub-port to a trunk.

```bash
orca trunk add-subport [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--port TEXT` | Sub-port port ID.  [required] |
| `--segmentation-type [vlan|inherit]` | |
| `--segmentation-id INTEGER` | VLAN ID (1–4094).  [required] |
| `--help` | Show this message and exit. |

---

## create

Create a trunk.

```bash
orca trunk create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--port TEXT` | Parent port ID (the trunk port).  [required] |
| `--name TEXT` | Trunk name. |
| `--description TEXT` | Description. |
| `--disable` | Create trunk in administratively down state. |
| `--help` | Show this message and exit. |

---

## delete

Delete a trunk.

```bash
orca trunk delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## list

List trunks.

```bash
orca trunk list [OPTIONS]
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

## remove-subport

Remove a sub-port from a trunk.

```bash
orca trunk remove-subport [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--port TEXT` | Sub-port port ID to remove.  [required] |
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## set

Update a trunk.

```bash
orca trunk set [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--name TEXT` | New name. |
| `--description TEXT` | New description. |
| `--enable / --disable` | Enable or disable the trunk. |
| `--help` | Show this message and exit. |

---

## show

Show trunk details.

```bash
orca trunk show [OPTIONS]
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

## subport-list

List sub-ports on a trunk.

```bash
orca trunk subport-list [OPTIONS]
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
