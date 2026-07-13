#!/bin/bash
# ============================================================================
# Kaapana Same-Version PVC Migration Tool (Auto-Discovery Edition)
# ============================================================================
# This script auto-discovers PVCs from:
# 1. Explicitly defined PVC_CONFIG
# 2. Released PVs (extracts namespace, name, size, storage class)
# 3. Orphaned directories in FAST/SLOW data dirs
# ============================================================================

set -eu -o pipefail

# ============================================================================
# PARAMETERS
# ============================================================================
SLOW_DATA_DIR="${SLOW_DATA_DIR:-}"
FAST_DATA_DIR="${FAST_DATA_DIR:-}"
MIGRATION_IMAGE="${MIGRATION_IMAGE:-}"
QUARANTINE_DIR="${QUARANTINE_DIR:-}"
DEFAULT_QUARANTINE_PVC_PATTERNS="services/dev-code-server-*-pv-claim,services/jupyterlab-*-pv-claim,services/tensorboard-*-pv-claim,services/slicer-*-pv-claim,services/mitk-*-pv-claim,services/desktop-*-pv-claim"
QUARANTINE_PVC_PATTERNS_RAW="${QUARANTINE_PVC_PATTERNS:-$DEFAULT_QUARANTINE_PVC_PATTERNS}"

SERVICES_NAMESPACE="${SERVICES_NAMESPACE:-services}"
ADMIN_NAMESPACE="${ADMIN_NAMESPACE:-admin}"
VOLUME_SLOW_DATA="${VOLUME_SLOW_DATA:-100Gi}"
# Allow recover flow to target either kaapana-* or racoon-* release names.
ADMIN_RELEASE_NAME="${ADMIN_RELEASE_NAME:-kaapana-admin-chart}"
PLATFORM_RELEASE_NAME="${PLATFORM_RELEASE_NAME:-kaapana-platform-chart}"
# Namespace prefix of the platform. Current kaapana creates project namespaces
# as <prefix>-project-<id>; legacy installs used bare project-<id>. Matching
# covers both forms so legacy data can be recovered onto a prefixed platform.
# PROJECT_NS_REGEX / PROJECT_ADMIN_NS are derived after argument parsing.
PLATFORM_PREFIX="${PLATFORM_PREFIX:-}"

STORAGE_CLASS_SLOW="kaapana-hostpath-slow-data-dir"
STORAGE_CLASS_FAST="kaapana-hostpath-fast-data-dir"
declare -a QUARANTINE_PVC_PATTERNS=()

# ============================================================================
# ARGUMENT PARSING
# ============================================================================
# Print CLI usage details for the recovery helper.
# Params: none.
# Returns: exits with status 0 after printing help text.
# Side effects: writes usage information to stdout.
show_help() {
    cat << EOF
Usage: $0 [OPTIONS]

Required:
  --fast-dir DIR        Fast data dir (/home/kaapana)
  --slow-dir DIR        Slow data dir (/home/kaapana)
  --migration-image IMG Migration image (e.g. <registry>/migration:<version>)

Optional:
  --services-namespace NS    (default: services)
  --admin-namespace NS       (default: admin)
  --volume-slow-data SIZE    (default: 10Gi)
  --admin-release-name NAME  (default: kaapana-admin-chart)
  --platform-release-name N  (default: kaapana-platform-chart)
  --platform-prefix PREFIX   Namespace prefix of the platform; project
                             namespaces are matched as [<prefix>-]project-*
                             (default: empty = legacy unprefixed only)
  --quarantine-dir DIR       Move matching orphaned PVC dirs here
                             (default: \$SLOW_DATA_DIR/recover-data-quarantine)
  --quarantine-pvc-patterns  Comma-separated shell globs for namespace/pvc-name
                             keys to exclude from recovery and quarantine
                             Default: $DEFAULT_QUARANTINE_PVC_PATTERNS
  --help, -h

Note: This script must be run with root privileges (sudo)

EOF
    exit 0
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --fast-dir) FAST_DATA_DIR="$2"; shift 2 ;;
        --slow-dir) SLOW_DATA_DIR="$2"; shift 2 ;;
        --migration-image) MIGRATION_IMAGE="$2"; shift 2 ;;
        --services-namespace) SERVICES_NAMESPACE="$2"; shift 2 ;;
        --admin-namespace) ADMIN_NAMESPACE="$2"; shift 2 ;;
        --volume-slow-data) VOLUME_SLOW_DATA="$2"; shift 2 ;;
        --admin-release-name) ADMIN_RELEASE_NAME="$2"; shift 2 ;;
        --platform-release-name) PLATFORM_RELEASE_NAME="$2"; shift 2 ;;
        --platform-prefix) PLATFORM_PREFIX="$2"; shift 2 ;;
        --quarantine-dir) QUARANTINE_DIR="$2"; shift 2 ;;
        --quarantine-pvc-patterns) QUARANTINE_PVC_PATTERNS_RAW="$2"; shift 2 ;;
        --help|-h) show_help ;;
        *) echo "ERROR: Unknown $1"; show_help ;;
    esac
done

[[ -z "$FAST_DATA_DIR" || -z "$SLOW_DATA_DIR" || -z "$MIGRATION_IMAGE" ]] && {
    echo "ERROR: Missing --fast-dir, --slow-dir, or --migration-image"
    exit 1
}

# jq is used inside process substitutions for Released-PV discovery; a missing
# binary there fails SILENTLY (errexit does not reach process substitutions)
# and would make discovery return zero PVs - check up front instead.
if ! command -v jq >/dev/null 2>&1; then
    echo "ERROR: jq is required but not installed."
    exit 1
fi

# Project-namespace matching derived from the optional platform prefix:
# always accept legacy unprefixed 'project-*' names, and additionally
# '<prefix>-project-*' when a prefix is configured.
if [[ -n "$PLATFORM_PREFIX" ]]; then
    PROJECT_NS_REGEX="^(${PLATFORM_PREFIX}-)?project-"
    PROJECT_ADMIN_NS="${PLATFORM_PREFIX}-project-admin"
else
    PROJECT_NS_REGEX="^project-"
    PROJECT_ADMIN_NS="project-admin"
fi

# Normalize a directory path while preserving the root directory.
# Params:
#   $1 directory path.
# Returns: echoes the normalized path without trailing slashes, except for "/".
# Side effects: none.
normalize_dir_path() {
    local dir_path="$1"

    if [[ "$dir_path" == "/" ]]; then
        echo "/"
        return 0
    fi

    while [[ -n "$dir_path" && "$dir_path" == */ ]]; do
        dir_path="${dir_path%/}"
    done

    echo "$dir_path"
}

FAST_DATA_DIR="$(normalize_dir_path "$FAST_DATA_DIR")"
SLOW_DATA_DIR="$(normalize_dir_path "$SLOW_DATA_DIR")"

# Parse the configured quarantine glob list into a bash array.
# Params: none.
# Returns: 0 when parsing succeeds.
# Side effects: populates QUARANTINE_PVC_PATTERNS and sets a default quarantine dir.
load_quarantine_config() {
    local raw_patterns="${QUARANTINE_PVC_PATTERNS_RAW:-}"
    local pattern=""
    local cleaned_patterns=()

    QUARANTINE_PVC_PATTERNS=()
    [[ -z "$raw_patterns" ]] && return 0

    IFS=',' read -r -a QUARANTINE_PVC_PATTERNS <<< "$raw_patterns"
    for pattern in "${QUARANTINE_PVC_PATTERNS[@]}"; do
        pattern="${pattern#"${pattern%%[![:space:]]*}"}"
        pattern="${pattern%"${pattern##*[![:space:]]}"}"
        [[ -n "$pattern" ]] && cleaned_patterns+=("$pattern")
    done
    QUARANTINE_PVC_PATTERNS=("${cleaned_patterns[@]}")

    if [[ ${#QUARANTINE_PVC_PATTERNS[@]} -gt 0 ]] && [[ -z "$QUARANTINE_DIR" ]]; then
        QUARANTINE_DIR="${SLOW_DATA_DIR%/}/recover-data-quarantine"
    fi
}

load_quarantine_config

if [[ -n "$QUARANTINE_DIR" ]]; then
    QUARANTINE_DIR="$(normalize_dir_path "$QUARANTINE_DIR")"
fi

# ============================================================================
# ROOT PRIVILEGE CHECK
# ============================================================================
if [ "$EUID" -ne 0 ]; then
    echo "======================================================"
    echo "ERROR: This script must be run with root privileges!"
    echo "======================================================"
    echo "Please run: sudo $0 $*"
    exit 1
fi

KUBE="kubectl"
command -v microk8s.kubectl >/dev/null 2>&1 && KUBE="microk8s.kubectl"

# ============================================================================
# IMAGE AVAILABILITY CHECK
# ============================================================================
echo "Checking if migration image is available..."
set +o pipefail
if microk8s ctr images ls 2>/dev/null | grep -q "$MIGRATION_IMAGE"; then
    echo "✓ Migration image found"
else
    echo "======================================================"
    echo "ERROR: Migration image not found in microk8s!"
    echo "======================================================"
    echo "Image: $MIGRATION_IMAGE"
    echo ""
    echo "Example: <registry>/migration:<version>"
    echo ""
    echo "Please pull the image first using:"
    echo ""
    echo "  microk8s ctr images pull \\"
    echo "    --user <username>:<password> \\"
    echo "    $MIGRATION_IMAGE"
    echo ""
    echo "Or if no authentication is required:"
    echo ""
    echo "  microk8s ctr images pull $MIGRATION_IMAGE"
    echo ""
    echo "======================================================"
    exit 1
fi
echo ""
set -o pipefail

echo "======================================================"
echo "Kaapana PVC Migration Tool (Auto-Discovery)"
echo "======================================================"
echo "Fast: $FAST_DATA_DIR"
echo "Slow: $SLOW_DATA_DIR"
echo "Image: $MIGRATION_IMAGE"
if [[ ${#QUARANTINE_PVC_PATTERNS[@]} -gt 0 ]]; then
    echo "Quarantine dir: $QUARANTINE_DIR"
    echo "Quarantine PVC patterns:"
    for pattern in "${QUARANTINE_PVC_PATTERNS[@]}"; do
        echo "  - $pattern"
    done
fi
echo "======================================================"

# ============================================================================
# STORAGE CLASS CHECK
# ============================================================================
echo "Checking storage classes..."
if ! $KUBE get storageclass "$STORAGE_CLASS_FAST" >/dev/null 2>&1; then
    echo "======================================================"
    echo "ERROR: Storage class not found!"
    echo "======================================================"
    echo "Storage class: $STORAGE_CLASS_FAST"
    echo ""
    echo "Please ensure the storage class exists and has a provisioner."
    echo "Install storage classes by running the kaapana deployment with --install-storage-classes"
    echo "Check with: kubectl get storageclass"
    echo "======================================================"
    exit 1
fi
echo "✓ Storage class found: $STORAGE_CLASS_FAST"
echo ""

# ============================================================================
# GLOBAL VARIABLES
# ============================================================================
declare -A PVC_CONFIG
declare -A NS_HELM_MAP
declare -A RELEASED_PV_MAP

# Known project PVC names used across 0.5.x and 0.6.x.
# This helps recover namespace/pvc splits from orphaned dir names like:
#   project-test-p1-models-pv-claim-pvc-<uuid>
# without collapsing namespace to project-test.
PROJECT_PVC_SUFFIXES=(
    "af-plugins-pv-claim"
    "dags-pv-claim"
    "af-logs-pv-claim"
    "tensorboard-pv-claim"
    "models-pv-claim"
    "workflow-data-pv-claim"
)

# ============================================================================
# HELPER: Get search directory from storage class
# ============================================================================
# Resolve the data directory for a storage class.
# Params:
#   $1 storage class name.
# Returns: echoes the matching search directory.
# Side effects: none.
get_search_dir_for_storage_class() {
    local storage_class="$1"
    if [[ "$storage_class" == "$STORAGE_CLASS_SLOW" ]]; then
        echo "$SLOW_DATA_DIR"
    else
        echo "$FAST_DATA_DIR"
    fi
}

# ============================================================================
# HELPER: Apply smart defaults and ensure namespace mapping
# ============================================================================
# Apply storage defaults for a PVC and ensure namespace Helm metadata exists.
# Params:
#   $1 namespace.
#   $2 pvc name.
#   $3 storage class.
#   $4 requested capacity.
# Returns: echoes "<storageClass>|<capacity>".
# Side effects: updates NS_HELM_MAP for discovered namespaces.
apply_pvc_defaults_and_ensure_namespace() {
    local namespace="$1"
    local pvc_name="$2"
    local storage_class="$3"
    local capacity="$4"

    # Smart defaults for [prefix-]project-* models/workflow-data
    if [[ "$namespace" =~ $PROJECT_NS_REGEX ]]; then
        if [[ "$pvc_name" == "models-pv-claim" || "$pvc_name" == "workflow-data-pv-claim" ]]; then
            storage_class="$STORAGE_CLASS_FAST"
            capacity="200Gi"
        fi
    fi

    # Ensure namespace is in Helm map
    if [[ "$namespace" =~ $PROJECT_NS_REGEX ]] && [[ -z "${NS_HELM_MAP[$namespace]:-}" ]]; then
        NS_HELM_MAP[$namespace]="$namespace|$ADMIN_NAMESPACE"
    elif [[ "$namespace" != "$SERVICES_NAMESPACE" && "$namespace" != "$ADMIN_NAMESPACE" && -z "${NS_HELM_MAP[$namespace]:-}" ]]; then
        NS_HELM_MAP[$namespace]="$PLATFORM_RELEASE_NAME|$ADMIN_NAMESPACE"
    fi

    echo "$storage_class|$capacity"
}

# Check whether a namespace/pvc key matches a configured quarantine glob.
# Params:
#   $1 pvc key in the form namespace/pvc-name.
# Returns: 0 if a pattern matches, otherwise 1.
# Side effects: none.
pvc_key_matches_quarantine_pattern() {
    local pvc_key="$1"
    local pattern=""

    for pattern in "${QUARANTINE_PVC_PATTERNS[@]}"; do
        if [[ "$pvc_key" == $pattern ]]; then
            return 0
        fi
    done

    return 1
}

# Parse an orphaned PVC directory name into namespace and PVC name.
# Params:
#   $1 directory basename such as services-airflow-pv-claim-pvc-<uuid>.
# Returns: echoes "<namespace>|<pvc-name>" when parsing succeeds.
# Side effects: writes warnings to stderr for ambiguous project namespaces.
parse_orphaned_dir_metadata() {
    local dirname="$1"
    local prefix=""
    local namespace=""
    local pvc_name=""

    if [[ ! "$dirname" =~ ^(.+)-pvc-[a-f0-9-]+$ ]]; then
        return 1
    fi
    prefix="${BASH_REMATCH[1]}"

    if [[ "$prefix" =~ ^($SERVICES_NAMESPACE|$ADMIN_NAMESPACE)-(.*) ]]; then
        namespace="${BASH_REMATCH[1]}"
        pvc_name="${BASH_REMATCH[2]}"
    elif [[ "$prefix" =~ $PROJECT_NS_REGEX ]]; then
        local matched_project_split=false
        local suffix=""

        for suffix in "${PROJECT_PVC_SUFFIXES[@]}"; do
            if [[ "$prefix" == *-"$suffix" ]]; then
                local candidate_ns="${prefix%-${suffix}}"
                if [[ "$candidate_ns" =~ ${PROJECT_NS_REGEX}.+ ]]; then
                    namespace="$candidate_ns"
                    pvc_name="$suffix"
                    matched_project_split=true
                    break
                fi
            fi
        done

        if [[ "$matched_project_split" == false ]]; then
            echo "  WARNING: Could not safely parse project orphaned dir '$dirname'; skipping." >&2
            return 1
        fi
    elif [[ "$prefix" =~ ^([^-]+)-(.*) ]]; then
        namespace="${BASH_REMATCH[1]}"
        pvc_name="${BASH_REMATCH[2]}"
    else
        return 1
    fi

    echo "$namespace|$pvc_name"
}

# Build a unique target path inside the quarantine area for a moved PVC folder.
# Params:
#   $1 source directory path.
# Returns: echoes the destination path.
# Side effects: creates QUARANTINE_DIR when needed.
build_quarantine_target_path() {
    local source_dir="$1"
    local source_name=""
    local candidate=""
    local timestamp=""

    source_name="$(basename "$source_dir")"
    mkdir -p "$QUARANTINE_DIR"

    candidate="${QUARANTINE_DIR%/}/${source_name}"
    if [[ -e "$candidate" ]]; then
        timestamp="$(date +%Y%m%d-%H%M%S)"
        candidate="${QUARANTINE_DIR%/}/${source_name}-${timestamp}"
    fi

    echo "$candidate"
}

# Move matching orphaned PVC directories into quarantine before discovery.
# Params: none.
# Returns: 0 when the quarantine scan completes.
# Side effects: creates QUARANTINE_DIR on demand and moves matching directories with mv.
quarantine_matching_orphaned_dirs() {
    echo "======================================================"
    echo "Step 1: Quarantining configured orphaned directories"
    echo "======================================================"

    if [[ ${#QUARANTINE_PVC_PATTERNS[@]} -eq 0 ]]; then
        echo "  No quarantine PVC patterns configured; skipping."
        echo ""
        return 0
    fi

    local count=0
    local dir=""
    local dirname=""
    local metadata=""
    local namespace=""
    local pvc_name=""
    local pvc_key=""
    local matched_pattern=""
    local target_dir=""
    local pattern=""

    while IFS= read -r -d '' dir; do
        [[ ! -d "$dir" ]] && continue
        dirname="$(basename "$dir")"

        if ! metadata="$(parse_orphaned_dir_metadata "$dirname")"; then
            continue
        fi
        IFS='|' read -r namespace pvc_name <<< "$metadata"
        pvc_key="$namespace/$pvc_name"

        matched_pattern=""
        for pattern in "${QUARANTINE_PVC_PATTERNS[@]}"; do
            if [[ "$pvc_key" == $pattern ]]; then
                matched_pattern="$pattern"
                break
            fi
        done
        [[ -z "$matched_pattern" ]] && continue

        target_dir="$(build_quarantine_target_path "$dir")"
        echo "  Quarantining orphaned dir: $dirname"
        echo "    pvc key: $pvc_key"
        echo "    matched pattern: $matched_pattern"
        echo "    from: $dir"
        echo "    to:   $target_dir"
        mv "$dir" "$target_dir"
        echo "    ✓ Moved to quarantine"

        ((count++)) || true
    done < <(find "$FAST_DATA_DIR" "$SLOW_DATA_DIR" -maxdepth 1 -type d -name '*-pvc-*' -print0 2>/dev/null || true)

    if [[ $count -eq 1 ]]; then
        echo "  Quarantined 1 orphaned directory"
    else
        echo "  Quarantined $count orphaned directories"
    fi
    echo ""
}

# ============================================================================
# DEFINE EXPLICIT PVC CONFIG (Known PVCs)
# Format: PVC_CONFIG["namespace/pvc-name"]="storageClass|size"
# ============================================================================
# Populate the baseline PVC map for known platform PVCs.
# Params: none.
# Returns: 0 when the known PVC list is initialized.
# Side effects: fills PVC_CONFIG with explicit entries.
define_explicit_pvcs() {
    # Services namespace
    PVC_CONFIG[$SERVICES_NAMESPACE/access-information-interface-pv-claim]="$STORAGE_CLASS_FAST|10Gi"
    PVC_CONFIG[$SERVICES_NAMESPACE/dicom-web-filter-pv-claim]="$STORAGE_CLASS_FAST|10Gi"
    PVC_CONFIG[$SERVICES_NAMESPACE/airflow-pv-claim]="$STORAGE_CLASS_FAST|10Gi"
    PVC_CONFIG[$SERVICES_NAMESPACE/notification-service-pv-claim]="$STORAGE_CLASS_FAST|10Gi"
    PVC_CONFIG[$SERVICES_NAMESPACE/kaapana-backend-pv-claim]="$STORAGE_CLASS_FAST|10Gi"
    PVC_CONFIG[$SERVICES_NAMESPACE/opensearch-pv-claim]="$STORAGE_CLASS_FAST|10Gi"
    PVC_CONFIG[$SERVICES_NAMESPACE/dcm4che-pv-claim]="$STORAGE_CLASS_FAST|100Gi"
    PVC_CONFIG[$SERVICES_NAMESPACE/os-certs-pv-claim]="$STORAGE_CLASS_FAST|10Gi"
    PVC_CONFIG[$SERVICES_NAMESPACE/dcm4chee-dicom-pv-claim]="$STORAGE_CLASS_SLOW|$VOLUME_SLOW_DATA"
    PVC_CONFIG[$SERVICES_NAMESPACE/dcm4chee-standalone-pv-claim]="$STORAGE_CLASS_SLOW|$VOLUME_SLOW_DATA"
    PVC_CONFIG[$SERVICES_NAMESPACE/minio-pv-claim]="$STORAGE_CLASS_SLOW|$VOLUME_SLOW_DATA"
    PVC_CONFIG[$SERVICES_NAMESPACE/ctp-data-pv-claim]="$STORAGE_CLASS_FAST|100Gi"
    PVC_CONFIG[$SERVICES_NAMESPACE/local-registry-pv-claim]="$STORAGE_CLASS_FAST|100Gi"
    PVC_CONFIG[$SERVICES_NAMESPACE/data-api-artifacts-pv-claim]="$STORAGE_CLASS_FAST|200Gi"
    PVC_CONFIG[$SERVICES_NAMESPACE/workflow-data-pv-claim]="$STORAGE_CLASS_FAST|200Gi"
    PVC_CONFIG[$SERVICES_NAMESPACE/models-pv-claim]="$STORAGE_CLASS_FAST|200Gi"

    # Admin namespace
    PVC_CONFIG[$ADMIN_NAMESPACE/tls-pv-claim]="$STORAGE_CLASS_FAST|10Gi"
    PVC_CONFIG[$ADMIN_NAMESPACE/keycloak-pv-claim]="$STORAGE_CLASS_FAST|10Gi"

    # Project-admin namespace (prefixed on current kaapana, see PROJECT_ADMIN_NS)
    PVC_CONFIG[$PROJECT_ADMIN_NS/models-pv-claim]="$STORAGE_CLASS_FAST|200Gi"
    PVC_CONFIG[$PROJECT_ADMIN_NS/workflow-data-pv-claim]="$STORAGE_CLASS_FAST|200Gi"
}

# ============================================================================
# BUILD NAMESPACE HELM MAPPING
# ============================================================================
# Populate the namespace-to-Helm ownership mapping used during recovery.
# Params: none.
# Returns: 0 when initialization completes.
# Side effects: fills NS_HELM_MAP.
build_namespace_helm_map() {
    # Base mappings; project-* namespaces are added dynamically if discovered.
    # Project namespaces are Helm releases named like the namespace itself.
    NS_HELM_MAP[$SERVICES_NAMESPACE]="$PLATFORM_RELEASE_NAME|$ADMIN_NAMESPACE"
    NS_HELM_MAP[$PROJECT_ADMIN_NS]="$PROJECT_ADMIN_NS|$ADMIN_NAMESPACE"
    NS_HELM_MAP[$ADMIN_NAMESPACE]="$ADMIN_RELEASE_NAME|default"
}

# ============================================================================
# DISCOVER RELEASED PVs AND ADD TO CONFIG
# ============================================================================
# Add released PVs to the recovery set unless they match quarantine patterns.
# Params: none.
# Returns: 0 when discovery completes.
# Side effects: updates RELEASED_PV_MAP and PVC_CONFIG.
discover_and_add_released_pvs() {
    echo "======================================================"
    echo "Step 2: Discovering Released PVs"
    echo "======================================================"

    local json=$($KUBE get pv -o json 2>/dev/null || echo '{"items":[]}')
    local count=0

    while IFS=$'\t' read -r pv_name ns pvc_name storage_class capacity hostpath; do
        [[ -z "$pv_name" || -z "$ns" || -z "$pvc_name" ]] && continue

        local pvc_key="$ns/$pvc_name"

        if pvc_key_matches_quarantine_pattern "$pvc_key"; then
            echo "  Skipping Released PV due to quarantine pattern: $pv_name ($pvc_key)"
            continue
        fi

        RELEASED_PV_MAP["$pvc_key"]="$pv_name"

        # Check if already in PVC_CONFIG using the full key
        if [[ -n "${PVC_CONFIG[$pvc_key]:-}" ]]; then
            continue
        fi

        echo "  Found Released PV: $pv_name ($pvc_key)"

        local final_sc="$STORAGE_CLASS_FAST"

        # 1) If PV has storageClassName: ALWAYS use it
        if [[ -n "$storage_class" ]]; then
            final_sc="$storage_class"
        else
            # 2) No storageClassName: infer from hostPath (only if dirs differ)
            if [[ "$FAST_DATA_DIR" != "$SLOW_DATA_DIR" ]] && [[ -n "$hostpath" ]] && [[ "$hostpath" == "$SLOW_DATA_DIR"* ]]; then
                final_sc="$STORAGE_CLASS_SLOW"
            fi
        fi

        # 3) Apply smart defaults and ensure namespace mapping
        local final_capacity="${capacity:-10Gi}"
        local defaults=$(apply_pvc_defaults_and_ensure_namespace "$ns" "$pvc_name" "$final_sc" "$final_capacity")

        PVC_CONFIG[$pvc_key]="$defaults"

        ((count++)) || true
    done < <(echo "$json" | jq -r '.items[]? | select(.status.phase=="Released") | [.metadata.name, .spec.claimRef.namespace, .spec.claimRef.name, .spec.storageClassName // "", .spec.capacity.storage // "10Gi", .spec.hostPath.path // ""] | @tsv')

    echo "  Auto-added $count PVCs from Released PVs"
    echo ""
}

# ============================================================================
# DISCOVER ORPHANED DIRECTORIES AND ADD TO CONFIG
# ============================================================================
# Add orphaned PVC directories to the recovery set unless they are quarantined.
# Params: none.
# Returns: 0 when discovery completes.
# Side effects: updates PVC_CONFIG.
discover_and_add_orphaned_dirs() {
    echo "======================================================"
    echo "Step 3: Discovering orphaned directories"
    echo "======================================================"

    local count=0
    local dirs=()

    # Collect all potential orphaned dirs
    while IFS= read -r -d '' dir; do
        dirs+=("$dir")
    done < <(find "$FAST_DATA_DIR" "$SLOW_DATA_DIR" -maxdepth 1 -type d -name '*-pvc-*' -print0 2>/dev/null || true)

    for dir in "${dirs[@]}"; do
        [[ ! -d "$dir" ]] && continue

        local dirname=$(basename "$dir")

        local metadata=""
        if metadata="$(parse_orphaned_dir_metadata "$dirname")"; then
            local namespace=""
            local pvc_name=""
            IFS='|' read -r namespace pvc_name <<< "$metadata"

            # Check if already in config using full key
            local pvc_key="$namespace/$pvc_name"
            if pvc_key_matches_quarantine_pattern "$pvc_key"; then
                echo "  Skipping orphaned dir due to quarantine pattern: $dirname ($pvc_key)"
                continue
            fi
            [[ -n "${PVC_CONFIG[$pvc_key]:-}" ]] && continue

            # Determine storage class from directory location (only if dirs differ)
            local storage_class="$STORAGE_CLASS_FAST"
            local capacity="10Gi"

            if [[ "$FAST_DATA_DIR" != "$SLOW_DATA_DIR" ]] && [[ "$dir" == "$SLOW_DATA_DIR"/* ]]; then
                storage_class="$STORAGE_CLASS_SLOW"
            fi

            # Apply smart defaults and ensure namespace mapping
            local defaults=$(apply_pvc_defaults_and_ensure_namespace "$namespace" "$pvc_name" "$storage_class" "$capacity")

            echo "  Found orphaned dir: $dirname"
            echo "    → namespace=$namespace, pvc=$pvc_name, storage=${defaults%|*}"

            PVC_CONFIG[$pvc_key]="$defaults"

            ((count++)) || true
        fi
    done

    echo "  Auto-added $count PVCs from orphaned directories"
    echo ""
}

# Remove PVCs that match quarantine patterns from the final recovery config.
# Params: none.
# Returns: 0 when filtering completes.
# Side effects: unsets matching keys from PVC_CONFIG and RELEASED_PV_MAP.
filter_quarantined_pvcs_from_config() {
    echo "======================================================"
    echo "Step 4: Filtering quarantined PVCs from recovery config"
    echo "======================================================"

    if [[ ${#QUARANTINE_PVC_PATTERNS[@]} -eq 0 ]]; then
        echo "  No quarantine PVC patterns configured; nothing to filter."
        echo ""
        return 0
    fi

    local filtered_count=0
    local pvc_key=""

    for pvc_key in "${!PVC_CONFIG[@]}"; do
        if pvc_key_matches_quarantine_pattern "$pvc_key"; then
            echo "  Excluding PVC from recovery config: $pvc_key"
            unset 'PVC_CONFIG[$pvc_key]'
            unset 'RELEASED_PV_MAP[$pvc_key]'
            ((filtered_count++)) || true
        fi
    done

    if [[ $filtered_count -eq 1 ]]; then
        echo "  Filtered 1 PVC from recovery config"
    else
        echo "  Filtered $filtered_count PVCs from recovery config"
    fi
    echo ""
}

# ============================================================================
# HELPERS
# ============================================================================
# Discover the best source directory for a namespace/PVC pair.
# Params:
#   $1 pvc name.
#   $2 data directory to search.
#   $3 namespace.
# Returns: echoes the selected source directory path when found.
# Side effects: writes discovery details to stderr.
discover_pv_directory() {
    local pvc_name="$1"
    local data_dir="$2"
    local namespace="$3"

    local pattern="${namespace}-${pvc_name}-pvc-*"
    local matches=()

    # Find all matching directories
    while IFS= read -r -d '' dir; do
        matches+=("$dir")
    done < <(find "$data_dir" -maxdepth 1 -type d -name "$pattern" -print0 2>/dev/null)

    # No matches found
    if [[ ${#matches[@]} -eq 0 ]]; then
        echo ""
        return 1
    fi

    # Single match
    if [[ ${#matches[@]} -eq 1 ]]; then
        echo "    Found source: $(basename "${matches[0]}")" >&2
        echo "${matches[0]}"
        return 0
    fi

    # Multiple matches - show all and pick newest
    echo "    Found ${#matches[@]} existing directories:" >&2
    for dir in "${matches[@]}"; do
        echo "      - $(basename "$dir")" >&2
    done

    # Select the NEWEST (reverse sort by name, which sorts by UUID timestamp)
    local newest=$(printf '%s\n' "${matches[@]}" | sort -r | head -n1)
    echo "    Selected newest: $(basename "$newest")" >&2
    echo "$newest"
    return 0
}

# Ensure a namespace exists with the expected Helm ownership annotations.
# Params:
#   $1 namespace to create or update.
# Returns: 0 when kubectl apply succeeds.
# Side effects: creates or updates a Kubernetes namespace.
ensure_namespace() {
    local namespace="$1"
    local helm_meta="${NS_HELM_MAP[$namespace]:-}"

    if [[ -z "$helm_meta" ]]; then
        # Default mapping for unknown namespaces
        helm_meta="$PLATFORM_RELEASE_NAME|$ADMIN_NAMESPACE"
        NS_HELM_MAP[$namespace]="$helm_meta"
    fi

    local release_name="${helm_meta%%|*}"
    local release_namespace="${helm_meta##*|}"

    cat << EOF | $KUBE apply -f - >/dev/null 2>&1
apiVersion: v1
kind: Namespace
metadata:
  name: $namespace
  labels:
    app.kubernetes.io/managed-by: Helm
  annotations:
    meta.helm.sh/release-name: $release_name
    meta.helm.sh/release-namespace: $release_namespace
    helm.sh/resource-policy: keep
EOF
}

# Move recovered data from the source directory into the target directory.
# Params:
#   $1 source directory.
#   $2 target directory.
# Returns: 0 on success, 1 on migration failure.
# Side effects: moves files on disk and may remove the emptied source dir.
migrate_data() {
    local source="$1" target="$2"
    [[ ! -d "$source" ]] && return 0
    [[ ! -d "$target" ]] && { echo "    ✗ Target directory doesn't exist"; return 1; }

    echo "    Migrating $source -> $target"

        # Check if source is empty
    if [[ -z "$(ls -A "$source" 2>/dev/null)" ]]; then
        echo "    Empty source - removing source directory"
        rmdir "$source" 2>/dev/null || true
        return 0
    fi

    shopt -s dotglob
    if mv "$source"/* "$target/" 2>&1; then
        shopt -u dotglob
        rmdir "$source" 2>/dev/null || true
        echo "    ✓ Migration complete"
        return 0
    fi
    shopt -u dotglob
    echo "    ✗ Migration failed"
    return 1
}

# ============================================================================
# MAIN PVC PROCESSOR
# ============================================================================
# Recover a single PVC and migrate any discovered hostPath data into it.
# Params:
#   $1 pvc name.
#   $2 namespace.
#   $3 storage class.
#   $4 requested storage size.
# Returns: 0 on success, 1 when PVC recovery fails.
# Side effects: creates Kubernetes PVCs/pods and moves data on disk.
process_single_pvc() {
    local pvc_name="$1"
    local namespace="$2"
    local storage_class="$3"
    local storage="$4"

    local pvc_key="$namespace/$pvc_name"

    echo "========================================"
    echo "[$counter/$total] Processing: $pvc_name"
    echo "  Namespace: $namespace"
    echo "  Storage: $storage ($storage_class)"
    echo "========================================"

    # [0] PRE-DISCOVER source directory BEFORE creating PVC
    echo "  [0/7] Pre-discovering source directory"
    local search_dir=$(get_search_dir_for_storage_class "$storage_class")
    local source_pv_path=""

    if source_pv_path=$(discover_pv_directory "$pvc_name" "$search_dir" "$namespace"); then
        : # source_pv_path is set
    else
        echo "    No existing source directory found"
    fi

    # [1] Check if already exists
    local status=$($KUBE get pvc "$pvc_name" -n "$namespace" -o jsonpath='{.status.phase}' 2>/dev/null || echo "")
    if [[ "$status" == "Bound" ]]; then
        echo "  ✓ Already bound - skipping"
        return 0
    elif [[ -n "$status" ]]; then
        echo "  Deleting existing PVC (status: $status)"
        $KUBE delete pvc "$pvc_name" -n "$namespace" --ignore-not-found --wait=false
        sleep 2
    fi

    # [2] Reclaim released PV if exists
    local released_pv="${RELEASED_PV_MAP[$pvc_key]:-}"
    if [[ -n "$released_pv" ]]; then
        echo "  [1/7] Reclaiming PV: $released_pv"
        $KUBE patch pv "$released_pv" --type=json -p='[{"op":"remove","path":"/spec/claimRef"}]' >/dev/null

        for i in {1..10}; do
            local pv_status=$($KUBE get pv "$released_pv" -o jsonpath='{.status.phase}' 2>/dev/null)
            [[ "$pv_status" == "Available" ]] && break
            sleep 1
        done
        echo "  ✓ PV reclaimed"
    else
        echo "  [1/7] No released PV found"
    fi

    # [3] Ensure namespace
    echo "  [2/7] Ensuring namespace"
    ensure_namespace "$namespace" || return 1

    # Wait for the namespace's default ServiceAccount before creating the binder
    # pod. Kubernetes provisions the default SA asynchronously, so on a freshly
    # created namespace pod creation is briefly rejected with
    # "serviceaccount default not found", which then causes a PVC binding
    # timeout. Poll up to 30s for the SA to appear.
    for _sa_wait in {1..30}; do
        $KUBE get sa default -n "$namespace" >/dev/null 2>&1 && break
        sleep 1
    done

    local helm_meta="${NS_HELM_MAP[$namespace]}"
    local release_name="${helm_meta%%|*}"
    local release_ns="${helm_meta##*|}"

    # [4] Create PVC
    echo "  [3/7] Creating PVC"
    cat << PVC_EOF | $KUBE apply -f - >/dev/null
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: $pvc_name
  namespace: $namespace
  labels:
    app.kubernetes.io/managed-by: Helm
  annotations:
    meta.helm.sh/release-name: $release_name
    meta.helm.sh/release-namespace: $release_ns
    helm.sh/resource-policy: keep
spec:
  storageClassName: $storage_class
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: $storage
PVC_EOF
    echo "  ✓ PVC created"

    # [5] Create binder pod
    local pod_name="migration-binder-${pvc_name//[^a-z0-9]/-}"
    echo "  [4/7] Creating binder pod: $pod_name"
    cat << POD_EOF | $KUBE apply -n "$namespace" -f - >/dev/null
apiVersion: v1
kind: Pod
metadata:
  name: $pod_name
spec:
  restartPolicy: Never
  containers:
  - name: binder
    image: $MIGRATION_IMAGE
    command: ["sh", "-c", "sleep 3600"]
    volumeMounts:
    - name: pvc-volume
      mountPath: /mnt/pvc
  volumes:
  - name: pvc-volume
    persistentVolumeClaim:
      claimName: $pvc_name
POD_EOF
    echo "  ✓ Binder pod created"

    # [6] Wait for PVC binding
    echo "  [5/7] Waiting for PVC to bind (max 60s)..."
    local attempts=0
    local bound_pv=""
    while [[ $attempts -lt 60 ]]; do
        bound_pv=$($KUBE get pvc "$pvc_name" -n "$namespace" -o jsonpath='{.spec.volumeName}' 2>/dev/null || echo "")
        [[ -n "$bound_pv" ]] && break
        sleep 1
        ((attempts++))
    done

    if [[ -z "$bound_pv" ]]; then
        echo "  ✗ ERROR: PVC binding timeout"
        return 1
    fi

    if [[ -n "$released_pv" && "$bound_pv" == "$released_pv" ]]; then
        echo "  ✓ Bound to reclaimed PV: $bound_pv"
    else
        echo "  ✓ Bound to PV: $bound_pv"
    fi

    # [7] Delete binder pod immediately
    echo "  [6/7] Deleting binder pod"
    $KUBE delete pod "$pod_name" -n "$namespace" --wait=false --ignore-not-found >/dev/null 2>&1 || true
    echo "  ✓ Binder pod deleted"

    # [8] Migrate data
    echo "  [7/7] Migrating data"

    local target_pv_path=$($KUBE get pv "$bound_pv" -o jsonpath='{.spec.hostPath.path}' 2>/dev/null)
    [[ -z "$target_pv_path" ]] && { echo "  ✗ No hostPath in PV"; return 1; }

    # Check if target has data
    if [[ -d "$target_pv_path" ]] && [[ -n "$(ls -A "$target_pv_path" 2>/dev/null)" ]]; then
        echo "    Target already has data - skip"
        echo "$pvc_key:ALREADY_HAS_DATA" >> "./migration_status"
        return 0
    fi

    # Use the pre-discovered source
    if [[ -z "$source_pv_path" ]]; then
        echo "    No source found in $search_dir"
        echo "$pvc_key:NO_SOURCE" >> "./migration_status"
        return 0
    fi

    echo "    Source: $source_pv_path"
    echo "    Target: $target_pv_path"

    # Skip if same
    if [[ "$source_pv_path" == "$target_pv_path" ]]; then
        echo "    Same path - PV reused"
        echo "$pvc_key:REUSED_PV" >> "./migration_status"
        return 0
    fi

    # Fix target directory permissions to match source
    echo "    Fixing target directory permissions..."
    chmod --reference="$source_pv_path" "$target_pv_path" 2>/dev/null || true
    chown --reference="$source_pv_path" "$target_pv_path" 2>/dev/null || true

    # Do migration
    if migrate_data "$source_pv_path" "$target_pv_path"; then
        echo "$pvc_key:OK" >> "./migration_status"
        return 0
    else
        echo "$pvc_key:FAILED" >> "./migration_status"
        return 1
    fi
}

# ============================================================================
# CLEANUP
# ============================================================================
# Remove temporary binder pods and report the overall script outcome.
# Params: none.
# Returns: exits with the original script exit code.
# Side effects: deletes migration-binder pods and prints a summary.
cleanup() {
    local exit_code=$?
    echo ""
    echo "======================================================"
    echo "Cleanup"
    echo "======================================================"

    $KUBE get pods --all-namespaces -o json 2>/dev/null | \
        jq -r '.items[]? | select(.metadata.name | startswith("migration-binder-")) | [.metadata.namespace, .metadata.name] | @tsv' | \
        while IFS=$'\t' read -r ns name; do
            echo "Deleting pod $name in $ns..."
            $KUBE delete pod "$name" -n "$ns" --wait=false --ignore-not-found >/dev/null 2>&1 || true
        done

    echo ""
    if [[ $exit_code -eq 0 ]]; then
        echo "✓ Migration completed successfully"
    else
        echo "✗ Migration completed with errors (exit: $exit_code)"
    fi
    echo "======================================================"
    exit $exit_code
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================
trap cleanup EXIT

# Step 1: Define explicit PVCs
define_explicit_pvcs

# Step 2: Build namespace Helm mapping
build_namespace_helm_map

# Step 3: Quarantine configured orphaned directories before discovery
quarantine_matching_orphaned_dirs

# Step 4: Auto-discover from Released PVs
discover_and_add_released_pvs

# Step 5: Auto-discover from orphaned directories
discover_and_add_orphaned_dirs

# Step 6: Remove any explicitly quarantined PVCs from the final recovery set
filter_quarantined_pvcs_from_config

# Step 7: Show final PVC config
echo "======================================================"
echo "Final PVC Configuration (${#PVC_CONFIG[@]} total)"
echo "======================================================"
for pvc_key in "${!PVC_CONFIG[@]}"; do
    IFS='|' read -r sc size <<< "${PVC_CONFIG[$pvc_key]}"
    echo "  $pvc_key → $sc, $size"
done
echo "======================================================"
echo ""

# Step 8: Process all PVCs
: > "./migration_status"
total=${#PVC_CONFIG[@]}
counter=1
failed=0

for pvc_key in "${!PVC_CONFIG[@]}"; do
    IFS='/' read -r namespace pvc_name <<< "$pvc_key"
    IFS='|' read -r storage_class storage <<< "${PVC_CONFIG[$pvc_key]}"

    if process_single_pvc "$pvc_name" "$namespace" "$storage_class" "$storage"; then
        : # Success
    else
        failed=$((failed+1))
    fi

    ((counter++))
    echo ""
done

echo "======================================================"
echo "Migration Summary"
echo "======================================================"
cat "./migration_status"
echo "======================================================"

[[ $failed -gt 0 ]] && { echo "✗ $failed PVC(s) failed"; exit 1; }
echo "✓ All PVCs processed successfully"
