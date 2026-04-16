"""Tests for ``orca secret`` commands."""

from __future__ import annotations

from unittest.mock import MagicMock

from orca_cli.core.config import save_profile, set_active_profile

# ── Helpers ────────────────────────────────────────────────────────────────

SECRET_ID = "11112222-3333-4444-5555-666677778888"
CONTAINER_ID = "aaaabbbb-cccc-dddd-eeee-ffffffffffff"


def _setup_mock(mock_client):
    mock_client.key_manager_url = "https://barbican.example.com"
    mock_client._token = "fake-token"

    http = MagicMock()
    mock_client._http = http

    posted = {}
    deleted = []

    def _get(url, **kwargs):
        if f"/secrets/{SECRET_ID}" in url and "/payload" not in url:
            return {
                "name": "my-secret", "secret_ref": f"https://barbican.example.com/v1/secrets/{SECRET_ID}",
                "secret_type": "opaque", "status": "ACTIVE", "algorithm": "AES",
                "bit_length": 256, "mode": "CBC",
                "expiration": None, "content_types": {"default": "text/plain"},
                "created": "2025-01-01T00:00:00", "updated": "2025-01-02T00:00:00",
            }
        if "/secrets" in url and "/containers" not in url:
            return {"secrets": [{
                "name": "my-secret",
                "secret_ref": f"https://barbican.example.com/v1/secrets/{SECRET_ID}",
                "secret_type": "opaque", "algorithm": "AES",
                "status": "ACTIVE", "created": "2025-01-01T00:00:00",
            }]}
        if f"/containers/{CONTAINER_ID}" in url:
            return {
                "name": "my-container",
                "container_ref": f"https://barbican.example.com/v1/containers/{CONTAINER_ID}",
                "type": "generic", "status": "ACTIVE",
                "created": "2025-01-01", "updated": "2025-01-02",
                "secret_refs": [
                    {"name": "key", "secret_ref": f"https://barbican.example.com/v1/secrets/{SECRET_ID}"},
                ],
            }
        if "/containers" in url:
            return {"containers": [{
                "name": "my-container",
                "container_ref": f"https://barbican.example.com/v1/containers/{CONTAINER_ID}",
                "type": "generic",
                "secret_refs": [{"name": "key", "secret_ref": "ref"}],
                "created": "2025-01-01",
            }]}
        return {}

    def _post(url, **kwargs):
        body = kwargs.get("json", {})
        posted.update(body)
        return {"secret_ref": "https://barbican.example.com/v1/secrets/new-id"}

    def _delete(url, **kwargs):
        deleted.append(url)

    mock_client.get = _get
    mock_client.post = _post
    mock_client.delete = _delete

    # For get-payload
    def _http_get(url, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        resp.text = "my-payload-value"
        return resp

    http.get = _http_get

    return {"posted": posted, "deleted": deleted}


# ══════════════════════════════════════════════════════════════════════════
#  secret list
# ══════════════════════════════════════════════════════════════════════════


class TestSecretList:

    def test_list(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["secret", "list"])
        assert result.exit_code == 0
        assert "my-sec" in result.output

    def test_list_empty(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        mock_client.key_manager_url = "https://barbican.example.com"
        mock_client.get = lambda url, **kw: {"secrets": []}

        result = invoke(["secret", "list"])
        assert result.exit_code == 0
        assert "No secrets found" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  secret show
# ══════════════════════════════════════════════════════════════════════════


class TestSecretShow:

    def test_show(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["secret", "show", SECRET_ID])
        assert result.exit_code == 0
        assert "my-secret" in result.output
        assert "opaque" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  secret create
# ══════════════════════════════════════════════════════════════════════════


class TestSecretCreate:

    def test_create(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["secret", "create", "new-secret", "--payload", "s3cret"])
        assert result.exit_code == 0
        assert "created" in result.output.lower()
        assert state["posted"]["name"] == "new-secret"
        assert state["posted"]["payload"] == "s3cret"

    def test_create_with_options(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["secret", "create", "my-key",
                         "--algorithm", "AES", "--bit-length", "256",
                         "--secret-type", "symmetric"])
        assert result.exit_code == 0
        assert state["posted"]["algorithm"] == "AES"
        assert state["posted"]["bit_length"] == 256
        assert state["posted"]["secret_type"] == "symmetric"


# ══════════════════════════════════════════════════════════════════════════
#  secret delete
# ══════════════════════════════════════════════════════════════════════════


class TestSecretDelete:

    def test_delete(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["secret", "delete", SECRET_ID, "-y"])
        assert result.exit_code == 0
        assert "deleted" in result.output.lower()
        assert len(state["deleted"]) == 1


# ══════════════════════════════════════════════════════════════════════════
#  secret get-payload
# ══════════════════════════════════════════════════════════════════════════


class TestSecretGetPayload:

    def test_get_payload(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["secret", "get-payload", SECRET_ID])
        assert result.exit_code == 0
        assert "my-payload" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  container-list
# ══════════════════════════════════════════════════════════════════════════


class TestContainerList:

    def test_list(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["secret", "container-list"])
        assert result.exit_code == 0
        assert "my-con" in result.output

    def test_list_empty(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        mock_client.key_manager_url = "https://barbican.example.com"
        mock_client.get = lambda url, **kw: {"containers": []}

        result = invoke(["secret", "container-list"])
        assert result.exit_code == 0
        assert "No containers found" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  container-show
# ══════════════════════════════════════════════════════════════════════════


class TestContainerShow:

    def test_show(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["secret", "container-show", CONTAINER_ID])
        assert result.exit_code == 0
        assert "my-container" in result.output
        assert "generic" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  container-delete
# ══════════════════════════════════════════════════════════════════════════


class TestContainerDelete:

    def test_delete(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _ = _setup_mock(mock_client)

        result = invoke(["secret", "container-delete", CONTAINER_ID, "-y"])
        assert result.exit_code == 0
        assert "deleted" in result.output.lower()


# ══════════════════════════════════════════════════════════════════════════
#  Help
# ══════════════════════════════════════════════════════════════════════════


class TestSecretHelp:

    def test_secret_help(self, invoke):
        result = invoke(["secret", "--help"])
        assert result.exit_code == 0
        for cmd in ("list", "show", "create", "delete", "get-payload",
                    "container-list", "container-show", "container-delete"):
            assert cmd in result.output


# ══════════════════════════════════════════════════════════════════════════
#  container-create / acl-get / acl-set / acl-delete
#  order-list / order-show / order-create / order-delete
# ══════════════════════════════════════════════════════════════════════════

_BARB = "https://barbican.example.com"
_ORDER_ID = "cccccccc-cccc-cccc-cccc-cccccccccccc"


class TestSecretContainerCreate:

    def test_create(self, invoke, mock_client):
        mock_client.key_manager_url = _BARB
        mock_client.post.return_value = {"container_ref": f"{_BARB}/v1/containers/{SECRET_ID}"}
        result = invoke(["secret", "container-create",
                         "--name", "my-cert", "--type", "generic"])
        assert result.exit_code == 0

    def test_create_with_secrets(self, invoke, mock_client):
        mock_client.key_manager_url = _BARB
        mock_client.post.return_value = {"container_ref": "ref"}
        result = invoke(["secret", "container-create",
                         "--type", "certificate",
                         "--secret", f"certificate={_BARB}/v1/secrets/{SECRET_ID}"])
        assert result.exit_code == 0
        body = mock_client.post.call_args[1]["json"]
        assert body["type"] == "certificate"
        assert len(body["secret_refs"]) == 1

    def test_help(self, invoke):
        assert invoke(["secret", "container-create", "--help"]).exit_code == 0


class TestSecretAcl:

    def test_acl_get(self, invoke, mock_client):
        mock_client.key_manager_url = _BARB
        mock_client.get.return_value = {
            "read": {"project-access": True, "users": [], "created": "", "updated": ""}
        }
        result = invoke(["secret", "acl-get", SECRET_ID])
        assert result.exit_code == 0

    def test_acl_set(self, invoke, mock_client):
        mock_client.key_manager_url = _BARB
        result = invoke(["secret", "acl-set", SECRET_ID,
                         "--user", "user-a", "--user", "user-b"])
        assert result.exit_code == 0
        body = mock_client.put.call_args[1]["json"]
        assert "read" in body
        assert "user-a" in body["read"]["users"]

    def test_acl_set_no_project_access(self, invoke, mock_client):
        mock_client.key_manager_url = _BARB
        invoke(["secret", "acl-set", SECRET_ID, "--no-project-access"])
        body = mock_client.put.call_args[1]["json"]
        assert body["read"]["project-access"] is False

    def test_acl_delete_yes(self, invoke, mock_client):
        mock_client.key_manager_url = _BARB
        result = invoke(["secret", "acl-delete", SECRET_ID, "--yes"])
        assert result.exit_code == 0
        mock_client.delete.assert_called_once()

    def test_acl_delete_requires_confirm(self, invoke, mock_client):
        mock_client.key_manager_url = _BARB
        result = invoke(["secret", "acl-delete", SECRET_ID], input="n\n")
        assert result.exit_code != 0
        mock_client.delete.assert_not_called()

    def test_acl_calls_correct_url(self, invoke, mock_client):
        mock_client.key_manager_url = _BARB
        mock_client.get.return_value = {"read": {}}
        invoke(["secret", "acl-get", SECRET_ID])
        url = mock_client.get.call_args[0][0]
        assert f"/v1/secrets/{SECRET_ID}/acl" in url

    def test_help_acl_get(self, invoke):
        assert invoke(["secret", "acl-get", "--help"]).exit_code == 0

    def test_help_acl_set(self, invoke):
        assert invoke(["secret", "acl-set", "--help"]).exit_code == 0

    def test_help_acl_delete(self, invoke):
        assert invoke(["secret", "acl-delete", "--help"]).exit_code == 0


class TestSecretOrders:

    def _order(self, **kw):
        return {"order_ref": f"{_BARB}/v1/orders/{_ORDER_ID}",
                "type": "key", "status": "ACTIVE", "created": "2026-01-01", **kw}

    def test_order_list(self, invoke, mock_client):
        mock_client.key_manager_url = _BARB
        mock_client.get.return_value = {"orders": [self._order()]}
        result = invoke(["secret", "order-list"])
        assert result.exit_code == 0
        assert "key" in result.output

    def test_order_list_empty(self, invoke, mock_client):
        mock_client.key_manager_url = _BARB
        mock_client.get.return_value = {"orders": []}
        result = invoke(["secret", "order-list"])
        assert "No orders" in result.output

    def test_order_show(self, invoke, mock_client):
        mock_client.key_manager_url = _BARB
        mock_client.get.return_value = {
            "order_ref": f"{_BARB}/v1/orders/{_ORDER_ID}",
            "type": "key", "status": "ACTIVE",
            "secret_ref": "", "created": "", "updated": "", "error_reason": "",
        }
        result = invoke(["secret", "order-show", _ORDER_ID])
        assert result.exit_code == 0

    def test_order_create_key(self, invoke, mock_client):
        mock_client.key_manager_url = _BARB
        mock_client.post.return_value = {"order_ref": f"{_BARB}/v1/orders/{_ORDER_ID}"}
        result = invoke(["secret", "order-create",
                         "--type", "key",
                         "--algorithm", "aes",
                         "--bit-length", "256"])
        assert result.exit_code == 0
        body = mock_client.post.call_args[1]["json"]
        assert body["type"] == "key"
        assert body["meta"]["algorithm"] == "aes"
        assert body["meta"]["bit_length"] == 256

    def test_order_delete_yes(self, invoke, mock_client):
        mock_client.key_manager_url = _BARB
        result = invoke(["secret", "order-delete", _ORDER_ID, "--yes"])
        assert result.exit_code == 0
        mock_client.delete.assert_called_once()

    def test_order_delete_requires_confirm(self, invoke, mock_client):
        mock_client.key_manager_url = _BARB
        result = invoke(["secret", "order-delete", _ORDER_ID], input="n\n")
        assert result.exit_code != 0
        mock_client.delete.assert_not_called()

    def test_help_order_list(self, invoke):
        assert invoke(["secret", "order-list", "--help"]).exit_code == 0

    def test_help_order_create(self, invoke):
        assert invoke(["secret", "order-create", "--help"]).exit_code == 0
