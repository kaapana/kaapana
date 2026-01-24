#!/bin/bash
set -eu -o pipefail

STORAGE_PROVIDER="${STORAGE_PROVIDER}"
STORAGE_CLASS_SLOW="${STORAGE_CLASS_SLOW}"
STORAGE_CLASS_FAST="${STORAGE_CLASS_FAST}"
STORAGE_CLASS_WORKFLOW="${STORAGE_CLASS_WORKFLOW}"
SERVICES_NAMESPACE="${SERVICES_NAMESPACE}"
ADMIN_NAMESPACE="${ADMIN_NAMESPACE}"
VOLUME_SLOW_DATA="${VOLUME_SLOW_DATA}"

echo "Using STORAGE_PROVIDER:${STORAGE_PROVIDER}"


echo "### Starting migration 0.5.x → 0.6.x ###"



if [[ "$STORAGE_PROVIDER" == "microk8s.io/hostpath" ]]; then
    echo "HostPath storage provider detected. Proceeding with migration."
else
    echo "Storage provider is not hostpath. Migration script is only for hostpath to dynamic storage migration."
    exit 0
fi


declare -A PVC_CONFIG
declare -A NS_HELM_MAP=(
  [$SERVICES_NAMESPACE]="kaapana-platform-chart|admin"
  [project-admin]="project-admin|admin"
  [$ADMIN_NAMESPACE]="kaapana-admin-chart|default"
)
PARALLEL_MIGRATIONS=4
define_pvcs() {
    #Services namespace
    PVC_CONFIG[access-information-interface-pv-claim]="$SERVICES_NAMESPACE|$STORAGE_CLASS_FAST|10Gi|${FAST_DATA_DIR}/access-information-interface-postgres-data:data"
    PVC_CONFIG[dicom-web-filter-pv-claim]="$SERVICES_NAMESPACE|$STORAGE_CLASS_FAST|10Gi|${FAST_DATA_DIR}/dicom-web-filter-postgres-data:data"
    PVC_CONFIG[airflow-pv-claim]="$SERVICES_NAMESPACE|$STORAGE_CLASS_FAST|10Gi|${FAST_DATA_DIR}/airflow-postgres-data:data"
    PVC_CONFIG[notification-service-pv-claim]="$SERVICES_NAMESPACE|$STORAGE_CLASS_FAST|10Gi|${FAST_DATA_DIR}/notification-service-postgres-data:data"
    PVC_CONFIG[kaapana-backend-pv-claim]="$SERVICES_NAMESPACE|$STORAGE_CLASS_FAST|10Gi|${FAST_DATA_DIR}/kaapana-backend-postgres-data:data"
    PVC_CONFIG[opensearch-pv-claim]="$SERVICES_NAMESPACE|$STORAGE_CLASS_FAST|10Gi|${FAST_DATA_DIR}/os/data:data|${FAST_DATA_DIR}/os/logs:logs|${FAST_DATA_DIR}/os/snapshots:snapshots"
    PVC_CONFIG[dcm4che-pv-claim]="$SERVICES_NAMESPACE|$STORAGE_CLASS_FAST|100Gi|${FAST_DATA_DIR}/postgres-dcm4che:postgres-dcm4che|${FAST_DATA_DIR}/ldap:ldap|${FAST_DATA_DIR}/slapd.d:slapd.d" 
    PVC_CONFIG[os-certs-pv-claim]="$SERVICES_NAMESPACE|$STORAGE_CLASS_FAST|10Gi|${FAST_DATA_DIR}/os/certs"
    PVC_CONFIG[dcm4chee-dicom-pv-claim]="$SERVICES_NAMESPACE|$STORAGE_CLASS_SLOW|$VOLUME_SLOW_DATA|${SLOW_DATA_DIR}/dcm4che/dicom_data"
    PVC_CONFIG[dcm4chee-standalone-pv-claim]="$SERVICES_NAMESPACE|$STORAGE_CLASS_SLOW|$VOLUME_SLOW_DATA|${SLOW_DATA_DIR}/dcm4che/server_data"
    PVC_CONFIG[minio-pv-claim]="$SERVICES_NAMESPACE|$STORAGE_CLASS_SLOW|$VOLUME_SLOW_DATA|${SLOW_DATA_DIR}/minio"
    # Admin namespace
    PVC_CONFIG[tls-pv-claim]="$ADMIN_NAMESPACE|$STORAGE_CLASS_FAST|10Gi|${FAST_DATA_DIR}/tls"
    PVC_CONFIG[keycloak-pv-claim]="$ADMIN_NAMESPACE|$STORAGE_CLASS_FAST|10Gi|${FAST_DATA_DIR}/keycloak-postgres-data:data"
    
    # Project-admin namespace models
    PVC_CONFIG[models-pv-claim]="project-admin|$STORAGE_CLASS_WORKFLOW|200Gi|${FAST_DATA_DIR}/workflows/models"
    
}

ensure_namespace() {
    local namespace="$1"

    local helm_meta="${NS_HELM_MAP[$namespace]}"

    if [[ -z "$helm_meta" ]]; then
        echo "[ERROR] No Helm mapping defined for namespace '$namespace'"
        return 1
    fi

    local release_name="${helm_meta%%|*}"
    local release_namespace="${helm_meta##*|}"

    echo "Ensuring namespace: $namespace (Helm release: $release_name)"

    cat <<EOF | kubectl apply -f - 2>&1
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


create_pvc_from_config() {
    local pvc_name="$1"
    local namespace="$2"
    local storage_class="$3"
    local storage="$4"

    echo "Creating PVC: $pvc_name in namespace: $namespace"

    # Ensure Helm-compatible namespace exists
    if ! ensure_namespace "$namespace"; then
        echo "[ERROR] Failed to ensure namespace: $namespace"
        return 1
    fi
    local helm_meta="${NS_HELM_MAP[$namespace]}"
    local release_name="${helm_meta%%|*}"
    local release_namespace="${helm_meta##*|}"  
    # Apply PVC and capture output
    local output
    output=$(
        cat <<EOF | kubectl apply -f - 2>&1
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: $pvc_name
  namespace: $namespace
  labels:
    app.kubernetes.io/managed-by: Helm
  annotations:
    meta.helm.sh/release-name: $release_name
    meta.helm.sh/release-namespace: $release_namespace
    helm.sh/resource-policy: keep
spec:
  storageClassName: $storage_class
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: $storage
EOF
    )

    local rc=$?

    # Always print kubectl output
    echo "$output"

    if [[ $rc -eq 0 ]]; then
        echo "PVC applied successfully: $pvc_name"
        return 0
    else
        echo "Failed to create PVC: $pvc_name"
        return 1
    fi
}


create_all_pvcs() {
    echo "Starting PVC creation..."    
    local created=0
    local failed=0
    local total=${#PVC_CONFIG[@]}
    local counter=1
    
    for pvc_name in "${!PVC_CONFIG[@]}"; do
        IFS='|' read -r namespace storage_class storage rest <<< "${PVC_CONFIG[$pvc_name]}"
        
        if create_pvc_from_config "$pvc_name" "$namespace" "$storage_class" "$storage"; then
            ((created++)) || true
            echo "[$counter/$total] PVC $pvc_name created successfully"
        else
            ((failed++)) || true
            echo "[$counter/$total] PVC $pvc_name creation failed"
        fi
        ((counter++)) || true
    done

    echo "PVC creation completed: $created created, $failed failed out of $total total"
    
    if [[ $failed -gt 0 ]]; then
        return 1
    fi
    return 0
}

create_dummy_pods() {
    # Build a unique list of namespaces from PVC_CONFIG
    local namespaces=()
    for pvc_name in "${!PVC_CONFIG[@]}"; do
        IFS='|' read -r ns _ <<< "${PVC_CONFIG[$pvc_name]}"
        local seen=false
        for existing in "${namespaces[@]}"; do
            if [[ "$existing" == "$ns" ]]; then
                seen=true
                break
            fi
        done
        if [[ "$seen" == false ]]; then
            namespaces+=("$ns")
        fi
    done

    for ns in "${namespaces[@]}"; do
        create_dummy_pod_for_namespace "$ns"
    done
}

create_dummy_pod_for_namespace() {
    local namespace="$1"
    local pod_name="kaapana-migration-dummy-pod-${namespace}"

    echo "Creating dummy pod '$pod_name' in namespace '$namespace' to bind PVCs..."

    local volumes=""
    local volume_mounts=""
    local idx=0

    for pvc_name in "${!PVC_CONFIG[@]}"; do
        IFS='|' read -r ns storage_class storage mount_specs <<< "${PVC_CONFIG[$pvc_name]}"

        # Only PVCs from this namespace
        if [[ "$ns" != "$namespace" ]]; then
            continue
        fi

        local vol_name="vol-$idx"
        volumes="$volumes
  - name: $vol_name
    persistentVolumeClaim:
      claimName: $pvc_name"

        volume_mounts="$volume_mounts
        - name: $vol_name
          mountPath: /mnt/$pvc_name"

        ((idx++)) || true
    done

    # No PVCs for this namespace → skip
    if [[ $idx -eq 0 ]]; then
        echo "No PVCs for namespace '$namespace', skipping dummy pod."
        return 0
    fi


    cat <<EOF | kubectl apply -n "$namespace" -f -
apiVersion: v1
kind: Pod
metadata:
  name: $pod_name
spec:
  restartPolicy: Never
  containers:
  - name: sleeper
    image: $MIGRATION_IMAGE
    command: ["sh", "-c", "sleep 3600"]
    volumeMounts:$volume_mounts
  volumes:$volumes
EOF

    echo "Waiting for dummy pod '$pod_name' to be Scheduled/Running..."

    for i in {1..60}; do
        phase=$(kubectl get pod "$pod_name" -n "$namespace" -o jsonpath='{.status.phase}' 2>/dev/null || echo "")
        echo "Dummy pod '$pod_name' phase: $phase"
        if [[ "$phase" == "Running" || "$phase" == "Pending" ]]; then
            break
        fi
        sleep 2
    done
}


wait_for_pvcs() {
    echo "Waiting for PVCs to be bound..."
    
    local max_attempts=60
    local attempt=0
    local total=${#PVC_CONFIG[@]}
    
    while [[ $attempt -lt $max_attempts ]]; do
        local bound=0
        
        for pvc_name in "${!PVC_CONFIG[@]}"; do
            IFS='|' read -r namespace rest <<< "${PVC_CONFIG[$pvc_name]}"
            
            if kubectl get pvc "$pvc_name" -n "$namespace" -o jsonpath='{.status.phase}' 2>/dev/null | grep -q "Bound"; then
                ((bound++)) || true
            fi
        done
        
        if [[ $bound -eq $total ]]; then
            echo "All PVCs are bound ($bound/$total)"
            return 0
        fi
        
        echo "Waiting for PVCs to bind... ($bound/$total)"
        sleep 2
        ((attempt++)) || true
    done
    
    echo "Timeout waiting for PVCs to be bound"
    return 1
}



# ============================================================================
# PV DISCOVERY & DATA MIGRATION
# ============================================================================

get_pv_hostpath() {
    local pvc_name="$1"
    local namespace="$2"
    
    # Get PV name from PVC
    local pv_name=$(kubectl get pvc "$pvc_name" -n "$namespace" -o jsonpath='{.spec.volumeName}' 2>/dev/null)
    
    if [[ -z "$pv_name" ]]; then
        echo "Could not find PV for PVC: $pvc_name"
        return 1
    fi
    
    # Get hostPath from PV
    local hostpath=$(kubectl get pv "$pv_name" -o jsonpath='{.spec.hostPath.path}' 2>/dev/null)
    
    if [[ -z "$hostpath" ]]; then
        echo "Could not find hostPath for PV: $pv_name"
        return 1
    fi
    
    echo "$hostpath"
}

migrate_data() {
    local source="$1"
    local target="$2"
    local pvc_name="$3"

    # Check if source exists
    if [[ ! -d "$source" ]]; then
        echo "Source directory does not exist (skipping): $source"
        return 0
    fi

    # Ensure target directory exists
    if [[ ! -d "$target" ]]; then
        if ! mkdir -p "$target" 2>/dev/null; then
            echo "Failed to create target directory: $target"
            return 1
        fi
    fi

    # Calculate source size
    local source_size
    source_size=$(du -sh "$source" 2>/dev/null | awk '{print $1}')
    echo "Migrating $source ($source_size) -> $target"

    # If directory is empty, nothing to move
    if [[ -z "$(ls -A "$source" 2>/dev/null)" ]]; then
        echo "Source directory is empty, nothing to migrate: $source"
        return 0
    fi

    local mv_output
    shopt -s dotglob # include hidden files
    if mv_output=$(mv "$source"/* "$target/" 2>&1); then
        shopt -u dotglob
        echo "Moved data via mv: $source/* -> $target"
        rmdir "$source" 2>/dev/null || true
        return 0
    fi
 
    shopt -u dotglob
    echo "Failed to migrate data from $source to $target"
    echo "mv output: $mv_output"
    return 1
}


migrate_pvc_data() {
    local pvc_name="$1"
    local config="${PVC_CONFIG[$pvc_name]}"

    IFS='|' read -r namespace storage_class storage mount_specs <<< "$config"

    echo "Processing PVC: $pvc_name (namespace: $namespace)"

    local pv_hostpath
    if ! pv_hostpath=$(get_pv_hostpath "$pvc_name" "$namespace"); then
        echo "Failed to discover PV hostpath for $pvc_name"
        echo "$pvc_name:ERROR" >> "./migration_status"
        return 1
    fi

    echo "PV hostpath: $pv_hostpath"

    local mount_count=0
    local mount_failed=0

    # Split mount_specs into entries separated by |
    while read -r spec; do
        [[ -z "$spec" ]] && continue

        if [[ "$spec" == *:* ]]; then
            IFS=':' read -r source target <<< "$spec"
        else
            source="$spec"
            target=""
        fi

        source=$(eval echo "$source")

        local target_dir="$pv_hostpath"
        if [[ -n "$target" ]]; then
            target_dir="$pv_hostpath/$target"
        fi

        echo "Migrating mount '$source' -> '$target_dir' for PVC $pvc_name"

        if migrate_data "$source" "$target_dir" "$pvc_name"; then
            ((mount_count++)) || true
        else
            ((mount_failed++)) || true
        fi
    done < <(echo "$mount_specs" | tr '|' '\n')

    if [[ "$mount_failed" -gt 0 ]]; then
        echo "$pvc_name:PARTIAL" >> "./migration_status"
        echo "Migration completed for $pvc_name ($mount_count mounts, $mount_failed failed)"
        return 1
    fi

    echo "$pvc_name:OK" >> "./migration_status"
    echo "Migration completed for $pvc_name ($mount_count mounts)"
    return 0
}


migrate_all_data() {
    echo "Starting data migration (parallel: $PARALLEL_MIGRATIONS)..."

    local status_file="./migration_status"
    : > "$status_file"   # truncate/create in CWD

    local total=${#PVC_CONFIG[@]}
    local pids=()

    for pvc_name in "${!PVC_CONFIG[@]}"; do
        while [[ $(jobs -r | wc -l) -ge $PARALLEL_MIGRATIONS ]]; do
            sleep 0.5
        done

        migrate_pvc_data "$pvc_name" "$status_file" &
        pids+=($!)
    done

    echo "Waiting for $total migration jobs to complete..."
    local failed=0
    for pid in "${pids[@]}"; do
        if ! wait "$pid" 2>/dev/null; then
            ((failed++)) || true
        fi
    done

    echo "Data migration completed"
    print_migration_summary "$status_file"

    return 0 #$failed
}

print_migration_summary() {
    local status_file="./migration_status"
    echo "Migration Summary:"
    echo "================="
    if [[ -f "$status_file" ]]; then
        cat "$status_file"
    else
        echo "No migration_status file found."
    fi
}

delete_dummy_pods() {
    echo "Deleting dummy pods..."

    # Match all pods whose name starts with this prefix, in all namespaces
    local prefix="kaapana-migration-dummy-pod"

    # Get "namespace podname" lines for matching pods
    kubectl get pods --all-namespaces \
        -o custom-columns='NS:.metadata.namespace,NAME:.metadata.name' \
        --no-headers 2>/dev/null | \
    awk -v pfx="$prefix" '$2 ~ "^"pfx {print $1, $2}' | while read -r ns name; do
        echo "Deleting dummy pod '$name' in namespace '$ns'..."
        kubectl delete pod "$name" -n "$ns" --wait=false || true
    done
}

# ============================================================================
# CLEANUP & EXIT
# ============================================================================

cleanup() {
    local exit_code=$?   # capture exit code of last command (main)
    # Best-effort deletion; do not change exit_code
    delete_dummy_pods || true

    if [[ $exit_code -eq 0 ]]; then
        echo "Migration completed successfully"
    else
        echo "Migration completed with errors (exit code: $exit_code)"
    fi

    exit $exit_code
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================
main() {    
    echo "======================================================"
    echo "Kaapana PVC Data Migration Tool v0.5-0.6"
    echo "======================================================"

    
    define_pvcs
    create_all_pvcs  
    create_dummy_pods         
    wait_for_pvcs 
    migrate_all_data

}




trap cleanup EXIT
main