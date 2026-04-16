"""Tests for profile export/import — openrc and clouds.yaml conversions."""

from __future__ import annotations

from pathlib import Path

import yaml

from orca_cli.core.config import save_profile, set_active_profile


class TestToOpenrc:

    def test_export_active_profile(self, invoke, config_dir, sample_profile, mock_client):
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        result = invoke(["profile", "to-openrc"])
        assert result.exit_code == 0
        output = result.output
        assert "export OS_AUTH_URL=" in output
        assert sample_profile["auth_url"] in output
        assert "export OS_USERNAME=" in output
        assert sample_profile["username"] in output
        assert "export OS_USER_DOMAIN_NAME=" in output
        assert "export OS_IDENTITY_API_VERSION=3" in output

    def test_export_named_profile(self, invoke, config_dir, sample_profile, mock_client):
        save_profile("staging", {**sample_profile, "username": "stage-user"})
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        result = invoke(["profile", "to-openrc", "staging"])
        assert result.exit_code == 0
        assert "stage-user" in result.output

    def test_export_to_file(self, invoke, config_dir, sample_profile, mock_client, tmp_path):
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        outfile = str(tmp_path / "openrc.sh")
        result = invoke(["profile", "to-openrc", "-o", outfile])
        assert result.exit_code == 0
        content = Path(outfile).read_text()
        assert "export OS_AUTH_URL=" in content

    def test_export_includes_project_name(self, invoke, config_dir, sample_profile, mock_client):
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        result = invoke(["profile", "to-openrc"])
        assert "OS_PROJECT_NAME" in result.output or "OS_PROJECT_ID" in result.output

    def test_export_nonexistent_profile_fails(self, invoke, config_dir, mock_client):
        save_profile("prod", {"auth_url": "x", "username": "u", "password": "p",
                               "user_domain_name": "D", "project_name": "P"})
        set_active_profile("prod")
        result = invoke(["profile", "to-openrc", "nope"])
        assert result.exit_code != 0


class TestToClouds:

    def test_export_as_clouds_yaml(self, invoke, config_dir, sample_profile, mock_client):
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        result = invoke(["profile", "to-clouds"])
        assert result.exit_code == 0
        data = yaml.safe_load(result.output)
        assert "clouds" in data
        assert "prod" in data["clouds"]
        cloud_auth = data["clouds"]["prod"]["auth"]
        assert cloud_auth["auth_url"] == sample_profile["auth_url"]
        assert cloud_auth["username"] == sample_profile["username"]

    def test_export_custom_cloud_name(self, invoke, config_dir, sample_profile, mock_client):
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        result = invoke(["profile", "to-clouds", "--cloud-name", "custom"])
        assert result.exit_code == 0
        data = yaml.safe_load(result.output)
        assert "custom" in data["clouds"]

    def test_export_to_file(self, invoke, config_dir, sample_profile, mock_client, tmp_path):
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        outfile = str(tmp_path / "clouds.yaml")
        result = invoke(["profile", "to-clouds", "-o", outfile])
        assert result.exit_code == 0
        data = yaml.safe_load(Path(outfile).read_text())
        assert "clouds" in data

    def test_insecure_becomes_verify_false(self, invoke, config_dir, mock_client):
        profile = {
            "auth_url": "https://ks:5000",
            "username": "u",
            "password": "p",
            "user_domain_name": "D",
            "project_name": "P",
            "insecure": "true",
        }
        save_profile("prod", profile)
        set_active_profile("prod")

        result = invoke(["profile", "to-clouds"])
        data = yaml.safe_load(result.output)
        assert data["clouds"]["prod"].get("verify") is False


class TestFromOpenrc:

    def test_import_openrc_file(self, invoke, config_dir, mock_client, tmp_path):
        openrc = tmp_path / "admin-openrc.sh"
        openrc.write_text(
            "# OpenRC\n"
            "export OS_AUTH_URL=https://imported-ks:5000\n"
            "export OS_USERNAME=imported-user\n"
            "export OS_PASSWORD=imported-pass\n"
            "export OS_USER_DOMAIN_NAME=ImportedDomain\n"
            "export OS_PROJECT_NAME=imported-proj\n"
            "export OS_IDENTITY_API_VERSION=3\n"
        )
        # Need at least one profile so config exists
        save_profile("dummy", {"auth_url": "x", "username": "x", "password": "x",
                                "user_domain_name": "D", "project_name": "P"})
        set_active_profile("dummy")

        result = invoke(["profile", "from-openrc", str(openrc)])
        assert result.exit_code == 0
        assert "imported" in result.output.lower() or "admin" in result.output.lower()

        from orca_cli.core.config import get_profile
        cfg = get_profile("admin")
        assert cfg["auth_url"] == "https://imported-ks:5000"
        assert cfg["username"] == "imported-user"
        assert cfg["user_domain_name"] == "ImportedDomain"

    def test_import_with_custom_name(self, invoke, config_dir, mock_client, tmp_path):
        openrc = tmp_path / "rc.sh"
        openrc.write_text(
            "export OS_AUTH_URL=https://ks:5000\n"
            "export OS_USERNAME=u\n"
            "export OS_PASSWORD=p\n"
            "export OS_USER_DOMAIN_NAME=D\n"
            "export OS_PROJECT_NAME=P\n"
        )
        save_profile("dummy", {"auth_url": "x", "username": "x", "password": "x",
                                "user_domain_name": "D", "project_name": "P"})
        set_active_profile("dummy")

        result = invoke(["profile", "from-openrc", str(openrc), "--name", "custom"])
        assert result.exit_code == 0

        from orca_cli.core.config import get_profile
        assert get_profile("custom")["username"] == "u"

    def test_import_no_auth_url_fails(self, invoke, config_dir, mock_client, tmp_path):
        openrc = tmp_path / "bad.sh"
        openrc.write_text("export OS_USERNAME=u\n")

        result = invoke(["profile", "from-openrc", str(openrc)])
        assert result.exit_code != 0

    def test_import_handles_quoted_values(self, invoke, config_dir, mock_client, tmp_path):
        openrc = tmp_path / "quoted.sh"
        openrc.write_text(
            'export OS_AUTH_URL="https://ks:5000"\n'
            "export OS_USERNAME='admin'\n"
            "export OS_PASSWORD='secret with spaces'\n"
            "export OS_USER_DOMAIN_NAME=Default\n"
            "export OS_PROJECT_NAME=demo\n"
        )
        save_profile("dummy", {"auth_url": "x", "username": "x", "password": "x",
                                "user_domain_name": "D", "project_name": "P"})
        set_active_profile("dummy")

        result = invoke(["profile", "from-openrc", str(openrc), "--name", "q"])
        assert result.exit_code == 0

        from orca_cli.core.config import get_profile
        cfg = get_profile("q")
        assert cfg["auth_url"] == "https://ks:5000"
        assert cfg["password"] == "secret with spaces"


class TestFromClouds:

    def test_import_from_clouds_yaml(self, invoke, config_dir, mock_client, tmp_path, monkeypatch):
        clouds_data = {
            "clouds": {
                "mycloud": {
                    "auth": {
                        "auth_url": "https://cloud-ks:5000",
                        "username": "cloud-user",
                        "password": "cloud-pass",
                        "user_domain_name": "CloudDomain",
                        "project_name": "cloud-proj",
                    },
                    "region_name": "RegionOne",
                }
            }
        }
        clouds_path = tmp_path / "clouds.yaml"
        with open(clouds_path, "w") as fh:
            yaml.dump(clouds_data, fh)

        monkeypatch.setattr("orca_cli.core.config._CLOUDS_YAML_PATHS", [clouds_path])
        # Also patch in the profile module since it imports _find_clouds_yaml
        monkeypatch.setattr("orca_cli.commands.profile._find_clouds_yaml",
                            lambda: clouds_path)

        save_profile("dummy", {"auth_url": "x", "username": "x", "password": "x",
                                "user_domain_name": "D", "project_name": "P"})
        set_active_profile("dummy")

        result = invoke(["profile", "from-clouds", "mycloud"])
        assert result.exit_code == 0

        from orca_cli.core.config import get_profile
        cfg = get_profile("mycloud")
        assert cfg["auth_url"] == "https://cloud-ks:5000"
        assert cfg["username"] == "cloud-user"
        assert cfg.get("region_name") == "RegionOne"

    def test_import_with_explicit_file(self, invoke, config_dir, mock_client, tmp_path):
        clouds_data = {
            "clouds": {
                "other": {
                    "auth": {
                        "auth_url": "https://other:5000",
                        "username": "u",
                        "password": "p",
                        "user_domain_name": "D",
                        "project_name": "P",
                    }
                }
            }
        }
        clouds_path = tmp_path / "my-clouds.yaml"
        with open(clouds_path, "w") as fh:
            yaml.dump(clouds_data, fh)

        save_profile("dummy", {"auth_url": "x", "username": "x", "password": "x",
                                "user_domain_name": "D", "project_name": "P"})
        set_active_profile("dummy")

        result = invoke(["profile", "from-clouds", "other", "-f", str(clouds_path)])
        assert result.exit_code == 0

        from orca_cli.core.config import get_profile
        assert get_profile("other")["auth_url"] == "https://other:5000"


class TestRoundTrip:
    """Export then import should preserve data."""

    def test_openrc_roundtrip(self, invoke, config_dir, mock_client, tmp_path):
        original = {
            "auth_url": "https://rt-ks:5000",
            "username": "rt-user",
            "password": "rt-pass",
            "user_domain_name": "RTDomain",
            "project_name": "rt-project",
            "region_name": "RegionOne",
        }
        save_profile("original", original)
        set_active_profile("original")

        # Export
        outfile = str(tmp_path / "rt.sh")
        result = invoke(["profile", "to-openrc", "-o", outfile])
        assert result.exit_code == 0

        # Import
        result = invoke(["profile", "from-openrc", outfile, "--name", "imported"])
        assert result.exit_code == 0

        from orca_cli.core.config import get_profile
        imported = get_profile("imported")
        assert imported["auth_url"] == original["auth_url"]
        assert imported["username"] == original["username"]
        assert imported["user_domain_name"] == original["user_domain_name"]
        assert imported["project_name"] == original["project_name"]

    def test_clouds_roundtrip(self, invoke, config_dir, mock_client, tmp_path, monkeypatch):
        original = {
            "auth_url": "https://rt-ks:5000",
            "username": "rt-user",
            "password": "rt-pass",
            "user_domain_name": "RTDomain",
            "project_name": "rt-project",
        }
        save_profile("original", original)
        set_active_profile("original")

        # Export
        outfile = str(tmp_path / "clouds.yaml")
        result = invoke(["profile", "to-clouds", "-o", outfile])
        assert result.exit_code == 0

        # Import
        result = invoke(["profile", "from-clouds", "original", "-f", outfile, "--name", "imported"])
        assert result.exit_code == 0

        from orca_cli.core.config import get_profile
        imported = get_profile("imported")
        assert imported["auth_url"] == original["auth_url"]
        assert imported["username"] == original["username"]
        assert imported["user_domain_name"] == original["user_domain_name"]
        assert imported["project_name"] == original["project_name"]
