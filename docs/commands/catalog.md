# Service Catalog — `shark catalog`

List available service endpoints from the Keystone identity catalog. The catalog is returned by Keystone during authentication and lists every OpenStack service available in your project, along with its type, interface, and endpoint URL.

This command is useful for:

- **Debugging** — verifying which services are available and their URLs
- **Discovery** — finding endpoint URLs for services not yet covered by `shark`
- **Troubleshooting** — confirming connectivity to specific services

---

## Usage

```bash
shark catalog
```

Output columns: **Service** (name), **Type** (e.g. `compute`, `network`, `identity`), **Interface** (`public`, `internal`, `admin`), **URL**.

### Example output

```
┌──────────┬───────────┬───────────┬───────────────────────────────────────┐
│ Service  │ Type      │ Interface │ URL                                   │
├──────────┼───────────┼───────────┼───────────────────────────────────────┤
│ nova     │ compute   │ public    │ https://compute.example.com/v2.1      │
│ neutron  │ network   │ public    │ https://network.example.com           │
│ glance   │ image     │ public    │ https://image.example.com             │
│ cinder   │ volumev3  │ public    │ https://volume.example.com/v3         │
│ keystone │ identity  │ public    │ https://identity.example.com/v3       │
│ octavia  │ load-bal… │ public    │ https://lb.example.com                │
│ barbican │ key-mana… │ public    │ https://secrets.example.com           │
│ magnum   │ containe… │ public    │ https://container.example.com         │
│ gnocchi  │ metric    │ public    │ https://metric.example.com            │
└──────────┴───────────┴───────────┴───────────────────────────────────────┘
```
