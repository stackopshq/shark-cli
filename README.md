# shark-cli

A professional, modular CLI for the [Sharktech](https://sharktech.net) Cloud Provider API.

**[Full Documentation](https://stackopshq.github.io/shark-cli/)**

## Highlights

- **14 command groups** covering all major OpenStack services
- **100+ sub-commands** for full lifecycle management
- **Rich terminal output** — coloured tables powered by [Rich](https://github.com/Textualize/rich)
- **Shell auto-completion** — Bash, Zsh, and Fish
- **Secure configuration** — env vars > YAML config; `0600` permissions

## Quick Start

```bash
pip install .        # or: poetry install
shark setup          # interactive credential setup
shark server list    # list your VMs
```

## Supported Services

| Command | Service | Backend |
|---|---|---|
| `shark server` | Compute | Nova |
| `shark flavor` | Flavors | Nova |
| `shark image` | Images | Glance |
| `shark network` | Networks, Subnets, Ports, Routers | Neutron |
| `shark keypair` | SSH Key Pairs | Nova |
| `shark volume` | Block Storage & Snapshots | Cinder |
| `shark security-group` | Security Groups & Rules | Neutron |
| `shark floating-ip` | Floating IPs | Neutron |
| `shark loadbalancer` | Load Balancers, Listeners, Pools, Members | Octavia |
| `shark secret` | Secrets & Containers | Barbican |
| `shark cluster` | Kubernetes Clusters & Templates | Magnum |
| `shark metric` | Metrics, Measures & Resources | Gnocchi |
| `shark catalog` | Service Endpoint Discovery | Keystone |

## Documentation

Full documentation is available at **[stackopshq.github.io/shark-cli](https://stackopshq.github.io/shark-cli/)**.

To build the docs locally:

```bash
pip install mkdocs-material
mkdocs serve
```

## Project Structure

```
sharktech-cli/
├── pyproject.toml          # Poetry packaging & dependencies
├── mkdocs.yml              # MkDocs Material configuration
├── docs/                   # Documentation source (MkDocs)
├── README.md
└── shark_cli/
    ├── __init__.py          # Package version
    ├── main.py              # Click group & entry point
    ├── core/
    │   ├── client.py        # Centralised httpx API client
    │   ├── config.py        # YAML / env-var config loader
    │   ├── context.py       # Shared SharkContext object
    │   ├── exceptions.py    # Domain-specific exceptions
    │   └── validators.py    # Input validators
    └── commands/
        ├── server.py        # shark server (28 commands)
        ├── image.py         # shark image (11 commands)
        ├── network.py       # shark network (21 commands)
        ├── volume.py        # shark volume (13 commands)
        ├── loadbalancer.py  # shark loadbalancer (18 commands)
        ├── secret.py        # shark secret (8 commands)
        ├── cluster.py       # shark cluster (10 commands)
        ├── metric.py        # shark metric (8 commands)
        └── ...              # flavor, keypair, security-group, floating-ip, catalog
```

## License

Apache-2.0
