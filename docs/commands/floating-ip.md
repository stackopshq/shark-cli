# `orca floating-ip` — floating-ip

Manage floating IPs.

---

## associate

Associate a floating IP with a port.

```bash
orca floating-ip associate [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--port-id TEXT` | Port ID to associate with.  [required] |
| `--fixed-ip TEXT` | Fixed IP on the port (if multiple). |
| `--help` | Show this message and exit. |

---

## bulk-release

Bulk-release floating IPs to free up unused addresses.

```bash
orca floating-ip bulk-release [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-s, --status TEXT` | Release floating IPs with this status (DOWN, ERROR, |
| `-u, --unassociated` | Release all unassociated floating IPs (no port_id), |
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## create

Allocate a floating IP from an external network.

```bash
orca floating-ip create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--network TEXT` | External network ID.  [required] |
| `--help` | Show this message and exit. |

---

## delete

Release a floating IP.

```bash
orca floating-ip delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## disassociate

FLOATING_IP_ID

```bash
orca floating-ip disassociate [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## list

List floating IPs.

```bash
orca floating-ip list [OPTIONS]
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

Set floating IP properties.

```bash
orca floating-ip set [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--port TEXT` | Associate with port ID. |
| `--fixed-ip-address TEXT` | Fixed IP on the port (if multiple). |
| `--description TEXT` | Set description. |
| `--qos-policy TEXT` | Attach QoS policy ID. |
| `--no-qos-policy` | Remove attached QoS policy. |
| `--help` | Show this message and exit. |

---

## show

Show floating IP details.

```bash
orca floating-ip show [OPTIONS]
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

Unset floating IP properties.

```bash
orca floating-ip unset [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--port` | Disassociate port. |
| `--qos-policy` | Remove QoS policy. |
| `--help` | Show this message and exit. |

---
