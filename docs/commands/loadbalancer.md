# `orca loadbalancer` — loadbalancer

Manage load balancers, listeners, pools & members (Octavia).

---

## amphora-failover

[OPTIONS] AMPHORA_ID

```bash
orca loadbalancer amphora-failover [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## amphora-list

List amphora (admin).

```bash
orca loadbalancer amphora-list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--lb-id TEXT` | Filter by load balancer ID. |
| `--status TEXT` | Filter by amphora status. |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## amphora-show

Show amphora details (admin).

```bash
orca loadbalancer amphora-show [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## create

Create a load balancer.

```bash
orca loadbalancer create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--subnet-id TEXT` | VIP subnet ID.  [required] |
| `--description TEXT` | Description. |
| `--provider TEXT` | Provider (e.g. amphora, ovn). |
| `--help` | Show this message and exit. |

---

## delete

Delete a load balancer.

```bash
orca loadbalancer delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--cascade` | Delete LB and all child resources. |
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## healthmonitor-create

[OPTIONS] NAME

```bash
orca loadbalancer healthmonitor-create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--pool-id TEXT` | Pool ID.  [required] |
| `--type [HTTP|HTTPS|PING|TCP|TLS-HELLO|UDP-CONNECT]` | |
| `--delay INTEGER` | Probe interval (seconds).  [required] |
| `--timeout INTEGER` | Probe timeout (seconds).  [required] |
| `--max-retries INTEGER` | Max retries (1-10).  [default: 3] |
| `--url-path TEXT` | HTTP URL path to probe.  [default: /] |
| `--expected-codes TEXT` | Expected HTTP codes.  [default: 200] |
| `--help` | Show this message and exit. |

---

## healthmonitor-delete

[OPTIONS] HM_ID

```bash
orca loadbalancer healthmonitor-delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## healthmonitor-list

[OPTIONS]

```bash
orca loadbalancer healthmonitor-list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## healthmonitor-set

[OPTIONS] HM_ID

```bash
orca loadbalancer healthmonitor-set [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--name TEXT` | New name. |
| `--delay INTEGER` | Probe interval (seconds). |
| `--timeout INTEGER` | Probe timeout (seconds). |
| `--max-retries INTEGER` | Max retries. |
| `--url-path TEXT` | HTTP URL path to probe. |
| `--expected-codes TEXT` | Expected HTTP codes. |
| `--enable / --disable` | Enable or disable the health monitor. |
| `--help` | Show this message and exit. |

---

## healthmonitor-show

[OPTIONS] HM_ID

```bash
orca loadbalancer healthmonitor-show [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## l7policy-create

[OPTIONS]

```bash
orca loadbalancer l7policy-create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--listener-id TEXT` | Listener to attach the policy to. |
| `--action [REDIRECT_TO_POOL|REDIRECT_TO_URL|REJECT|REDIRECT_PREFIX]` | |
| `--name TEXT` | Policy name. |
| `--description TEXT` | Description. |
| `--position INTEGER` | Policy position (order). |
| `--redirect-pool-id TEXT` | Pool to redirect to (REDIRECT_TO_POOL). |
| `--redirect-url TEXT` | URL to redirect to (REDIRECT_TO_URL). |
| `--redirect-prefix TEXT` | URL prefix to redirect to (REDIRECT_PREFIX). |
| `--help` | Show this message and exit. |

---

## l7policy-delete

[OPTIONS] L7POLICY_ID

```bash
orca loadbalancer l7policy-delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## l7policy-list

List L7 policies.

```bash
orca loadbalancer l7policy-list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## l7policy-set

Update an L7 policy.

```bash
orca loadbalancer l7policy-set [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--name TEXT` | New name. |
| `--description TEXT` | New description. |
| `--action [REDIRECT_TO_POOL|REDIRECT_TO_URL|REJECT|REDIRECT_PREFIX]` | |
| `--position INTEGER` | New position. |
| `--redirect-pool-id TEXT` | New redirect pool ID. |
| `--redirect-url TEXT` | New redirect URL. |
| `--enable / --disable` | Enable or disable. |
| `--help` | Show this message and exit. |

---

## l7policy-show

L7POLICY_ID

```bash
orca loadbalancer l7policy-show [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## l7rule-create

L7POLICY_ID

```bash
orca loadbalancer l7rule-create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--type [COOKIE|FILE_TYPE|HEADER|HOST_NAME|PATH|SSL_CONN_HAS_CERT|SSL_VERIFY_RESULT|SSL_DN_FIELD]` | |
| `--compare-type [CONTAINS|ENDS_WITH|EQUAL_TO|REGEX|STARTS_WITH]` | |
| `--value TEXT` | Value to compare against.  [required] |
| `--key TEXT` | Key (for HEADER, COOKIE rules). |
| `--invert` | Invert the match result. |
| `--help` | Show this message and exit. |

---

## l7rule-delete

L7POLICY_ID
L7RULE_ID

```bash
orca loadbalancer l7rule-delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## l7rule-list

List L7 rules for a policy.

```bash
orca loadbalancer l7rule-list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## l7rule-set

L7RULE_ID

```bash
orca loadbalancer l7rule-set [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--type [COOKIE|FILE_TYPE|HEADER|HOST_NAME|PATH|SSL_CONN_HAS_CERT|SSL_VERIFY_RESULT|SSL_DN_FIELD]` | |
| `--compare-type [CONTAINS|ENDS_WITH|EQUAL_TO|REGEX|STARTS_WITH]` | |
| `--value TEXT` | New value. |
| `--key TEXT` | New key. |
| `--invert / --no-invert` | Invert match. |
| `--enable / --disable` | Enable or disable the rule. |
| `--help` | Show this message and exit. |

---

## l7rule-show

L7RULE_ID

```bash
orca loadbalancer l7rule-show [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## list

List load balancers.

```bash
orca loadbalancer list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## listener-create

[OPTIONS] NAME

```bash
orca loadbalancer listener-create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--lb-id TEXT` | Load balancer ID.  [required] |
| `--protocol [HTTP|HTTPS|TCP|UDP|TERMINATED_HTTPS]` | |
| `--port INTEGER` | Listen port.  [required] |
| `--default-pool-id TEXT` | Default pool ID. |
| `--help` | Show this message and exit. |

---

## listener-delete

[OPTIONS] LISTENER_ID

```bash
orca loadbalancer listener-delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## listener-list

List listeners.

```bash
orca loadbalancer listener-list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## listener-set

Update a listener.

```bash
orca loadbalancer listener-set [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--name TEXT` | New name. |
| `--description TEXT` | New description. |
| `--default-pool-id TEXT` | New default pool ID. |
| `--connection-limit INTEGER` | Max connections (-1 for unlimited). |
| `--enable / --disable` | Enable or disable the listener. |
| `--help` | Show this message and exit. |

---

## listener-show

LISTENER_ID

```bash
orca loadbalancer listener-show [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## member-add

Add a member to a pool.

```bash
orca loadbalancer member-add [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--address TEXT` | Member IP address.  [required] |
| `--port INTEGER` | Member port.  [required] |
| `--subnet-id TEXT` | Member subnet ID. |
| `--weight INTEGER` | Weight (0-256).  [default: 1] |
| `--name TEXT` | Member name. |
| `--help` | Show this message and exit. |

---

## member-list

List members in a pool.

```bash
orca loadbalancer member-list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## member-remove

MEMBER_ID

```bash
orca loadbalancer member-remove [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## member-set

MEMBER_ID

```bash
orca loadbalancer member-set [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--name TEXT` | New name. |
| `--weight INTEGER` | New weight (0-256). |
| `--enable / --disable` | Enable or disable the member. |
| `--help` | Show this message and exit. |

---

## member-show

MEMBER_ID

```bash
orca loadbalancer member-show [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## pool-create

Create a pool.

```bash
orca loadbalancer pool-create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--listener-id TEXT` | Listener ID to attach to. |
| `--lb-id TEXT` | Load balancer ID (if no listener). |
| `--protocol [HTTP|HTTPS|PROXY|TCP|UDP]` | |
| `--algorithm [ROUND_ROBIN|LEAST_CONNECTIONS|SOURCE_IP]` | |
| `--help` | Show this message and exit. |

---

## pool-delete

Delete a pool.

```bash
orca loadbalancer pool-delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## pool-list

List pools.

```bash
orca loadbalancer pool-list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## pool-set

Update a pool.

```bash
orca loadbalancer pool-set [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--name TEXT` | New name. |
| `--description TEXT` | New description. |
| `--algorithm [ROUND_ROBIN|LEAST_CONNECTIONS|SOURCE_IP]` | |
| `--enable / --disable` | Enable or disable the pool. |
| `--help` | Show this message and exit. |

---

## pool-show

Show pool details.

```bash
orca loadbalancer pool-show [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## set

Update a load balancer.

```bash
orca loadbalancer set [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--name TEXT` | New name. |
| `--description TEXT` | New description. |
| `--enable / --disable` | Enable or disable the load balancer. |
| `--help` | Show this message and exit. |

---

## show

Show load balancer details.

```bash
orca loadbalancer show [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## stats-show

Show load balancer statistics.

```bash
orca loadbalancer stats-show [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## status-show

Show load balancer operating status tree.

```bash
orca loadbalancer status-show [OPTIONS]
```

| Option | Description |
|--------|-------------|

---
