# Networks — `shark network`

Manage networks, subnets, ports & routers (Neutron). This is the core networking command group — create isolated networks, assign IP ranges with subnets, manage ports, and connect to the outside world with routers.

---

## Networks

### list

List all networks in the project with their subnets, status, and external/shared flags.

```bash
shark network list
```

### show

Display detailed properties of a network: admin state, MTU, subnets, availability zones.

```bash
shark network show <network-id>
```

### create

Create a new virtual network.

```bash
shark network create my-network
shark network create my-network --no-admin-state   # create in down state
shark network create my-network --shared            # shared across projects
```

| Option | Default | Description |
|---|---|---|
| `--admin-state/--no-admin-state` | `True` | Admin state up |
| `--shared` | `False` | Shared across projects |

### update

Update a network's name or admin state.

```bash
shark network update <network-id> --name new-name
shark network update <network-id> --no-admin-state
```

### delete

Delete a network. All subnets and ports must be removed first.

```bash
shark network delete <network-id> -y
```

---

## Subnets

### subnet-list

List all subnets with their CIDR, gateway, network, and IP version.

```bash
shark network subnet-list
```

### subnet-show

Display subnet details: CIDR, DHCP, DNS servers, allocation pools.

```bash
shark network subnet-show <subnet-id>
```

### subnet-create

Create a subnet on an existing network. Defines the IP range, gateway, and DHCP settings.

```bash
shark network subnet-create my-subnet \
  --network-id <network-id> \
  --cidr 10.0.0.0/24 \
  --gateway 10.0.0.1

# IPv6 with custom DNS
shark network subnet-create v6-subnet \
  --network-id <id> \
  --cidr fd00::/64 \
  --ip-version 6 \
  --dns 2001:4860:4860::8888
```

| Option | Default | Description |
|---|---|---|
| `--network-id` | *required* | Parent network ID |
| `--cidr` | *required* | CIDR (e.g. `10.0.0.0/24`) |
| `--ip-version` | `4` | `4` or `6` |
| `--gateway` | auto | Gateway IP |
| `--dhcp/--no-dhcp` | `True` | Enable DHCP |
| `--dns` | — | DNS nameserver (repeatable) |

### subnet-delete

Delete a subnet. No ports may be using it.

```bash
shark network subnet-delete <subnet-id> -y
```

---

## Ports

### port-list

List all ports. Optionally filter by network.

```bash
shark network port-list
shark network port-list --network-id <network-id>
```

### port-show

Display port details: MAC address, fixed IPs, status, device owner, security groups.

```bash
shark network port-show <port-id>
```

### port-create

Create a port on a network. Optionally assign a fixed IP and name.

```bash
shark network port-create --network-id <network-id>
shark network port-create --network-id <id> --name my-port --fixed-ip 10.0.0.50
```

| Option | Description |
|---|---|
| `--network-id` | Network ID (*required*) |
| `--name` | Port name |
| `--fixed-ip` | Fixed IP address |

### port-update

Update a port's name or admin state.

```bash
shark network port-update <port-id> --name new-name
shark network port-update <port-id> --no-admin-state
```

| Option | Description |
|---|---|
| `--name` | New name |
| `--admin-state/--no-admin-state` | Admin state up/down |

### port-delete

Delete a port.

```bash
shark network port-delete <port-id> -y
```

---

## Routers

### router-list

List all routers with their status and external gateway.

```bash
shark network router-list
```

### router-show

Display router details: external gateway info, static routes, admin state.

```bash
shark network router-show <router-id>
```

### router-create

Create a router. Optionally set an external gateway for internet access.

```bash
shark network router-create my-router
shark network router-create my-router --external-network <ext-network-id>
```

| Option | Description |
|---|---|
| `--external-network` | External network ID for gateway |

### router-update

Update a router's name or external gateway.

```bash
shark network router-update <router-id> --name new-name
shark network router-update <router-id> --external-network <ext-net-id>
```

### router-delete

Delete a router. All interfaces must be removed first.

```bash
shark network router-delete <router-id> -y
```

### router-add-interface

Connect a subnet to a router. This enables routing between the subnet and the router's external gateway.

```bash
shark network router-add-interface <router-id> --subnet-id <subnet-id>
```

### router-remove-interface

Disconnect a subnet from a router.

```bash
shark network router-remove-interface <router-id> --subnet-id <subnet-id>
```

---

## Full Example: Private Network with Internet Access

```bash
# 1. Create network and subnet
shark network create my-network
shark network subnet-create my-subnet \
  --network-id <network-id> \
  --cidr 10.0.0.0/24 \
  --gateway 10.0.0.1

# 2. Create router with external gateway
shark network router-create my-router \
  --external-network <ext-network-id>

# 3. Attach subnet to router
shark network router-add-interface <router-id> \
  --subnet-id <subnet-id>

# 4. Create a server on this network
shark server create my-vm \
  --name my-vm --flavor <id> --image <id> \
  --network <network-id>
```
