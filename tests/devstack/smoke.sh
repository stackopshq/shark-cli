#!/usr/bin/env bash
# Smoke test: run a representative `list` for every orca module that maps to
# a service activated by tests/devstack/local.conf. Fast (read-only), exits
# non-zero on any failure.
#
# Usage:
#   ORCA_PROFILE=devstack tests/devstack/smoke.sh
#
# The profile must already exist (auth_url, admin/secret, RegionOne).

set -u
ORCA="${ORCA:-.venv/bin/orca}"
PROFILE="${ORCA_PROFILE:-devstack}"

PASS=0
FAIL=0
SKIP=0
FAILED_CMDS=()

run() {
    local label="$1"; shift
    printf '  %-40s ' "$label"
    if out=$("$ORCA" -P "$PROFILE" "$@" -f value 2>&1); then
        printf 'PASS\n'
        PASS=$((PASS + 1))
    else
        printf 'FAIL\n'
        FAIL=$((FAIL + 1))
        FAILED_CMDS+=("$label :: $* :: ${out:0:200}")
    fi
}

skip() {
    printf '  %-40s SKIP (%s)\n' "$1" "$2"
    SKIP=$((SKIP + 1))
}

echo "=== orca DevStack smoke test (profile: $PROFILE) ==="

echo "[1] identity (keystone)"
run "user list"             user list
run "project list"          project list
run "role list"             role list
run "domain list"           domain list
run "service list"          service list
run "endpoint list"         endpoint list
run "region list"           region list

echo "[2] catalog"
run "catalog"               catalog

echo "[3] image (glance)"
run "image list"            image list

echo "[4] compute (nova)"
run "flavor list"           flavor list
run "hypervisor list"       hypervisor list
run "availability-zone list" availability-zone list
run "aggregate list"        aggregate list
run "keypair list"          keypair list

echo "[5] server (nova)"
run "server list"           server list

echo "[6] placement"
run "placement resource-provider-list" placement resource-provider-list
run "placement resource-class-list" placement resource-class-list

echo "[7] network (neutron)"
run "network list"          network list
run "network subnet list"   network subnet list
run "floating-ip list"      floating-ip list
run "security-group list"   security-group list

echo "[8] volume (cinder)"
run "volume list"           volume list

echo "[9] object_store (swift)"
run "container list"        container list

echo "[10] orchestration (heat)"
run "stack list"            stack list

echo "[11] dns (designate)"
run "zone list"             zone list

echo "[12] key_manager (barbican)"
run "secret list"           secret list

echo
echo "[skipped — plugins not enabled in local.conf]"
skip "load_balancer (Octavia)" "ovn-octavia-provider broken on stable/2025.2"
skip "backup (Freezer)"     "freezer plugin disabled"
skip "container_infra (Magnum)" "magnum plugin disabled"
skip "alarm (Aodh)"         "aodh plugin disabled"
skip "metric (Gnocchi)"     "gnocchi plugin disabled"
skip "rating (CloudKitty)"  "cloudkitty plugin disabled"

echo
echo "=== summary: $PASS pass, $FAIL fail, $SKIP skip ==="
if (( FAIL > 0 )); then
    echo
    echo "=== failures ==="
    for line in "${FAILED_CMDS[@]}"; do
        echo "  $line"
    done
    exit 1
fi
