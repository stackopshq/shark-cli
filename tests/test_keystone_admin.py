"""Tests for Keystone admin commands: endpoint, service, credential, region, trust, token-revoke."""

from __future__ import annotations

import pytest

ID  = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
ID2 = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
KS  = "https://keystone.example.com:5000/v3"


def _client(mock_client):
    mock_client.identity_url = KS
    mock_client._catalog = []
    return mock_client


# ══════════════════════════════════════════════════════════════════════════
#  endpoint
# ══════════════════════════════════════════════════════════════════════════

class TestEndpointList:

    def test_list(self, invoke, mock_client):
        _client(mock_client)
        mock_client.get.return_value = {"endpoints": [
            {"id": ID, "service_id": ID2, "interface": "public",
             "region_id": "RegionOne", "url": "https://nova.example.com", "enabled": True},
        ]}
        result = invoke(["endpoint", "list"])
        assert result.exit_code == 0
        assert "publ" in result.output

    def test_list_filter_interface(self, invoke, mock_client):
        _client(mock_client)
        mock_client.get.return_value = {"endpoints": []}
        invoke(["endpoint", "list", "--interface", "internal"])
        params = mock_client.get.call_args[1]["params"]
        assert params["interface"] == "internal"

    def test_list_filter_region(self, invoke, mock_client):
        _client(mock_client)
        mock_client.get.return_value = {"endpoints": []}
        invoke(["endpoint", "list", "--region", "dc3-a"])
        params = mock_client.get.call_args[1]["params"]
        assert params["region_id"] == "dc3-a"

    def test_list_empty(self, invoke, mock_client):
        _client(mock_client)
        mock_client.get.return_value = {"endpoints": []}
        result = invoke(["endpoint", "list"])
        assert result.exit_code == 0
        assert "No endpoints" in result.output

    def test_help(self, invoke):
        result = invoke(["endpoint", "list", "--help"])
        assert result.exit_code == 0


class TestEndpointShow:

    def test_show(self, invoke, mock_client):
        _client(mock_client)
        mock_client.get.return_value = {"endpoint": {
            "id": ID, "service_id": ID2, "interface": "public",
            "region_id": "RegionOne", "url": "https://nova.example.com", "enabled": True,
        }}
        result = invoke(["endpoint", "show", ID])
        assert result.exit_code == 0
        assert "public" in result.output

    def test_help(self, invoke):
        assert invoke(["endpoint", "show", "--help"]).exit_code == 0


class TestEndpointCreate:

    def test_create(self, invoke, mock_client):
        _client(mock_client)
        mock_client.post.return_value = {"endpoint": {"id": ID}}
        result = invoke(["endpoint", "create",
                         "--service", ID2,
                         "--interface", "public",
                         "--url", "https://nova.example.com"])
        assert result.exit_code == 0
        assert mock_client.post.called
        body = mock_client.post.call_args[1]["json"]["endpoint"]
        assert body["interface"] == "public"
        assert body["service_id"] == ID2

    def test_create_with_region(self, invoke, mock_client):
        _client(mock_client)
        mock_client.post.return_value = {"endpoint": {"id": ID}}
        invoke(["endpoint", "create", "--service", ID2, "--interface", "internal",
                "--url", "http://internal", "--region", "dc3-a"])
        body = mock_client.post.call_args[1]["json"]["endpoint"]
        assert body["region_id"] == "dc3-a"

    def test_help(self, invoke):
        assert invoke(["endpoint", "create", "--help"]).exit_code == 0


class TestEndpointSet:

    def test_set_url(self, invoke, mock_client):
        _client(mock_client)
        invoke(["endpoint", "set", ID, "--url", "https://new.example.com"])
        body = mock_client.patch.call_args[1]["json"]["endpoint"]
        assert body["url"] == "https://new.example.com"

    def test_set_nothing(self, invoke, mock_client):
        _client(mock_client)
        result = invoke(["endpoint", "set", ID])
        assert result.exit_code == 0
        mock_client.patch.assert_not_called()

    def test_help(self, invoke):
        assert invoke(["endpoint", "set", "--help"]).exit_code == 0


class TestEndpointDelete:

    def test_delete_yes(self, invoke, mock_client):
        _client(mock_client)
        result = invoke(["endpoint", "delete", ID, "--yes"])
        assert result.exit_code == 0
        mock_client.delete.assert_called_once()
        assert ID in mock_client.delete.call_args[0][0]

    def test_help(self, invoke):
        assert invoke(["endpoint", "delete", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════
#  service
# ══════════════════════════════════════════════════════════════════════════

class TestServiceList:

    def test_list(self, invoke, mock_client):
        _client(mock_client)
        mock_client.get.return_value = {"services": [
            {"id": ID, "name": "nova", "type": "compute",
             "description": "Compute", "enabled": True},
        ]}
        result = invoke(["service", "list"])
        assert result.exit_code == 0
        assert "nova" in result.output
        assert "compute" in result.output

    def test_list_filter_type(self, invoke, mock_client):
        _client(mock_client)
        mock_client.get.return_value = {"services": []}
        invoke(["service", "list", "--type", "identity"])
        params = mock_client.get.call_args[1]["params"]
        assert params["type"] == "identity"

    def test_list_empty(self, invoke, mock_client):
        _client(mock_client)
        mock_client.get.return_value = {"services": []}
        result = invoke(["service", "list"])
        assert "No services" in result.output

    def test_help(self, invoke):
        assert invoke(["service", "list", "--help"]).exit_code == 0


class TestServiceCreate:

    def test_create(self, invoke, mock_client):
        _client(mock_client)
        mock_client.post.return_value = {"service": {"id": ID}}
        result = invoke(["service", "create", "--name", "nova", "--type", "compute"])
        assert result.exit_code == 0
        body = mock_client.post.call_args[1]["json"]["service"]
        assert body["name"] == "nova"
        assert body["type"] == "compute"

    def test_create_with_description(self, invoke, mock_client):
        _client(mock_client)
        mock_client.post.return_value = {"service": {"id": ID}}
        invoke(["service", "create", "--name", "nova", "--type", "compute",
                "--description", "Nova Compute"])
        body = mock_client.post.call_args[1]["json"]["service"]
        assert body["description"] == "Nova Compute"

    def test_help(self, invoke):
        assert invoke(["service", "create", "--help"]).exit_code == 0


class TestServiceSet:

    def test_set_name(self, invoke, mock_client):
        _client(mock_client)
        invoke(["service", "set", ID, "--name", "nova2"])
        body = mock_client.patch.call_args[1]["json"]["service"]
        assert body["name"] == "nova2"

    def test_set_nothing(self, invoke, mock_client):
        _client(mock_client)
        result = invoke(["service", "set", ID])
        assert result.exit_code == 0
        mock_client.patch.assert_not_called()


class TestServiceDelete:

    def test_delete_yes(self, invoke, mock_client):
        _client(mock_client)
        result = invoke(["service", "delete", ID, "--yes"])
        assert result.exit_code == 0
        mock_client.delete.assert_called_once()

    def test_help(self, invoke):
        assert invoke(["service", "delete", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════
#  credential
# ══════════════════════════════════════════════════════════════════════════

class TestCredentialList:

    def test_list(self, invoke, mock_client):
        _client(mock_client)
        mock_client.get.return_value = {"credentials": [
            {"id": ID, "type": "ec2", "user_id": ID2,
             "project_id": ID2, "blob": '{"access":"abc","secret":"xyz"}'},
        ]}
        result = invoke(["credential", "list"])
        assert result.exit_code == 0
        assert "ec2" in result.output

    def test_list_filter_user(self, invoke, mock_client):
        _client(mock_client)
        mock_client.get.return_value = {"credentials": []}
        invoke(["credential", "list", "--user", ID2])
        params = mock_client.get.call_args[1]["params"]
        assert params["user_id"] == ID2

    def test_list_filter_type(self, invoke, mock_client):
        _client(mock_client)
        mock_client.get.return_value = {"credentials": []}
        invoke(["credential", "list", "--type", "totp"])
        assert mock_client.get.call_args[1]["params"]["type"] == "totp"

    def test_help(self, invoke):
        assert invoke(["credential", "list", "--help"]).exit_code == 0


class TestCredentialCreate:

    def test_create(self, invoke, mock_client):
        _client(mock_client)
        mock_client.post.return_value = {"credential": {"id": ID}}
        result = invoke(["credential", "create",
                         "--user", ID2,
                         "--type", "ec2",
                         "--blob", '{"access":"abc"}'])
        assert result.exit_code == 0
        body = mock_client.post.call_args[1]["json"]["credential"]
        assert body["user_id"] == ID2
        assert body["type"] == "ec2"

    def test_create_with_project(self, invoke, mock_client):
        _client(mock_client)
        mock_client.post.return_value = {"credential": {"id": ID}}
        invoke(["credential", "create", "--user", ID2, "--type", "ec2",
                "--blob", "{}", "--project", ID])
        body = mock_client.post.call_args[1]["json"]["credential"]
        assert body["project_id"] == ID

    def test_help(self, invoke):
        assert invoke(["credential", "create", "--help"]).exit_code == 0


class TestCredentialDelete:

    def test_delete_yes(self, invoke, mock_client):
        _client(mock_client)
        result = invoke(["credential", "delete", ID, "--yes"])
        assert result.exit_code == 0
        mock_client.delete.assert_called_once()

    def test_help(self, invoke):
        assert invoke(["credential", "delete", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════
#  region
# ══════════════════════════════════════════════════════════════════════════

class TestRegionList:

    def test_list(self, invoke, mock_client):
        _client(mock_client)
        mock_client.get.return_value = {"regions": [
            {"id": "RegionOne", "description": "Primary region", "parent_region_id": None},
            {"id": "RegionTwo", "description": "", "parent_region_id": "RegionOne"},
        ]}
        result = invoke(["region", "list"])
        assert result.exit_code == 0
        assert "RegionOne" in result.output
        assert "RegionTwo" in result.output

    def test_list_filter_parent(self, invoke, mock_client):
        _client(mock_client)
        mock_client.get.return_value = {"regions": []}
        invoke(["region", "list", "--parent", "RegionOne"])
        params = mock_client.get.call_args[1]["params"]
        assert params["parent_region_id"] == "RegionOne"

    def test_list_empty(self, invoke, mock_client):
        _client(mock_client)
        mock_client.get.return_value = {"regions": []}
        result = invoke(["region", "list"])
        assert "No regions" in result.output

    def test_help(self, invoke):
        assert invoke(["region", "list", "--help"]).exit_code == 0


class TestRegionShow:

    def test_show(self, invoke, mock_client):
        _client(mock_client)
        mock_client.get.return_value = {"region": {
            "id": "RegionOne", "description": "Main", "parent_region_id": None,
        }}
        result = invoke(["region", "show", "RegionOne"])
        assert result.exit_code == 0
        assert "RegionOne" in result.output

    def test_help(self, invoke):
        assert invoke(["region", "show", "--help"]).exit_code == 0


class TestRegionCreate:

    def test_create(self, invoke, mock_client):
        _client(mock_client)
        mock_client.post.return_value = {"region": {"id": "dc3-a"}}
        result = invoke(["region", "create", "dc3-a"])
        assert result.exit_code == 0
        body = mock_client.post.call_args[1]["json"]["region"]
        assert body["id"] == "dc3-a"

    def test_create_with_description(self, invoke, mock_client):
        _client(mock_client)
        mock_client.post.return_value = {"region": {"id": "dc3-a"}}
        invoke(["region", "create", "dc3-a", "--description", "DC3 zone A"])
        body = mock_client.post.call_args[1]["json"]["region"]
        assert body["description"] == "DC3 zone A"

    def test_create_with_parent(self, invoke, mock_client):
        _client(mock_client)
        mock_client.post.return_value = {"region": {"id": "dc3-a"}}
        invoke(["region", "create", "dc3-a", "--parent", "RegionOne"])
        body = mock_client.post.call_args[1]["json"]["region"]
        assert body["parent_region_id"] == "RegionOne"

    def test_help(self, invoke):
        assert invoke(["region", "create", "--help"]).exit_code == 0


class TestRegionSet:

    def test_set_description(self, invoke, mock_client):
        _client(mock_client)
        result = invoke(["region", "set", "RegionOne", "--description", "Updated"])
        assert result.exit_code == 0
        body = mock_client.patch.call_args[1]["json"]["region"]
        assert body["description"] == "Updated"

    def test_set_nothing(self, invoke, mock_client):
        _client(mock_client)
        result = invoke(["region", "set", "RegionOne"])
        assert result.exit_code == 0
        mock_client.patch.assert_not_called()


class TestRegionDelete:

    def test_delete_yes(self, invoke, mock_client):
        _client(mock_client)
        result = invoke(["region", "delete", "RegionOne", "--yes"])
        assert result.exit_code == 0
        mock_client.delete.assert_called_once()
        assert "RegionOne" in mock_client.delete.call_args[0][0]

    def test_help(self, invoke):
        assert invoke(["region", "delete", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════
#  trust
# ══════════════════════════════════════════════════════════════════════════

class TestTrustList:

    def test_list(self, invoke, mock_client):
        _client(mock_client)
        mock_client.get.return_value = {"trusts": [
            {"id": ID, "trustor_user_id": ID2, "trustee_user_id": ID2,
             "project_id": ID, "impersonation": True, "expires_at": None},
        ]}
        result = invoke(["trust", "list"])
        assert result.exit_code == 0
        assert ID[:8] in result.output

    def test_list_filter_trustor(self, invoke, mock_client):
        _client(mock_client)
        mock_client.get.return_value = {"trusts": []}
        invoke(["trust", "list", "--trustor", ID2])
        assert mock_client.get.call_args[1]["params"]["trustor_user_id"] == ID2

    def test_list_filter_trustee(self, invoke, mock_client):
        _client(mock_client)
        mock_client.get.return_value = {"trusts": []}
        invoke(["trust", "list", "--trustee", ID])
        assert mock_client.get.call_args[1]["params"]["trustee_user_id"] == ID

    def test_list_empty(self, invoke, mock_client):
        _client(mock_client)
        mock_client.get.return_value = {"trusts": []}
        result = invoke(["trust", "list"])
        assert "No trusts" in result.output

    def test_help(self, invoke):
        assert invoke(["trust", "list", "--help"]).exit_code == 0


class TestTrustShow:

    def test_show(self, invoke, mock_client):
        _client(mock_client)
        mock_client.get.return_value = {"trust": {
            "id": ID, "trustor_user_id": ID2, "trustee_user_id": ID2,
            "project_id": ID, "impersonation": True, "expires_at": None,
            "remaining_uses": None, "roles": [{"name": "member"}],
        }}
        result = invoke(["trust", "show", ID])
        assert result.exit_code == 0
        assert "member" in result.output

    def test_help(self, invoke):
        assert invoke(["trust", "show", "--help"]).exit_code == 0


class TestTrustCreate:

    def test_create(self, invoke, mock_client):
        _client(mock_client)
        mock_client.post.return_value = {"trust": {"id": ID}}
        result = invoke(["trust", "create",
                         "--trustor", ID,
                         "--trustee", ID2,
                         "--project", ID,
                         "--role", "member"])
        assert result.exit_code == 0
        body = mock_client.post.call_args[1]["json"]["trust"]
        assert body["trustor_user_id"] == ID
        assert body["trustee_user_id"] == ID2
        assert body["roles"] == [{"name": "member"}]

    def test_create_impersonation(self, invoke, mock_client):
        _client(mock_client)
        mock_client.post.return_value = {"trust": {"id": ID}}
        invoke(["trust", "create", "--trustor", ID, "--trustee", ID2, "--impersonate"])
        body = mock_client.post.call_args[1]["json"]["trust"]
        assert body["impersonation"] is True

    def test_create_expires_at(self, invoke, mock_client):
        _client(mock_client)
        mock_client.post.return_value = {"trust": {"id": ID}}
        invoke(["trust", "create", "--trustor", ID, "--trustee", ID2,
                "--expires-at", "2026-12-31T23:59:59Z"])
        body = mock_client.post.call_args[1]["json"]["trust"]
        assert body["expires_at"] == "2026-12-31T23:59:59Z"

    def test_help(self, invoke):
        assert invoke(["trust", "create", "--help"]).exit_code == 0


class TestTrustDelete:

    def test_delete_yes(self, invoke, mock_client):
        _client(mock_client)
        result = invoke(["trust", "delete", ID, "--yes"])
        assert result.exit_code == 0
        mock_client.delete.assert_called_once()

    def test_help(self, invoke):
        assert invoke(["trust", "delete", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════
#  auth token-revoke
# ══════════════════════════════════════════════════════════════════════════

class TestTokenRevoke:

    def test_revoke(self, invoke, mock_client):
        mock_client.identity_url = KS
        result = invoke(["auth", "token-revoke", "my-token-value"])
        assert result.exit_code == 0
        assert mock_client.delete.called
        url = mock_client.delete.call_args[0][0]
        assert "auth/tokens" in url

    def test_revoke_sends_subject_token_header(self, invoke, mock_client):
        mock_client.identity_url = KS
        invoke(["auth", "token-revoke", "my-secret-token"])
        headers = mock_client.delete.call_args[1].get("headers", {})
        assert headers.get("X-Subject-Token") == "my-secret-token"

    def test_help(self, invoke):
        result = invoke(["auth", "token-revoke", "--help"])
        assert result.exit_code == 0


# ══════════════════════════════════════════════════════════════════════════
#  CLI registration
# ══════════════════════════════════════════════════════════════════════════

class TestRegistration:

    @pytest.mark.parametrize("cmd", ["endpoint", "service", "credential", "region", "trust"])
    def test_command_registered(self, invoke, cmd):
        result = invoke([cmd, "--help"])
        assert result.exit_code == 0

    def test_token_revoke_registered(self, invoke):
        result = invoke(["auth", "token-revoke", "--help"])
        assert result.exit_code == 0
