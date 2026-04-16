"""Tests for ``orca catalog`` command."""

from __future__ import annotations

from orca_cli.core.config import save_profile, set_active_profile


class TestCatalogList:

    def test_catalog_displays_services(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        result = invoke(["catalog"])
        assert result.exit_code == 0
        assert "Service Catalog" in result.output
        assert "nova" in result.output
        assert "keystone" in result.output
        assert "neutron" in result.output

    def test_catalog_shows_types(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        result = invoke(["catalog"])
        assert "compute" in result.output
        assert "identity" in result.output
        assert "network" in result.output

    def test_catalog_shows_interfaces(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        result = invoke(["catalog"])
        assert "public" in result.output

    def test_catalog_shows_urls(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        result = invoke(["catalog"])
        assert "nova.example.com" in result.output
        assert "keystone.example.com" in result.output
        assert "neutron.example.com" in result.output

    def test_catalog_multiple_interfaces(self, invoke, config_dir, mock_client, sample_profile):
        """Services with multiple interfaces show one row per endpoint."""
        save_profile("prod", sample_profile)
        set_active_profile("prod")
        mock_client._catalog = [
            {
                "type": "compute",
                "name": "nova",
                "endpoints": [
                    {"interface": "public", "url": "https://nova-pub.example.com/v2.1", "region_id": "R1"},
                    {"interface": "internal", "url": "https://nova-int.example.com/v2.1", "region_id": "R1"},
                    {"interface": "admin", "url": "https://nova-adm.example.com/v2.1", "region_id": "R1"},
                ],
            },
        ]

        result = invoke(["catalog"])
        assert result.exit_code == 0
        assert "public" in result.output
        assert "internal" in result.output
        assert "admin" in result.output

    def test_catalog_empty(self, invoke, config_dir, mock_client, sample_profile):
        """Empty catalog shows message."""
        save_profile("prod", sample_profile)
        set_active_profile("prod")
        mock_client._catalog = []

        result = invoke(["catalog"])
        assert result.exit_code == 0
        assert "No service catalog available" in result.output

    def test_catalog_service_no_endpoints(self, invoke, config_dir, mock_client, sample_profile):
        """Service with no endpoints is not listed."""
        save_profile("prod", sample_profile)
        set_active_profile("prod")
        mock_client._catalog = [
            {"type": "compute", "name": "nova", "endpoints": []},
        ]

        result = invoke(["catalog"])
        assert result.exit_code == 0
        # No rows to display since endpoints list is empty
        assert "No service catalog available" in result.output

    def test_catalog_many_services(self, invoke, config_dir, mock_client, sample_profile):
        """Multiple services are all listed."""
        save_profile("prod", sample_profile)
        set_active_profile("prod")
        mock_client._catalog = [
            {"type": "compute", "name": "nova",
             "endpoints": [{"interface": "public", "url": "https://nova:8774"}]},
            {"type": "network", "name": "neutron",
             "endpoints": [{"interface": "public", "url": "https://neutron:9696"}]},
            {"type": "image", "name": "glance",
             "endpoints": [{"interface": "public", "url": "https://glance:9292"}]},
            {"type": "volume", "name": "cinder",
             "endpoints": [{"interface": "public", "url": "https://cinder:8776"}]},
            {"type": "object-store", "name": "swift",
             "endpoints": [{"interface": "public", "url": "https://swift:8080"}]},
        ]

        result = invoke(["catalog"])
        assert result.exit_code == 0
        for name in ("nova", "neutron", "glance", "cinder", "swift"):
            assert name in result.output


class TestCatalogOutputFormats:

    def test_catalog_json_format(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        result = invoke(["catalog", "-f", "json"])
        assert result.exit_code == 0
        import json
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) == 3  # 3 services in conftest FAKE_TOKEN_DATA
        assert data[0]["Service"] in ("nova", "keystone", "neutron")

    def test_catalog_value_format(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        result = invoke(["catalog", "-f", "value"])
        assert result.exit_code == 0
        # Value format outputs raw values
        assert "nova" in result.output

    def test_catalog_column_filter(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("prod", sample_profile)
        set_active_profile("prod")

        result = invoke(["catalog", "-c", "Service", "-c", "URL"])
        assert result.exit_code == 0
        assert "nova" in result.output
        # Type column should not appear when filtered out
        # (can't assert absence since "compute" might appear in URL)


class TestCatalogHelp:

    def test_help(self, invoke):
        result = invoke(["catalog", "--help"])
        assert result.exit_code == 0
        assert "service endpoints" in result.output.lower()
        assert "--format" in result.output or "-f" in result.output
