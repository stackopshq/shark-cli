"""Tests for ``orca placement`` commands (OpenStack Placement API)."""

from __future__ import annotations

import pytest

# ── Constants ─────────────────────────────────────────────────────────────────

RP_UUID  = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
RP2_UUID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
CONSUMER = "cccccccc-cccc-cccc-cccc-cccccccccccc"
BASE     = "https://placement.example.com"


def _placement(mc):
    mc.placement_url = BASE
    return mc


def _rp(**kw):
    return {
        "uuid": RP_UUID, "name": "compute-node-1", "generation": 0,
        "parent_provider_uuid": None, "root_provider_uuid": RP_UUID,
        **kw,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  Resource Providers
# ══════════════════════════════════════════════════════════════════════════════

class TestResourceProviderList:

    def test_list(self, invoke, mock_client):
        _placement(mock_client)
        mock_client.get.return_value = {"resource_providers": [_rp()]}
        result = invoke(["placement", "resource-provider-list"])
        assert result.exit_code == 0
        assert "compute" in result.output

    def test_list_empty(self, invoke, mock_client):
        _placement(mock_client)
        mock_client.get.return_value = {"resource_providers": []}
        result = invoke(["placement", "resource-provider-list"])
        assert "No resource providers" in result.output

    def test_filter_name(self, invoke, mock_client):
        _placement(mock_client)
        mock_client.get.return_value = {"resource_providers": []}
        invoke(["placement", "resource-provider-list", "--name", "compute"])
        assert mock_client.get.call_args[1]["params"]["name"] == "compute"

    def test_filter_in_tree(self, invoke, mock_client):
        _placement(mock_client)
        mock_client.get.return_value = {"resource_providers": []}
        invoke(["placement", "resource-provider-list", "--in-tree", RP_UUID])
        assert mock_client.get.call_args[1]["params"]["in_tree"] == RP_UUID

    def test_help(self, invoke):
        assert invoke(["placement", "resource-provider-list", "--help"]).exit_code == 0


class TestResourceProviderShow:

    def test_show(self, invoke, mock_client):
        _placement(mock_client)
        mock_client.get.return_value = _rp()
        result = invoke(["placement", "resource-provider-show", RP_UUID])
        assert result.exit_code == 0
        assert "compute" in result.output

    def test_help(self, invoke):
        assert invoke(["placement", "resource-provider-show", "--help"]).exit_code == 0


class TestResourceProviderCreate:

    def test_create(self, invoke, mock_client):
        _placement(mock_client)
        mock_client.post.return_value = _rp(name="new-rp")
        result = invoke(["placement", "resource-provider-create", "new-rp"])
        assert result.exit_code == 0
        body = mock_client.post.call_args[1]["json"]
        assert body["name"] == "new-rp"

    def test_create_with_parent(self, invoke, mock_client):
        _placement(mock_client)
        mock_client.post.return_value = _rp(parent_provider_uuid=RP2_UUID)
        result = invoke(["placement", "resource-provider-create", "child-rp",
                         "--parent-uuid", RP2_UUID])
        assert result.exit_code == 0
        body = mock_client.post.call_args[1]["json"]
        assert body["parent_provider_uuid"] == RP2_UUID

    def test_help(self, invoke):
        assert invoke(["placement", "resource-provider-create", "--help"]).exit_code == 0


class TestResourceProviderSet:

    def test_set_name(self, invoke, mock_client):
        _placement(mock_client)
        result = invoke(["placement", "resource-provider-set", RP_UUID,
                         "--name", "renamed"])
        assert result.exit_code == 0
        body = mock_client.put.call_args[1]["json"]
        assert body["name"] == "renamed"

    def test_set_nothing(self, invoke, mock_client):
        _placement(mock_client)
        result = invoke(["placement", "resource-provider-set", RP_UUID])
        assert result.exit_code == 0
        mock_client.put.assert_not_called()

    def test_help(self, invoke):
        assert invoke(["placement", "resource-provider-set", "--help"]).exit_code == 0


class TestResourceProviderDelete:

    def test_delete_yes(self, invoke, mock_client):
        _placement(mock_client)
        result = invoke(["placement", "resource-provider-delete", RP_UUID, "--yes"])
        assert result.exit_code == 0
        mock_client.delete.assert_called_once()

    def test_delete_requires_confirm(self, invoke, mock_client):
        _placement(mock_client)
        result = invoke(["placement", "resource-provider-delete", RP_UUID], input="n\n")
        assert result.exit_code != 0
        mock_client.delete.assert_not_called()

    def test_help(self, invoke):
        assert invoke(["placement", "resource-provider-delete", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════════
#  Inventories
# ══════════════════════════════════════════════════════════════════════════════

class TestInventory:

    def test_list(self, invoke, mock_client):
        _placement(mock_client)
        mock_client.get.return_value = {
            "inventories": {
                "VCPU": {"total": 64, "reserved": 0, "min_unit": 1,
                         "max_unit": 64, "step_size": 1, "allocation_ratio": 16.0},
            },
            "resource_provider_generation": 1,
        }
        result = invoke(["placement", "resource-provider-inventory-list", RP_UUID])
        assert result.exit_code == 0
        assert "VCPU" in result.output

    def test_list_empty(self, invoke, mock_client):
        _placement(mock_client)
        mock_client.get.return_value = {"inventories": {}, "resource_provider_generation": 0}
        result = invoke(["placement", "resource-provider-inventory-list", RP_UUID])
        assert "No inventories" in result.output

    def test_set(self, invoke, mock_client):
        _placement(mock_client)
        mock_client.get.return_value = _rp(generation=2)
        result = invoke(["placement", "resource-provider-inventory-set", RP_UUID, "VCPU",
                         "--total", "64"])
        assert result.exit_code == 0
        body = mock_client.put.call_args[1]["json"]
        assert body["total"] == 64
        assert body["resource_provider_generation"] == 2

    def test_delete_yes(self, invoke, mock_client):
        _placement(mock_client)
        result = invoke(["placement", "resource-provider-inventory-delete",
                         RP_UUID, "VCPU", "--yes"])
        assert result.exit_code == 0
        mock_client.delete.assert_called_once()

    def test_delete_requires_confirm(self, invoke, mock_client):
        _placement(mock_client)
        result = invoke(["placement", "resource-provider-inventory-delete",
                         RP_UUID, "VCPU"], input="n\n")
        assert result.exit_code != 0
        mock_client.delete.assert_not_called()

    def test_help_list(self, invoke):
        assert invoke(["placement", "resource-provider-inventory-list", "--help"]).exit_code == 0

    def test_help_set(self, invoke):
        assert invoke(["placement", "resource-provider-inventory-set", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════════
#  Usages
# ══════════════════════════════════════════════════════════════════════════════

class TestUsage:

    def test_rp_usage(self, invoke, mock_client):
        _placement(mock_client)
        mock_client.get.return_value = {"usages": {"VCPU": 8, "MEMORY_MB": 2048}}
        result = invoke(["placement", "resource-provider-usage", RP_UUID])
        assert result.exit_code == 0
        assert "VCPU" in result.output

    def test_rp_usage_empty(self, invoke, mock_client):
        _placement(mock_client)
        mock_client.get.return_value = {"usages": {}}
        result = invoke(["placement", "resource-provider-usage", RP_UUID])
        assert "No usages" in result.output

    def test_usage_list(self, invoke, mock_client):
        _placement(mock_client)
        mock_client.get.return_value = {"usages": {"VCPU": 16}}
        result = invoke(["placement", "usage-list", "--project-id", "proj-1"])
        assert result.exit_code == 0
        assert "VCPU" in result.output

    def test_usage_list_filters(self, invoke, mock_client):
        _placement(mock_client)
        mock_client.get.return_value = {"usages": {}}
        invoke(["placement", "usage-list", "--project-id", "p1", "--user-id", "u1"])
        params = mock_client.get.call_args[1]["params"]
        assert params["project_id"] == "p1"
        assert params["user_id"] == "u1"

    def test_help_rp_usage(self, invoke):
        assert invoke(["placement", "resource-provider-usage", "--help"]).exit_code == 0

    def test_help_usage_list(self, invoke):
        assert invoke(["placement", "usage-list", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════════
#  Resource Classes
# ══════════════════════════════════════════════════════════════════════════════

class TestResourceClass:

    def test_list(self, invoke, mock_client):
        _placement(mock_client)
        mock_client.get.return_value = {
            "resource_classes": [{"name": "VCPU"}, {"name": "MEMORY_MB"}, {"name": "DISK_GB"}]
        }
        result = invoke(["placement", "resource-class-list"])
        assert result.exit_code == 0
        assert "VCPU" in result.output

    def test_list_empty(self, invoke, mock_client):
        _placement(mock_client)
        mock_client.get.return_value = {"resource_classes": []}
        result = invoke(["placement", "resource-class-list"])
        assert "No resource classes" in result.output

    def test_show(self, invoke, mock_client):
        _placement(mock_client)
        mock_client.get.return_value = {}
        result = invoke(["placement", "resource-class-show", "VCPU"])
        assert result.exit_code == 0
        assert "VCPU" in result.output

    def test_create(self, invoke, mock_client):
        _placement(mock_client)
        result = invoke(["placement", "resource-class-create", "CUSTOM_GPU"])
        assert result.exit_code == 0
        url = mock_client.put.call_args[0][0]
        assert "CUSTOM_GPU" in url

    def test_delete_yes(self, invoke, mock_client):
        _placement(mock_client)
        result = invoke(["placement", "resource-class-delete", "CUSTOM_GPU", "--yes"])
        assert result.exit_code == 0
        mock_client.delete.assert_called_once()

    def test_delete_requires_confirm(self, invoke, mock_client):
        _placement(mock_client)
        result = invoke(["placement", "resource-class-delete", "CUSTOM_GPU"], input="n\n")
        assert result.exit_code != 0
        mock_client.delete.assert_not_called()

    def test_help_list(self, invoke):
        assert invoke(["placement", "resource-class-list", "--help"]).exit_code == 0

    def test_help_create(self, invoke):
        assert invoke(["placement", "resource-class-create", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════════
#  Traits
# ══════════════════════════════════════════════════════════════════════════════

class TestTrait:

    def test_list(self, invoke, mock_client):
        _placement(mock_client)
        mock_client.get.return_value = {
            "traits": ["HW_CPU_X86_AVX2", "CUSTOM_HPC_ENABLED"]
        }
        result = invoke(["placement", "trait-list"])
        assert result.exit_code == 0
        assert "HW_CPU" in result.output

    def test_list_empty(self, invoke, mock_client):
        _placement(mock_client)
        mock_client.get.return_value = {"traits": []}
        result = invoke(["placement", "trait-list"])
        assert "No traits" in result.output

    def test_list_filter(self, invoke, mock_client):
        _placement(mock_client)
        mock_client.get.return_value = {"traits": []}
        invoke(["placement", "trait-list", "--name", "CUSTOM"])
        assert mock_client.get.call_args[1]["params"]["name"] == "CUSTOM"

    def test_list_associated(self, invoke, mock_client):
        _placement(mock_client)
        mock_client.get.return_value = {"traits": []}
        invoke(["placement", "trait-list", "--associated"])
        assert mock_client.get.call_args[1]["params"]["associated"] == "true"

    def test_create(self, invoke, mock_client):
        _placement(mock_client)
        result = invoke(["placement", "trait-create", "CUSTOM_HPC_ENABLED"])
        assert result.exit_code == 0
        url = mock_client.put.call_args[0][0]
        assert "CUSTOM_HPC_ENABLED" in url

    def test_delete_yes(self, invoke, mock_client):
        _placement(mock_client)
        result = invoke(["placement", "trait-delete", "CUSTOM_HPC_ENABLED", "--yes"])
        assert result.exit_code == 0
        mock_client.delete.assert_called_once()

    def test_delete_requires_confirm(self, invoke, mock_client):
        _placement(mock_client)
        result = invoke(["placement", "trait-delete", "CUSTOM_HPC_ENABLED"], input="n\n")
        assert result.exit_code != 0
        mock_client.delete.assert_not_called()

    def test_help_list(self, invoke):
        assert invoke(["placement", "trait-list", "--help"]).exit_code == 0

    def test_help_create(self, invoke):
        assert invoke(["placement", "trait-create", "--help"]).exit_code == 0


class TestResourceProviderTrait:

    def test_list(self, invoke, mock_client):
        _placement(mock_client)
        mock_client.get.return_value = {
            "traits": ["CUSTOM_HPC_ENABLED"],
            "resource_provider_generation": 1,
        }
        result = invoke(["placement", "resource-provider-trait-list", RP_UUID])
        assert result.exit_code == 0
        assert "CUSTOM" in result.output

    def test_list_empty(self, invoke, mock_client):
        _placement(mock_client)
        mock_client.get.return_value = {"traits": [], "resource_provider_generation": 0}
        result = invoke(["placement", "resource-provider-trait-list", RP_UUID])
        assert "No traits" in result.output

    def test_set(self, invoke, mock_client):
        _placement(mock_client)
        mock_client.get.return_value = _rp(generation=3)
        result = invoke(["placement", "resource-provider-trait-set", RP_UUID,
                         "CUSTOM_HPC_ENABLED", "HW_CPU_X86_AVX2"])
        assert result.exit_code == 0
        body = mock_client.put.call_args[1]["json"]
        assert "CUSTOM_HPC_ENABLED" in body["traits"]
        assert body["resource_provider_generation"] == 3

    def test_delete_yes(self, invoke, mock_client):
        _placement(mock_client)
        result = invoke(["placement", "resource-provider-trait-delete", RP_UUID, "--yes"])
        assert result.exit_code == 0
        mock_client.delete.assert_called_once()

    def test_delete_requires_confirm(self, invoke, mock_client):
        _placement(mock_client)
        result = invoke(["placement", "resource-provider-trait-delete", RP_UUID], input="n\n")
        assert result.exit_code != 0
        mock_client.delete.assert_not_called()

    def test_help_list(self, invoke):
        assert invoke(["placement", "resource-provider-trait-list", "--help"]).exit_code == 0

    def test_help_set(self, invoke):
        assert invoke(["placement", "resource-provider-trait-set", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════════
#  Allocations
# ══════════════════════════════════════════════════════════════════════════════

class TestAllocation:

    def test_show(self, invoke, mock_client):
        _placement(mock_client)
        mock_client.get.return_value = {
            "allocations": {
                RP_UUID: {"resources": {"VCPU": 4, "MEMORY_MB": 1024}},
            },
            "project_id": "proj-1",
            "user_id": "user-1",
        }
        result = invoke(["placement", "allocation-show", CONSUMER])
        assert result.exit_code == 0
        assert "VCPU" in result.output

    def test_show_empty(self, invoke, mock_client):
        _placement(mock_client)
        mock_client.get.return_value = {"allocations": {}}
        result = invoke(["placement", "allocation-show", CONSUMER])
        assert "No allocations" in result.output

    def test_delete_yes(self, invoke, mock_client):
        _placement(mock_client)
        result = invoke(["placement", "allocation-delete", CONSUMER, "--yes"])
        assert result.exit_code == 0
        mock_client.delete.assert_called_once()

    def test_delete_requires_confirm(self, invoke, mock_client):
        _placement(mock_client)
        result = invoke(["placement", "allocation-delete", CONSUMER], input="n\n")
        assert result.exit_code != 0
        mock_client.delete.assert_not_called()

    def test_set(self, invoke, mock_client):
        _placement(mock_client)
        result = invoke(["placement", "allocation-set", CONSUMER,
                         "--resource-provider", RP_UUID,
                         "--resource", "VCPU=4",
                         "--resource", "MEMORY_MB=1024",
                         "--project-id", "proj-1",
                         "--user-id", "user-1"])
        assert result.exit_code == 0
        body = mock_client.put.call_args[1]["json"]
        assert body["allocations"][RP_UUID]["resources"]["VCPU"] == 4
        assert body["project_id"] == "proj-1"

    def test_set_invalid_resource(self, invoke, mock_client):
        _placement(mock_client)
        result = invoke(["placement", "allocation-set", CONSUMER,
                         "--resource-provider", RP_UUID,
                         "--resource", "BADFORMAT",
                         "--project-id", "proj-1",
                         "--user-id", "user-1"])
        assert result.exit_code != 0

    def test_help_show(self, invoke):
        assert invoke(["placement", "allocation-show", "--help"]).exit_code == 0

    def test_help_delete(self, invoke):
        assert invoke(["placement", "allocation-delete", "--help"]).exit_code == 0

    def test_help_set(self, invoke):
        assert invoke(["placement", "allocation-set", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════════
#  Allocation Candidates
# ══════════════════════════════════════════════════════════════════════════════

class TestAllocationCandidates:

    def _candidate(self):
        return {
            "allocations": {
                RP_UUID: {"resources": {"VCPU": 4, "MEMORY_MB": 1024}},
            }
        }

    def test_list(self, invoke, mock_client):
        _placement(mock_client)
        mock_client.get.return_value = {
            "allocation_requests": [self._candidate()],
            "provider_summaries": {},
        }
        result = invoke(["placement", "allocation-candidate-list",
                         "--resource", "VCPU=4"])
        assert result.exit_code == 0
        assert "VCPU" in result.output

    def test_list_empty(self, invoke, mock_client):
        _placement(mock_client)
        mock_client.get.return_value = {"allocation_requests": [], "provider_summaries": {}}
        result = invoke(["placement", "allocation-candidate-list",
                         "--resource", "VCPU=4"])
        assert "No allocation candidates" in result.output

    def test_list_with_traits(self, invoke, mock_client):
        _placement(mock_client)
        mock_client.get.return_value = {"allocation_requests": [], "provider_summaries": {}}
        invoke(["placement", "allocation-candidate-list",
                "--resource", "VCPU=4",
                "--required", "HW_CPU_X86_AVX2",
                "--forbidden", "CUSTOM_NO_LIVE_MIGRATION"])
        params = mock_client.get.call_args[1]["params"]
        assert "HW_CPU_X86_AVX2" in params["required"]
        assert "!CUSTOM_NO_LIVE_MIGRATION" in params["forbidden"]

    def test_help(self, invoke):
        assert invoke(["placement", "allocation-candidate-list", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════════
#  Resource Provider Aggregates
# ══════════════════════════════════════════════════════════════════════════════

AGG_UUID = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"


class TestResourceProviderAggregate:

    def test_list(self, invoke, mock_client):
        _placement(mock_client)
        mock_client.get.return_value = {
            "aggregates": [AGG_UUID],
            "resource_provider_generation": 1,
        }
        result = invoke(["placement", "resource-provider-aggregate-list", RP_UUID])
        assert result.exit_code == 0
        assert "eeee" in result.output

    def test_list_empty(self, invoke, mock_client):
        _placement(mock_client)
        mock_client.get.return_value = {"aggregates": [], "resource_provider_generation": 0}
        result = invoke(["placement", "resource-provider-aggregate-list", RP_UUID])
        assert "No aggregates" in result.output

    def test_set(self, invoke, mock_client):
        _placement(mock_client)
        mock_client.get.return_value = _rp(generation=1)
        result = invoke(["placement", "resource-provider-aggregate-set", RP_UUID, AGG_UUID])
        assert result.exit_code == 0
        body = mock_client.put.call_args[1]["json"]
        assert AGG_UUID in body["aggregates"]
        assert body["resource_provider_generation"] == 1

    def test_delete_yes(self, invoke, mock_client):
        _placement(mock_client)
        mock_client.get.return_value = _rp(generation=2)
        result = invoke(["placement", "resource-provider-aggregate-delete", RP_UUID, "--yes"])
        assert result.exit_code == 0
        body = mock_client.put.call_args[1]["json"]
        assert body["aggregates"] == []

    def test_delete_requires_confirm(self, invoke, mock_client):
        _placement(mock_client)
        result = invoke(["placement", "resource-provider-aggregate-delete", RP_UUID],
                        input="n\n")
        assert result.exit_code != 0

    def test_help_list(self, invoke):
        assert invoke(["placement", "resource-provider-aggregate-list", "--help"]).exit_code == 0

    def test_help_set(self, invoke):
        assert invoke(["placement", "resource-provider-aggregate-set", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════════
#  Inventory — show single / delete all
# ══════════════════════════════════════════════════════════════════════════════

class TestInventoryExtra:

    def test_show_single(self, invoke, mock_client):
        _placement(mock_client)
        mock_client.get.return_value = {
            "total": 64, "reserved": 0, "min_unit": 1,
            "max_unit": 64, "step_size": 1, "allocation_ratio": 16.0,
            "resource_provider_generation": 1,
        }
        result = invoke(["placement", "resource-provider-inventory-show", RP_UUID, "VCPU"])
        assert result.exit_code == 0
        assert "64" in result.output

    def test_delete_all_yes(self, invoke, mock_client):
        _placement(mock_client)
        result = invoke(["placement", "resource-provider-inventory-delete-all",
                         RP_UUID, "--yes"])
        assert result.exit_code == 0
        mock_client.delete.assert_called_once()

    def test_delete_all_requires_confirm(self, invoke, mock_client):
        _placement(mock_client)
        result = invoke(["placement", "resource-provider-inventory-delete-all", RP_UUID],
                        input="n\n")
        assert result.exit_code != 0
        mock_client.delete.assert_not_called()

    def test_help_show(self, invoke):
        assert invoke(["placement", "resource-provider-inventory-show", "--help"]).exit_code == 0

    def test_help_delete_all(self, invoke):
        assert invoke(["placement", "resource-provider-inventory-delete-all",
                       "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════════
#  Registration
# ══════════════════════════════════════════════════════════════════════════════

class TestRegistration:

    @pytest.mark.parametrize("sub", [
        "resource-provider-list", "resource-provider-show",
        "resource-provider-create", "resource-provider-set", "resource-provider-delete",
        "resource-provider-inventory-list", "resource-provider-inventory-set",
        "resource-provider-inventory-delete",
        "resource-provider-inventory-show", "resource-provider-inventory-delete-all",
        "resource-provider-usage",
        "resource-provider-trait-list", "resource-provider-trait-set",
        "resource-provider-trait-delete",
        "usage-list",
        "resource-class-list", "resource-class-show",
        "resource-class-create", "resource-class-delete",
        "trait-list", "trait-create", "trait-delete",
        "allocation-show", "allocation-delete", "allocation-set",
        "allocation-candidate-list",
        "resource-provider-aggregate-list", "resource-provider-aggregate-set",
        "resource-provider-aggregate-delete",
    ])
    def test_subcommand_help(self, invoke, sub):
        assert invoke(["placement", sub, "--help"]).exit_code == 0
