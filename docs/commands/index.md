# Command Reference

`orca` organises commands by OpenStack service. Every command supports `--help` for inline documentation.

```bash
orca --help              # List all command groups
orca server --help       # List all server sub-commands
orca server create --help  # Detailed help for a specific command
```

## Command Groups

| Group | Description |
|---|---|
| [`server`](server.md) | Compute instances — full lifecycle |
| [`flavor`](flavor.md) | List available flavors |
| [`image`](image.md) | Glance image management |
| [`network`](network.md) | Networks, subnets, ports & routers |
| [`keypair`](keypair.md) | SSH key pair management |
| [`volume`](volume.md) | Block storage volumes & snapshots |
| [`security-group`](security-group.md) | Security groups & rules |
| [`floating-ip`](floating-ip.md) | Floating IP allocation & association |
| [`loadbalancer`](loadbalancer.md) | Load balancers, listeners, pools, members & health monitors |
| [`secret`](secret.md) | Secrets & containers (Barbican) |
| [`cluster`](cluster.md) | Kubernetes clusters & templates (Magnum) |
| [`metric`](metric.md) | Metrics, measures & resources (Gnocchi) |
| [`alarm`](alarm.md) | Alarms (Aodh) |
| [`placement`](placement.md) | Placement resources |
| [`stack`](stack.md) | Orchestration stacks (Heat) |
| [`backup`](backup.md) | Backups (Freezer) |
| [`zone`](zone.md) / [`recordset`](recordset.md) | DNS (Designate) |
| [`catalog`](catalog.md) | Service endpoint discovery |

## Orca-exclusive

| Command | Description |
|---|---|
| [`overview`](overview.md) | Project dashboard |
| [`watch`](watch.md) | Live auto-refreshing dashboard |
| [`doctor`](doctor.md) | Pre-deployment health check |
| [`audit`](audit.md) | Security audit |
| [`cleanup`](cleanup.md) | Orphaned resource detection |
| [`export`](export.md) | Infrastructure snapshot to YAML/JSON |
| [`profile`](profile.md) | Multi-account profile management |

## Common Patterns

### Confirmation prompts

Destructive commands ask for confirmation. Skip with `-y`/`--yes`:

```bash
orca server delete <id> -y
orca loadbalancer delete <id> --cascade -y
```

### Output format

All list/show commands support `--format` and `--column`:

```bash
orca server list --format json
orca server list --column id --column name
orca server list | less -R
```
