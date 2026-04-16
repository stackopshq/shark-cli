"""Tests for Keystone gap commands: policy, federation, limits, access-rule, token, endpoint-group, implied roles."""

from __future__ import annotations

import json

import pytest

# ── Constants ──────────────────────────────────────────────────────────────────

POLICY_ID   = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
IDP_ID      = "my-idp"
MAPPING_ID  = "my-mapping"
SP_ID       = "my-sp"
RL_ID       = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
LIMIT_ID    = "cccccccc-cccc-cccc-cccc-cccccccccccc"
SERVICE_ID  = "dddddddd-dddd-dddd-dddd-dddddddddddd"
PROJECT_ID  = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"
ROLE_A      = "ffffffff-ffff-ffff-ffff-ffffffffffff"
ROLE_B      = "11111111-1111-1111-1111-111111111111"
EG_ID       = "22222222-2222-2222-2222-222222222222"
AR_ID       = "33333333-3333-3333-3333-333333333333"
USER_ID     = "44444444-4444-4444-4444-444444444444"
BASE        = "https://keystone.example.com"


def _iam(mc):
    mc.identity_url = BASE
    return mc


# ══════════════════════════════════════════════════════════════════════════════
#  Policy
# ══════════════════════════════════════════════════════════════════════════════

class TestPolicy:

    def _p(self, **kw):
        return {"id": POLICY_ID, "type": "application/json",
                "blob": '{"default": false}', **kw}

    def test_list(self, invoke, mock_client):
        _iam(mock_client)
        mock_client.get.return_value = {"policies": [self._p()]}
        result = invoke(["policy", "list"])
        assert result.exit_code == 0

    def test_list_empty(self, invoke, mock_client):
        _iam(mock_client)
        mock_client.get.return_value = {"policies": []}
        result = invoke(["policy", "list"])
        assert "No policies" in result.output

    def test_list_filter_type(self, invoke, mock_client):
        _iam(mock_client)
        mock_client.get.return_value = {"policies": []}
        invoke(["policy", "list", "--type", "application/json"])
        assert mock_client.get.call_args[1]["params"]["type"] == "application/json"

    def test_show(self, invoke, mock_client):
        _iam(mock_client)
        mock_client.get.return_value = {"policy": self._p()}
        result = invoke(["policy", "show", POLICY_ID])
        assert result.exit_code == 0

    def test_create(self, invoke, mock_client):
        _iam(mock_client)
        mock_client.post.return_value = {"policy": self._p()}
        result = invoke(["policy", "create", '{"default": false}'])
        assert result.exit_code == 0
        body = mock_client.post.call_args[1]["json"]["policy"]
        assert body["blob"] == '{"default": false}'

    def test_set(self, invoke, mock_client):
        _iam(mock_client)
        result = invoke(["policy", "set", POLICY_ID, "--blob", '{"default": true}'])
        assert result.exit_code == 0
        body = mock_client.patch.call_args[1]["json"]["policy"]
        assert body["blob"] == '{"default": true}'

    def test_set_nothing(self, invoke, mock_client):
        _iam(mock_client)
        result = invoke(["policy", "set", POLICY_ID])
        assert result.exit_code == 0
        mock_client.patch.assert_not_called()

    def test_delete_yes(self, invoke, mock_client):
        _iam(mock_client)
        result = invoke(["policy", "delete", POLICY_ID, "--yes"])
        assert result.exit_code == 0
        mock_client.delete.assert_called_once()

    def test_delete_requires_confirm(self, invoke, mock_client):
        _iam(mock_client)
        result = invoke(["policy", "delete", POLICY_ID], input="n\n")
        assert result.exit_code != 0
        mock_client.delete.assert_not_called()

    @pytest.mark.parametrize("sub", ["list", "show", "create", "set", "delete"])
    def test_help(self, invoke, sub):
        assert invoke(["policy", sub, "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════════
#  Identity Provider
# ══════════════════════════════════════════════════════════════════════════════

class TestIdentityProvider:

    def _idp(self, **kw):
        return {"id": IDP_ID, "enabled": True, "description": "",
                "domain_id": None, "remote_ids": [], **kw}

    def test_list(self, invoke, mock_client):
        _iam(mock_client)
        mock_client.get.return_value = {"identity_providers": [self._idp()]}
        result = invoke(["identity-provider", "list"])
        assert result.exit_code == 0
        assert IDP_ID in result.output

    def test_list_empty(self, invoke, mock_client):
        _iam(mock_client)
        mock_client.get.return_value = {"identity_providers": []}
        result = invoke(["identity-provider", "list"])
        assert "No identity providers" in result.output

    def test_show(self, invoke, mock_client):
        _iam(mock_client)
        mock_client.get.return_value = {"identity_provider": self._idp()}
        result = invoke(["identity-provider", "show", IDP_ID])
        assert result.exit_code == 0

    def test_create(self, invoke, mock_client):
        _iam(mock_client)
        mock_client.put.return_value = {"identity_provider": self._idp()}
        result = invoke(["identity-provider", "create", IDP_ID,
                         "--remote-id", "https://sso.example.com"])
        assert result.exit_code == 0
        body = mock_client.put.call_args[1]["json"]["identity_provider"]
        assert "https://sso.example.com" in body["remote_ids"]

    def test_set(self, invoke, mock_client):
        _iam(mock_client)
        result = invoke(["identity-provider", "set", IDP_ID, "--description", "My IDP"])
        assert result.exit_code == 0
        body = mock_client.patch.call_args[1]["json"]["identity_provider"]
        assert body["description"] == "My IDP"

    def test_set_nothing(self, invoke, mock_client):
        _iam(mock_client)
        result = invoke(["identity-provider", "set", IDP_ID])
        assert result.exit_code == 0
        mock_client.patch.assert_not_called()

    def test_delete_yes(self, invoke, mock_client):
        _iam(mock_client)
        result = invoke(["identity-provider", "delete", IDP_ID, "--yes"])
        assert result.exit_code == 0
        mock_client.delete.assert_called_once()

    @pytest.mark.parametrize("sub", ["list", "show", "create", "set", "delete"])
    def test_help(self, invoke, sub):
        assert invoke(["identity-provider", sub, "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════════
#  Federation Protocol
# ══════════════════════════════════════════════════════════════════════════════

class TestFederationProtocol:

    def test_list(self, invoke, mock_client):
        _iam(mock_client)
        mock_client.get.return_value = {
            "protocols": [{"id": "saml2", "mapping_id": MAPPING_ID}]
        }
        result = invoke(["federation-protocol", "list", IDP_ID])
        assert result.exit_code == 0
        assert "saml2" in result.output

    def test_list_empty(self, invoke, mock_client):
        _iam(mock_client)
        mock_client.get.return_value = {"protocols": []}
        result = invoke(["federation-protocol", "list", IDP_ID])
        assert "No protocols" in result.output

    def test_show(self, invoke, mock_client):
        _iam(mock_client)
        mock_client.get.return_value = {"protocol": {"id": "saml2", "mapping_id": MAPPING_ID}}
        result = invoke(["federation-protocol", "show", IDP_ID, "saml2"])
        assert result.exit_code == 0

    def test_create(self, invoke, mock_client):
        _iam(mock_client)
        mock_client.put.return_value = {"protocol": {"id": "saml2", "mapping_id": MAPPING_ID}}
        result = invoke(["federation-protocol", "create", IDP_ID, "saml2",
                         "--mapping-id", MAPPING_ID])
        assert result.exit_code == 0
        body = mock_client.put.call_args[1]["json"]["protocol"]
        assert body["mapping_id"] == MAPPING_ID

    def test_set(self, invoke, mock_client):
        _iam(mock_client)
        result = invoke(["federation-protocol", "set", IDP_ID, "saml2",
                         "--mapping-id", MAPPING_ID])
        assert result.exit_code == 0
        body = mock_client.patch.call_args[1]["json"]["protocol"]
        assert body["mapping_id"] == MAPPING_ID

    def test_delete_yes(self, invoke, mock_client):
        _iam(mock_client)
        result = invoke(["federation-protocol", "delete", IDP_ID, "saml2", "--yes"])
        assert result.exit_code == 0
        mock_client.delete.assert_called_once()

    @pytest.mark.parametrize("sub", ["list", "show", "create", "set", "delete"])
    def test_help(self, invoke, sub):
        assert invoke(["federation-protocol", sub, "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════════
#  Mapping
# ══════════════════════════════════════════════════════════════════════════════

_RULES = [{"local": [{"user": {"name": "{0}"}}],
           "remote": [{"type": "REMOTE_USER"}]}]


class TestMapping:

    def test_list(self, invoke, mock_client):
        _iam(mock_client)
        mock_client.get.return_value = {
            "mappings": [{"id": MAPPING_ID, "schema_version": "1.0"}]
        }
        result = invoke(["mapping", "list"])
        assert result.exit_code == 0
        assert MAPPING_ID in result.output

    def test_list_empty(self, invoke, mock_client):
        _iam(mock_client)
        mock_client.get.return_value = {"mappings": []}
        result = invoke(["mapping", "list"])
        assert "No mappings" in result.output

    def test_show(self, invoke, mock_client):
        _iam(mock_client)
        mock_client.get.return_value = {"mapping": {"id": MAPPING_ID, "rules": _RULES}}
        result = invoke(["mapping", "show", MAPPING_ID])
        assert result.exit_code == 0

    def test_create(self, invoke, mock_client):
        _iam(mock_client)
        mock_client.put.return_value = {"mapping": {"id": MAPPING_ID}}
        result = invoke(["mapping", "create", MAPPING_ID,
                         "--rules", json.dumps(_RULES)])
        assert result.exit_code == 0
        body = mock_client.put.call_args[1]["json"]["mapping"]
        assert body["rules"] == _RULES

    def test_create_invalid_json(self, invoke, mock_client):
        _iam(mock_client)
        result = invoke(["mapping", "create", MAPPING_ID, "--rules", "bad-json"])
        assert result.exit_code != 0

    def test_set(self, invoke, mock_client):
        _iam(mock_client)
        result = invoke(["mapping", "set", MAPPING_ID,
                         "--rules", json.dumps(_RULES)])
        assert result.exit_code == 0
        body = mock_client.patch.call_args[1]["json"]["mapping"]
        assert body["rules"] == _RULES

    def test_delete_yes(self, invoke, mock_client):
        _iam(mock_client)
        result = invoke(["mapping", "delete", MAPPING_ID, "--yes"])
        assert result.exit_code == 0
        mock_client.delete.assert_called_once()

    @pytest.mark.parametrize("sub", ["list", "show", "create", "set", "delete"])
    def test_help(self, invoke, sub):
        assert invoke(["mapping", sub, "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════════
#  Service Provider
# ══════════════════════════════════════════════════════════════════════════════

class TestServiceProvider:

    def _sp(self, **kw):
        return {"id": SP_ID, "enabled": True, "description": "",
                "auth_url": "https://sp.example.com/v3/auth/tokens",
                "sp_url": "https://sp.example.com/Shibboleth.sso/SAML2/ECP",
                "relay_state_prefix": "", **kw}

    def test_list(self, invoke, mock_client):
        _iam(mock_client)
        mock_client.get.return_value = {"service_providers": [self._sp()]}
        result = invoke(["service-provider", "list"])
        assert result.exit_code == 0
        assert SP_ID in result.output

    def test_list_empty(self, invoke, mock_client):
        _iam(mock_client)
        mock_client.get.return_value = {"service_providers": []}
        result = invoke(["service-provider", "list"])
        assert "No service providers" in result.output

    def test_show(self, invoke, mock_client):
        _iam(mock_client)
        mock_client.get.return_value = {"service_provider": self._sp()}
        result = invoke(["service-provider", "show", SP_ID])
        assert result.exit_code == 0

    def test_create(self, invoke, mock_client):
        _iam(mock_client)
        mock_client.put.return_value = {"service_provider": self._sp()}
        result = invoke(["service-provider", "create", SP_ID,
                         "--auth-url", "https://sp.example.com/v3/auth/tokens",
                         "--sp-url", "https://sp.example.com/Shibboleth.sso/SAML2/ECP"])
        assert result.exit_code == 0
        body = mock_client.put.call_args[1]["json"]["service_provider"]
        assert "auth_url" in body

    def test_set(self, invoke, mock_client):
        _iam(mock_client)
        result = invoke(["service-provider", "set", SP_ID, "--description", "My SP"])
        assert result.exit_code == 0
        body = mock_client.patch.call_args[1]["json"]["service_provider"]
        assert body["description"] == "My SP"

    def test_set_nothing(self, invoke, mock_client):
        _iam(mock_client)
        result = invoke(["service-provider", "set", SP_ID])
        assert result.exit_code == 0
        mock_client.patch.assert_not_called()

    def test_delete_yes(self, invoke, mock_client):
        _iam(mock_client)
        result = invoke(["service-provider", "delete", SP_ID, "--yes"])
        assert result.exit_code == 0
        mock_client.delete.assert_called_once()

    @pytest.mark.parametrize("sub", ["list", "show", "create", "set", "delete"])
    def test_help(self, invoke, sub):
        assert invoke(["service-provider", sub, "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════════
#  Registered Limits
# ══════════════════════════════════════════════════════════════════════════════

class TestRegisteredLimit:

    def _rl(self, **kw):
        return {"id": RL_ID, "service_id": SERVICE_ID, "resource_name": "server",
                "default_limit": 10, "region_id": None, "description": "", **kw}

    def test_list(self, invoke, mock_client):
        _iam(mock_client)
        mock_client.get.return_value = {"registered_limits": [self._rl()]}
        result = invoke(["registered-limit", "list"])
        assert result.exit_code == 0
        assert "server" in result.output

    def test_list_empty(self, invoke, mock_client):
        _iam(mock_client)
        mock_client.get.return_value = {"registered_limits": []}
        result = invoke(["registered-limit", "list"])
        assert "No registered limits" in result.output

    def test_list_filter(self, invoke, mock_client):
        _iam(mock_client)
        mock_client.get.return_value = {"registered_limits": []}
        invoke(["registered-limit", "list", "--resource-name", "server"])
        assert mock_client.get.call_args[1]["params"]["resource_name"] == "server"

    def test_show(self, invoke, mock_client):
        _iam(mock_client)
        mock_client.get.return_value = {"registered_limit": self._rl()}
        result = invoke(["registered-limit", "show", RL_ID])
        assert result.exit_code == 0

    def test_create(self, invoke, mock_client):
        _iam(mock_client)
        mock_client.post.return_value = {"registered_limits": [self._rl()]}
        result = invoke(["registered-limit", "create",
                         "--service-id", SERVICE_ID,
                         "--resource-name", "server",
                         "--default-limit", "10"])
        assert result.exit_code == 0
        body = mock_client.post.call_args[1]["json"]["registered_limits"][0]
        assert body["resource_name"] == "server"
        assert body["default_limit"] == 10

    def test_set(self, invoke, mock_client):
        _iam(mock_client)
        result = invoke(["registered-limit", "set", RL_ID, "--default-limit", "20"])
        assert result.exit_code == 0
        body = mock_client.patch.call_args[1]["json"]["registered_limit"]
        assert body["default_limit"] == 20

    def test_set_nothing(self, invoke, mock_client):
        _iam(mock_client)
        result = invoke(["registered-limit", "set", RL_ID])
        assert result.exit_code == 0
        mock_client.patch.assert_not_called()

    def test_delete_yes(self, invoke, mock_client):
        _iam(mock_client)
        result = invoke(["registered-limit", "delete", RL_ID, "--yes"])
        assert result.exit_code == 0
        mock_client.delete.assert_called_once()

    @pytest.mark.parametrize("sub", ["list", "show", "create", "set", "delete"])
    def test_help(self, invoke, sub):
        assert invoke(["registered-limit", sub, "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════════
#  Limits
# ══════════════════════════════════════════════════════════════════════════════

class TestLimit:

    def _lim(self, **kw):
        return {"id": LIMIT_ID, "project_id": PROJECT_ID, "service_id": SERVICE_ID,
                "resource_name": "server", "resource_limit": 5,
                "region_id": None, "description": "", **kw}

    def test_list(self, invoke, mock_client):
        _iam(mock_client)
        mock_client.get.return_value = {"limits": [self._lim()]}
        result = invoke(["limit", "list"])
        assert result.exit_code == 0
        assert "server" in result.output

    def test_list_empty(self, invoke, mock_client):
        _iam(mock_client)
        mock_client.get.return_value = {"limits": []}
        result = invoke(["limit", "list"])
        assert "No limits" in result.output

    def test_list_filter_project(self, invoke, mock_client):
        _iam(mock_client)
        mock_client.get.return_value = {"limits": []}
        invoke(["limit", "list", "--project-id", PROJECT_ID])
        assert mock_client.get.call_args[1]["params"]["project_id"] == PROJECT_ID

    def test_show(self, invoke, mock_client):
        _iam(mock_client)
        mock_client.get.return_value = {"limit": self._lim()}
        result = invoke(["limit", "show", LIMIT_ID])
        assert result.exit_code == 0

    def test_create(self, invoke, mock_client):
        _iam(mock_client)
        mock_client.post.return_value = {"limits": [self._lim()]}
        result = invoke(["limit", "create",
                         "--project-id", PROJECT_ID,
                         "--service-id", SERVICE_ID,
                         "--resource-name", "server",
                         "--resource-limit", "5"])
        assert result.exit_code == 0
        body = mock_client.post.call_args[1]["json"]["limits"][0]
        assert body["resource_limit"] == 5

    def test_set(self, invoke, mock_client):
        _iam(mock_client)
        result = invoke(["limit", "set", LIMIT_ID, "--resource-limit", "15"])
        assert result.exit_code == 0
        body = mock_client.patch.call_args[1]["json"]["limit"]
        assert body["resource_limit"] == 15

    def test_set_nothing(self, invoke, mock_client):
        _iam(mock_client)
        result = invoke(["limit", "set", LIMIT_ID])
        assert result.exit_code == 0
        mock_client.patch.assert_not_called()

    def test_delete_yes(self, invoke, mock_client):
        _iam(mock_client)
        result = invoke(["limit", "delete", LIMIT_ID, "--yes"])
        assert result.exit_code == 0
        mock_client.delete.assert_called_once()

    @pytest.mark.parametrize("sub", ["list", "show", "create", "set", "delete"])
    def test_help(self, invoke, sub):
        assert invoke(["limit", sub, "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════════
#  Implied Roles
# ══════════════════════════════════════════════════════════════════════════════

class TestImpliedRole:

    def test_list(self, invoke, mock_client):
        _iam(mock_client)
        mock_client.get.return_value = {
            "role_inferences": [
                {"prior_role": {"id": ROLE_A, "name": "admin"},
                 "implies": [{"id": ROLE_B, "name": "member"}]}
            ]
        }
        result = invoke(["role", "implied-list"])
        assert result.exit_code == 0
        assert "admin" in result.output

    def test_list_empty(self, invoke, mock_client):
        _iam(mock_client)
        mock_client.get.return_value = {"role_inferences": []}
        result = invoke(["role", "implied-list"])
        assert "No implied roles" in result.output

    def test_create(self, invoke, mock_client):
        _iam(mock_client)
        result = invoke(["role", "implied-create", ROLE_A, ROLE_B])
        assert result.exit_code == 0
        url = mock_client.put.call_args[0][0]
        assert f"role_inferences/{ROLE_A}/implies/{ROLE_B}" in url

    def test_delete_yes(self, invoke, mock_client):
        _iam(mock_client)
        result = invoke(["role", "implied-delete", ROLE_A, ROLE_B, "--yes"])
        assert result.exit_code == 0
        mock_client.delete.assert_called_once()

    def test_delete_requires_confirm(self, invoke, mock_client):
        _iam(mock_client)
        result = invoke(["role", "implied-delete", ROLE_A, ROLE_B], input="n\n")
        assert result.exit_code != 0
        mock_client.delete.assert_not_called()

    @pytest.mark.parametrize("sub", ["implied-list", "implied-create", "implied-delete"])
    def test_help(self, invoke, sub):
        assert invoke(["role", sub, "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════════
#  Endpoint Group
# ══════════════════════════════════════════════════════════════════════════════

class TestEndpointGroup:

    def _eg(self, **kw):
        return {"id": EG_ID, "name": "my-eg", "description": "",
                "filters": {"service_id": SERVICE_ID}, **kw}

    def test_list(self, invoke, mock_client):
        _iam(mock_client)
        mock_client.get.return_value = {"endpoint_groups": [self._eg()]}
        result = invoke(["endpoint-group", "list"])
        assert result.exit_code == 0
        assert "my-eg" in result.output

    def test_list_empty(self, invoke, mock_client):
        _iam(mock_client)
        mock_client.get.return_value = {"endpoint_groups": []}
        result = invoke(["endpoint-group", "list"])
        assert "No endpoint groups" in result.output

    def test_show(self, invoke, mock_client):
        _iam(mock_client)
        mock_client.get.return_value = {"endpoint_group": self._eg()}
        result = invoke(["endpoint-group", "show", EG_ID])
        assert result.exit_code == 0

    def test_create(self, invoke, mock_client):
        _iam(mock_client)
        mock_client.post.return_value = {"endpoint_group": self._eg()}
        result = invoke(["endpoint-group", "create",
                         "--name", "my-eg",
                         "--filter", f"service_id={SERVICE_ID}"])
        assert result.exit_code == 0
        body = mock_client.post.call_args[1]["json"]["endpoint_group"]
        assert body["name"] == "my-eg"
        assert body["filters"]["service_id"] == SERVICE_ID

    def test_create_invalid_filter(self, invoke, mock_client):
        _iam(mock_client)
        result = invoke(["endpoint-group", "create", "--name", "x", "--filter", "bad"])
        assert result.exit_code != 0

    def test_set(self, invoke, mock_client):
        _iam(mock_client)
        result = invoke(["endpoint-group", "set", EG_ID, "--name", "renamed"])
        assert result.exit_code == 0
        body = mock_client.patch.call_args[1]["json"]["endpoint_group"]
        assert body["name"] == "renamed"

    def test_set_nothing(self, invoke, mock_client):
        _iam(mock_client)
        result = invoke(["endpoint-group", "set", EG_ID])
        assert result.exit_code == 0
        mock_client.patch.assert_not_called()

    def test_delete_yes(self, invoke, mock_client):
        _iam(mock_client)
        result = invoke(["endpoint-group", "delete", EG_ID, "--yes"])
        assert result.exit_code == 0
        mock_client.delete.assert_called_once()

    def test_delete_requires_confirm(self, invoke, mock_client):
        _iam(mock_client)
        result = invoke(["endpoint-group", "delete", EG_ID], input="n\n")
        assert result.exit_code != 0
        mock_client.delete.assert_not_called()

    def test_add_project(self, invoke, mock_client):
        _iam(mock_client)
        result = invoke(["endpoint-group", "add-project", EG_ID, PROJECT_ID])
        assert result.exit_code == 0
        url = mock_client.put.call_args[0][0]
        assert f"endpoint_groups/{EG_ID}/projects/{PROJECT_ID}" in url

    def test_remove_project_yes(self, invoke, mock_client):
        _iam(mock_client)
        result = invoke(["endpoint-group", "remove-project", EG_ID, PROJECT_ID, "--yes"])
        assert result.exit_code == 0
        url = mock_client.delete.call_args[0][0]
        assert f"endpoint_groups/{EG_ID}/projects/{PROJECT_ID}" in url

    @pytest.mark.parametrize("sub", [
        "list", "show", "create", "set", "delete", "add-project", "remove-project",
    ])
    def test_help(self, invoke, sub):
        assert invoke(["endpoint-group", sub, "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════════
#  Access Rule
# ══════════════════════════════════════════════════════════════════════════════

class TestAccessRule:

    def _ar(self, **kw):
        return {"id": AR_ID, "service": "compute", "method": "GET",
                "path": "/v2.1/servers", **kw}

    def test_list(self, invoke, mock_client):
        _iam(mock_client)
        mock_client.get.return_value = {"access_rules": [self._ar()]}
        mock_client._token_data = {"user": {"id": USER_ID}}
        result = invoke(["access-rule", "list", "--user-id", USER_ID])
        assert result.exit_code == 0
        assert "compute" in result.output

    def test_list_empty(self, invoke, mock_client):
        _iam(mock_client)
        mock_client.get.return_value = {"access_rules": []}
        mock_client._token_data = {"user": {"id": USER_ID}}
        result = invoke(["access-rule", "list", "--user-id", USER_ID])
        assert "No access rules" in result.output

    def test_show(self, invoke, mock_client):
        _iam(mock_client)
        mock_client.get.return_value = {"access_rule": self._ar()}
        mock_client._token_data = {"user": {"id": USER_ID}}
        result = invoke(["access-rule", "show", AR_ID, "--user-id", USER_ID])
        assert result.exit_code == 0

    def test_delete_yes(self, invoke, mock_client):
        _iam(mock_client)
        mock_client._token_data = {"user": {"id": USER_ID}}
        result = invoke(["access-rule", "delete", AR_ID, "--user-id", USER_ID, "--yes"])
        assert result.exit_code == 0
        mock_client.delete.assert_called_once()

    def test_delete_requires_confirm(self, invoke, mock_client):
        _iam(mock_client)
        mock_client._token_data = {"user": {"id": USER_ID}}
        result = invoke(["access-rule", "delete", AR_ID, "--user-id", USER_ID], input="n\n")
        assert result.exit_code != 0
        mock_client.delete.assert_not_called()

    @pytest.mark.parametrize("sub", ["list", "show", "delete"])
    def test_help(self, invoke, sub):
        assert invoke(["access-rule", sub, "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════════
#  Token
# ══════════════════════════════════════════════════════════════════════════════

class TestToken:

    def test_issue(self, invoke, mock_client):
        _iam(mock_client)
        mock_client._token = "tok-abc"
        mock_client._token_data = {
            "user": {"id": USER_ID, "name": "admin"},
            "project": {"id": PROJECT_ID, "name": "myproject"},
            "domain": {},
            "catalog": [],
            "expires_at": "2026-01-01T00:00:00Z",
            "issued_at": "2025-12-31T00:00:00Z",
        }
        result = invoke(["token", "issue"])
        assert result.exit_code == 0
        assert "tok-abc" in result.output

    def test_revoke_yes(self, invoke, mock_client):
        _iam(mock_client)
        fake_token = "a" * 32
        result = invoke(["token", "revoke", fake_token, "--yes"])
        assert result.exit_code == 0
        assert mock_client.delete.call_args[1]["headers"]["X-Subject-Token"] == fake_token

    def test_revoke_requires_confirm(self, invoke, mock_client):
        _iam(mock_client)
        result = invoke(["token", "revoke", "a" * 32], input="n\n")
        assert result.exit_code != 0
        mock_client.delete.assert_not_called()

    @pytest.mark.parametrize("sub", ["issue", "revoke"])
    def test_help(self, invoke, sub):
        assert invoke(["token", sub, "--help"]).exit_code == 0
