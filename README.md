# orca

OpenStack Rich Command-line Alternative — a unified CLI for managing OpenStack cloud infrastructure.

**[Full Documentation](https://stackopshq.github.io/orca-cli/)**

## Highlights

- **60+ command groups** covering all major OpenStack services
- **Rich terminal output** — coloured tables powered by [Rich](https://github.com/Textualize/rich)
- **Multi-account profiles** — named profiles, `clouds.yaml` and `OS_*` env var support
- **Shell auto-completion** — Bash, Zsh, and Fish
- **Orca-exclusive** — `overview`, `watch`, `doctor`, `audit`, `cleanup`, `export`

## Quick Start

```bash
pip install .        # or: poetry install
orca setup           # interactive credential setup
orca server list     # list your VMs
```

## Supported Services

| Command | Service | Backend |
|---|---|---|
| `orca server` | Compute | Nova |
| `orca flavor` | Flavors | Nova |
| `orca image` | Images | Glance |
| `orca network` | Networks, Subnets, Ports, Routers | Neutron |
| `orca keypair` | SSH Key Pairs | Nova |
| `orca volume` | Block Storage & Snapshots | Cinder |
| `orca security-group` | Security Groups & Rules | Neutron |
| `orca floating-ip` | Floating IPs | Neutron |
| `orca loadbalancer` | Load Balancers, Listeners, Pools, Members | Octavia |
| `orca secret` | Secrets & Containers | Barbican |
| `orca cluster` | Kubernetes Clusters & Templates | Magnum |
| `orca metric` | Metrics, Measures & Resources | Gnocchi |
| `orca placement` | Placement API | Placement |
| `orca stack` | Orchestration | Heat |
| `orca backup` | Backups | Freezer |
| `orca zone` / `orca recordset` | DNS | Designate |
| `orca alarm` | Alarms | Aodh |
| `orca catalog` | Service Endpoint Discovery | Keystone |

## Documentation

Full documentation: **[stackopshq.github.io/orca-cli](https://stackopshq.github.io/orca-cli/)**

```bash
pip install mkdocs-material
mkdocs serve
```

## License

Apache-2.0
