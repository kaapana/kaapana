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

SERVICES_NAMESPACE="${SERVICES_NAMESPACE:-services}"
ADMIN_NAMESPACE="${ADMIN_NAMESPACE:-admin}"
VOLUME_SLOW_DATA="${VOLUME_SLOW_DATA:-100Gi}"

STORAGE_CLASS_SLOW="kaapana-hostpath-slow-data-dir"
STORAGE_CLASS_FAST="kaapana-hostpath-fast-data-dir"

# ============================================================================
# ARGUMENT PARSING
# ============================================================================
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
        --help|-h) show_help ;;
        *) echo "ERROR: Unknown $1"; show_help ;;
    esac
done

[[ -z "$FAST_DATA_DIR" || -z "$SLOW_DATA_DIR" || -z "$MIGRATION_IMAGE" ]] && {
    echo "ERROR: Missing --fast-dir, --slow-dir, or --migration-image"
    exit 1
}

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

# ============================================================================
# HELPER: Get search directory from storage class
# ============================================================================
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
apply_pvc_defaults_and_ensure_namespace() {
    local namespace="$1"
    local pvc_name="$2"
    local storage_class="$3"
    local capacity="$4"
    
    # Smart defaults for project-* models/workflow-data
    if [[ "$namespace" =~ ^project- ]]; then
        if [[ "$pvc_name" == "models-pv-claim" || "$pvc_name" == "workflow-data-pv-claim" ]]; then
            storage_class="$STORAGE_CLASS_FAST"
            capacity="200Gi"
        fi
    fi
    
    # Ensure namespace is in Helm map
    if [[ "$namespace" =~ ^project- ]] && [[ -z "${NS_HELM_MAP[$namespace]:-}" ]]; then
        NS_HELM_MAP[$namespace]="$namespace|$ADMIN_NAMESPACE"
    elif [[ "$namespace" != "$SERVICES_NAMESPACE" && "$namespace" != "$ADMIN_NAMESPACE" && -z "${NS_HELM_MAP[$namespace]:-}" ]]; then
        NS_HELM_MAP[$namespace]="kaapana-platform-chart|$ADMIN_NAMESPACE"
    fi
    
    echo "$storage_class|$capacity"
}

# ============================================================================
# DEFINE EXPLICIT PVC CONFIG (Known PVCs)
# Format: PVC_CONFIG["namespace/pvc-name"]="storageClass|size"
# ============================================================================
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
    
    # Project-admin namespace
    PVC_CONFIG[project-admin/models-pv-claim]="$STORAGE_CLASS_FAST|200Gi"
    PVC_CONFIG[project-admin/workflow-data-pv-claim]="$STORAGE_CLASS_FAST|200Gi"
}

# ============================================================================
# BUILD NAMESPACE HELM MAPPING
# ============================================================================
build_namespace_helm_map() {
    NS_HELM_MAP[$SERVICES_NAMESPACE]="kaapana-platform-chart|$ADMIN_NAMESPACE"
    NS_HELM_MAP[project-admin]="project-admin|$ADMIN_NAMESPACE"
    NS_HELM_MAP[$ADMIN_NAMESPACE]="kaapana-admin-chart|default"
}

# ============================================================================
# DISCOVER RELEASED PVs AND ADD TO CONFIG
# ============================================================================
discover_and_add_released_pvs() {
    echo "======================================================"
    echo "Step 1: Discovering Released PVs"
    echo "======================================================"
    
    local json=$($KUBE get pv -o json 2>/dev/null || echo '{"items":[]}')
    local count=0
    
    while IFS=$'\t' read -r pv_name ns pvc_name storage_class capacity hostpath; do
        [[ -z "$pv_name" || -z "$ns" || -z "$pvc_name" ]] && continue
        
        local pvc_key="$ns/$pvc_name"
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
discover_and_add_orphaned_dirs() {
    echo "======================================================"
    echo "Step 2: Discovering orphaned directories"
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
        
        # Parse pattern: namespace-pvcname-pvc-uuid
        if [[ "$dirname" =~ ^(.+)-pvc-[a-f0-9-]+$ ]]; then
            local prefix="${BASH_REMATCH[1]}"
            
            local namespace=""
            local pvc_name=""
            
            # Try to extract namespace and pvc name
            if [[ "$prefix" =~ ^($SERVICES_NAMESPACE|$ADMIN_NAMESPACE)-(.*) ]]; then
                namespace="${BASH_REMATCH[1]}"
                pvc_name="${BASH_REMATCH[2]}"
            elif [[ "$prefix" =~ ^(project-[^-]+)-(.*) ]]; then
                namespace="${BASH_REMATCH[1]}"
                pvc_name="${BASH_REMATCH[2]}"
            elif [[ "$prefix" =~ ^([^-]+)-(.*) ]]; then
                namespace="${BASH_REMATCH[1]}"
                pvc_name="${BASH_REMATCH[2]}"
            else
                continue
            fi
            
            # Check if already in config using full key
            local pvc_key="$namespace/$pvc_name"
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

# ============================================================================
# HELPERS
# ============================================================================
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

ensure_namespace() {
    local namespace="$1"
    local helm_meta="${NS_HELM_MAP[$namespace]:-}"
    
    if [[ -z "$helm_meta" ]]; then
        # Default mapping for unknown namespaces
        helm_meta="kaapana-platform-chart|$ADMIN_NAMESPACE"
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

# Step 3: Auto-discover from Released PVs
discover_and_add_released_pvs

# Step 4: Auto-discover from orphaned directories
discover_and_add_orphaned_dirs

# Step 5: Show final PVC config
echo "======================================================"
echo "Final PVC Configuration (${#PVC_CONFIG[@]} total)"
echo "======================================================"
for pvc_key in "${!PVC_CONFIG[@]}"; do
    IFS='|' read -r sc size <<< "${PVC_CONFIG[$pvc_key]}"
    echo "  $pvc_key → $sc, $size"
done
echo "======================================================"
echo ""

# Step 6: Process all PVCs
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
        ((failed++))
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
