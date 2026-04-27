# Getting Started

## Requirements

- Python **3.9 – 3.14**
- An OpenStack account with API credentials

## Installation

=== "pip"

    ```bash
    pip install orca-openstackclient
    ```

=== "Poetry (development)"

    ```bash
    git clone https://github.com/stackopshq/orca-cli.git
    cd orca-cli
    poetry install --with dev
    poetry run orca --help
    ```

After installation the `orca` command is available globally.

## Configuration

### Interactive setup

```bash
orca setup
```

This prompts for all fields and stores them in `~/.orca/config.yaml` (mode `0600`). The token cache lives next to it as `~/.orca/token_cache.yaml`.

### Profiles

orca supports multiple named profiles for managing several clouds:

```bash
orca profile add               # add a new profile interactively
orca profile list              # list all profiles
orca profile switch prod       # switch the active profile
orca --profile dev server list # use a specific profile for one command
```

### Import from clouds.yaml

```bash
orca profile from-clouds mycloud
```

### Environment variables

Standard OpenStack `OS_*` variables are supported:

```bash
export OS_AUTH_URL="https://keystone.example.com:5000/v3"
export OS_USERNAME="myuser"
export OS_PASSWORD="mypassword"
export OS_USER_DOMAIN_NAME="Default"
export OS_PROJECT_NAME="myproject"
```

!!! tip
    Resolution priority: `--profile` flag → `ORCA_PROFILE` → `OS_*` env vars → `OS_CLOUD` → `clouds.yaml` → active orca profile.

## Shell Auto-Completion

Use `orca completion install` — it generates a static script under `$XDG_DATA_HOME/orca/completion.<shell>` and adds a single `source` line to your rc file. This avoids re-spawning `orca` on every shell startup (cf. [ADR 0010](adr/0010-static-completion-script.md)).

=== "Bash"

    ```bash
    orca completion install bash
    # or, manually:
    orca completion bash > ~/.orca/completion.bash
    echo 'source ~/.orca/completion.bash' >> ~/.bashrc
    ```

=== "Zsh"

    ```zsh
    orca completion install zsh
    ```

=== "Fish"

    ```fish
    orca completion install fish
    ```

Open a new shell and `orca <TAB>` should suggest commands. Resource IDs/names (servers, volumes, flavors, images, networks, security groups, server groups, keypairs) are completed via per-profile cached lookups (5-minute TTL).

## Verify Installation

```bash
orca --version
orca catalog                 # list available service endpoints
orca server list             # list your compute instances
orca doctor                  # health-check config and connectivity
```

## Next Steps

Browse the [command reference](commands/index.md) for detailed usage of each service, or the [CLI Reference](reference.md) for an exhaustive single-page view.
