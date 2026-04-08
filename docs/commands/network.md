# Networks — `shark network`

Manage networks, subnets, ports & routers (Neutron).

## Networks

| Command | Description |
|---|---|
| `list` | List networks |
| `show <id>` | Show network details |
| `create <name>` | Create a network |
| `update <id>` | Update a network |
| `delete <id>` | Delete a network |

## Subnets

| Command | Description |
|---|---|
| `subnet-list` | List subnets |
| `subnet-show <id>` | Show subnet details |
| `subnet-create <name>` | Create a subnet |
| `subnet-delete <id>` | Delete a subnet |

## Ports

| Command | Description |
|---|---|
| `port-list` | List ports |
| `port-show <id>` | Show port details |
| `port-create` | Create a port |
| `port-update <id>` | Update a port |
| `port-delete <id>` | Delete a port |

## Routers

| Command | Description |
|---|---|
| `router-list` | List routers |
| `router-show <id>` | Show router details |
| `router-create <name>` | Create a router |
| `router-update <id>` | Update a router |
| `router-delete <id>` | Delete a router |
| `router-add-interface <id>` | Add a subnet interface |
| `router-remove-interface <id>` | Remove a subnet interface |

## Examples

### Create a network with subnet

```bash
shark network create my-network
shark network subnet-create my-subnet \
  --network-id <network-id> \
  --cidr 10.0.0.0/24 \
  --gateway 10.0.0.1
```

### Create a router and attach subnet

```bash
shark network router-create my-router \
  --external-gateway <ext-network-id>
shark network router-add-interface <router-id> \
  --subnet-id <subnet-id>
```
