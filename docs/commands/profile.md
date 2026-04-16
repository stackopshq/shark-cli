# `orca profile` — Profile (multi-account)

Manage configuration profiles (multi-account).

---

## add

Add a new profile interactively.

```bash
orca profile add [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--copy-from TEXT` | Copy settings from an existing profile. |
| `--color TEXT` | Profile color (e.g. red, green, blue, cyan, magenta, |
| `--help` | Show this message and exit. |

---

## edit

Edit an existing profile interactively.

```bash
orca profile edit [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## from-clouds

Import a cloud from clouds.yaml as an orca profile.

```bash
orca profile from-clouds [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-n, --name TEXT` | Profile name (default: cloud name). |
| `-f, --file TEXT` | Path to clouds.yaml (default: auto-detect). |
| `--help` | Show this message and exit. |

---

## from-openrc

Import an OpenRC file as an orca profile.

```bash
orca profile from-openrc [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-n, --name TEXT` | Profile name (default: filename without extension). |
| `--help` | Show this message and exit. |

---

## list

List all profiles.

```bash
orca profile list [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## regions

List available regions from the Keystone service catalog.

```bash
orca profile regions [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## remove

Remove a profile.

```bash
orca profile remove [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## rename

Rename a profile.

```bash
orca profile rename [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## set-color

Set a color for a profile. Use 'none' to remove.

```bash
orca profile set-color [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## set-region

Set the default region for a profile.

```bash
orca profile set-region [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## show

Show profile details. Defaults to active profile.

```bash
orca profile show [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## switch

Switch the active profile.

```bash
orca profile switch [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## to-clouds

Export a profile as a clouds.yaml entry.

```bash
orca profile to-clouds [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-o, --output TEXT` | Write to file instead of stdout. |
| `--cloud-name TEXT` | Cloud name in clouds.yaml (default: profile name). |
| `--help` | Show this message and exit. |

---

## to-openrc

Export a profile as an OpenRC shell script.

```bash
orca profile to-openrc [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-o, --output TEXT` | Write to file instead of stdout. |
| `--help` | Show this message and exit. |

---
