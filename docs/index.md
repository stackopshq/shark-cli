# orca

OpenStack Rich Command-line Alternative — a unified CLI for managing OpenStack cloud infrastructure.

## What is orca?

`orca` lets you manage your entire OpenStack infrastructure from the terminal — virtual machines, networks, load balancers, secrets, Kubernetes clusters, metrics, and more.

## Highlights

- **60+ command groups** covering all major OpenStack services
- **Rich terminal output** — coloured tables powered by [Rich](https://github.com/Textualize/rich)
- **Multi-account profiles** — named profiles with `clouds.yaml` and `OS_*` env var support
- **Shell auto-completion** — Bash, Zsh, and Fish
- **Orca-exclusive** — `overview`, `watch`, `doctor`, `audit`, `cleanup`, `export`

## Supported Services

| Service | Command | Backend |
|---|---|---|
| Compute | `orca server` | Nova |
| Flavors | `orca flavor` | Nova |
| Images | `orca image` | Glance |
| Networks | `orca network` | Neutron |
| Key Pairs | `orca keypair` | Nova |
| Volumes | `orca volume` | Cinder |
| Security Groups | `orca security-group` | Neutron |
| Floating IPs | `orca floating-ip` | Neutron |
| Load Balancers | `orca loadbalancer` | Octavia |
| Secrets | `orca secret` | Barbican |
| Clusters | `orca cluster` | Magnum |
| Metrics | `orca metric` | Gnocchi |
| Alarms | `orca alarm` | Aodh |
| Placement | `orca placement` | Placement |
| Orchestration | `orca stack` | Heat |
| Backup | `orca backup` | Freezer |
| DNS | `orca zone` / `orca recordset` | Designate |
| Service Catalog | `orca catalog` | Keystone |

## Quick Start

```bash
pip install .
orca setup
orca server list
```

See the [Getting Started](getting-started.md) guide for full installation and configuration instructions.
