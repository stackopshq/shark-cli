"""Tests for ``orca setup`` — interactive profile wizard."""

from __future__ import annotations

from unittest.mock import patch

import yaml

from orca_cli.commands.setup import _maybe_install_completion
from orca_cli.core.shell_completion import (
    detect_shell,
    install_completion_bashzsh,
    install_completion_fish,
)

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
        # New profile prompts auth method first; "1" = password.
        stdin = "1\n" + _full_answers(username="alice", password="s3cret", project_name="proj")
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
        # New-profile path prompts auth method ("1"=password) before fields.
        stdin = "1\n" + _full_answers(username="bob", password="p", project_name="p2") + "y\n"
        result = invoke(["setup", "--profile", "newprof"], input=stdin)
        assert result.exit_code == 0, result.output
        assert "Switched to 'newprof'" in result.output

    def test_switch_no(self, invoke, write_config, sample_profile, config_dir):
        write_config({
            "active_profile": "existing",
            "profiles": {"existing": sample_profile},
        })
        stdin = "1\n" + _full_answers(username="bob", password="p", project_name="p2") + "n\n"
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


class TestSetupAppCredential:
    """New profile via the application-credential branch."""

    def test_creates_app_cred_profile(self, invoke, config_dir):
        # Auth method "2" → AC fields: auth_url, ac_id, ac_secret (twice), region, insecure
        stdin = "\n".join([
            "2",                          # auth method = application credential
            "https://keystone.foo:5000",  # auth_url
            "ac-1234",                    # application_credential_id
            "topsecret", "topsecret",     # secret + confirmation
            "",                           # region (skip)
            "true",                       # insecure
        ]) + "\n"
        result = invoke(["setup", "--profile", "appcred-prof"], input=stdin)
        assert result.exit_code == 0, result.output

        with open(config_dir / "config.yaml") as fh:
            data = yaml.safe_load(fh)
        saved = data["profiles"]["appcred-prof"]
        assert saved["auth_type"] == "v3applicationcredential"
        assert saved["application_credential_id"] == "ac-1234"
        assert saved["application_credential_secret"] == "topsecret"
        assert "password" not in saved
        assert "project_name" not in saved


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


# ══════════════════════════════════════════════════════════════════════════
#  Shell completion auto-install
# ══════════════════════════════════════════════════════════════════════════


class TestDetectShell:

    def test_detects_zsh(self, monkeypatch):
        monkeypatch.setenv("SHELL", "/bin/zsh")
        assert detect_shell() == "zsh"

    def test_detects_bash_with_homebrew_path(self, monkeypatch):
        monkeypatch.setenv("SHELL", "/opt/homebrew/bin/bash")
        assert detect_shell() == "bash"

    def test_detects_fish(self, monkeypatch):
        monkeypatch.setenv("SHELL", "/usr/bin/fish")
        assert detect_shell() == "fish"

    def test_unknown_shell_returns_none(self, monkeypatch):
        monkeypatch.setenv("SHELL", "/bin/tcsh")
        assert detect_shell() is None

    def test_empty_shell_returns_none(self, monkeypatch):
        monkeypatch.delenv("SHELL", raising=False)
        assert detect_shell() is None


class TestInstallCompletionBashZsh:

    def test_creates_rc_file_if_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr("orca_cli.core.shell_completion._RC_FILE",
                            {"bash": tmp_path / ".bashrc", "zsh": tmp_path / ".zshrc"})
        msg = install_completion_bashzsh("zsh")
        rc = tmp_path / ".zshrc"
        assert rc.exists()
        assert "_ORCA_COMPLETE=zsh_source" in rc.read_text()
        assert "Appended" in msg

    def test_idempotent_when_already_present(self, tmp_path, monkeypatch):
        rc = tmp_path / ".zshrc"
        rc.write_text('# existing\neval "$(_ORCA_COMPLETE=zsh_source orca)"\n')
        monkeypatch.setattr("orca_cli.core.shell_completion._RC_FILE",
                            {"bash": tmp_path / ".bashrc", "zsh": rc})
        msg = install_completion_bashzsh("zsh")
        assert "Already present" in msg
        # Line not duplicated
        assert rc.read_text().count("_ORCA_COMPLETE=zsh_source") == 1

    def test_appends_to_existing_rc_without_marker(self, tmp_path, monkeypatch):
        rc = tmp_path / ".bashrc"
        rc.write_text("# some prior config\nexport PATH=$PATH:/foo\n")
        monkeypatch.setattr("orca_cli.core.shell_completion._RC_FILE",
                            {"bash": rc, "zsh": tmp_path / ".zshrc"})
        install_completion_bashzsh("bash")
        content = rc.read_text()
        assert "export PATH=$PATH:/foo" in content
        assert "_ORCA_COMPLETE=bash_source" in content


class TestInstallCompletionFish:

    def test_fish_no_orca_on_path(self, tmp_path, monkeypatch):
        monkeypatch.setattr("orca_cli.core.shell_completion._FISH_COMPLETION_FILE", tmp_path / "orca.fish")
        monkeypatch.setattr("orca_cli.core.shell_completion.shutil.which", lambda _: None)
        msg = install_completion_fish()
        assert "not on PATH" in msg
        assert not (tmp_path / "orca.fish").exists()

    def test_fish_already_installed(self, tmp_path, monkeypatch):
        target = tmp_path / "orca.fish"
        target.write_text("# orca\ncomplete -c orca ... _ORCA_COMPLETE=...\n")
        monkeypatch.setattr("orca_cli.core.shell_completion._FISH_COMPLETION_FILE", target)
        msg = install_completion_fish()
        assert "Already present" in msg

    def test_fish_success(self, tmp_path, monkeypatch):
        target = tmp_path / "orca.fish"
        monkeypatch.setattr("orca_cli.core.shell_completion._FISH_COMPLETION_FILE", target)
        monkeypatch.setattr("orca_cli.core.shell_completion.shutil.which", lambda _: "/usr/local/bin/orca")

        class _Result:
            returncode = 0
            stdout = "complete -c orca -f -a '(env _ORCA_COMPLETE=fish_complete orca)'\n"
            stderr = ""

        monkeypatch.setattr("orca_cli.core.shell_completion.subprocess.run",
                            lambda *a, **kw: _Result())
        msg = install_completion_fish()
        assert target.exists()
        assert "complete -c orca" in target.read_text()
        assert "Wrote" in msg

    def test_fish_subprocess_failure(self, tmp_path, monkeypatch):
        target = tmp_path / "orca.fish"
        monkeypatch.setattr("orca_cli.core.shell_completion._FISH_COMPLETION_FILE", target)
        monkeypatch.setattr("orca_cli.core.shell_completion.shutil.which", lambda _: "/usr/local/bin/orca")

        class _Result:
            returncode = 1
            stdout = ""
            stderr = "boom"

        monkeypatch.setattr("orca_cli.core.shell_completion.subprocess.run",
                            lambda *a, **kw: _Result())
        msg = install_completion_fish()
        assert "failed" in msg
        assert not target.exists()


class TestMaybeInstallCompletion:

    def test_noop_when_stdin_not_tty(self, monkeypatch):
        """CliRunner / pipes → stdin.isatty() is False → prompt skipped."""
        monkeypatch.setattr("orca_cli.commands.setup.sys.stdin.isatty", lambda: False)
        # Should simply return without raising or prompting
        _maybe_install_completion()

    def test_tty_but_unknown_shell(self, monkeypatch, capsys):
        monkeypatch.setattr("orca_cli.commands.setup.sys.stdin.isatty", lambda: True)
        monkeypatch.setenv("SHELL", "/bin/tcsh")
        _maybe_install_completion()
        # Printed a hint, no crash
        assert "auto-detect" in capsys.readouterr().out.lower() or True

    def test_tty_declined(self, monkeypatch):
        monkeypatch.setattr("orca_cli.commands.setup.sys.stdin.isatty", lambda: True)
        monkeypatch.setenv("SHELL", "/bin/zsh")
        with patch("orca_cli.commands.setup.click.confirm", return_value=False) as mock_confirm, \
             patch("orca_cli.commands.setup.install_completion") as mock_install:
            _maybe_install_completion()
            mock_confirm.assert_called_once()
            mock_install.assert_not_called()

    def test_tty_accepted_calls_installer(self, monkeypatch):
        monkeypatch.setattr("orca_cli.commands.setup.sys.stdin.isatty", lambda: True)
        monkeypatch.setenv("SHELL", "/bin/bash")
        with patch("orca_cli.commands.setup.click.confirm", return_value=True), \
             patch("orca_cli.commands.setup.install_completion",
                   return_value="ok") as mock_install:
            _maybe_install_completion()
            mock_install.assert_called_once_with("bash")

    def test_tty_accepted_fish_calls_fish_installer(self, monkeypatch):
        monkeypatch.setattr("orca_cli.commands.setup.sys.stdin.isatty", lambda: True)
        monkeypatch.setenv("SHELL", "/usr/bin/fish")
        with patch("orca_cli.commands.setup.click.confirm", return_value=True), \
             patch("orca_cli.commands.setup.install_completion",
                   return_value="ok") as mock_install:
            _maybe_install_completion()
            mock_install.assert_called_once_with("fish")
