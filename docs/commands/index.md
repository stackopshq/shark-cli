# Command Reference

`shark-cli` organises commands by OpenStack service. Every command supports `--help` for inline documentation.

```bash
shark --help              # List all command groups
shark server --help       # List all server sub-commands
shark server create --help  # Detailed help for a specific command
```

## Command Groups

| Group | Commands | Description |
|---|:---:|---|
| [`server`](server.md) | 28 | Compute instances — full lifecycle |
| [`flavor`](flavor.md) | 1 | List available flavors |
| [`image`](image.md) | 11 | Glance image management |
| [`network`](network.md) | 21 | Networks, subnets, ports & routers |
| [`keypair`](keypair.md) | 5 | SSH key pair management |
| [`volume`](volume.md) | 13 | Block storage volumes & snapshots |
| [`security-group`](security-group.md) | 7 | Security groups & rules |
| [`floating-ip`](floating-ip.md) | 6 | Floating IP allocation & association |
| [`loadbalancer`](loadbalancer.md) | 18 | Load balancers, listeners, pools, members & health monitors |
| [`secret`](secret.md) | 8 | Secrets & containers (Barbican) |
| [`cluster`](cluster.md) | 10 | Kubernetes clusters & templates (Magnum) |
| [`metric`](metric.md) | 8 | Metrics, measures & resources (Gnocchi) |
| [`catalog`](catalog.md) | 1 | Service endpoint discovery |

## Common Patterns

### Confirmation prompts

Destructive commands (delete, remove) ask for confirmation. Skip with `-y`:

```bash
shark server delete <id> -y
shark loadbalancer delete <id> --cascade -y
```

### Output format

All commands output rich, coloured tables. Pipe to `less -R` for paging:

```bash
shark server list | less -R
```
