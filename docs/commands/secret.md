# Secrets — `shark secret`

Manage secrets and containers (Barbican key-manager). Barbican securely stores sensitive data — passwords, API keys, symmetric/asymmetric keys, and certificates. All payloads are encrypted at rest.

---

## Secrets

### list

List all secrets in the project with their name, type, algorithm, status, and creation date.

```bash
shark secret list
shark secret list --limit 20
```

| Option | Description |
|---|---|
| `--limit` | Max number of results |

### show

Display secret metadata: name, type, status, algorithm, bit length, content types, expiration, timestamps. The payload itself is not shown — use `get-payload` for that.

```bash
shark secret show <secret-id>
```

### create

Create a new secret. You can store the payload inline or create metadata first and upload the payload later.

```bash
# Store a password
shark secret create db-password \
  --payload "s3cret!" \
  --secret-type passphrase

# Store a symmetric key (metadata only, no payload)
shark secret create aes-key \
  --secret-type symmetric \
  --algorithm AES \
  --bit-length 256

# Store a certificate with expiration
shark secret create tls-cert \
  --payload "$(cat cert.pem)" \
  --payload-content-type "application/x-pem-file" \
  --secret-type certificate \
  --expiration 2026-12-31T23:59:59
```

| Option | Default | Description |
|---|---|---|
| `--payload` | — | Secret payload (inline) |
| `--payload-content-type` | `text/plain` | MIME type of payload |
| `--secret-type` | `opaque` | `symmetric`, `public`, `private`, `passphrase`, `certificate`, `opaque` |
| `--algorithm` | — | Algorithm (e.g. `AES`, `RSA`) |
| `--bit-length` | — | Bit length |
| `--expiration` | — | Expiration datetime (ISO 8601) |

### get-payload

Retrieve the decrypted secret payload. The raw value is printed to stdout.

```bash
shark secret get-payload <secret-id>
```

!!! warning
    This prints the decrypted secret value. Treat the output as sensitive.

### delete

Delete a secret. Asks for confirmation.

```bash
shark secret delete <secret-id>
shark secret delete <secret-id> -y
```

---

## Containers

Containers group related secrets together (e.g. a TLS certificate with its private key and CA chain).

### container-list

List all secret containers with their type and number of secrets.

```bash
shark secret container-list
```

### container-show

Display container details and the list of secrets it references.

```bash
shark secret container-show <container-id>
```

### container-delete

Delete a secret container. The contained secrets are not deleted.

```bash
shark secret container-delete <container-id>
shark secret container-delete <container-id> -y
```
