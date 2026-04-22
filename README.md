# orca

OpenStack Rich Command-line Alternative — a unified CLI for managing OpenStack cloud infrastructure.

**[Full Documentation](https://stackopshq.github.io/orca-cli/)**

## Highlights

- **60+ command groups** covering every major OpenStack service (Keystone, Nova, Neutron, Cinder, Glance, Swift, Heat, Octavia, Designate, Barbican, Magnum, Gnocchi, Aodh, CloudKitty, Placement, Freezer)
- **Typed service layer** — every resource flows through a typed `*Service` class with TypedDict models, catching field-name typos at mypy time
- **Rich terminal output** — coloured tables, trees and progress bars powered by [Rich](https://github.com/Textualize/rich)
- **Multi-account profiles** — named profiles, `clouds.yaml` and `OS_*` env var support, transparent token caching
- **Shell auto-completion** — Bash, Zsh, and Fish, with per-profile resource caching
- **Orca-exclusive commands** — `overview`, `watch`, `doctor`, `audit`, `cleanup`, `export`, `find`, `ip-whois`

## Quick Start

```bash
pip install orca-openstackclient
orca setup           # interactive credential setup
orca server list     # list your VMs
```

From source (development):

```bash
git clone https://github.com/stackopshq/orca-cli.git
cd orca-cli
poetry install --with dev
poetry run orca --help
```

Requires Python **3.9 – 3.14**.

## Commands at a glance

### Compute (Nova)
`server` · `server bulk` · `flavor` · `keypair` · `aggregate` · `hypervisor` · `availability-zone` · `compute-service` · `server-group` · `usage` · `limits` · `event`

### Networking (Neutron)
`network` · `floating-ip` · `security-group` · `subnet-pool` · `trunk` · `qos`

### Storage
`volume` · `image` (Glance) · `object` / `container` (Swift) · `backup` (Freezer)

### Identity (Keystone)
`project` · `user` · `role` · `domain` · `group` · `credential` · `application-credential` · `endpoint` · `endpoint-group` · `service` · `region` · `policy` · `trust` · `token` · `access-rule` · `limit` · `registered-limit` · `identity-provider` · `federation-protocol` · `mapping` · `service-provider` · `catalog`

### Platform services
`stack` (Heat) · `loadbalancer` (Octavia) · `zone` / `recordset` (Designate) · `secret` (Barbican) · `cluster` (Magnum) · `metric` (Gnocchi) · `alarm` (Aodh) · `rating` (CloudKitty) · `placement`

### Orca-exclusive
`overview` · `watch` · `doctor` · `audit` · `cleanup` · `export` · `find` · `ip-whois` · `quota` · `profile` · `setup`

## Documentation

Full documentation: **[stackopshq.github.io/orca-cli](https://stackopshq.github.io/orca-cli/)**

Local preview:

```bash
poetry install --with docs
mkdocs serve
```

Release notes: see [CHANGELOG.md](CHANGELOG.md).

Architectural decisions: [docs/adr/](docs/adr/).

## License

Apache-2.0
