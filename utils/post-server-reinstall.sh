#!/bin/bash
set -euo pipefail

# Post-server-reinstall orchestration helper for Kaapana/Racoon setups.
# Important: this script does NOT reinstall the server/OS itself.
# This script performs:
# 1) Mandatory migration image pull into microk8s containerd
# 2) Storage-class setup via kaapanactl --install-storage-classes
# 3) PVC/data recovery via recover_data.sh
#
# It is intentionally parameterized (no hardcoded credentials, registry paths,
# or private tokens) so it can be reused across environments.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KAAPANA_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
KAAPANACTL="${KAAPANA_DIR}/kaapanactl.sh"
RECOVER_SCRIPT="${SCRIPT_DIR}/recover_data.sh"

KUBE="kubectl"
CTR="microk8s ctr"
if command -v microk8s.kubectl >/dev/null 2>&1; then
    KUBE="microk8s.kubectl"
fi

CHART_REF=""
REGISTRY_PREFIX=""
VERSION_TAG=""
MIGRATION_IMAGE=""

REGISTRY_USERNAME=""
REGISTRY_PASSWORD=""

FAST_DIR=""
SLOW_DIR=""
QUARANTINE_DIR=""
QUARANTINE_PVC_PATTERNS=""
# post-server-reinstall default: none. Recovery must receive Retain explicitly
# through --hostpath-reclaim-policy Retain or HOSTPATH_RECLAIM_POLICY=Retain.
HOSTPATH_RECLAIM_POLICY="${HOSTPATH_RECLAIM_POLICY:-}"

ADMIN_RELEASE_NAME=""
PLATFORM_RELEASE_NAME="kaapana-platform-chart"

# Print CLI usage for the post-reinstall helper.
# Params: none.
# Returns: writes usage text to stdout.
# Side effects: none.
usage() {
    cat <<'EOF'
Usage:
  ./kaapana/utils/post-server-reinstall.sh --chart <registry/path/admin-chart:tag> [options]

Purpose:
  Run platform/data recovery tasks AFTER a server reinstall/reboot.
  This script does not perform the server reinstall itself.

Prerequisite (server reinstall first):
  1) sudo ./kaapana/kaapanactl.sh install --uninstall
  2) sudo ./kaapana/kaapanactl.sh install
  3) sudo reboot
  4) run this script on the fresh boot

Required:
  --chart REF                    Full admin chart reference (e.g. registry/.../racoon-admin-chart:0.6.1)
  --registry-username USER       Registry username
  --registry-password PASS       Registry password/token
  --fast-dir DIR                 Fast data dir
  --slow-dir DIR                 Slow data dir

Registry/Auth options:
  --registry-prefix PREFIX       Image prefix for migration pull (default: chart repo parent)
  --migration-image IMAGE        Migration image reference (default: <registry-prefix>/migration:<chart-tag>)

Data recovery options:
  --hostpath-reclaim-policy Retain
                                 Required explicit opt-in for retained hostpath PVs
  --admin-release-name NAME      Recover target admin release (default: chart name)
  --platform-release-name NAME   Recover target platform release (default: kaapana-platform-chart)
  --quarantine-dir DIR           Move matching orphaned PVC dirs here during recovery
  --quarantine-pvc-patterns CSV  Comma-separated namespace/pvc-name globs to
                                 exclude from recovery and quarantine

Other:
  -h, --help                     Show this help

Hostpath reclaim-policy defaults:
  kaapana-storage-chart          Delete
  kaapanactl.sh deploy           Delete unless --hostpath-reclaim-policy overrides it
  generated deploy_platform.sh   Delete unless deployment_config.yaml sets hostpath_reclaim_policy
  post-server-reinstall.sh       no default; requires Retain via flag or environment

Notes:
  - recover_data.sh requires sudo privileges and may prompt for your password.
  - Storage classes are always installed in a dedicated pre-step via:
    kaapanactl.sh deploy --hostpath-reclaim-policy Retain --install-storage-classes
    - Platform deploy runs project namespace reconciliation automatically when
        reconcile_project_namespaces.sh is shipped next to kaapanactl.sh.
        You can also run it manually after deploy if required.
  - This script does not deploy the platform/admin chart.
  - Example:
    ./kaapana/utils/post-server-reinstall.sh --chart <ref> --fast-dir <dir> --slow-dir <dir> --hostpath-reclaim-policy Retain
EOF
}

die() {
    echo "ERROR: $*"
    exit 1
}

log_step() {
    echo ""
    echo "======================================================"
    echo "$*"
    echo "======================================================"
}

# Parse supported CLI flags for the post-reinstall recovery helper.
# Params:
#   all CLI arguments passed to the script.
# Returns: 0 when parsing succeeds.
# Side effects: populates global option variables.
parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --chart) CHART_REF="$2"; shift 2 ;;
            --registry-prefix) REGISTRY_PREFIX="$2"; shift 2 ;;
            --registry-username) REGISTRY_USERNAME="$2"; shift 2 ;;
            --registry-password) REGISTRY_PASSWORD="$2"; shift 2 ;;
            --migration-image) MIGRATION_IMAGE="$2"; shift 2 ;;
            --fast-dir) FAST_DIR="$2"; shift 2 ;;
            --slow-dir) SLOW_DIR="$2"; shift 2 ;;
            --hostpath-reclaim-policy) HOSTPATH_RECLAIM_POLICY="$2"; shift 2 ;;
            --quarantine-dir) QUARANTINE_DIR="$2"; shift 2 ;;
            --quarantine-pvc-patterns) QUARANTINE_PVC_PATTERNS="$2"; shift 2 ;;
            --admin-release-name) ADMIN_RELEASE_NAME="$2"; shift 2 ;;
            --platform-release-name) PLATFORM_RELEASE_NAME="$2"; shift 2 ;;
            -h|--help) usage; exit 0 ;;
            *) die "Unknown argument: $1" ;;
        esac
    done
}

derive_defaults() {
    [[ -n "${CHART_REF}" ]] || die "--chart is required"
    [[ "${CHART_REF}" == *:* ]] || die "--chart must include a tag (expected ...:<version>)"

    local chart_repo="${CHART_REF%:*}"
    VERSION_TAG="${CHART_REF##*:}"

    if [[ -z "${REGISTRY_PREFIX}" ]]; then
        REGISTRY_PREFIX="${chart_repo%/*}"
    fi

    if [[ -z "${MIGRATION_IMAGE}" ]]; then
        MIGRATION_IMAGE="${REGISTRY_PREFIX}/migration:${VERSION_TAG}"
    fi

    if [[ -z "${ADMIN_RELEASE_NAME}" ]]; then
        ADMIN_RELEASE_NAME="${chart_repo##*/}"
    fi

    [[ -n "${REGISTRY_USERNAME}" ]] || die "Missing registry username (--registry-username)"
    [[ -n "${REGISTRY_PASSWORD}" ]] || die "Missing registry password (--registry-password)"
    [[ -n "${FAST_DIR}" ]] || die "Missing fast data dir (--fast-dir)"
    [[ -n "${SLOW_DIR}" ]] || die "Missing slow data dir (--slow-dir)"

    # Recovery depends on retained hostpath PVs. Refuse Delete instead of
    # changing the policy implicitly inside the recovery helper.
    case "${HOSTPATH_RECLAIM_POLICY}" in
        Retain)
            ;;
        Delete|"")
            die "Post-reinstall recovery requires --hostpath-reclaim-policy Retain"
            ;;
        *)
            die "Invalid hostpath reclaim policy '${HOSTPATH_RECLAIM_POLICY}'. Use Retain for recovery."
            ;;
    esac
}

# Validate required executables before recovery steps start.
validate_prereqs() {
    [[ -x "${KAAPANACTL}" ]] || die "Missing executable: ${KAAPANACTL}"
    [[ -x "${RECOVER_SCRIPT}" ]] || die "Missing executable: ${RECOVER_SCRIPT}"
    command -v "${KUBE}" >/dev/null 2>&1 || die "Kubernetes client not found: ${KUBE}"
    command -v microk8s >/dev/null 2>&1 || echo "WARNING: 'microk8s' command not found; migration image pull might fail."
}

pull_migration_image() {
    log_step "Pull Migration Image"

    local auth_args=(--user "${REGISTRY_USERNAME}:${REGISTRY_PASSWORD}")
    local max_retries=3
    local attempt

    # Reuse the cached image when available to avoid unnecessary registry access.
    if ${CTR} images ls 2>/dev/null | awk '{print $1}' | grep -Fxq "${MIGRATION_IMAGE}"; then
        echo "Migration image already cached: ${MIGRATION_IMAGE}"
        return 0
    fi

    if [[ -z "${REGISTRY_USERNAME}" || -z "${REGISTRY_PASSWORD}" ]]; then
        die "Recovery needs registry credentials to pull migration image ${MIGRATION_IMAGE}"
    fi

    for attempt in $(seq 1 ${max_retries}); do
        echo "Migration image pull attempt ${attempt}/${max_retries}: ${MIGRATION_IMAGE}"
        if ${CTR} images pull "${auth_args[@]}" "${MIGRATION_IMAGE}"; then
            return 0
        fi

        if [[ ${attempt} -lt ${max_retries} ]]; then
            echo "Migration image pull attempt ${attempt}/${max_retries} failed. Waiting for microk8s runtime and retrying..."
            microk8s status --wait-ready >/dev/null 2>&1 || true
            sleep 3
        fi
    done

    echo "You can retry the recovery flow or preload the image manually with:"
    echo "  microk8s ctr images pull --user <username>:<password> ${MIGRATION_IMAGE}"
    die "Failed to pull migration image after ${max_retries} attempts: ${MIGRATION_IMAGE}"
}

run_storage_class_setup() {
    # This invocation is intentionally storage-class only.
    # kaapanactl exits after setup when --install-storage-classes is provided.
    # The Retain requirement was already validated above and is forwarded rather
    # than chosen here.
    log_step "Install Storage Classes"

    local storage_cmd=(
        "${KAAPANACTL}" deploy
        --chart "${CHART_REF}"
        --fast-data-dir "${FAST_DIR}"
        --slow-data-dir "${SLOW_DIR}"
        --hostpath-reclaim-policy "${HOSTPATH_RECLAIM_POLICY}"
        --username "${REGISTRY_USERNAME}"
        --password "${REGISTRY_PASSWORD}"
        --install-storage-classes
    )
    "${storage_cmd[@]}"
}

# Run the PVC recovery helper with any configured quarantine options.
# Params: none.
# Returns: 0 when the recovery helper succeeds.
# Side effects: invokes recover_data.sh via sudo.
run_recover() {
    log_step "Recover PV/PVC Data"

    local recover_cmd=(
        sudo "${RECOVER_SCRIPT}"
        --fast-dir "${FAST_DIR}"
        --slow-dir "${SLOW_DIR}"
        --migration-image "${MIGRATION_IMAGE}"
        --admin-release-name "${ADMIN_RELEASE_NAME}"
        --platform-release-name "${PLATFORM_RELEASE_NAME}"
    )

    if [[ -n "${QUARANTINE_DIR}" ]]; then
        recover_cmd+=(--quarantine-dir "${QUARANTINE_DIR}")
    fi

    if [[ -n "${QUARANTINE_PVC_PATTERNS}" ]]; then
        recover_cmd+=(--quarantine-pvc-patterns "${QUARANTINE_PVC_PATTERNS}")
    fi

    "${recover_cmd[@]}"
}

verify_state() {
    log_step "Final Project Namespace Check"
    ${KUBE} get ns | grep '^project-' || true
}

# Run the mandatory post-reinstall recovery flow in a fixed order.
# Params:
#   all CLI arguments passed to the script.
# Returns: exits with the script status.
# Side effects: executes image pull, storage setup, and PVC recovery steps.
main() {
    parse_args "$@"
    derive_defaults
    validate_prereqs

    log_step "Configuration"
    echo "Chart:                 ${CHART_REF}"
    echo "Registry prefix:       ${REGISTRY_PREFIX}"
    echo "Version tag:           ${VERSION_TAG}"
    echo "Migration image:       ${MIGRATION_IMAGE}"
    echo "Fast dir:              ${FAST_DIR}"
    echo "Slow dir:              ${SLOW_DIR}"
    echo "Hostpath reclaim:      ${HOSTPATH_RECLAIM_POLICY}"
    if [[ -n "${QUARANTINE_PVC_PATTERNS}" ]]; then
        echo "Quarantine dir:        ${QUARANTINE_DIR:-${SLOW_DIR}/recover-data-quarantine}"
        echo "Quarantine patterns:   ${QUARANTINE_PVC_PATTERNS}"
    fi
    echo "Admin release:         ${ADMIN_RELEASE_NAME}"
    echo "Platform release:      ${PLATFORM_RELEASE_NAME}"
    echo "Kube client:           ${KUBE}"

    pull_migration_image
    run_storage_class_setup
    run_recover
    verify_state
}

main "$@"
