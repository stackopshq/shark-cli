# Metrics — `shark metric`

Query metrics, measures & resources (Gnocchi).

## Commands

| Command | Description |
|---|---|
| `resource-type-list` | List resource types |
| `resource-list` | List resources |
| `resource-show <id>` | Show resource details and its metrics |
| `list` | List metrics |
| `show <id>` | Show metric details (archive policy, granularity) |
| `measures <id>` | Get measures (datapoints) for a metric |
| `archive-policy-list` | List archive policies |
| `status` | Show Gnocchi processing status (admin only) |

## Examples

### Browse resources

```bash
# List all resource types
shark metric resource-type-list

# List instance resources
shark metric resource-list --type instance --limit 10

# Show a specific resource and its metrics
shark metric resource-show <resource-id> --type instance
```

### Query measures

```bash
# Get CPU metrics for the last 24 hours
shark metric measures <metric-id> \
  --start 2026-04-07T00:00:00 \
  --stop 2026-04-08T00:00:00 \
  --granularity 300

# Get memory usage
shark metric measures <metric-id> \
  --start -1h \
  --granularity 300
```

### Inspect a metric

```bash
shark metric show <metric-id>
```

This shows the metric's **archive policy** and available **granularities**. Always use a granularity that matches the policy.

!!! tip "Finding the right granularity"
    Use `shark metric show <id>` to see the archive policy. Each policy defines granularity/points pairs. For example, `ceilometer-low-rate` stores 8640 points at 5-minute (300s) granularity.

!!! note
    The `status` command requires admin privileges and will return **403 Forbidden** for regular users.
