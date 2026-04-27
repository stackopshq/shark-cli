# orca

OpenStack Rich Command-line Alternative — a unified CLI for managing OpenStack cloud infrastructure.

## What is orca?

`orca` lets you manage your entire OpenStack infrastructure from the terminal — virtual machines, networks, load balancers, secrets, Kubernetes clusters, metrics, and more — through one consistent interface.

## Highlights

- **60+ command groups** covering every major OpenStack service (Keystone, Nova, Neutron, Cinder, Glance, Swift, Heat, Octavia, Designate, Barbican, Magnum, Gnocchi, Aodh, CloudKitty, Placement, Freezer, Federation)
- **Typed service layer** — every resource flows through a typed `*Service` class with `TypedDict` models, catching field-name typos at mypy time
- **Rich terminal output** — coloured tables, trees and progress bars powered by [Rich](https://github.com/Textualize/rich)
- **Multi-account profiles** — named profiles, `clouds.yaml` and `OS_*` env var support, transparent token caching
- **Shell auto-completion** — Bash, Zsh, and Fish, with per-profile resource caching for IDs and names
- **Orca-exclusive commands** — `overview`, `watch`, `doctor`, `audit`, `cleanup`, `export`, `find`, `ip`

## Supported Services

| Service | Command | Backend |
|---|---|---|
| Compute | `orca server`, `orca flavor`, `orca keypair`, `orca aggregate`, `orca hypervisor`, `orca availability-zone`, `orca compute-service`, `orca server-group`, `orca event`, `orca usage` | Nova |
| Image | `orca image` | Glance |
| Block Storage | `orca volume` (incl. `volume upload-to-image`), `orca backup` | Cinder, Freezer |
| Object Storage | `orca container`, `orca object` | Swift |
| Network | `orca network`, `orca floating-ip`, `orca security-group`, `orca qos`, `orca subnet-pool`, `orca trunk` | Neutron |
| Load Balancer | `orca loadbalancer` | Octavia |
| DNS | `orca zone`, `orca recordset` | Designate |
| Orchestration | `orca stack` | Heat |
| Clusters | `orca cluster` | Magnum |
| Metrics & Alarms | `orca metric`, `orca alarm` | Gnocchi, Aodh |
| Rating | `orca rating` | CloudKitty |
| Placement | `orca placement` | Placement |
| Secrets | `orca secret` | Barbican |
| Identity | `orca user`, `orca project`, `orca domain`, `orca role`, `orca group`, `orca policy`, `orca credential`, `orca application-credential`, `orca access-rule`, `orca trust`, `orca token`, `orca auth`, `orca endpoint`, `orca endpoint-group`, `orca region`, `orca service`, `orca limit`, `orca registered-limit` | Keystone |
| Federation | `orca identity-provider`, `orca federation-protocol`, `orca mapping`, `orca service-provider` | Keystone |
| Utilities | `orca ip`, `orca limits`, `orca quota`, `orca catalog`, `orca completion` | — |
| Orca-exclusive | `orca overview`, `orca watch`, `orca doctor`, `orca audit`, `orca cleanup`, `orca export`, `orca find`, `orca profile`, `orca setup` | — |

## Quick Start

```bash
pip install orca-openstackclient
orca setup
orca server list
```

See the [Getting Started](getting-started.md) guide for full installation and configuration instructions, and the [Command Reference](commands/index.md) for per-command documentation generated directly from the running CLI.
