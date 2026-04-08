# Security Groups — `shark security-group`

Manage security groups & rules (Neutron).

## Commands

| Command | Description |
|---|---|
| `list` | List security groups |
| `show <id>` | Show details and rules |
| `create <name>` | Create a security group |
| `update <id>` | Update name or description |
| `delete <id>` | Delete a security group |
| `rule-add <sg-id>` | Add a rule |
| `rule-delete <rule-id>` | Delete a rule |

## Examples

### Create a security group with rules

```bash
shark security-group create web-sg --description "Web servers"

# Allow HTTP
shark security-group rule-add <sg-id> \
  --protocol tcp --port-min 80 --port-max 80 \
  --remote-ip 0.0.0.0/0

# Allow HTTPS
shark security-group rule-add <sg-id> \
  --protocol tcp --port-min 443 --port-max 443 \
  --remote-ip 0.0.0.0/0

# Allow SSH
shark security-group rule-add <sg-id> \
  --protocol tcp --port-min 22 --port-max 22 \
  --remote-ip 10.0.0.0/8
```
