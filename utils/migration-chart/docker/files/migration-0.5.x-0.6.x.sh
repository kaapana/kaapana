#!/bin/bash
set -eu -o pipefail

#TODO remove
# Use kubectl if available; otherwise fallback to microk8s.kubectl
command -v kubectl >/dev/null 2>&1 || {
    kubectl() { microk8s.kubectl "$@"; }
}

FAST_DATA_DIR="$1"
SLOW_DATA_DIR="$2"

echo "Using FAST_DATA_DIR: ${FAST_DATA_DIR}"
echo "Using SLOW_DATA_DIR: ${SLOW_DATA_DIR}"


echo "### Starting migration 0.5.x → 0.6.x ###"

# Get all PVCs with their storage class (skip header)
pvc_storageclasses=$(kubectl get pvc -A --no-headers | awk '{print $7}' | sort -u)

# Check if any storage class contains "kaapana"
if echo "$pvc_storageclasses" | grep -q "kaapana"; then
    echo "Kaapana storageclass detected:"
    echo "$pvc_storageclasses" | grep "kaapana"
else
    echo "No kaapana specific storageclass used so far."
    echo "A fresh deployment and undeployment is needed before migration can be done."
    # Write the flag to the version file
    CURRENT_VERSION=$(cat "$FAST_DATA_DIR/version")
    echo "${CURRENT_VERSION}-fresh deploy and redeploy-needed" > "$FAST_DATA_DIR/version"
    
    # 🚨 CRITICAL CHANGE: Exit 1 to signal failure to the pipeline.
    # The pipeline should then read the .version file for guidance.
    exit 1
fi




declare -A STORAGE=(
  ["access-information-interface-pv-claim"]="$FAST_DATA_DIR/access-information-interface-postgres-data:data"
  ["dicom-web-filter-pv-claim"]="$FAST_DATA_DIR/dicom-web-filter-postgres-data:data"
  ["airflow-pv-claim"]="$FAST_DATA_DIR/airflow-postgres-data:data"
  ["keycloak-pv-claim"]="$FAST_DATA_DIR/keycloak-postgres-data:data"
  ["notification-service-pv-claim"]="$FAST_DATA_DIR/notification-service-postgres-data:data"
  ["kaapana-backend-pv-claim"]="$FAST_DATA_DIR/kaapana-backend-postgres-data:data"
  ["opensearch-pv-claim"]="$FAST_DATA_DIR/os/data:data $FAST_DATA_DIR/os/logs:logs $FAST_DATA_DIR/os/snapshots:snapshots"
  ["dcm4che-pv-claim"]="$FAST_DATA_DIR/postgres-dcm4che:data $FAST_DATA_DIR/ldap:ldap $FAST_DATA_DIR/slapd.d:slapd.d"
  # Continued list from your PVC output:
  # admin namespace
  ["extensions-pv-claim"]="$FAST_DATA_DIR/extensions:extensions $FAST_DATA_DIR/platforms:platforms"
  ["tls-pv-claim"]="$FAST_DATA_DIR/tls"
  ["traefik-pv-claim"]="$FAST_DATA_DIR/traefik"


  # project-admin namespace
  ["project-admin-models-pv-claim"]="$FAST_DATA_DIR/workflows/models"
  ["project-admin-tensorboard-pv-claim"]="$FAST_DATA_DIR/tensorboard"
  #["project-admin-workflow-data-pv-claim"]="$FAST_DATA_DIR/workflows/data"

  # services namespace (picking up after your last entry)
  ["af-data-pv-claim"]="$FAST_DATA_DIR/workflows/data"
  ["af-logs-pv-claim"]="$FAST_DATA_DIR/airflow/logs"
  ["af-plugins-pv-claim"]="$FAST_DATA_DIR/workflows/plugins"
  ["ctp-data-pv-claim"]="$FAST_DATA_DIR/ctp"
  ["dags-pv-claim"]="$FAST_DATA_DIR/workflows/dags"
  # These next two use the 'slow' StorageClass
  ["dcm4chee-dicom-pv-claim"]="$SLOW_DATA_DIR/dcm4che/dicom_data" 
  ["dcm4chee-standalone-pv-claim"]="$SLOW_DATA_DIR/dcm4che/server_data" 
  ["loki-pv-claim"]="$FAST_DATA_DIR/loki"
  # minio also uses the 'slow' StorageClass
  ["minio-pv-claim"]="$SLOW_DATA_DIR/minio" 
  #["models-pv-claim"]="$FAST_DATA_DIR/models-global"
  ["os-certs-pv-claim"]="$FAST_DATA_DIR/os/certs"
  ["prometheus-pv-claim"]="$FAST_DATA_DIR/prometheus"
  ["uploads-pv-claim"]="$FAST_DATA_DIR/uploads"
  ["workflow-api-pv-claim"]="$FAST_DATA_DIR/workflow-api-data"
)


# for pvc in "${!STORAGE[@]}"; do
#   for tuple in ${STORAGE[$pvc]}; do
#     base="${tuple%%:*}"
#     if [[ "$tuple" == *:* ]]; then
#       sub="${tuple##*:}"
#     else
#       sub=""  # no subpath provided
#     fi
#     echo "$pvc mounts $base at subdir '$sub'"
#   done
# done



dir_list=$(ls -d ${FAST_DATA_DIR}/*/ 2>/dev/null | xargs -n 1 basename)
echo "Found directories in FAST_DATA_DIR: ${dir_list}"

dir_list=$(ls -d ${SLOW_DATA_DIR}/*/ 2>/dev/null | xargs -n 1 basename)
echo "Found directories in SLOW_DATA_DIR: ${dir_list}"

WORKDIR="/tmp/migration"
mkdir -p "${WORKDIR}"

echo "1️⃣ Fetching existing PVC namespaces..."
# Get PVC name and namespace for all PVCs that will be migrated
PVC_NAMESPACES=$(kubectl get pvc -A --no-headers | awk '/kaapana/ {print $2 ":" $1}')

# Convert list to a lookup map (pvc_name -> namespace)
declare -A PVC_NS_MAP
while IFS=':' read -r pvc_name ns; do
  PVC_NS_MAP["$pvc_name"]="$ns"
done <<< "$PVC_NAMESPACES"

if [ ${#PVC_NS_MAP[@]} -eq 0 ]; then
  echo "No existing kaapana-hostpath PVCs found. Exiting."
  exit 0
fi

echo "2️⃣ Starting data migration to existing PVCs..."
MIGRATOR_IMAGE="registry.hzdr.de/h.gao/kaapana-dev/migration:0.5.2-latest"
#MIGRATOR_IMAGE= "{{ .Values.global.registry_url }}/migration:{{ .Values.global.kaapana_build_version }}" # TODO add gloabls to migration and check if : Use an image that has rsync installed


wait_for_job() {
    local job="$1"
    local namespace="$2"
    local timeout_seconds="$3"
    local end=$((SECONDS + timeout_seconds))

    echo "⏳ Waiting for job $job in namespace $namespace to complete or fail..."

    while (( SECONDS < end )); do
        status=$(kubectl get job "$job" -n "$namespace" -o jsonpath="{.status.conditions[*].type}")

        if [[ "$status" == *"Complete"* ]]; then
            echo "✔ Job $job completed."
            return 0   # success: continue loop
        fi

        if [[ "$status" == *"Failed"* ]]; then
            echo "❌ Job $job failed."
            return 1   # failure: exit script
        fi

        sleep 3
    done

    echo "⏱ Timeout waiting for job $job"
    return 2
}

# Iterate over PVCs defined in the STORAGE map
for pvc in "${!STORAGE[@]}"; do
  if [[ -v PVC_NS_MAP["$pvc"] ]]; then
    NAMESPACE="${PVC_NS_MAP["$pvc"]}"
    EXISTING_PVC_NAME="${pvc}"
    HOSTPATH_TUPLES="${STORAGE[$pvc]}" # Get the path(s) and subpath(s)

    # The HOSTPATH_TUPLES string can contain multiple host paths for one PVC (e.g., Opensearch)
    for tuple in $HOSTPATH_TUPLES; do
        OLD_PATH_VAR="${tuple%%:*}"
        
        # Extract SUBPATH only if tuple contains a colon
        if [[ "$tuple" == *:* ]]; then
          SUBPATH="${tuple##*:}"
        else
          SUBPATH=""
        fi

        # Resolve the actual hostPath variable value (e.g., $FAST_DATA_DIR/...)
        OLD_PATH=$(eval echo "$OLD_PATH_VAR")
        

        if [ ! -d "${OLD_PATH}" ]; then
          echo "⚠️ Skipping tuple for ${pvc}: HostPath directory ${OLD_PATH} does not exist. Subpath: ${SUBPATH:-<none>}"
          continue # Skip to the next tuple/pvc
        fi

        # The existing PVC is mounted at /new
        # If a subpath is defined, the PVC volume mount must specify it.
        # However, since the goal is to switch the PVC to a dynamic one later, 
        # we copy the old hostPath contents (e.g., /data) directly into the root of the existing PVC.

        # The hostPath volume will be mounted at /old
        # The existing PVC will be mounted at /new
        
        # When mounting a PVC, it's mounted at the root of the volume.
        # If the original PVC had multiple paths (like Opensearch), those paths were actually subdirectories
        # of the *hostPath volume*. When switching to dynamic, those will be subdirectories of the PVC root.

        # We need to copy OLD_PATH contents (e.g., /fast_data/os/data) into /new/data
        # Where /new is the PVC mount point, and 'data' is the target subdirectory/subpath.

        NEW_MOUNT_TARGET="/new"
        if [ -n "$SUBPATH" ]; then
          NEW_MOUNT_TARGET="/new/${SUBPATH}"
        fi
        
        echo "Migrating tuple for ${pvc} in ${NAMESPACE}: ${OLD_PATH} -> ${EXISTING_PVC_NAME} (target dir: ${NEW_MOUNT_TARGET})"
        #echo "⚠️ WARNING: Using --delete to ensure old database replaces any existing data in the PVC."
        JOB_NAME="migrate-${EXISTING_PVC_NAME:0:40}${SUBPATH}" 
        kubectl apply -f - <<EOF
apiVersion: batch/v1
kind: Job
metadata:
  name: ${JOB_NAME}
  namespace: ${NAMESPACE}
spec:
  backoffLimit: 0
  ttlSecondsAfterFinished: 600  # Clean up 10 minutes after completion/failure
  template:
    spec:
      restartPolicy: Never
      containers:
      - name: migrator
        image: ${MIGRATOR_IMAGE}
        command: ["/bin/bash", "-c"]
        args: ["mkdir -p ${NEW_MOUNT_TARGET} && rsync -avh --delete --progress /old/ ${NEW_MOUNT_TARGET}/"]
        volumeMounts:
        - name: old
          mountPath: /old
        - name: new
          mountPath: /new
      volumes:
      - name: old
        hostPath:
          path: "${OLD_PATH}"
      - name: new
        persistentVolumeClaim:
          claimName: ${EXISTING_PVC_NAME}
EOF
        echo "Waiting for job ${JOB_NAME} to complete..."
        if ! wait_for_job ${JOB_NAME} "${NAMESPACE}" $((24*3600)); then
            echo "❌ ERROR: Migration failed for ${pvc} (${EXISTING_PVC_NAME}) in namespace ${NAMESPACE}"
            echo "Check logs with: kubectl logs -n ${NAMESPACE} -l job-name=${JOB_NAME}"
            exit 1
        fi

        echo "✅ Successfully migrated ${pvc})"
            done
          else
            echo "Skipping ${pvc}: No existing PVC with that name was found in the cluster."
          fi
        done

echo "3️⃣ Migration done."
echo "✅ Next Step:"
echo "Verify data integrity in the existing PVCs."


# Clean up the version flag if migration succeeded
if [ -f "$FAST_DATA_DIR/version" ]; then
  sed -i 's/-fresh deploy and redeploy-needed//' "$FAST_DATA_DIR/version"
fi

echo "✅ Next Steps:"
echo "1. Verify data integrity in the existing PVCs."
echo "2. Patch your Helm chart configuration to use your new dynamic StorageClass, e.g., 'storageClassName: <new-storage-class>', for the existing PVC names (e.g., ${EXISTING_PVC_NAME})."
echo "3. Undeploy and redeploy your application to pick up the new PV/PVC binding logic.