# Clusters — `shark cluster`

Manage Kubernetes clusters and cluster templates (Magnum). Magnum provisions production-ready Kubernetes clusters on top of the Sharktech Cloud infrastructure, including master/worker nodes, networking, and load balancing.

---

## Clusters

### list

List all Kubernetes clusters with their status, node/master count, and template.

```bash
shark cluster list
```

### show

Display detailed cluster properties: UUID, status, status reason, COE version, API address, node/master addresses, keypair, stack ID, and timestamps.

```bash
shark cluster show <cluster-id>
```

### create

Create a new Kubernetes cluster from a cluster template. The cluster creation is asynchronous — use `show` to track progress.

```bash
shark cluster create my-k8s --template <template-id>

shark cluster create my-k8s \
  --template <template-id> \
  --node-count 3 \
  --master-count 1 \
  --keypair my-keypair

shark cluster create prod \
  --template <id> \
  --master-count 3 \
  --node-count 5 \
  --flavor <flavor-id> \
  --master-flavor <master-flavor-id>
```

| Option | Required | Default | Description |
|---|---|---|---|
| `--template` | yes | — | Cluster template UUID or name |
| `--node-count` | no | `1` | Number of worker nodes |
| `--master-count` | no | `1` | Number of master nodes |
| `--keypair` | no | — | SSH keypair name |
| `--timeout` | no | `60` | Creation timeout in minutes |
| `--flavor` | no | — | Node flavor (overrides template) |
| `--master-flavor` | no | — | Master flavor (overrides template) |

### delete

Delete a cluster and all its resources (VMs, networks, volumes). The deletion is asynchronous.

```bash
shark cluster delete <cluster-id>
shark cluster delete <cluster-id> -y
```

### resize

Scale the number of worker nodes up or down. Masters are not affected.

```bash
shark cluster resize <cluster-id> --node-count 5
shark cluster resize <cluster-id> --node-count 1
```

| Option | Required | Description |
|---|---|---|
| `--node-count` | yes | New number of worker nodes |

### kubeconfig

Display the cluster's API address and connection information. Use this to configure `kubectl`.

```bash
shark cluster kubeconfig <cluster-id>
```

!!! tip
    The API address is only available once the cluster reaches `CREATE_COMPLETE` status.

---

## Cluster Templates

Templates define the blueprint for clusters: base image, flavors, networking, COE, and driver options.

### template-list

List all cluster templates with their COE, image, network driver, and public flag.

```bash
shark cluster template-list
```

### template-show

Display detailed template properties: image, flavors, network config, DNS, labels, TLS settings.

```bash
shark cluster template-show <template-id>
```

### template-create

Create a cluster template. This defines the infrastructure blueprint that clusters will use.

```bash
# Basic template
shark cluster template-create k8s-template \
  --image <image-id> \
  --external-network <ext-net-id>

# Full-featured template
shark cluster template-create k8s-prod \
  --image <image-id> \
  --external-network <ext-net-id> \
  --coe kubernetes \
  --keypair my-keypair \
  --flavor <flavor-id> \
  --master-flavor <master-flavor-id> \
  --network-driver flannel \
  --docker-volume-size 50 \
  --dns 8.8.8.8 \
  --master-lb \
  --label boot_volume_size=20 \
  --label boot_volume_type=ceph-ssd
```

| Option | Required | Default | Description |
|---|---|---|---|
| `--image` | yes | — | Base image UUID or name |
| `--external-network` | yes | — | External network ID |
| `--coe` | no | `kubernetes` | `kubernetes`, `swarm`, `mesos` |
| `--keypair` | no | — | SSH keypair name |
| `--flavor` | no | — | Node flavor |
| `--master-flavor` | no | — | Master flavor |
| `--network-driver` | no | — | Network driver (`flannel`, `calico`, etc.) |
| `--docker-volume-size` | no | — | Docker volume size in GB |
| `--dns` | no | `8.8.8.8` | DNS nameserver |
| `--master-lb/--no-master-lb` | no | `True` | Enable master load balancing |
| `--floating-ip/--no-floating-ip` | no | `True` | Assign floating IPs |
| `--label` | no | — | Key=value label (repeatable) |

!!! tip "Labels"
    Use `--label key=value` (repeatable) to set Magnum driver labels. Common labels:

    - `boot_volume_size` — Root volume size in GB (required for boot-from-volume clouds)
    - `boot_volume_type` — Volume type (e.g. `ceph-ssd`)
    - `kube_tag` — Kubernetes version tag

### template-delete

Delete a cluster template. It must not be in use by any cluster.

```bash
shark cluster template-delete <template-id>
shark cluster template-delete <template-id> -y
```

---

## Full Example: Deploy a Kubernetes Cluster

```bash
# 1. Create a template
shark cluster template-create k8s-template \
  --image <image-id> \
  --external-network <ext-net-id> \
  --keypair my-key \
  --flavor <flavor-id> \
  --label boot_volume_size=20

# 2. Create a cluster
shark cluster create my-k8s \
  --template k8s-template \
  --node-count 3 \
  --master-count 1

# 3. Monitor progress
shark cluster show my-k8s

# 4. Get connection info
shark cluster kubeconfig my-k8s

# 5. Scale up workers
shark cluster resize my-k8s --node-count 5

# 6. Tear down
shark cluster delete my-k8s -y
```
