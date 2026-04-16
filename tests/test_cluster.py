"""Tests for ``orca cluster`` commands."""

from __future__ import annotations

from orca_cli.core.config import save_profile, set_active_profile


# ── Helpers ────────────────────────────────────────────────────────────────

CLUSTER_ID = "11112222-3333-4444-5555-666677778888"
TEMPLATE_ID = "aaaabbbb-cccc-dddd-eeee-ffffffffffff"


def _cluster(uuid=CLUSTER_ID, name="my-k8s", status="CREATE_COMPLETE"):
    return {
        "uuid": uuid, "name": name, "status": status,
        "status_reason": "Stack CREATE completed",
        "coe_version": "v1.21.5", "api_address": "https://10.0.0.5:6443",
        "master_count": 1, "node_count": 3,
        "master_addresses": ["10.0.0.5"],
        "node_addresses": ["10.0.0.10", "10.0.0.11", "10.0.0.12"],
        "cluster_template_id": TEMPLATE_ID, "keypair": "my-key",
        "stack_id": "stack-1", "create_timeout": 60,
        "created_at": "2025-01-01", "updated_at": None,
    }


def _template(uuid=TEMPLATE_ID, name="k8s-tmpl"):
    return {
        "uuid": uuid, "name": name, "coe": "kubernetes",
        "image_id": "img-1", "keypair_id": "my-key",
        "external_network_id": "ext-net",
        "fixed_network": None, "fixed_subnet": None,
        "network_driver": "flannel", "volume_driver": "cinder",
        "docker_volume_size": 50, "server_type": "vm",
        "master_flavor_id": "m1.large", "flavor_id": "m1.medium",
        "dns_nameserver": "8.8.8.8", "public": False,
        "tls_disabled": False, "master_lb_enabled": True,
        "floating_ip_enabled": True, "labels": {},
        "created_at": "2025-01-01", "updated_at": None,
    }


def _setup_mock(mock_client):
    mock_client.container_infra_url = "https://magnum.example.com/v1"

    posted = {}
    patched = {}
    deleted = []

    def _get(url, **kwargs):
        if f"/clusters/{CLUSTER_ID}" in url:
            return _cluster()
        if "/clusters" in url:
            return {"clusters": [_cluster()]}
        if f"/clustertemplates/{TEMPLATE_ID}" in url:
            return _template()
        if "/clustertemplates" in url:
            return {"clustertemplates": [_template()]}
        return {}

    def _post(url, **kwargs):
        body = kwargs.get("json", {})
        posted["last_body"] = body
        if "/clustertemplates" in url:
            return {"uuid": "new-tmpl", "name": body.get("name", "")}
        if "/clusters" in url:
            return {"uuid": "new-cluster", "name": body.get("name", "")}
        return {}

    def _patch(url, **kwargs):
        patched["last_body"] = kwargs.get("json", {})

    def _delete(url, **kwargs):
        deleted.append(url)

    mock_client.get = _get
    mock_client.post = _post
    mock_client.patch = _patch
    mock_client.delete = _delete

    return {"posted": posted, "patched": patched, "deleted": deleted}


# ══════════════════════════════════════════════════════════════════════════
#  cluster list
# ══════════════════════════════════════════════════════════════════════════


class TestClusterList:

    def test_list(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["cluster", "list"])
        assert result.exit_code == 0
        assert "my-" in result.output

    def test_list_empty(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        mock_client.container_infra_url = "https://magnum.example.com/v1"
        mock_client.get = lambda url, **kw: {"clusters": []}

        result = invoke(["cluster", "list"])
        assert result.exit_code == 0
        assert "No clusters found" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  cluster show
# ══════════════════════════════════════════════════════════════════════════


class TestClusterShow:

    def test_show(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["cluster", "show", CLUSTER_ID])
        assert result.exit_code == 0
        assert "my-k8s" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  cluster create
# ══════════════════════════════════════════════════════════════════════════


class TestClusterCreate:

    def test_create(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["cluster", "create", "prod-k8s",
                         "--template", TEMPLATE_ID, "--node-count", "3"])
        assert result.exit_code == 0
        assert "creation started" in result.output
        body = state["posted"]["last_body"]
        assert body["name"] == "prod-k8s"
        assert body["node_count"] == 3

    def test_create_with_options(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["cluster", "create", "dev",
                         "--template", TEMPLATE_ID,
                         "--master-count", "3",
                         "--keypair", "my-key",
                         "--flavor", "m1.large"])
        assert result.exit_code == 0
        body = state["posted"]["last_body"]
        assert body["master_count"] == 3
        assert body["keypair"] == "my-key"
        assert body["flavor_id"] == "m1.large"


# ══════════════════════════════════════════════════════════════════════════
#  cluster delete
# ══════════════════════════════════════════════════════════════════════════


class TestClusterDelete:

    def test_delete(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["cluster", "delete", CLUSTER_ID, "-y"])
        assert result.exit_code == 0
        assert "deletion started" in result.output
        assert len(state["deleted"]) == 1


# ══════════════════════════════════════════════════════════════════════════
#  cluster resize
# ══════════════════════════════════════════════════════════════════════════


class TestClusterResize:

    def test_resize(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["cluster", "resize", CLUSTER_ID, "--node-count", "5"])
        assert result.exit_code == 0
        assert "resize" in result.output.lower()


# ══════════════════════════════════════════════════════════════════════════
#  cluster kubeconfig
# ══════════════════════════════════════════════════════════════════════════


class TestClusterKubeconfig:

    def test_kubeconfig(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["cluster", "kubeconfig", CLUSTER_ID])
        assert result.exit_code == 0
        assert "API URL" in result.output
        assert "10.0.0.5" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  template-list / template-show
# ══════════════════════════════════════════════════════════════════════════


class TestClusterTemplates:

    def test_template_list(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["cluster", "template-list"])
        assert result.exit_code == 0
        assert "k8s" in result.output

    def test_template_list_empty(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        mock_client.container_infra_url = "https://magnum.example.com/v1"
        mock_client.get = lambda url, **kw: {"clustertemplates": []}

        result = invoke(["cluster", "template-list"])
        assert result.exit_code == 0
        assert "No cluster templates found" in result.output

    def test_template_show(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["cluster", "template-show", TEMPLATE_ID])
        assert result.exit_code == 0
        assert "k8s-tmpl" in result.output

    def test_template_create(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["cluster", "template-create", "new-tmpl",
                         "--image", "img-1", "--external-network", "ext-net",
                         "--coe", "kubernetes"])
        assert result.exit_code == 0
        assert "created" in result.output
        body = state["posted"]["last_body"]
        assert body["name"] == "new-tmpl"
        assert body["coe"] == "kubernetes"

    def test_template_delete(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["cluster", "template-delete", TEMPLATE_ID, "-y"])
        assert result.exit_code == 0
        assert "deleted" in result.output.lower()
        assert len(state["deleted"]) == 1


# ══════════════════════════════════════════════════════════════════════════
#  Help
# ══════════════════════════════════════════════════════════════════════════


class TestClusterHelp:

    def test_cluster_help(self, invoke):
        result = invoke(["cluster", "--help"])
        assert result.exit_code == 0
        for cmd in ("list", "show", "create", "delete", "resize",
                    "kubeconfig", "template-list", "template-show",
                    "template-create", "template-delete"):
            assert cmd in result.output


# ══════════════════════════════════════════════════════════════════════════
#  cluster upgrade / nodegroup CRUD
# ══════════════════════════════════════════════════════════════════════════

NG_ID = "11111111-1111-1111-1111-111111111111"


class TestClusterUpgrade:

    def test_upgrade(self, invoke, mock_client):
        mock_client.container_infra_url = "https://magnum.example.com/v1"
        result = invoke(["cluster", "upgrade", CLUSTER_ID, "--template-id", "new-tmpl"])
        assert result.exit_code == 0
        mock_client.post.assert_called_once()
        url = mock_client.post.call_args[0][0]
        assert f"/clusters/{CLUSTER_ID}/actions/upgrade" in url

    def test_help(self, invoke):
        assert invoke(["cluster", "upgrade", "--help"]).exit_code == 0


class TestNodegroupList:

    def test_list(self, invoke, mock_client):
        mock_client.container_infra_url = "https://magnum.example.com/v1"
        mock_client.get.return_value = {"nodegroups": [
            {"uuid": NG_ID, "name": "default-worker", "role": "worker",
             "node_count": 3, "status": "CREATE_COMPLETE", "flavor_id": "m1.medium"},
        ]}
        result = invoke(["cluster", "nodegroup-list", CLUSTER_ID])
        assert result.exit_code == 0
        assert "work" in result.output

    def test_list_empty(self, invoke, mock_client):
        mock_client.container_infra_url = "https://magnum.example.com/v1"
        mock_client.get.return_value = {"nodegroups": []}
        result = invoke(["cluster", "nodegroup-list", CLUSTER_ID])
        assert "No node groups" in result.output

    def test_help(self, invoke):
        assert invoke(["cluster", "nodegroup-list", "--help"]).exit_code == 0


class TestNodegroupShow:

    def test_show(self, invoke, mock_client):
        mock_client.container_infra_url = "https://magnum.example.com/v1"
        mock_client.get.return_value = {
            "uuid": NG_ID, "name": "default-worker", "cluster_id": CLUSTER_ID,
            "role": "worker", "flavor_id": "m1.medium", "image_id": "",
            "node_count": 3, "min_node_count": 1, "max_node_count": 10,
            "status": "CREATE_COMPLETE", "status_reason": "",
            "created_at": "", "updated_at": "",
        }
        result = invoke(["cluster", "nodegroup-show", CLUSTER_ID, NG_ID])
        assert result.exit_code == 0
        assert "work" in result.output

    def test_help(self, invoke):
        assert invoke(["cluster", "nodegroup-show", "--help"]).exit_code == 0


class TestNodegroupCreate:

    def test_create(self, invoke, mock_client):
        mock_client.container_infra_url = "https://magnum.example.com/v1"
        mock_client.post.return_value = {"uuid": NG_ID}
        result = invoke(["cluster", "nodegroup-create", CLUSTER_ID,
                         "--name", "gpu-pool",
                         "--flavor-id", "gpu.medium",
                         "--node-count", "2"])
        assert result.exit_code == 0
        body = mock_client.post.call_args[1]["json"]
        assert body["name"] == "gpu-pool"
        assert body["node_count"] == 2

    def test_help(self, invoke):
        assert invoke(["cluster", "nodegroup-create", "--help"]).exit_code == 0


class TestNodegroupUpdate:

    def test_update_node_count(self, invoke, mock_client):
        mock_client.container_infra_url = "https://magnum.example.com/v1"
        result = invoke(["cluster", "nodegroup-update", CLUSTER_ID, NG_ID,
                         "--node-count", "5"])
        assert result.exit_code == 0
        ops = mock_client.patch.call_args[1]["json"]
        assert any(op["path"] == "/node_count" and op["value"] == 5 for op in ops)

    def test_update_nothing(self, invoke, mock_client):
        mock_client.container_infra_url = "https://magnum.example.com/v1"
        result = invoke(["cluster", "nodegroup-update", CLUSTER_ID, NG_ID])
        assert result.exit_code == 0
        mock_client.patch.assert_not_called()

    def test_help(self, invoke):
        assert invoke(["cluster", "nodegroup-update", "--help"]).exit_code == 0


class TestNodegroupDelete:

    def test_delete_yes(self, invoke, mock_client):
        mock_client.container_infra_url = "https://magnum.example.com/v1"
        result = invoke(["cluster", "nodegroup-delete", CLUSTER_ID, NG_ID, "--yes"])
        assert result.exit_code == 0
        mock_client.delete.assert_called_once()

    def test_delete_requires_confirm(self, invoke, mock_client):
        mock_client.container_infra_url = "https://magnum.example.com/v1"
        result = invoke(["cluster", "nodegroup-delete", CLUSTER_ID, NG_ID], input="n\n")
        assert result.exit_code != 0
        mock_client.delete.assert_not_called()

    def test_help(self, invoke):
        assert invoke(["cluster", "nodegroup-delete", "--help"]).exit_code == 0
