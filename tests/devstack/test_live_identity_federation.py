"""Live e2e: Keystone federation (SAML2/OIDC config).

Covers ``identity-provider`` (5), ``federation-protocol`` (5),
``mapping`` (5), ``service-provider`` (5) — 20 cmds.

These are CRUD operations on Keystone config objects; they don't
require an actual IdP backend running. We just verify orca pushes
the right shape to Keystone.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.live


def test_identity_provider_full(live_invoke, cleanup, live_name):
    idp_id = live_name("idp")
    res = live_invoke("identity-provider", "create", idp_id,
                      "--description", "live test idp",
                      "--remote-id", "https://example.com/idp",
                      "--enable")
    assert res.exit_code == 0, res.output
    cleanup(lambda: live_invoke("identity-provider", "delete", idp_id, "--yes"))

    res = live_invoke("identity-provider", "set", idp_id, "--description", "updated")
    assert res.exit_code == 0, res.output

    res = live_invoke("identity-provider", "list", "-f", "value", "-c", "ID")
    assert res.exit_code == 0
    assert idp_id in res.output

    res = live_invoke("identity-provider", "show", idp_id,
                      "-f", "value", "-c", "description")
    assert res.exit_code == 0
    assert "updated" in res.output


def test_mapping_full(live_invoke, cleanup, live_name):
    mapping_id = live_name("map")
    rules = (
        '[{"local": [{"user": {"name": "{0}"}}], '
        '"remote": [{"type": "openstack_user"}]}]'
    )
    res = live_invoke("mapping", "create", mapping_id, "--rules", rules)
    assert res.exit_code == 0, res.output
    cleanup(lambda: live_invoke("mapping", "delete", mapping_id, "--yes"))

    new_rules = (
        '[{"local": [{"user": {"name": "{0}"}}, '
        '{"group": {"id": "abc"}}], '
        '"remote": [{"type": "openstack_user"}, {"type": "groups"}]}]'
    )
    res = live_invoke("mapping", "set", mapping_id, "--rules", new_rules)
    assert res.exit_code == 0, res.output

    res = live_invoke("mapping", "list", "-f", "value", "-c", "ID")
    assert res.exit_code == 0
    assert mapping_id in res.output

    # mapping show prints raw JSON (no output_options decorator).
    res = live_invoke("mapping", "show", mapping_id)
    assert res.exit_code == 0, res.output
    assert mapping_id in res.output


def test_federation_protocol_full(live_invoke, cleanup, live_name):
    # Need an IdP and a mapping.
    idp_id = live_name("idp")
    res = live_invoke("identity-provider", "create", idp_id, "--enable")
    assert res.exit_code == 0, res.output
    cleanup(lambda: live_invoke("identity-provider", "delete", idp_id, "--yes"))

    mapping_id = live_name("map")
    rules = (
        '[{"local": [{"user": {"name": "{0}"}}], '
        '"remote": [{"type": "openstack_user"}]}]'
    )
    res = live_invoke("mapping", "create", mapping_id, "--rules", rules)
    assert res.exit_code == 0, res.output
    cleanup(lambda: live_invoke("mapping", "delete", mapping_id, "--yes"))

    # Now the protocol bound to the IdP.
    proto_id = "saml2"
    res = live_invoke("federation-protocol", "create",
                      idp_id, proto_id, "--mapping-id", mapping_id)
    assert res.exit_code == 0, res.output
    cleanup(lambda: live_invoke("federation-protocol", "delete",
                                idp_id, proto_id, "--yes"))

    # Re-bind to a different mapping (set)
    mapping2_id = live_name("map2")
    res = live_invoke("mapping", "create", mapping2_id, "--rules", rules)
    assert res.exit_code == 0, res.output
    cleanup(lambda: live_invoke("mapping", "delete", mapping2_id, "--yes"))

    res = live_invoke("federation-protocol", "set",
                      idp_id, proto_id, "--mapping-id", mapping2_id)
    assert res.exit_code == 0, res.output

    res = live_invoke("federation-protocol", "list", idp_id,
                      "-f", "value", "-c", "ID")
    assert res.exit_code == 0
    assert proto_id in res.output

    res = live_invoke("federation-protocol", "show", idp_id, proto_id,
                      "-f", "value", "-c", "mapping_id")
    assert res.exit_code == 0


def test_service_provider_full(live_invoke, cleanup, live_name):
    sp_id = live_name("sp")
    res = live_invoke("service-provider", "create", sp_id,
                      "--auth-url", "https://remote.example.com/identity",
                      "--sp-url", "https://remote.example.com/Shibboleth.sso/SAML2/ECP",
                      "--description", "live test sp",
                      "--enable")
    assert res.exit_code == 0, res.output
    cleanup(lambda: live_invoke("service-provider", "delete", sp_id, "--yes"))

    res = live_invoke("service-provider", "set", sp_id, "--description", "updated")
    assert res.exit_code == 0, res.output

    res = live_invoke("service-provider", "list", "-f", "value", "-c", "ID")
    assert res.exit_code == 0
    assert sp_id in res.output

    res = live_invoke("service-provider", "show", sp_id,
                      "-f", "value", "-c", "description")
    assert res.exit_code == 0
    assert "updated" in res.output
