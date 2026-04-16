# `orca network` — network

Manage networks, subnets, ports & routers.

---

## agent-delete

Delete a Neutron agent record.

```bash
orca network agent-delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## agent-list

List Neutron agents.

```bash
orca network agent-list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--host TEXT` | Filter by host. |
| `--agent-type TEXT` | Filter by agent type. |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## agent-set

Update a Neutron agent.

```bash
orca network agent-set [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--enable / --disable` | Enable or disable the agent. |
| `--description TEXT` | New description. |
| `--help` | Show this message and exit. |

---

## agent-show

Show a Neutron agent's details.

```bash
orca network agent-show [OPTIONS]
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

## auto-allocated-topology-delete

[OPTIONS]

```bash
orca network auto-allocated-topology-delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--project-id TEXT` | Project ID (default: current project). |
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## auto-allocated-topology-show

[OPTIONS]

```bash
orca network auto-allocated-topology-show [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--project-id TEXT` | Project ID (default: current project). |
| `--check-resources` | Validate resources without creating |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## create

Create a network.

```bash
orca network create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--admin-state / --no-admin-state` | |
| `--shared` | Shared across projects. |
| `--help` | Show this message and exit. |

---

## delete

Delete a network.

```bash
orca network delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## list

List networks.

```bash
orca network list [OPTIONS]
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

## port-create

Create a port.

```bash
orca network port-create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--network-id TEXT` | Network ID.  [required] |
| `--name TEXT` | Port name. |
| `--fixed-ip TEXT` | Fixed IP address. |
| `--help` | Show this message and exit. |

---

## port-delete

Delete a port.

```bash
orca network port-delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## port-list

List ports.

```bash
orca network port-list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--network-id TEXT` | Filter by network ID. |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## port-show

Show port details.

```bash
orca network port-show [OPTIONS]
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

## port-unset

Remove properties from a port.

```bash
orca network port-unset [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--security-group TEXT` | Security group ID to remove (repeatable). |
| `--qos-policy` | Remove the QoS policy from the port. |
| `--description` | Clear the port description. |
| `--help` | Show this message and exit. |

---

## port-update

Update a port.

```bash
orca network port-update [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--name TEXT` | New name. |
| `--admin-state / --no-admin-state` | |
| `--help` | Show this message and exit. |

---

## rbac-create

Create an RBAC policy to share a network resource.

```bash
orca network rbac-create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--object-type [network|qos_policy|security_group|address_group|address_scope|subnetpool]` | |
| `--object TEXT` | ID of the object to share.  [required] |
| `--action [access_as_shared|access_as_external]` | |
| `--target-project TEXT` | Project ID to grant access to (use '*' for |
| `--help` | Show this message and exit. |

---

## rbac-delete

Delete an RBAC policy.

```bash
orca network rbac-delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## rbac-list

List RBAC policies.

```bash
orca network rbac-list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--object-type [network|qos_policy|security_group|address_group|address_scope|subnetpool]` | |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## rbac-show

Show an RBAC policy.

```bash
orca network rbac-show [OPTIONS]
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

## rbac-update

Update the target project of an RBAC policy.

```bash
orca network rbac-update [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--target-project TEXT` | New target project ID (use '*' for all projects). |
| `--help` | Show this message and exit. |

---

## router-add-interface

[OPTIONS] ROUTER_ID

```bash
orca network router-add-interface [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--subnet-id TEXT` | Subnet to attach.  [required] |
| `--help` | Show this message and exit. |

---

## router-add-route

Add a static route to a router (requires extraroute-atomic extension).

```bash
orca network router-add-route [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--destination CIDR` | Destination network (e.g. 10.1.0.0/24).  [required] |
| `--nexthop IP` | Next-hop IP address.  [required] |
| `--help` | Show this message and exit. |

---

## router-create

Create a router.

```bash
orca network router-create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--external-network TEXT` | External network ID for gateway. |
| `--help` | Show this message and exit. |

---

## router-delete

Delete a router.

```bash
orca network router-delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## router-list

List routers.

```bash
orca network router-list [OPTIONS]
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

## router-remove-interface

[OPTIONS] ROUTER_ID

```bash
orca network router-remove-interface [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--subnet-id TEXT` | Subnet to detach.  [required] |
| `--help` | Show this message and exit. |

---

## router-remove-route

[OPTIONS] ROUTER_ID

```bash
orca network router-remove-route [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--destination CIDR` | Destination network to remove.  [required] |
| `--nexthop IP` | Next-hop IP address.  [required] |
| `--help` | Show this message and exit. |

---

## router-set-gateway

Set (or replace) the external gateway on a router.

```bash
orca network router-set-gateway [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--external-network TEXT` | External network ID to use as gateway. |
| `--enable-snat / --disable-snat` | Enable or disable SNAT on the gateway. |
| `--help` | Show this message and exit. |

---

## router-show

Show router details.

```bash
orca network router-show [OPTIONS]
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

## router-unset-gateway

[OPTIONS] ROUTER_ID

```bash
orca network router-unset-gateway [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## router-update

Update a router.

```bash
orca network router-update [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--name TEXT` | New name. |
| `--external-network TEXT` | New external gateway network ID. |
| `--help` | Show this message and exit. |

---

## segment-create

Create a network segment.

```bash
orca network segment-create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--network-id TEXT` | Network ID this segment belongs to. |
| `--network-type [flat|geneve|gre|local|vlan|vxlan]` | |
| `--physical-network TEXT` | Physical network name. |
| `--segment INTEGER` | Segmentation ID (VLAN ID or tunnel ID). |
| `--description TEXT` | Segment description. |
| `--help` | Show this message and exit. |

---

## segment-delete

Delete a network segment.

```bash
orca network segment-delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## segment-list

List network segments.

```bash
orca network segment-list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--network-id TEXT` | Filter by network ID. |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## segment-set

Update a network segment.

```bash
orca network segment-set [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--name TEXT` | New name. |
| `--description TEXT` | New description. |
| `--help` | Show this message and exit. |

---

## segment-show

Show a network segment.

```bash
orca network segment-show [OPTIONS]
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

## show

Show network details.

```bash
orca network show [OPTIONS]
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

## subnet-create

Create a subnet.

```bash
orca network subnet-create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--network-id TEXT` | Parent network ID.  [required] |
| `--cidr TEXT` | CIDR (e.g. 10.0.0.0/24).  [required] |
| `--ip-version [4|6]` | [default: 4] |
| `--gateway TEXT` | Gateway IP. Auto if omitted. |
| `--dhcp / --no-dhcp` | Enable DHCP.  [default: dhcp] |
| `--dns TEXT` | DNS nameserver (repeatable). |
| `--help` | Show this message and exit. |

---

## subnet-delete

Delete a subnet.

```bash
orca network subnet-delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## subnet-list

List subnets.

```bash
orca network subnet-list [OPTIONS]
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

## subnet-show

Show subnet details.

```bash
orca network subnet-show [OPTIONS]
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

## subnet-update

Update a subnet.

```bash
orca network subnet-update [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--name TEXT` | New name. |
| `--description TEXT` | New description. |
| `--dns-nameserver TEXT` | DNS nameserver IP (repeatable, replaces |
| `--enable-dhcp / --disable-dhcp` | Enable or disable DHCP. |
| `--help` | Show this message and exit. |

---

## topology

Display the network topology as a tree.

```bash
orca network topology [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--network-id TEXT` | Show only this network. |
| `--help` | Show this message and exit. |

---

## trace

Trace the full network path for a server instance.

```bash
orca network trace [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## update

Update a network.

```bash
orca network update [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--name TEXT` | New name. |
| `--admin-state / --no-admin-state` | |
| `--help` | Show this message and exit. |

---
