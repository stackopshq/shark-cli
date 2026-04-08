# Floating IPs — `shark floating-ip`

Manage floating IPs (Neutron).

## Commands

| Command | Description |
|---|---|
| `list` | List floating IPs |
| `show <id>` | Show floating IP details |
| `create` | Allocate a floating IP from an external network |
| `delete <id>` | Release a floating IP |
| `associate <id>` | Associate with a port |
| `disassociate <id>` | Disassociate from its port |

## Examples

### Allocate and associate

```bash
# Allocate from external network
shark floating-ip create --network <ext-network-id>

# Associate with a server port
shark floating-ip associate <fip-id> --port-id <port-id>
```

### Disassociate and release

```bash
shark floating-ip disassociate <fip-id>
shark floating-ip delete <fip-id> -y
```
