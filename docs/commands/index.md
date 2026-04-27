# Command Reference

`orca` organises commands by OpenStack service. Every command supports `--help` for inline documentation, and every page in this section is generated directly from the live CLI by `mkdocs-click` — they always reflect the version installed.

```bash
orca --help                  # list all command groups
orca server --help           # list all sub-commands of `server`
orca server image create --help  # detailed help for one command
```

For a single-page exhaustive reference, see the [CLI Reference](../reference.md).

## Compute (Nova)

| Group | What it manages |
|---|---|
| [`server`](server.md) | Compute instances — full lifecycle (create, snapshot, migrate, console, attach/detach, …) |
| [`flavor`](flavor.md) | Flavors and their access rules |
| [`keypair`](keypair.md) | SSH key pairs |
| [`aggregate`](aggregate.md) | Host aggregates |
| [`hypervisor`](hypervisor.md) | Hypervisor inventory |
| [`availability-zone`](availability-zone.md) | Availability zones |
| [`compute-service`](compute-service.md) | Nova back-end services |
| [`server-group`](server-group.md) | Anti-affinity / affinity groups |
| [`event`](event.md) | Instance event history |
| [`usage`](usage.md) | Tenant usage statistics |

## Image (Glance)

| Group | What it manages |
|---|---|
| [`image`](image.md) | Images, members, tasks, cache, stores |

## Block Storage (Cinder, Freezer)

| Group | What it manages |
|---|---|
| [`volume`](volume.md) | Volumes, snapshots, backups, attachments, types, QoS, transfers, groups. Includes `volume upload-to-image` for cross-cloud BFV migration. |
| [`backup`](backup.md) | Trilio Freezer scheduled backups |

## Object Storage (Swift)

| Group | What it manages |
|---|---|
| [`container`](container.md) | Containers |
| [`object`](object.md) | Objects |

## Network (Neutron)

| Group | What it manages |
|---|---|
| [`network`](network.md) | Networks, subnets, ports, routers (with nested `router add/remove/set/unset`) |
| [`floating-ip`](floating-ip.md) | Allocation and association |
| [`security-group`](security-group.md) | Security groups and rules |
| [`qos`](qos.md) | QoS policies and rules |
| [`subnet-pool`](subnet-pool.md) | Subnet pools |
| [`trunk`](trunk.md) | Trunk ports and sub-ports |

## Load Balancer (Octavia)

| Group | What it manages |
|---|---|
| [`loadbalancer`](loadbalancer.md) | LBs, listeners, pools, members, health monitors, L7 policies, amphora |

## DNS (Designate)

| Group | What it manages |
|---|---|
| [`zone`](zone.md) | Zones and zone transfers |
| [`recordset`](recordset.md) | Records inside a zone |

## Orchestration & Clusters

| Group | What it manages |
|---|---|
| [`stack`](stack.md) | Heat stacks, resources, templates |
| [`cluster`](cluster.md) | Magnum clusters and templates |

## Telemetry & Rating

| Group | What it manages |
|---|---|
| [`metric`](metric.md) | Gnocchi metrics, measures, resource types |
| [`alarm`](alarm.md) | Aodh alarms and history |
| [`rating`](rating.md) | CloudKitty rating modules |

## Placement & Secrets

| Group | What it manages |
|---|---|
| [`placement`](placement.md) | Resource providers, traits, inventories, allocations |
| [`secret`](secret.md) | Barbican secrets and containers |

## Identity (Keystone)

| Group | What it manages |
|---|---|
| [`user`](user.md), [`project`](project.md), [`domain`](domain.md), [`role`](role.md), [`group`](group.md) | Core RBAC |
| [`policy`](policy.md) | Service policies |
| [`credential`](credential.md), [`application-credential`](application-credential.md), [`access-rule`](access-rule.md) | Credentials and scoped tokens |
| [`trust`](trust.md), [`token`](token.md), [`auth`](auth.md) | Trust delegation, token introspection |
| [`endpoint`](endpoint.md), [`endpoint-group`](endpoint-group.md), [`region`](region.md), [`service`](service.md) | Service catalog |
| [`limit`](limit.md), [`registered-limit`](registered-limit.md) | Project / system limits |

## Federation

| Group | What it manages |
|---|---|
| [`identity-provider`](identity-provider.md), [`federation-protocol`](federation-protocol.md), [`mapping`](mapping.md), [`service-provider`](service-provider.md) | Federated identity |

## Utilities

| Group | What it manages |
|---|---|
| [`ip`](ip.md) | Address WHOIS / introspection (orca-exclusive) |
| [`limits`](limits.md), [`quota`](quota.md) | Quota inspection |
| [`catalog`](catalog.md) | Service catalog dump |
| [`completion`](completion.md) | Shell completion install / print |

## Orca-exclusive

| Command | Description |
|---|---|
| [`overview`](overview.md) | Single-screen project dashboard |
| [`watch`](watch.md) | Live auto-refreshing dashboard |
| [`doctor`](doctor.md) | Configuration / connectivity health check |
| [`audit`](audit.md) | Cross-resource security audit |
| [`cleanup`](cleanup.md) | Detect / delete dangling resources |
| [`export`](export.md) | Snapshot infrastructure to YAML/JSON |
| [`find`](find.md) | Locate a resource by partial ID or name |
| [`profile`](profile.md) | Multi-account profile management |
| [`setup`](setup.md) | Interactive credential wizard |

## Common Patterns

### Confirmation prompts

Destructive commands ask for confirmation. Skip with `-y` / `--yes`:

```bash
orca server delete <id> -y
orca loadbalancer delete <id> --cascade -y
```

### Output format

All `list` / `show` commands accept `--format`, `--column`, `--fit-width`, `--max-width`, `--noindent`:

```bash
orca server list --format json
orca server list --column id --column name
orca volume show <id> -f value -c id -c size
```

### Errors

Every error surfaced to the user lands on the central red `Error: …` formatter from version 2.2.0 onward — there is no "`Unexpected error: …`" path on operational failures. Use `--debug` to log HTTP requests and retry decisions to stderr.
