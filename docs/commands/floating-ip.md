# Floating IPs — `shark floating-ip`

Manage floating IPs (Neutron). Floating IPs are public IPv4 addresses that can be dynamically associated with servers to make them reachable from the internet. They are allocated from an external network and can be moved between servers at any time.

---

## list

List all floating IPs in the project with their public address, associated fixed IP, port, and status.

```bash
shark floating-ip list
```

---

## show

Display detailed properties of a floating IP: addresses, network, port, router, status, and timestamps.

```bash
shark floating-ip show <floating-ip-id>
```

---

## create

Allocate a new floating IP from an external network. The IP is reserved but not yet associated with any server.

```bash
shark floating-ip create --network <ext-network-id>
```

| Option | Required | Description |
|---|---|---|
| `--network` | yes | External network ID to allocate from |

!!! tip
    Find your external network with `shark network list` — look for networks with `External = True`.

---

## associate

Associate a floating IP with a port (typically the port of a server). This makes the server reachable from the internet on that public IP.

```bash
shark floating-ip associate <floating-ip-id> --port-id <port-id>
shark floating-ip associate <floating-ip-id> --port-id <port-id> --fixed-ip 10.0.0.5
```

| Option | Required | Description |
|---|---|---|
| `--port-id` | yes | Port ID to associate with |
| `--fixed-ip` | no | Fixed IP on the port (if the port has multiple IPs) |

!!! tip
    Find a server's port ID with `shark server list-interfaces <server-id>`.

---

## disassociate

Disassociate a floating IP from its port. The IP remains allocated and can be re-associated later.

```bash
shark floating-ip disassociate <floating-ip-id>
```

---

## delete

Release a floating IP back to the external network pool. The IP is no longer reserved. Asks for confirmation.

```bash
shark floating-ip delete <floating-ip-id>
shark floating-ip delete <floating-ip-id> -y
```

---

## Full Example: Make a Server Public

```bash
# 1. Allocate a floating IP
shark floating-ip create --network <ext-network-id>
# → Floating IP 203.0.113.42 allocated (fip-id)

# 2. Find the server's port
shark server list-interfaces <server-id>

# 3. Associate
shark floating-ip associate <fip-id> --port-id <port-id>

# 4. SSH to server
ssh -i ~/.ssh/shark-my-key ubuntu@203.0.113.42

# 5. Later: disassociate and release
shark floating-ip disassociate <fip-id>
shark floating-ip delete <fip-id> -y
```
