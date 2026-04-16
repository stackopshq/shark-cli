# Key Pairs — `orca keypair`

Manage SSH key pairs (Nova). Key pairs are used to inject SSH public keys into servers at boot for password-less authentication. You can generate keys server-side, generate them locally and upload the public half, or import existing keys.

---

## list

List all key pairs in the project with their type and fingerprint.

```bash
orca keypair list
```

---

## show

Display key pair details including the public key content.

```bash
orca keypair show my-key
```

---

## create

Generate a key pair server-side. The private key is returned **once** and saved to disk. The public key is stored in Nova.

```bash
orca keypair create my-key
orca keypair create my-key --save-to /tmp/my-key.pem
```

| Option | Default | Description |
|---|---|---|
| `--save-to` | `~/.ssh/<name>.pem` | Path to save the private key |

!!! warning
    The private key is only returned once. If lost, delete and recreate the key pair.

---

## generate

Generate a key pair **locally** using `ssh-keygen` and upload the public key to OpenStack. The private key never leaves your machine. *This is the recommended method.*

```bash
orca keypair generate my-key
orca keypair generate my-key --type rsa --bits 4096
orca keypair generate my-key --save-to ~/.ssh/custom-key
```

| Option | Default | Description |
|---|---|---|
| `--type` | `ed25519` | `ed25519`, `rsa`, `ecdsa` |
| `--bits` | `4096` (RSA only) | Key size |
| `--save-to` | `~/.ssh/orca-<name>` | Private key path |

---

## upload

Import an existing public key into OpenStack.

```bash
orca keypair upload my-key --public-key-file ~/.ssh/id_ed25519.pub
orca keypair upload my-key --public-key "ssh-ed25519 AAAA..."
```

| Option | Default | Description |
|---|---|---|
| `--public-key-file` | `~/.ssh/id_rsa.pub` | Path to public key file |
| `--public-key` | — | Public key content as string |

If neither option is given, the CLI tries `~/.ssh/id_rsa.pub` then `~/.ssh/id_ed25519.pub`.

---

## delete

Delete a key pair from OpenStack. This does not delete local files.

```bash
orca keypair delete my-key
orca keypair delete my-key -y
```
