"""Tests for orca_cli.core.config — multi-profile, clouds.yaml, OS_* env vars."""

from __future__ import annotations

import pytest
import yaml

from orca_cli.core.config import (
    _has_os_env,
    _load_os_env,
    _normalise_clouds_yaml,
    _normalise_legacy_keys,
    config_is_complete,
    delete_profile,
    get_active_profile_name,
    get_profile,
    list_profiles,
    load_config,
    rename_profile,
    save_profile,
    set_active_profile,
)

# ── Profile CRUD ────────────────────────────────────────────────────────

class TestProfileCRUD:

    def test_save_and_get_profile(self, config_dir, sample_profile):
        save_profile("prod", sample_profile)
        assert get_profile("prod") == sample_profile

    def test_list_profiles(self, config_dir, sample_profile):
        save_profile("prod", sample_profile)
        save_profile("staging", {**sample_profile, "username": "staging-user"})
        profiles = list_profiles()
        assert "prod" in profiles
        assert "staging" in profiles
        assert profiles["staging"]["username"] == "staging-user"

    def test_first_profile_becomes_active(self, config_dir, sample_profile):
        save_profile("prod", sample_profile)
        assert get_active_profile_name() == "prod"

    def test_set_active_profile(self, config_dir, sample_profile):
        save_profile("prod", sample_profile)
        save_profile("staging", sample_profile)
        set_active_profile("staging")
        assert get_active_profile_name() == "staging"

    def test_set_active_nonexistent_raises(self, config_dir, sample_profile):
        save_profile("prod", sample_profile)
        with pytest.raises(KeyError, match="nope"):
            set_active_profile("nope")

    def test_delete_profile(self, config_dir, sample_profile):
        save_profile("prod", sample_profile)
        save_profile("staging", sample_profile)
        set_active_profile("prod")
        delete_profile("staging")
        assert "staging" not in list_profiles()

    def test_delete_active_raises(self, config_dir, sample_profile):
        save_profile("prod", sample_profile)
        set_active_profile("prod")
        with pytest.raises(ValueError, match="Cannot delete the active"):
            delete_profile("prod")

    def test_rename_profile(self, config_dir, sample_profile):
        save_profile("old", sample_profile)
        set_active_profile("old")
        rename_profile("old", "new")
        assert "new" in list_profiles()
        assert "old" not in list_profiles()
        assert get_active_profile_name() == "new"

    def test_rename_to_existing_raises(self, config_dir, sample_profile):
        save_profile("a", sample_profile)
        save_profile("b", sample_profile)
        with pytest.raises(ValueError, match="already exists"):
            rename_profile("a", "b")

    def test_get_nonexistent_profile_returns_empty(self, config_dir):
        assert get_profile("nope") == {}


# ── Legacy migration ────────────────────────────────────────────────────

class TestLegacyMigration:

    def test_legacy_flat_config_migrated(self, config_dir, write_config, legacy_profile):
        write_config(legacy_profile)
        profiles = list_profiles()
        assert "default" in profiles
        assert profiles["default"]["auth_url"] == legacy_profile["auth_url"]

    def test_normalise_legacy_keys_domain(self):
        cfg = {"domain_id": "MyDomain", "project_id": "my-proj"}
        _normalise_legacy_keys(cfg)
        assert cfg["user_domain_name"] == "MyDomain"
        assert cfg["project_domain_name"] == "MyDomain"
        assert cfg["project_name"] == "my-proj"
        # Legacy keys are removed to avoid ID-based scoping confusion
        assert "domain_id" not in cfg
        assert "project_id" not in cfg

    def test_normalise_legacy_keys_no_overwrite(self):
        cfg = {
            "domain_id": "OldDomain",
            "user_domain_name": "NewDomain",
            "project_name": "explicit",
        }
        _normalise_legacy_keys(cfg)
        assert cfg["user_domain_name"] == "NewDomain"
        assert cfg["project_name"] == "explicit"


# ── config_is_complete ──────────────────────────────────────────────────

class TestConfigIsComplete:

    def test_complete_with_names(self, sample_profile):
        assert config_is_complete(sample_profile) is True

    def test_complete_with_ids(self):
        cfg = {
            "auth_url": "https://ks:5000",
            "username": "u",
            "password": "p",
            "user_domain_id": "did",
            "project_id": "pid",
        }
        assert config_is_complete(cfg) is True

    def test_incomplete_no_password(self, sample_profile):
        del sample_profile["password"]
        assert config_is_complete(sample_profile) is False

    def test_incomplete_no_domain(self):
        cfg = {
            "auth_url": "https://ks:5000",
            "username": "u",
            "password": "p",
            "project_name": "proj",
        }
        assert config_is_complete(cfg) is False

    def test_incomplete_no_project(self):
        cfg = {
            "auth_url": "https://ks:5000",
            "username": "u",
            "password": "p",
            "user_domain_name": "Default",
        }
        assert config_is_complete(cfg) is False


# ── clouds.yaml ─────────────────────────────────────────────────────────

class TestCloudsYaml:

    def test_normalise_clouds_yaml_names(self):
        cloud = {
            "auth": {
                "auth_url": "https://ks:5000",
                "username": "admin",
                "password": "secret",
                "user_domain_name": "Default",
                "project_domain_name": "Default",
                "project_name": "demo",
            },
            "region_name": "RegionOne",
            "interface": "internal",
        }
        cfg = _normalise_clouds_yaml(cloud)
        assert cfg["auth_url"] == "https://ks:5000"
        assert cfg["username"] == "admin"
        assert cfg["user_domain_name"] == "Default"
        assert cfg["project_domain_name"] == "Default"
        assert cfg["project_name"] == "demo"
        assert cfg["region_name"] == "RegionOne"
        assert cfg["interface"] == "internal"

    def test_normalise_clouds_yaml_ids(self):
        cloud = {
            "auth": {
                "auth_url": "https://ks:5000",
                "username": "admin",
                "password": "secret",
                "user_domain_id": "abc123",
                "project_id": "proj-uuid",
            },
        }
        cfg = _normalise_clouds_yaml(cloud)
        assert cfg["user_domain_id"] == "abc123"
        assert cfg["project_domain_id"] == "abc123"  # fallback
        assert cfg["project_id"] == "proj-uuid"

    def test_normalise_clouds_yaml_domain_fallback(self):
        cloud = {
            "auth": {
                "auth_url": "https://ks:5000",
                "username": "admin",
                "password": "secret",
                "domain_name": "FallbackDomain",
                "project_name": "demo",
            },
        }
        cfg = _normalise_clouds_yaml(cloud)
        assert cfg["user_domain_name"] == "FallbackDomain"
        assert cfg["project_domain_name"] == "FallbackDomain"

    def test_normalise_clouds_yaml_verify_false(self):
        cloud = {
            "auth": {"auth_url": "x", "username": "u", "password": "p",
                     "user_domain_name": "D", "project_name": "P"},
            "verify": False,
        }
        cfg = _normalise_clouds_yaml(cloud)
        assert cfg["insecure"] == "true"

    def test_normalise_clouds_yaml_cacert(self):
        cloud = {
            "auth": {"auth_url": "x", "username": "u", "password": "p",
                     "user_domain_name": "D", "project_name": "P"},
            "cacert": "/path/to/ca.pem",
        }
        cfg = _normalise_clouds_yaml(cloud)
        assert cfg["cacert"] == "/path/to/ca.pem"

    def test_load_config_via_os_cloud(self, monkeypatch, config_dir, tmp_path):
        clouds_data = {
            "clouds": {
                "mycloud": {
                    "auth": {
                        "auth_url": "https://cloud-ks:5000",
                        "username": "cloud-user",
                        "password": "cloud-pass",
                        "user_domain_name": "Default",
                        "project_name": "cloud-proj",
                    }
                }
            }
        }
        clouds_path = tmp_path / "clouds.yaml"
        with open(clouds_path, "w") as fh:
            yaml.dump(clouds_data, fh)

        monkeypatch.setattr("orca_cli.core.config._CLOUDS_YAML_PATHS", [clouds_path])
        monkeypatch.setenv("OS_CLOUD", "mycloud")

        cfg = load_config()
        assert cfg["auth_url"] == "https://cloud-ks:5000"
        assert cfg["username"] == "cloud-user"
        assert cfg["project_name"] == "cloud-proj"


# ── OS_* env vars ───────────────────────────────────────────────────────

class TestOSEnvVars:

    def test_load_os_env(self, monkeypatch):
        monkeypatch.setenv("OS_AUTH_URL", "https://env-ks:5000")
        monkeypatch.setenv("OS_USERNAME", "env-user")
        monkeypatch.setenv("OS_PASSWORD", "env-pass")
        monkeypatch.setenv("OS_USER_DOMAIN_NAME", "EnvDomain")
        monkeypatch.setenv("OS_PROJECT_NAME", "env-proj")
        cfg = _load_os_env()
        assert cfg["auth_url"] == "https://env-ks:5000"
        assert cfg["username"] == "env-user"
        assert cfg["user_domain_name"] == "EnvDomain"
        assert cfg["project_name"] == "env-proj"

    def test_has_os_env_true(self, monkeypatch):
        monkeypatch.setenv("OS_AUTH_URL", "https://x")
        assert _has_os_env() is True

    def test_has_os_env_false(self):
        assert _has_os_env() is False

    def test_os_env_takes_priority_over_orca_profile(self, monkeypatch, config_dir, sample_profile):
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        monkeypatch.setenv("OS_AUTH_URL", "https://os-env:5000")
        monkeypatch.setenv("OS_USERNAME", "os-user")
        monkeypatch.setenv("OS_PASSWORD", "os-pass")
        monkeypatch.setenv("OS_USER_DOMAIN_NAME", "OS-Domain")
        monkeypatch.setenv("OS_PROJECT_NAME", "os-proj")

        cfg = load_config()
        assert cfg["auth_url"] == "https://os-env:5000"
        assert cfg["username"] == "os-user"

    def test_explicit_profile_overrides_os_env(self, monkeypatch, config_dir, sample_profile):
        save_profile("prod", sample_profile)

        monkeypatch.setenv("OS_AUTH_URL", "https://os-env:5000")
        monkeypatch.setenv("OS_USERNAME", "os-user")

        cfg = load_config(profile_name="prod")
        assert cfg["auth_url"] == sample_profile["auth_url"]
        assert cfg["username"] == sample_profile["username"]

    def test_orca_env_overlays_os_env(self, monkeypatch, config_dir):
        monkeypatch.setenv("OS_AUTH_URL", "https://os:5000")
        monkeypatch.setenv("OS_USERNAME", "os-user")
        monkeypatch.setenv("OS_PASSWORD", "os-pass")
        monkeypatch.setenv("OS_USER_DOMAIN_NAME", "D")
        monkeypatch.setenv("OS_PROJECT_NAME", "P")

        monkeypatch.setenv("ORCA_USERNAME", "orca-override")

        cfg = load_config()
        assert cfg["auth_url"] == "https://os:5000"
        assert cfg["username"] == "orca-override"  # ORCA_* wins


# ── load_config priority chain ──────────────────────────────────────────

class TestLoadConfigPriority:

    def test_path4_fallback_to_orca_profile(self, config_dir, sample_profile):
        """No OS_* or OS_CLOUD → falls back to orca active profile."""
        save_profile("default", sample_profile)
        cfg = load_config()
        assert cfg["auth_url"] == sample_profile["auth_url"]

    def test_path1_orca_profile_flag(self, config_dir, sample_profile):
        other = {**sample_profile, "username": "other-user"}
        save_profile("default", sample_profile)
        save_profile("other", other)
        cfg = load_config(profile_name="other")
        assert cfg["username"] == "other-user"

    def test_path3_os_cloud(self, monkeypatch, config_dir, tmp_path):
        clouds = {
            "clouds": {
                "test": {
                    "auth": {
                        "auth_url": "https://cloud:5000",
                        "username": "cuser",
                        "password": "cpass",
                        "user_domain_name": "D",
                        "project_name": "P",
                    }
                }
            }
        }
        p = tmp_path / "clouds.yaml"
        with open(p, "w") as fh:
            yaml.dump(clouds, fh)
        monkeypatch.setattr("orca_cli.core.config._CLOUDS_YAML_PATHS", [p])
        monkeypatch.setenv("OS_CLOUD", "test")

        cfg = load_config()
        assert cfg["username"] == "cuser"

    def test_os_env_beats_os_cloud(self, monkeypatch, config_dir, tmp_path):
        """OS_* env vars (path 2) should win over OS_CLOUD (path 3)."""
        clouds = {
            "clouds": {
                "test": {
                    "auth": {
                        "auth_url": "https://cloud:5000",
                        "username": "cloud-user",
                        "password": "p",
                        "user_domain_name": "D",
                        "project_name": "P",
                    }
                }
            }
        }
        p = tmp_path / "clouds.yaml"
        with open(p, "w") as fh:
            yaml.dump(clouds, fh)
        monkeypatch.setattr("orca_cli.core.config._CLOUDS_YAML_PATHS", [p])
        monkeypatch.setenv("OS_CLOUD", "test")

        monkeypatch.setenv("OS_AUTH_URL", "https://env:5000")
        monkeypatch.setenv("OS_USERNAME", "env-user")
        monkeypatch.setenv("OS_PASSWORD", "env-pass")
        monkeypatch.setenv("OS_USER_DOMAIN_NAME", "D")
        monkeypatch.setenv("OS_PROJECT_NAME", "P")

        cfg = load_config()
        assert cfg["username"] == "env-user"  # OS_* wins


# ── Edge cases & error paths ─────────────────────────────────────────────

class TestConfigEdgeCases:

    def test_get_active_profile_env_override(self, config_dir, sample_profile, monkeypatch):
        """ORCA_PROFILE env var takes precedence over config file active_profile."""
        save_profile("prod", sample_profile)
        save_profile("staging", sample_profile)
        monkeypatch.setenv("ORCA_PROFILE", "staging")
        assert get_active_profile_name() == "staging"

    def test_config_is_complete_loads_when_no_arg(self, config_dir, sample_profile):
        """Passing None triggers an internal load_config() call."""
        save_profile("prod", sample_profile)
        assert config_is_complete() is True

    def test_save_legacy_config_hits_active(self, config_dir, sample_profile):
        """Legacy save_config() writes to the active profile."""
        from orca_cli.core.config import save_config
        save_profile("prod", sample_profile)
        save_config({**sample_profile, "username": "renamed"})
        assert get_profile("prod")["username"] == "renamed"

    def test_find_clouds_yaml_none(self, monkeypatch, tmp_path):
        """No clouds.yaml on disk → returns None."""
        from orca_cli.core.config import _find_clouds_yaml
        monkeypatch.setattr(
            "orca_cli.core.config._CLOUDS_YAML_PATHS",
            [tmp_path / "missing.yaml"],
        )
        assert _find_clouds_yaml() is None

    def test_load_clouds_yaml_missing_file_returns_empty(self, monkeypatch, tmp_path):
        """No clouds.yaml anywhere → empty dict, not a crash."""
        from orca_cli.core.config import _load_clouds_yaml
        monkeypatch.setattr(
            "orca_cli.core.config._CLOUDS_YAML_PATHS",
            [tmp_path / "missing.yaml"],
        )
        assert _load_clouds_yaml("anycloud") == {}

    def test_load_clouds_yaml_unknown_cloud_returns_empty(self, monkeypatch, tmp_path):
        """File exists but cloud name not found → empty dict."""
        p = tmp_path / "clouds.yaml"
        p.write_text(yaml.dump({"clouds": {"other": {"auth": {"auth_url": "x"}}}}))
        monkeypatch.setattr("orca_cli.core.config._CLOUDS_YAML_PATHS", [p])
        from orca_cli.core.config import _load_clouds_yaml
        assert _load_clouds_yaml("nope") == {}


class TestCloudsYamlNormalisation:
    """Cover fallback branches in _normalise_clouds_yaml."""

    def test_user_domain_id_only(self):
        cfg = _normalise_clouds_yaml({"auth": {
            "auth_url": "x", "username": "u", "password": "p",
            "user_domain_id": "did",
            "project_name": "proj",
        }})
        assert cfg["user_domain_id"] == "did"

    def test_domain_name_falls_back_to_user_domain_name(self):
        """domain_name (no user_ prefix) is mapped to user_domain_name."""
        cfg = _normalise_clouds_yaml({"auth": {
            "auth_url": "x", "username": "u", "password": "p",
            "domain_name": "Default",
            "project_name": "proj",
        }})
        assert cfg["user_domain_name"] == "Default"

    def test_domain_id_falls_back_to_user_domain_id(self):
        cfg = _normalise_clouds_yaml({"auth": {
            "auth_url": "x", "username": "u", "password": "p",
            "domain_id": "did",
            "project_name": "proj",
        }})
        assert cfg["user_domain_id"] == "did"

    def test_project_domain_id_explicit(self):
        cfg = _normalise_clouds_yaml({"auth": {
            "auth_url": "x", "username": "u", "password": "p",
            "user_domain_name": "Default",
            "project_domain_id": "pdid",
            "project_name": "proj",
        }})
        assert cfg["project_domain_id"] == "pdid"

    def test_project_domain_falls_back_to_user_domain_id(self):
        """When only user_domain_id is set, project domain inherits by id."""
        cfg = _normalise_clouds_yaml({"auth": {
            "auth_url": "x", "username": "u", "password": "p",
            "user_domain_id": "did",
            "project_name": "proj",
        }})
        assert cfg["project_domain_id"] == "did"
