"""Tests for ``orca setup`` — interactive profile wizard."""

from __future__ import annotations

import yaml

# ══════════════════════════════════════════════════════════════════════════
#  Help
# ══════════════════════════════════════════════════════════════════════════


class TestSetupHelp:

    def test_setup_help(self, invoke):
        result = invoke(["setup", "--help"])
        assert result.exit_code == 0
        assert "--profile" in result.output
        assert "credentials" in result.output.lower()


# ══════════════════════════════════════════════════════════════════════════
#  New profile — no other profiles exist → auto-activates
# ══════════════════════════════════════════════════════════════════════════


def _full_answers(
    auth_url="https://keystone.foo:5000",
    username="alice",
    password="s3cret",
    user_domain_name="Default",
    project_name="proj",
    region_name="",
    insecure="true",
) -> str:
    """Build the newline-separated stdin for the 7 prompt fields.

    Password is hidden + confirmation_prompt → user types it twice.
    """
    return "\n".join([
        auth_url,
        username,
        password, password,  # confirmation
        user_domain_name,
        project_name,
        region_name,
        insecure,
    ]) + "\n"


class TestSetupNewProfileNoExisting:
    """First-time setup: no profiles on disk → new profile becomes active."""

    def test_creates_and_auto_activates(self, invoke, config_dir):
        stdin = _full_answers(username="alice", password="s3cret", project_name="proj")
        result = invoke(["setup", "--profile", "first"], input=stdin)

        assert result.exit_code == 0, result.output
        assert "new profile: first" in result.output
        assert "saved" in result.output.lower()
        assert "active profile" in result.output.lower()

        # Verify persisted to disk
        with open(config_dir / "config.yaml") as fh:
            data = yaml.safe_load(fh)
        assert data["active_profile"] == "first"
        assert data["profiles"]["first"]["username"] == "alice"
        assert data["profiles"]["first"]["project_name"] == "proj"
        # region_name was empty → omitted
        assert "region_name" not in data["profiles"]["first"]


# ══════════════════════════════════════════════════════════════════════════
#  New profile — other profiles exist → asks "Switch to X now?"
# ══════════════════════════════════════════════════════════════════════════


class TestSetupNewProfileWithOthers:

    def test_switch_yes(self, invoke, write_config, sample_profile):
        write_config({
            "active_profile": "existing",
            "profiles": {"existing": sample_profile},
        })
        # Full answers + "y" for switch prompt
        stdin = _full_answers(username="bob", password="p", project_name="p2") + "y\n"
        result = invoke(["setup", "--profile", "newprof"], input=stdin)
        assert result.exit_code == 0, result.output
        assert "Switched to 'newprof'" in result.output

    def test_switch_no(self, invoke, write_config, sample_profile, config_dir):
        write_config({
            "active_profile": "existing",
            "profiles": {"existing": sample_profile},
        })
        stdin = _full_answers(username="bob", password="p", project_name="p2") + "n\n"
        result = invoke(["setup", "--profile", "newprof"], input=stdin)
        assert result.exit_code == 0, result.output
        # Profile saved, but not active
        with open(config_dir / "config.yaml") as fh:
            data = yaml.safe_load(fh)
        assert "newprof" in data["profiles"]
        assert data["active_profile"] == "existing"


# ══════════════════════════════════════════════════════════════════════════
#  Edit existing profile — no switch prompt, pre-fills defaults
# ══════════════════════════════════════════════════════════════════════════


class TestSetupEditExisting:

    def test_edit_keeps_defaults(self, invoke, write_config, sample_profile, config_dir):
        write_config({
            "active_profile": "prod",
            "profiles": {"prod": sample_profile},
        })
        # Accept every default by pressing enter for non-password fields;
        # but password has no default (it's hidden) so we must type it.
        stdin = "\n".join([
            "",               # auth_url → accept default
            "",               # username → accept default
            "secret", "secret",  # password (retyped — no default stored in prompt)
            "",               # user_domain_name → accept
            "",               # project_name → accept
            "",               # region_name → skip
            "",               # insecure → accept
        ]) + "\n"

        result = invoke(["setup", "--profile", "prod"], input=stdin)
        assert result.exit_code == 0, result.output
        assert "editing profile: prod" in result.output
        # No switch prompt when editing
        assert "Switch to" not in result.output

    def test_edit_legacy_profile_falls_back_to_domain_id(
        self, invoke, write_config, legacy_profile, config_dir
    ):
        """Editing a legacy profile: user_domain_name is empty → default pulled from domain_id."""
        write_config({
            "active_profile": "legacy",
            "profiles": {"legacy": legacy_profile},
        })
        stdin = "\n".join([
            "",                         # auth_url
            "",                         # username
            "secret", "secret",         # password
            "",                         # user_domain_name → takes domain_id fallback
            "",                         # project_name → takes project_id fallback
            "",                         # region_name
            "",                         # insecure
        ]) + "\n"

        result = invoke(["setup", "--profile", "legacy"], input=stdin)
        assert result.exit_code == 0, result.output

        with open(config_dir / "config.yaml") as fh:
            data = yaml.safe_load(fh)
        saved = data["profiles"]["legacy"]
        # Fallback kicked in
        assert saved.get("user_domain_name") == legacy_profile["domain_id"]
        assert saved.get("project_name") == legacy_profile["project_id"]


# ══════════════════════════════════════════════════════════════════════════
#  Default profile resolution — when --profile is omitted, uses active
# ══════════════════════════════════════════════════════════════════════════


class TestSetupDefaultProfileResolution:

    def test_no_profile_flag_uses_active(self, invoke, write_config, sample_profile):
        write_config({
            "active_profile": "active-one",
            "profiles": {"active-one": sample_profile},
        })
        stdin = "\n".join([
            "", "",  # auth_url, username
            "secret", "secret",  # password
            "", "", "", "",      # domain, project, region, insecure
        ]) + "\n"
        result = invoke(["setup"], input=stdin)
        assert result.exit_code == 0, result.output
        assert "editing profile: active-one" in result.output
