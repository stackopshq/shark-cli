# `orca qos` — qos

Manage Neutron QoS policies and rules.

---

## policy-create

Create a QoS policy.

```bash
orca qos policy-create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--name TEXT` | Policy name.  [required] |
| `--shared` | Share with all projects. |
| `--default` | Set as default policy. |
| `--description TEXT` | Description. |
| `--help` | Show this message and exit. |

---

## policy-delete

Delete a QoS policy.

```bash
orca qos policy-delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## policy-list

List QoS policies.

```bash
orca qos policy-list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--shared` | Show only shared policies. |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## policy-set

Update a QoS policy.

```bash
orca qos policy-set [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--name TEXT` | New name. |
| `--description TEXT` | New description. |
| `--shared / --no-shared` | Share or un-share. |
| `--default / --no-default` | Set or unset as default. |
| `--help` | Show this message and exit. |

---

## policy-show

Show a QoS policy.

```bash
orca qos policy-show [OPTIONS]
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

## rule-create

Create a QoS rule.

```bash
orca qos rule-create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--type [bandwidth-limit|dscp-marking|minimum-bandwidth|minimum-packet-rate]` | |
| `--max-kbps INTEGER` | Maximum bandwidth in kbps (bandwidth-limit). |
| `--max-burst-kbps INTEGER` | Maximum burst bandwidth in kbps (bandwidth- |
| `--direction [ingress|egress]` | Traffic direction (bandwidth-limit, minimum- |
| `--dscp-mark INTEGER` | DSCP mark value 0-56 (dscp-marking). |
| `--min-kbps INTEGER` | Minimum bandwidth in kbps (minimum- |
| `--help` | Show this message and exit. |

---

## rule-delete

Delete a QoS rule.

```bash
orca qos rule-delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--type [bandwidth-limit|dscp-marking|minimum-bandwidth|minimum-packet-rate]` | |
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## rule-list

List QoS rules for a policy.

```bash
orca qos rule-list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--type [bandwidth-limit|dscp-marking|minimum-bandwidth|minimum-packet-rate]` | |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---
