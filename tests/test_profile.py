"""Tests for ``orca profile`` commands."""

from __future__ import annotations

from pathlib import Path

from orca_cli.core.config import get_active_profile_name, save_profile, set_active_profile

# ══════════════════════════════════════════════════════════════════════════
#  list
# ══════════════════════════════════════════════════════════════════════════


class TestProfileList:

    def test_list(self, invoke, config_dir, sample_profile):
        save_profile("prod", sample_profile)
        save_profile("staging", {**sample_profile, "project_name": "staging"})
        set_active_profile("prod")

        result = invoke(["profile", "list"])
        assert result.exit_code == 0
        assert "prod" in result.output
        assert "stag" in result.output

    def test_list_empty(self, invoke, config_dir):
        result = invoke(["profile", "list"])
        assert result.exit_code == 0
        assert "No profiles" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  show
# ══════════════════════════════════════════════════════════════════════════


class TestProfileShow:

    def test_show(self, invoke, config_dir, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")

        result = invoke(["profile", "show", "p"])
        assert result.exit_code == 0
        assert "auth_url" in result.output
        assert "password" in result.output

    def test_show_active(self, invoke, config_dir, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")

        result = invoke(["profile", "show"])
        assert result.exit_code == 0
        assert "p" in result.output

    def test_show_not_found(self, invoke, config_dir, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")

        result = invoke(["profile", "show", "nonexistent"])
        assert result.exit_code != 0
        assert "not found" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  switch
# ══════════════════════════════════════════════════════════════════════════


class TestProfileSwitch:

    def test_switch(self, invoke, config_dir, sample_profile):
        save_profile("a", sample_profile)
        save_profile("b", {**sample_profile, "project_name": "b-proj"})
        set_active_profile("a")

        result = invoke(["profile", "switch", "b"])
        assert result.exit_code == 0
        assert "switched" in result.output.lower()

    def test_switch_not_found(self, invoke, config_dir, sample_profile):
        save_profile("a", sample_profile)
        set_active_profile("a")

        result = invoke(["profile", "switch", "nope"])
        assert result.exit_code != 0
        assert "not found" in result.output.lower()

    # ── Interactive wizard (no NAME argument) ──────────────────────────

    def test_interactive_switches_to_selected(self, invoke, config_dir, sample_profile):
        """Choosing profile 2 in the menu switches to it."""
        save_profile("alpha", sample_profile)
        save_profile("beta", {**sample_profile, "project_name": "beta-proj"})
        set_active_profile("alpha")

        # Items are sorted alphabetically: 1=alpha, 2=beta → pick 2
        result = invoke(["profile", "switch"], input="2\n")
        assert result.exit_code == 0
        assert "beta" in result.output.lower() or "switched" in result.output.lower()
        assert get_active_profile_name() == "beta"

    def test_interactive_pick_first(self, invoke, config_dir, sample_profile):
        save_profile("alpha", sample_profile)
        save_profile("beta", {**sample_profile, "project_name": "b"})
        set_active_profile("beta")

        result = invoke(["profile", "switch"], input="1\n")
        assert result.exit_code == 0
        assert get_active_profile_name() == "alpha"

    def test_interactive_shows_profile_names(self, invoke, config_dir, sample_profile):
        save_profile("production", sample_profile)
        save_profile("staging", {**sample_profile, "project_name": "stg"})

        result = invoke(["profile", "switch"], input="1\n")
        assert result.exit_code == 0
        assert "production" in result.output
        assert "staging" in result.output

    def test_interactive_shows_project(self, invoke, config_dir, sample_profile):
        save_profile("prod", {**sample_profile, "project_name": "my-project"})

        result = invoke(["profile", "switch"], input="1\n")
        assert result.exit_code == 0
        assert "my-project" in result.output

    def test_interactive_shows_username(self, invoke, config_dir, sample_profile):
        save_profile("prod", {**sample_profile, "username": "kevin"})

        result = invoke(["profile", "switch"], input="1\n")
        assert result.exit_code == 0
        assert "kevin" in result.output

    def test_interactive_no_profiles_raises(self, invoke, config_dir):
        result = invoke(["profile", "switch"])
        assert result.exit_code != 0
        assert "no profiles" in result.output.lower()

    def test_interactive_active_profile_shown(self, invoke, config_dir, sample_profile):
        """The currently active profile should be marked in the menu."""
        save_profile("alpha", sample_profile)
        save_profile("beta", {**sample_profile, "project_name": "b"})
        set_active_profile("alpha")

        result = invoke(["profile", "switch"], input="1\n")
        # Active marker ● should appear
        assert "●" in result.output

    def test_help_shows_interactive_hint(self, invoke):
        result = invoke(["profile", "switch", "--help"])
        assert result.exit_code == 0
        assert "interactive" in result.output.lower() or "menu" in result.output.lower()


# ══════════════════════════════════════════════════════════════════════════
#  set-color
# ══════════════════════════════════════════════════════════════════════════


class TestProfileSetColor:

    def test_set_color(self, invoke, config_dir, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")

        result = invoke(["profile", "set-color", "red"])
        assert result.exit_code == 0
        assert "Color set" in result.output

    def test_remove_color(self, invoke, config_dir, sample_profile):
        cfg = {**sample_profile, "color": "blue"}
        save_profile("p", cfg)
        set_active_profile("p")

        result = invoke(["profile", "set-color", "none"])
        assert result.exit_code == 0
        assert "removed" in result.output.lower()

    def test_set_color_not_found(self, invoke, config_dir):
        result = invoke(["profile", "set-color", "red", "nope"])
        assert result.exit_code != 0


# ══════════════════════════════════════════════════════════════════════════
#  remove
# ══════════════════════════════════════════════════════════════════════════


class TestProfileRemove:

    def test_remove(self, invoke, config_dir, sample_profile):
        save_profile("p", sample_profile)
        save_profile("q", sample_profile)
        set_active_profile("q")

        result = invoke(["profile", "remove", "p", "-y"])
        assert result.exit_code == 0
        assert "removed" in result.output.lower()

    def test_remove_not_found(self, invoke, config_dir, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")

        result = invoke(["profile", "remove", "nope", "-y"])
        assert result.exit_code != 0
        assert "not found" in result.output.lower()


# ══════════════════════════════════════════════════════════════════════════
#  rename
# ══════════════════════════════════════════════════════════════════════════


class TestProfileRename:

    def test_rename(self, invoke, config_dir, sample_profile):
        save_profile("old", sample_profile)
        set_active_profile("old")

        result = invoke(["profile", "rename", "old", "new"])
        assert result.exit_code == 0
        assert "renamed" in result.output.lower()

    def test_rename_not_found(self, invoke, config_dir, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")

        result = invoke(["profile", "rename", "nope", "new"])
        assert result.exit_code != 0


# ══════════════════════════════════════════════════════════════════════════
#  set-region
# ══════════════════════════════════════════════════════════════════════════


class TestProfileSetRegion:

    def test_set_region(self, invoke, config_dir, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")

        result = invoke(["profile", "set-region", "us-east-1"])
        assert result.exit_code == 0
        assert "us-east-1" in result.output

    def test_clear_region(self, invoke, config_dir, sample_profile):
        cfg = {**sample_profile, "region_name": "us-west-2"}
        save_profile("p", cfg)
        set_active_profile("p")

        result = invoke(["profile", "set-region", "none"])
        assert result.exit_code == 0
        assert "cleared" in result.output.lower()


# ══════════════════════════════════════════════════════════════════════════
#  to-openrc
# ══════════════════════════════════════════════════════════════════════════


class TestProfileToOpenrc:

    def test_to_openrc_stdout(self, invoke, config_dir, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")

        result = invoke(["profile", "to-openrc"])
        assert result.exit_code == 0
        assert "OS_AUTH_URL" in result.output
        assert "export" in result.output

    def test_to_openrc_file(self, invoke, config_dir, sample_profile, tmp_path):
        save_profile("p", sample_profile)
        set_active_profile("p")
        out = str(tmp_path / "openrc.sh")

        result = invoke(["profile", "to-openrc", "-o", out])
        assert result.exit_code == 0
        content = Path(out).read_text()
        assert "OS_AUTH_URL" in content


# ══════════════════════════════════════════════════════════════════════════
#  to-clouds
# ══════════════════════════════════════════════════════════════════════════


class TestProfileToClouds:

    def test_to_clouds_stdout(self, invoke, config_dir, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")

        result = invoke(["profile", "to-clouds"])
        assert result.exit_code == 0
        assert "clouds:" in result.output
        assert "auth_url" in result.output

    def test_to_clouds_file(self, invoke, config_dir, sample_profile, tmp_path):
        save_profile("p", sample_profile)
        set_active_profile("p")
        out = str(tmp_path / "clouds.yaml")

        result = invoke(["profile", "to-clouds", "-o", out])
        assert result.exit_code == 0
        content = Path(out).read_text()
        assert "clouds:" in content


# ══════════════════════════════════════════════════════════════════════════
#  Helpers: _shell_quote, _parse_openrc, _os_env_to_cfg, _cfg_to_os_env
# ══════════════════════════════════════════════════════════════════════════


class TestHelpers:

    def test_shell_quote_simple(self):
        from orca_cli.commands.profile import _shell_quote
        assert _shell_quote("hello") == "hello"

    def test_shell_quote_special(self):
        from orca_cli.commands.profile import _shell_quote
        result = _shell_quote("hello world")
        assert result.startswith("'")
        assert "hello world" in result

    def test_parse_openrc(self):
        from orca_cli.commands.profile import _parse_openrc
        content = (
            '# comment\n'
            'export OS_AUTH_URL=https://keystone:5000\n'
            'export OS_USERNAME="admin"\n'
            "export OS_PASSWORD='secret'\n"
        )
        env = _parse_openrc(content)
        assert env["OS_AUTH_URL"] == "https://keystone:5000"
        assert env["OS_USERNAME"] == "admin"
        assert env["OS_PASSWORD"] == "secret"

    def test_os_env_to_cfg(self):
        from orca_cli.commands.profile import _os_env_to_cfg
        env = {
            "OS_AUTH_URL": "https://keystone:5000",
            "OS_USERNAME": "admin",
            "OS_PASSWORD": "secret",
            "OS_PROJECT_NAME": "myproj",
            "OS_USER_DOMAIN_NAME": "Default",
        }
        cfg = _os_env_to_cfg(env)
        assert cfg["auth_url"] == "https://keystone:5000"
        assert cfg["username"] == "admin"
        assert cfg["project_name"] == "myproj"

    def test_cfg_to_os_env(self):
        from orca_cli.commands.profile import _cfg_to_os_env
        cfg = {
            "auth_url": "https://keystone:5000",
            "username": "admin",
            "password": "secret",
            "project_name": "myproj",
            "user_domain_name": "Default",
        }
        env = _cfg_to_os_env(cfg)
        assert env["OS_AUTH_URL"] == "https://keystone:5000"
        assert env["OS_USERNAME"] == "admin"
        assert env["OS_PROJECT_NAME"] == "myproj"
        assert env["OS_IDENTITY_API_VERSION"] == "3"


# ══════════════════════════════════════════════════════════════════════════
#  Help
# ══════════════════════════════════════════════════════════════════════════


class TestProfileHelp:

    def test_profile_help(self, invoke):
        result = invoke(["profile", "--help"])
        assert result.exit_code == 0
        for cmd in ("list", "show", "add", "edit", "switch", "remove",
                    "rename", "set-color", "set-region", "regions",
                    "to-openrc", "to-clouds", "from-openrc", "from-clouds"):
            assert cmd in result.output
