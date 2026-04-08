# shark-cli

A professional, modular CLI for the **Sharktech Cloud Provider** API.

## What is shark-cli?

`shark-cli` lets you manage your entire Sharktech Cloud infrastructure from the terminal — virtual machines, networks, load balancers, secrets, Kubernetes clusters, metrics, and more.

## Highlights

- **14 command groups** covering all major OpenStack services
- **100+ sub-commands** for full lifecycle management
- **Rich terminal output** — coloured tables powered by [Rich](https://github.com/Textualize/rich)
- **Shell auto-completion** — Bash, Zsh, and Fish
- **Secure configuration** — env vars take precedence; config file written with `0600` permissions

## Supported Services

| Service | Command | Backend |
|---|---|---|
| Compute | `shark server` | Nova |
| Flavors | `shark flavor` | Nova |
| Images | `shark image` | Glance |
| Networks | `shark network` | Neutron |
| Key Pairs | `shark keypair` | Nova |
| Volumes | `shark volume` | Cinder |
| Security Groups | `shark security-group` | Neutron |
| Floating IPs | `shark floating-ip` | Neutron |
| Load Balancers | `shark loadbalancer` | Octavia |
| Secrets | `shark secret` | Barbican |
| Clusters | `shark cluster` | Magnum |
| Metrics | `shark metric` | Gnocchi |
| Service Catalog | `shark catalog` | Keystone |

## Quick Start

```bash
pip install .
shark setup
shark server list
```

See the [Getting Started](getting-started.md) guide for full installation and configuration instructions.
