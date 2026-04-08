# Load Balancers — `shark loadbalancer`

Manage load balancers, listeners, pools, members & health monitors (Octavia).

## Load Balancers

| Command | Description |
|---|---|
| `list` | List load balancers |
| `show <id>` | Show load balancer details |
| `create <name>` | Create a load balancer |
| `delete <id>` | Delete a load balancer (supports `--cascade`) |

## Listeners

| Command | Description |
|---|---|
| `listener-list` | List listeners |
| `listener-show <id>` | Show listener details |
| `listener-create <name>` | Create a listener |
| `listener-delete <id>` | Delete a listener |

## Pools

| Command | Description |
|---|---|
| `pool-list` | List pools |
| `pool-show <id>` | Show pool details |
| `pool-create <name>` | Create a pool |
| `pool-delete <id>` | Delete a pool |

## Members

| Command | Description |
|---|---|
| `member-list <pool-id>` | List members in a pool |
| `member-add <pool-id>` | Add a member to a pool |
| `member-remove <pool-id> <member-id>` | Remove a member |

## Health Monitors

| Command | Description |
|---|---|
| `healthmonitor-list` | List health monitors |
| `healthmonitor-create <name>` | Create a health monitor |
| `healthmonitor-delete <id>` | Delete a health monitor |

## Examples

### Create a complete HTTP load balancer

```bash
# 1. Create the load balancer
shark loadbalancer create my-lb --subnet-id <subnet-id>

# 2. Wait for ACTIVE status
shark loadbalancer show <lb-id>

# 3. Create a listener
shark loadbalancer listener-create http-listener \
  --lb-id <lb-id> --protocol HTTP --port 80

# 4. Create a pool
shark loadbalancer pool-create web-pool \
  --listener-id <listener-id> \
  --protocol HTTP --algorithm ROUND_ROBIN

# 5. Add members
shark loadbalancer member-add <pool-id> \
  --address 10.0.0.10 --port 8080 \
  --subnet-id <subnet-id> --name web-1

shark loadbalancer member-add <pool-id> \
  --address 10.0.0.11 --port 8080 \
  --subnet-id <subnet-id> --name web-2

# 6. Add a health monitor
shark loadbalancer healthmonitor-create http-check \
  --pool-id <pool-id> --type HTTP \
  --delay 10 --timeout 5 --max-retries 3 \
  --url-path /health
```

### Cascade delete

Delete a load balancer and all child resources in one command:

```bash
shark loadbalancer delete <lb-id> --cascade -y
```

!!! note
    Octavia requires the load balancer to be in `ACTIVE` provisioning status before most mutations. Wait for the status to settle between operations.
