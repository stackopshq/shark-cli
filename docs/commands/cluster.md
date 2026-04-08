# Clusters — `shark cluster`

Manage Kubernetes clusters & cluster templates (Magnum).

## Clusters

| Command | Description |
|---|---|
| `list` | List clusters |
| `show <id>` | Show cluster details |
| `create <name>` | Create a Kubernetes cluster |
| `delete <id>` | Delete a cluster |
| `resize <id>` | Resize worker node count |
| `kubeconfig <id>` | Show cluster API address and connection info |

## Cluster Templates

| Command | Description |
|---|---|
| `template-list` | List cluster templates |
| `template-show <id>` | Show template details |
| `template-create <name>` | Create a cluster template |
| `template-delete <id>` | Delete a cluster template |

## Examples

### Create a cluster template

```bash
shark cluster template-create k8s-template \
  --image <image-id> \
  --external-network <ext-net-id> \
  --coe kubernetes \
  --keypair my-keypair \
  --flavor <flavor-id> \
  --master-flavor <flavor-id> \
  --docker-volume-size 20 \
  --network-driver flannel \
  --label boot_volume_size=20 \
  --label boot_volume_type=ceph-ssd
```

### Create a cluster

```bash
shark cluster create my-k8s \
  --template <template-id> \
  --node-count 3 \
  --master-count 1 \
  --keypair my-keypair \
  --timeout 60
```

### Monitor cluster creation

```bash
shark cluster show <cluster-id>
```

### Get kubeconfig

```bash
shark cluster kubeconfig <cluster-id>
```

### Resize workers

```bash
shark cluster resize <cluster-id> --node-count 5
```

!!! tip "Labels"
    Use `--label key=value` (repeatable) on `template-create` to set Magnum driver labels. Common labels:

    - `boot_volume_size` — Root volume size in GB (required for boot-from-volume clouds)
    - `boot_volume_type` — Volume type (e.g. `ceph-ssd`)
    - `kube_tag` — Kubernetes version tag
