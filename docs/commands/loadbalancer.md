# Load Balancers — `shark loadbalancer`

Manage load balancers, listeners, pools, members & health monitors (Octavia). Load balancers distribute incoming traffic across multiple backend servers to improve availability and scalability.

The Octavia resource hierarchy is: **Load Balancer → Listener → Pool → Members**, with an optional **Health Monitor** per pool.

!!! note
    Octavia requires the load balancer to be in `ACTIVE` provisioning status before most mutations. Wait for the status to settle between operations.

---

## Load Balancers

### list

List all load balancers with their VIP address, provisioning/operating status, and provider.

```bash
shark loadbalancer list
```

### show

Display detailed properties of a load balancer: VIP address, subnet, port, listeners, pools, status.

```bash
shark loadbalancer show <lb-id>
```

### create

Create a new load balancer. A VIP (virtual IP) is allocated on the specified subnet and serves as the entry point for traffic.

```bash
shark loadbalancer create my-lb --subnet-id <subnet-id>
shark loadbalancer create my-lb --subnet-id <id> --provider amphora
shark loadbalancer create my-lb --subnet-id <id> --description "Production LB"
```

| Option | Required | Default | Description |
|---|---|---|---|
| `--subnet-id` | yes | — | VIP subnet ID |
| `--description` | no | `""` | Description |
| `--provider` | no | — | Provider (e.g. `amphora`, `ovn`) |

### delete

Delete a load balancer. Use `--cascade` to delete all child resources (listeners, pools, members, health monitors) in one operation.

```bash
shark loadbalancer delete <lb-id>
shark loadbalancer delete <lb-id> --cascade -y
```

| Option | Description |
|---|---|
| `--cascade` | Delete LB and all child resources |
| `-y` | Skip confirmation |

---

## Listeners

A listener defines a frontend protocol and port on the load balancer.

### listener-list

List all listeners with their protocol, port, load balancer, and status.

```bash
shark loadbalancer listener-list
```

### listener-show

Display listener details: protocol, port, default pool, connection limit, status.

```bash
shark loadbalancer listener-show <listener-id>
```

### listener-create

Create a listener on a load balancer. Each listener listens on a specific protocol and port.

```bash
shark loadbalancer listener-create http-listener \
  --lb-id <lb-id> --protocol HTTP --port 80

shark loadbalancer listener-create https-listener \
  --lb-id <lb-id> --protocol HTTPS --port 443
```

| Option | Required | Description |
|---|---|---|
| `--lb-id` | yes | Load balancer ID |
| `--protocol` | yes | `HTTP`, `HTTPS`, `TCP`, `UDP`, `TERMINATED_HTTPS` |
| `--port` | yes | Listen port number |
| `--default-pool-id` | no | Default pool ID |

### listener-delete

Delete a listener.

```bash
shark loadbalancer listener-delete <listener-id> -y
```

---

## Pools

A pool is a group of backend members that receive traffic from a listener.

### pool-list

List all pools with their protocol, algorithm, member count, and status.

```bash
shark loadbalancer pool-list
```

### pool-show

Display pool details: protocol, algorithm, session persistence, health monitor, status.

```bash
shark loadbalancer pool-show <pool-id>
```

### pool-create

Create a pool and attach it to a listener (or directly to a load balancer).

```bash
shark loadbalancer pool-create web-pool \
  --listener-id <listener-id> \
  --protocol HTTP \
  --algorithm ROUND_ROBIN

shark loadbalancer pool-create tcp-pool \
  --lb-id <lb-id> \
  --protocol TCP \
  --algorithm LEAST_CONNECTIONS
```

| Option | Required | Description |
|---|---|---|
| `--listener-id` | * | Listener ID to attach to |
| `--lb-id` | * | Load balancer ID (if no listener) |
| `--protocol` | yes | `HTTP`, `HTTPS`, `PROXY`, `TCP`, `UDP` |
| `--algorithm` | yes | `ROUND_ROBIN`, `LEAST_CONNECTIONS`, `SOURCE_IP` |

\* Provide either `--listener-id` or `--lb-id`.

### pool-delete

Delete a pool.

```bash
shark loadbalancer pool-delete <pool-id> -y
```

---

## Members

Members are the backend servers that receive traffic from a pool.

### member-list

List all members in a pool with their address, port, weight, and operating status.

```bash
shark loadbalancer member-list <pool-id>
```

### member-add

Add a backend server to a pool. Each member is identified by an IP address and port.

```bash
shark loadbalancer member-add <pool-id> \
  --address 10.0.0.10 --port 8080 --name web-1

shark loadbalancer member-add <pool-id> \
  --address 10.0.0.11 --port 8080 \
  --subnet-id <subnet-id> --weight 2
```

| Option | Required | Default | Description |
|---|---|---|---|
| `--address` | yes | — | Member IP address |
| `--port` | yes | — | Member port |
| `--subnet-id` | no | — | Member subnet ID |
| `--weight` | no | `1` | Weight (0-256) for weighted algorithms |
| `--name` | no | — | Member name |

### member-remove

Remove a member from a pool.

```bash
shark loadbalancer member-remove <pool-id> <member-id>
shark loadbalancer member-remove <pool-id> <member-id> -y
```

---

## Health Monitors

Health monitors periodically check backend members and remove unhealthy ones from rotation.

### healthmonitor-list

List all health monitors with their type, delay, timeout, pool, and status.

```bash
shark loadbalancer healthmonitor-list
```

### healthmonitor-create

Create a health monitor for a pool. The monitor probes each member and marks it as healthy or unhealthy.

```bash
# HTTP health check
shark loadbalancer healthmonitor-create http-check \
  --pool-id <pool-id> --type HTTP \
  --delay 10 --timeout 5 --max-retries 3 \
  --url-path /health --expected-codes 200

# TCP health check
shark loadbalancer healthmonitor-create tcp-check \
  --pool-id <pool-id> --type TCP \
  --delay 5 --timeout 3
```

| Option | Required | Default | Description |
|---|---|---|---|
| `--pool-id` | yes | — | Pool ID |
| `--type` | yes | — | `HTTP`, `HTTPS`, `PING`, `TCP`, `TLS-HELLO`, `UDP-CONNECT` |
| `--delay` | yes | — | Probe interval (seconds) |
| `--timeout` | yes | — | Probe timeout (seconds) |
| `--max-retries` | no | `3` | Max retries before marking unhealthy |
| `--url-path` | no | `/` | HTTP URL path to probe (HTTP/HTTPS only) |
| `--expected-codes` | no | `200` | Expected HTTP status codes (HTTP/HTTPS only) |

### healthmonitor-delete

Delete a health monitor.

```bash
shark loadbalancer healthmonitor-delete <hm-id> -y
```

---

## Full Example: HTTP Load Balancer

```bash
# 1. Create the load balancer
shark loadbalancer create my-lb --subnet-id <subnet-id>

# 2. Wait for ACTIVE status
shark loadbalancer show <lb-id>

# 3. Create a listener on port 80
shark loadbalancer listener-create http-listener \
  --lb-id <lb-id> --protocol HTTP --port 80

# 4. Create a pool with round-robin
shark loadbalancer pool-create web-pool \
  --listener-id <listener-id> \
  --protocol HTTP --algorithm ROUND_ROBIN

# 5. Add backend servers
shark loadbalancer member-add <pool-id> \
  --address 10.0.0.10 --port 8080 --name web-1
shark loadbalancer member-add <pool-id> \
  --address 10.0.0.11 --port 8080 --name web-2

# 6. Add a health check
shark loadbalancer healthmonitor-create http-check \
  --pool-id <pool-id> --type HTTP \
  --delay 10 --timeout 5 --url-path /health

# 7. Clean up everything at once
shark loadbalancer delete <lb-id> --cascade -y
```
