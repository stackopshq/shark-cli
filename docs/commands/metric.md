# Metrics — `shark metric`

Query metrics, measures and resources (Gnocchi). Gnocchi is a time-series database that stores metering data from your cloud infrastructure — CPU usage, memory, disk I/O, network traffic, etc. Use these commands to explore resources, inspect metrics, and retrieve datapoints.

---

## Resource Types

### resource-type-list

List all available resource types (e.g. `instance`, `volume`, `network`). Each type defines attributes that resources of that type can have.

```bash
shark metric resource-type-list
```

---

## Resources

A resource is a cloud object (server, volume, etc.) that has metrics associated with it.

### resource-list

List resources of a given type. Each resource shows its ID, type, original resource ID, and metric count.

```bash
shark metric resource-list
shark metric resource-list --type instance
shark metric resource-list --type instance --limit 10
```

| Option | Default | Description |
|---|---|---|
| `--type` | `generic` | Resource type to list |
| `--limit` | — | Max number of results |

### resource-show

Display a resource's details and all its associated metrics (metric name → metric ID).

```bash
shark metric resource-show <resource-id>
shark metric resource-show <resource-id> --type instance
```

| Option | Default | Description |
|---|---|---|
| `--type` | `generic` | Resource type |

---

## Metrics

### list

List all metrics with their name, unit, archive policy, and associated resource.

```bash
shark metric list
shark metric list --limit 20
```

| Option | Description |
|---|---|
| `--limit` | Max number of results |

### show

Display a metric's details including its archive policy and available granularities. Use this to find the correct granularity for `measures` queries.

```bash
shark metric show <metric-id>
```

The output includes the archive policy **definition** — a list of granularity/points/timespan tuples that tell you what resolutions are available.

---

## Measures

### measures

Retrieve time-series datapoints for a metric. Each datapoint contains a timestamp, granularity, and aggregated value.

```bash
# Last hour of data
shark metric measures <metric-id> --start -1h

# Specific time range with 5-minute granularity
shark metric measures <metric-id> \
  --start 2026-04-07T00:00:00 \
  --stop 2026-04-08T00:00:00 \
  --granularity 300

# Last 24h, max aggregation
shark metric measures <metric-id> \
  --start -24h --aggregation max

# Limit number of results
shark metric measures <metric-id> --start -1h --limit 50
```

| Option | Default | Description |
|---|---|---|
| `--start` | — | Start timestamp (ISO 8601 or relative, e.g. `-1h`, `-7d`) |
| `--stop` | — | Stop timestamp |
| `--granularity` | — | Granularity in seconds (must match archive policy) |
| `--aggregation` | `mean` | Aggregation method (`mean`, `max`, `min`, `sum`, `count`, etc.) |
| `--limit` | — | Max measures to return |

!!! tip "Finding the right granularity"
    Use `shark metric show <id>` to see the archive policy. Each policy defines granularity/points pairs. For example, `ceilometer-low-rate` stores 8640 points at 5-minute (300s) granularity. Always use a granularity that matches the policy.

---

## Archive Policies

### archive-policy-list

List all archive policies with their aggregation methods and retention definitions.

```bash
shark metric archive-policy-list
```

Each policy shows its granularity/points pairs — these determine the resolution and retention period of metrics using that policy.

---

## Status

### status

Show Gnocchi's internal processing status: number of measures waiting to be processed and metrics with pending measures.

```bash
shark metric status
```

!!! note
    This command requires admin privileges and will return **403 Forbidden** for regular users.

---

## Full Example: Monitor Server CPU

```bash
# 1. Find the server resource
shark metric resource-list --type instance --limit 5

# 2. Show its metrics
shark metric resource-show <resource-id> --type instance
# → cpu: <metric-id>

# 3. Check available granularities
shark metric show <metric-id>

# 4. Query CPU usage for the last 6 hours
shark metric measures <metric-id> \
  --start -6h --granularity 300 --aggregation mean
```
