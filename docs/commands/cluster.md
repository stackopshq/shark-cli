# `orca cluster` — cluster (Magnum)

Manage Kubernetes clusters & cluster templates (Magnum).

---

## create

Create a Kubernetes cluster.

```bash
orca cluster create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--template TEXT` | Cluster template UUID or name.  [required] |
| `--node-count INTEGER` | Number of worker nodes.  [default: 1] |
| `--master-count INTEGER` | Number of master nodes.  [default: 1] |
| `--keypair TEXT` | SSH keypair name. |
| `--timeout INTEGER` | Creation timeout (minutes).  [default: 60] |
| `--flavor TEXT` | Node flavor (overrides template). |
| `--master-flavor TEXT` | Master flavor (overrides template). |
| `--help` | Show this message and exit. |

---

## delete

Delete a cluster.

```bash
orca cluster delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## kubeconfig

Show the cluster API address and connection info.

```bash
orca cluster kubeconfig [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## list

List clusters.

```bash
orca cluster list [OPTIONS]
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

## nodegroup-create

Create a node group in a cluster.

```bash
orca cluster nodegroup-create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--name TEXT` | Node group name.  [required] |
| `--flavor-id TEXT` | Flavor ID for nodes.  [required] |
| `--node-count INTEGER` | Initial number of nodes.  [default: 1] |
| `--min-node-count INTEGER` | Minimum node count (for autoscaling). |
| `--max-node-count INTEGER` | Maximum node count (for autoscaling). |
| `--role TEXT` | Node group role (worker/infra).  [default: worker] |
| `--image-id TEXT` | Override image ID. |
| `--help` | Show this message and exit. |

---

## nodegroup-delete

NODEGROUP_ID

```bash
orca cluster nodegroup-delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## nodegroup-list

List node groups in a cluster.

```bash
orca cluster nodegroup-list [OPTIONS]
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

## nodegroup-show

NODEGROUP_ID

```bash
orca cluster nodegroup-show [OPTIONS]
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

## nodegroup-update

NODEGROUP_ID

```bash
orca cluster nodegroup-update [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--node-count INTEGER` | New node count. |
| `--min-node-count INTEGER` | New minimum node count. |
| `--max-node-count INTEGER` | New maximum node count. |
| `--help` | Show this message and exit. |

---

## resize

Resize a cluster (change worker node count).

```bash
orca cluster resize [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--node-count INTEGER` | New number of worker nodes.  [required] |
| `--help` | Show this message and exit. |

---

## show

Show cluster details.

```bash
orca cluster show [OPTIONS]
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

## template-create

Create a cluster template.

```bash
orca cluster template-create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--image TEXT` | Base image UUID or name.  [required] |
| `--external-network TEXT` | External network ID.  [required] |
| `--coe [kubernetes|swarm|mesos]` | [default: kubernetes] |
| `--keypair TEXT` | SSH keypair name. |
| `--flavor TEXT` | Node flavor. |
| `--master-flavor TEXT` | Master flavor. |
| `--network-driver TEXT` | Network driver (flannel, calico, etc.). |
| `--docker-volume-size INTEGER` | Docker volume size in GB. |
| `--dns TEXT` | DNS nameserver.  [default: 8.8.8.8] |
| `--master-lb / --no-master-lb` | [default: master-lb] |
| `--floating-ip / --no-floating-ip` | |
| `--label TEXT` | Key=value label (repeatable). E.g. --label |
| `--help` | Show this message and exit. |

---

## template-delete

Delete a cluster template.

```bash
orca cluster template-delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## template-list

List cluster templates.

```bash
orca cluster template-list [OPTIONS]
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

## template-show

Show cluster template details.

```bash
orca cluster template-show [OPTIONS]
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

## upgrade

Upgrade a cluster to a new template version.

```bash
orca cluster upgrade [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--template-id TEXT` | New cluster template ID to upgrade to.  [required] |
| `--max-batch-size INTEGER` | Max number of nodes to upgrade simultaneously. |
| `--nodegroup TEXT` | Specific nodegroup to upgrade. |
| `--help` | Show this message and exit. |

---
