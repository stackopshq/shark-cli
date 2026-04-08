# Security Groups — `shark security-group`

Manage security groups and firewall rules (Neutron). Security groups act as virtual firewalls for servers — they control which inbound (ingress) and outbound (egress) traffic is allowed based on protocol, port, and source/destination IP.

---

## list

List all security groups in the project with their description and rule count.

```bash
shark security-group list
```

---

## show

Display a security group's details and all its rules (direction, protocol, ports, remote IP/group).

```bash
shark security-group show <group-id>
```

---

## create

Create a new security group. By default it includes egress-allow-all rules.

```bash
shark security-group create web-sg
shark security-group create web-sg --description "Web servers"
```

| Option | Description |
|---|---|
| `--description` | Description for the security group |

---

## update

Update the name or description of an existing security group.

```bash
shark security-group update <group-id> --name new-name
shark security-group update <group-id> --description "Updated description"
```

---

## delete

Delete a security group. It must not be in use by any port. Asks for confirmation.

```bash
shark security-group delete <group-id>
shark security-group delete <group-id> -y
```

---

## rule-add

Add a firewall rule to a security group. Rules specify the direction, protocol, port range, and allowed source/destination.

```bash
# Allow SSH from anywhere
shark security-group rule-add <sg-id> \
  --direction ingress --protocol tcp --port-min 22

# Allow HTTP/HTTPS from specific CIDR
shark security-group rule-add <sg-id> \
  --direction ingress --protocol tcp \
  --port-min 80 --port-max 443 \
  --remote-ip 0.0.0.0/0

# Allow ICMP (ping)
shark security-group rule-add <sg-id> \
  --direction ingress --protocol icmp

# Allow traffic from another security group
shark security-group rule-add <sg-id> \
  --direction ingress --protocol tcp \
  --port-min 3306 --remote-group <other-sg-id>
```

| Option | Required | Default | Description |
|---|---|---|---|
| `--direction` | yes | — | `ingress` or `egress` |
| `--protocol` | no | any | `tcp`, `udp`, `icmp`, or protocol number |
| `--port-min` | no | any | Minimum port (or single port) |
| `--port-max` | no | = port-min | Maximum port |
| `--remote-ip` | no | — | Remote IP prefix (CIDR) |
| `--remote-group` | no | — | Remote security group ID |
| `--ethertype` | no | `IPv4` | `IPv4` or `IPv6` |

---

## rule-delete

Delete a specific security group rule by its ID. Asks for confirmation.

```bash
shark security-group rule-delete <rule-id>
shark security-group rule-delete <rule-id> -y
```

---

## Full Example: Web Server Security Group

```bash
# Create the group
shark security-group create web-sg --description "Web servers"

# Allow SSH from office
shark security-group rule-add <sg-id> \
  --direction ingress --protocol tcp --port-min 22 \
  --remote-ip 203.0.113.0/24

# Allow HTTP and HTTPS from everywhere
shark security-group rule-add <sg-id> \
  --direction ingress --protocol tcp --port-min 80 \
  --remote-ip 0.0.0.0/0
shark security-group rule-add <sg-id> \
  --direction ingress --protocol tcp --port-min 443 \
  --remote-ip 0.0.0.0/0

# Allow ICMP (ping)
shark security-group rule-add <sg-id> \
  --direction ingress --protocol icmp

# Use when creating a server
shark server create --name web01 ... --security-group web-sg
```
