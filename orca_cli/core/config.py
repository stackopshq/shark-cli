"""Configuration loader — supports multiple profiles, clouds.yaml and OS_* env vars.

Config file: ``~/.orca/config.yaml``

New multi-profile format::

    active_profile: production
    profiles:
      production:
        auth_url: https://keystone.example.com:5000
        username: admin
        password: secret
        domain_id: Default
        project_id: my-project
      staging:
        auth_url: ...

Legacy flat format (auto-migrated on first load)::

    auth_url: ...
    username: ...

**Config resolution priority** (first match wins):

1. ``--profile`` flag / ``ORCA_PROFILE`` → load that orca profile, overlay ``ORCA_*``
2. ``OS_*`` environment variables (standard OpenStack env vars)
3. ``OS_CLOUD`` → look up cloud in ``clouds.yaml``
4. Active orca profile (fallback)
"""

from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

CONFIG_DIR = Path.home() / ".orca"
CONFIG_FILE = CONFIG_DIR / "config.yaml"

# Mapping: ORCA_* env-var name → config key
_ORCA_ENV_MAP = {
    "ORCA_AUTH_URL": "auth_url",
    "ORCA_USERNAME": "username",
    "ORCA_PASSWORD": "password",
    "ORCA_DOMAIN_ID": "domain_id",
    "ORCA_PROJECT_ID": "project_id",
    "ORCA_INSECURE": "insecure",
}

# Mapping: OS_* env-var name → config key (standard OpenStack env vars)
_OS_ENV_MAP = {
    "OS_AUTH_URL": "auth_url",
    "OS_USERNAME": "username",
    "OS_PASSWORD": "password",
    "OS_USER_DOMAIN_NAME": "user_domain_name",
    "OS_USER_DOMAIN_ID": "user_domain_id",
    "OS_PROJECT_DOMAIN_NAME": "project_domain_name",
    "OS_PROJECT_DOMAIN_ID": "project_domain_id",
    "OS_PROJECT_NAME": "project_name",
    "OS_PROJECT_ID": "project_id",
    "OS_REGION_NAME": "region_name",
    "OS_INTERFACE": "interface",
    "OS_CACERT": "cacert",
    "OS_INSECURE": "insecure",
}

# clouds.yaml search paths (standard OpenStack order)
_CLOUDS_YAML_PATHS: List[Path] = [
    Path("clouds.yaml"),                           # current directory
    Path.home() / ".config" / "openstack" / "clouds.yaml",
    Path("/etc/openstack/clouds.yaml"),
]

REQUIRED_KEYS = ("auth_url", "username", "password")

# A config is "complete" if it has auth_url + username + password and at least
# one form of domain + project identification.
_DOMAIN_KEYS = ("domain_id", "user_domain_name", "user_domain_id")
_PROJECT_KEYS = ("project_id", "project_name")

DEFAULT_PROFILE = "default"


# ── Raw file I/O ─────────────────────────────────────────────────────────

def _load_raw() -> Dict[str, Any]:
    """Load the raw YAML file as-is."""
    if not CONFIG_FILE.exists():
        return {}
    with open(CONFIG_FILE, "r") as fh:
        return yaml.safe_load(fh) or {}


def _save_raw(data: Dict[str, Any]) -> Path:
    """Write *data* to the config file with 0600 permissions."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as fh:
        yaml.dump(data, fh, default_flow_style=False)
    CONFIG_FILE.chmod(stat.S_IRUSR | stat.S_IWUSR)
    return CONFIG_FILE


# ── Migration ────────────────────────────────────────────────────────────

def _is_legacy(raw: Dict[str, Any]) -> bool:
    """True if the file uses the old flat format (no ``profiles`` key)."""
    return "profiles" not in raw and any(k in raw for k in REQUIRED_KEYS)


def _migrate(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Convert legacy flat config to multi-profile format in-place."""
    profile_data = {k: v for k, v in raw.items() if k != "profiles" and k != "active_profile"}
    new = {
        "active_profile": DEFAULT_PROFILE,
        "profiles": {DEFAULT_PROFILE: profile_data},
    }
    _save_raw(new)
    return new


# ── Profile helpers ──────────────────────────────────────────────────────

def _ensure_structure(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Migrate if legacy, return normalised structure."""
    if _is_legacy(raw):
        return _migrate(raw)
    raw.setdefault("profiles", {})
    raw.setdefault("active_profile", DEFAULT_PROFILE)
    return raw


def get_active_profile_name(override: str | None = None) -> str:
    """Resolve which profile to use (CLI flag > env var > config file)."""
    if override:
        return override
    env = os.environ.get("ORCA_PROFILE")
    if env:
        return env
    raw = _ensure_structure(_load_raw())
    return raw.get("active_profile", DEFAULT_PROFILE)


def list_profiles() -> Dict[str, Dict[str, Any]]:
    """Return all profiles as ``{name: config_dict}``."""
    raw = _ensure_structure(_load_raw())
    return raw.get("profiles", {})


def get_profile(name: str) -> Dict[str, Any]:
    """Return a single profile by name, or empty dict."""
    return list_profiles().get(name, {})


def set_active_profile(name: str) -> None:
    """Switch the active profile."""
    raw = _ensure_structure(_load_raw())
    if name not in raw.get("profiles", {}):
        raise KeyError(f"Profile '{name}' does not exist.")
    raw["active_profile"] = name
    _save_raw(raw)


def save_profile(name: str, data: Dict[str, Any]) -> Path:
    """Create or update a profile."""
    raw = _ensure_structure(_load_raw())
    raw["profiles"][name] = data
    # If it's the only profile, make it active
    if len(raw["profiles"]) == 1:
        raw["active_profile"] = name
    return _save_raw(raw)


def delete_profile(name: str) -> None:
    """Delete a profile. Cannot delete the active profile."""
    raw = _ensure_structure(_load_raw())
    if name not in raw.get("profiles", {}):
        raise KeyError(f"Profile '{name}' does not exist.")
    if raw.get("active_profile") == name:
        raise ValueError(f"Cannot delete the active profile '{name}'. Switch first.")
    del raw["profiles"][name]
    _save_raw(raw)


def rename_profile(old_name: str, new_name: str) -> None:
    """Rename a profile."""
    raw = _ensure_structure(_load_raw())
    profiles = raw.get("profiles", {})
    if old_name not in profiles:
        raise KeyError(f"Profile '{old_name}' does not exist.")
    if new_name in profiles:
        raise ValueError(f"Profile '{new_name}' already exists.")
    profiles[new_name] = profiles.pop(old_name)
    if raw.get("active_profile") == old_name:
        raw["active_profile"] = new_name
    _save_raw(raw)


# ── clouds.yaml support ─────────────────────────────────────────────────

def _find_clouds_yaml() -> Optional[Path]:
    """Locate the first existing clouds.yaml in standard paths."""
    for p in _CLOUDS_YAML_PATHS:
        if p.exists():
            return p
    return None


def _load_clouds_yaml(cloud_name: str) -> Dict[str, Any]:
    """Load a named cloud from ``clouds.yaml`` and normalise to orca keys."""
    path = _find_clouds_yaml()
    if not path:
        return {}
    with open(path, "r") as fh:
        data = yaml.safe_load(fh) or {}
    cloud = data.get("clouds", {}).get(cloud_name)
    if not cloud:
        return {}
    return _normalise_clouds_yaml(cloud)


def _normalise_clouds_yaml(cloud: Dict[str, Any]) -> Dict[str, Any]:
    """Map clouds.yaml structure to flat orca config keys."""
    auth = cloud.get("auth", {})
    cfg: Dict[str, Any] = {}

    cfg["auth_url"] = auth.get("auth_url", "")
    cfg["username"] = auth.get("username", "")
    cfg["password"] = auth.get("password", "")

    # Domain: user_domain_name / user_domain_id / domain_name
    if auth.get("user_domain_name"):
        cfg["user_domain_name"] = auth["user_domain_name"]
    elif auth.get("user_domain_id"):
        cfg["user_domain_id"] = auth["user_domain_id"]
    elif auth.get("domain_name"):
        cfg["user_domain_name"] = auth["domain_name"]
    elif auth.get("domain_id"):
        cfg["user_domain_id"] = auth["domain_id"]

    # Project domain
    if auth.get("project_domain_name"):
        cfg["project_domain_name"] = auth["project_domain_name"]
    elif auth.get("project_domain_id"):
        cfg["project_domain_id"] = auth["project_domain_id"]
    # Fall back to user domain for project domain if not specified
    elif cfg.get("user_domain_name"):
        cfg["project_domain_name"] = cfg["user_domain_name"]
    elif cfg.get("user_domain_id"):
        cfg["project_domain_id"] = cfg["user_domain_id"]

    # Project: project_name / project_id
    if auth.get("project_name"):
        cfg["project_name"] = auth["project_name"]
    elif auth.get("project_id"):
        cfg["project_id"] = auth["project_id"]

    # Extra fields
    if cloud.get("region_name"):
        cfg["region_name"] = cloud["region_name"]
    if cloud.get("interface"):
        cfg["interface"] = cloud["interface"]
    if cloud.get("cacert"):
        cfg["cacert"] = cloud["cacert"]
    if cloud.get("verify") is False:
        cfg["insecure"] = "true"

    return {k: v for k, v in cfg.items() if v}


# ── OS_* env var support ────────────────────────────────────────────────

def _load_os_env() -> Dict[str, Any]:
    """Collect config from standard ``OS_*`` environment variables."""
    cfg: Dict[str, Any] = {}
    for env_var, key in _OS_ENV_MAP.items():
        value = os.environ.get(env_var)
        if value:
            cfg[key] = value
    return cfg


def _has_os_env() -> bool:
    """Return True if any ``OS_*`` auth env vars are set."""
    return bool(os.environ.get("OS_AUTH_URL"))


# ── Public API (used by context.py / commands) ───────────────────────────

def load_config(profile_name: str | None = None) -> Dict[str, Any]:
    """Load the resolved config with full priority chain.

    Priority (first match wins):
      1. Orca profile (``--profile`` / ``ORCA_PROFILE`` / active) + ``ORCA_*`` overrides
      2. ``OS_*`` environment variables (standard OpenStack)
      3. ``OS_CLOUD`` → ``clouds.yaml``
      4. Active orca profile (fallback)

    If ``profile_name`` or ``ORCA_PROFILE`` is explicitly set, only path 1 is used.
    """
    # ── Path 1: explicit orca profile requested ──
    explicit_orca = profile_name or os.environ.get("ORCA_PROFILE")
    if explicit_orca:
        name = get_active_profile_name(profile_name)
        config = dict(get_profile(name))
        _apply_orca_env(config)
        _normalise_legacy_keys(config)
        return config

    # ── Path 2: OS_* env vars ──
    if _has_os_env():
        config = _load_os_env()
        # Also overlay ORCA_* for power users mixing both
        _apply_orca_env(config)
        return config

    # ── Path 3: OS_CLOUD → clouds.yaml ──
    os_cloud = os.environ.get("OS_CLOUD")
    if os_cloud:
        config = _load_clouds_yaml(os_cloud)
        if config:
            _apply_orca_env(config)
            return config

    # ── Path 4: fallback to active orca profile ──
    name = get_active_profile_name(None)
    config = dict(get_profile(name))
    _apply_orca_env(config)
    _normalise_legacy_keys(config)
    return config


def _apply_orca_env(config: Dict[str, Any]) -> None:
    """Overlay ``ORCA_*`` env vars onto *config* in-place."""
    for env_var, key in _ORCA_ENV_MAP.items():
        value = os.environ.get(env_var)
        if value:
            config[key] = value


def _normalise_legacy_keys(config: Dict[str, Any]) -> None:
    """Map legacy orca config keys (``domain_id``, ``project_id``) to the
    canonical name-based fields when the new keys are absent.

    Legacy orca profiles stored the domain *name* under ``domain_id`` and the
    project *name* under ``project_id``.  This helper ensures those values are
    available under the correct canonical keys so the client can build the
    right auth payload.
    """
    if not config.get("user_domain_name") and not config.get("user_domain_id"):
        if config.get("domain_id"):
            config["user_domain_name"] = config["domain_id"]
    if not config.get("project_domain_name") and not config.get("project_domain_id"):
        if config.get("domain_id"):
            config["project_domain_name"] = config["domain_id"]
    if not config.get("project_name") and config.get("project_id"):
        # Legacy profiles stored the project *name* under "project_id".
        # Copy it to project_name so the client can use name-based scoping.
        config["project_name"] = config["project_id"]

    # Legacy keys (domain_id, project_id) were actually names, not UUIDs.
    # Remove them so the client doesn't mistakenly use ID-based scoping.
    if config.get("domain_id"):
        config.pop("domain_id", None)
    if config.get("project_id") and config.get("project_name") == config.get("project_id"):
        config.pop("project_id", None)


def config_is_complete(config: Optional[Dict[str, Any]] = None) -> bool:
    """Return ``True`` if all required credentials are present."""
    if config is None:
        config = load_config()
    if not all(config.get(k) for k in REQUIRED_KEYS):
        return False
    has_domain = any(config.get(k) for k in _DOMAIN_KEYS)
    has_project = any(config.get(k) for k in _PROJECT_KEYS)
    return has_domain and has_project


# Legacy compat
def save_config(data: Dict[str, Any]) -> Path:
    """Save to the active profile (backwards compatible)."""
    raw = _ensure_structure(_load_raw())
    name = raw.get("active_profile", DEFAULT_PROFILE)
    return save_profile(name, data)
