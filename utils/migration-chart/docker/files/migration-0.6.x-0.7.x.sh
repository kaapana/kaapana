#!/bin/bash
set -eu -o pipefail

# ============================================================================
# Kaapana migration 0.6.x -> 0.7.x
#
# In 0.7 the project identifier changed from `name` to `short_id`, and project
# namespaces gained the platform prefix:
#     0.6.x: namespace  = project-<name>
#     0.7.x: namespace  = <PLATFORM_PREFIX>-project-<short_id>
#
# The admin project (short_id == "admin") therefore moves from `project-admin`
# to `<PLATFORM_PREFIX>-project-admin`. Its workflow PVCs (installed models,
# tensorboard, workflow scratch) live on dynamically-provisioned volumes bound
# to the old namespace, so they must be moved to the new namespace or the data
# is orphaned after the upgrade.
#
# MinIO buckets and OpenSearch indexes are NOT re-keyed here: they are handled
# after redeploy by the project-rekey job (services must be running for that).
# Non-admin project namespaces are not migrated here (their short_id can only be
# derived from the running AII) - see migration_guide_0.7.rst.
# ============================================================================

STORAGE_PROVIDER="${STORAGE_PROVIDER}"
STORAGE_CLASS_WORKFLOW="${STORAGE_CLASS_WORKFLOW}"
ADMIN_NAMESPACE="${ADMIN_NAMESPACE}"
PLATFORM_PREFIX="${PLATFORM_PREFIX}"

OLD_NAMESPACE="project-admin"
NEW_NAMESPACE="${PLATFORM_PREFIX}-project-admin"
# The project-namespace helm release is named after the namespace and lives in
# the admin namespace (see aii kubehelm.install_project_helm_chart).
RELEASE_NAME="$NEW_NAMESPACE"
RELEASE_NAMESPACE="$ADMIN_NAMESPACE"

# Workflow PVCs defined by the project-namespace chart (global.dynamicVolumes).
declare -A PVC_SIZE=(
  [models-pv-claim]="200Gi"
  [tensorboard-pv-claim]="10Gi"
  [workflow-data-pv-claim]="200Gi"
)

echo "### Starting migration 0.6.x -> 0.7.x ###"
echo "Using STORAGE_PROVIDER: ${STORAGE_PROVIDER}"
echo "Admin project namespace: ${OLD_NAMESPACE} -> ${NEW_NAMESPACE}"

if [[ "$STORAGE_PROVIDER" != "microk8s.io/hostpath" ]]; then
    echo "Storage provider is not hostpath. Namespace PVC data move is only implemented for hostpath."
    echo "Nothing to do at rest; MinIO/OpenSearch re-keying happens post-deploy."
    exit 0
fi

ensure_namespace() {
    local namespace="$1"
    echo "Ensuring namespace: $namespace (Helm release: $RELEASE_NAME)"
    cat <<EOF | kubectl apply -f - 2>&1
apiVersion: v1
kind: Namespace
metadata:
  name: $namespace
  labels:
    app.kubernetes.io/managed-by: Helm
  annotations:
    meta.helm.sh/release-name: $RELEASE_NAME
    meta.helm.sh/release-namespace: $RELEASE_NAMESPACE
    helm.sh/resource-policy: keep
EOF
}

create_pvc() {
    local pvc_name="$1"
    local namespace="$2"
    local storage="$3"
    echo "Creating PVC $pvc_name in $namespace"
    cat <<EOF | kubectl apply -f - 2>&1
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: $pvc_name
  namespace: $namespace
  labels:
    app.kubernetes.io/managed-by: Helm
  annotations:
    meta.helm.sh/release-name: $RELEASE_NAME
    meta.helm.sh/release-namespace: $RELEASE_NAMESPACE
    helm.sh/resource-policy: keep
spec:
  storageClassName: $STORAGE_CLASS_WORKFLOW
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: $storage
EOF
}

bind_pvc_with_dummy_pod() {
    # Schedule a short-lived pod that mounts the PVC so the hostpath provisioner
    # binds it and materializes the PV hostPath.
    local pvc_name="$1"
    local namespace="$2"
    local pod_name="kaapana-migration-dummy-${pvc_name}"

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
    volumeMounts:
      - name: vol
        mountPath: /mnt/vol
  volumes:
    - name: vol
      persistentVolumeClaim:
        claimName: $pvc_name
EOF

    # Wait for the PVC to actually bind (the pod being merely Pending is not enough:
    # a WaitForFirstConsumer hostpath PV is only created once the pod is scheduled).
    for _ in {1..60}; do
        pvc_phase=$(kubectl get pvc "$pvc_name" -n "$namespace" -o jsonpath='{.status.phase}' 2>/dev/null || echo "")
        if [[ "$pvc_phase" == "Bound" ]]; then
            break
        fi
        sleep 2
    done
}

get_pv_hostpath() {
    local pvc_name="$1"
    local namespace="$2"
    local pv_name
    pv_name=$(kubectl get pvc "$pvc_name" -n "$namespace" -o jsonpath='{.spec.volumeName}' 2>/dev/null)
    [[ -z "$pv_name" ]] && return 1
    kubectl get pv "$pv_name" -o jsonpath='{.spec.hostPath.path}' 2>/dev/null
}

move_data() {
    local source="$1"
    local target="$2"
    if [[ ! -d "$source" || -z "$(ls -A "$source" 2>/dev/null)" ]]; then
        echo "Source empty or missing, nothing to move: $source"
        return 0
    fi
    mkdir -p "$target"
    echo "Moving $source ($(du -sh "$source" 2>/dev/null | awk '{print $1}')) -> $target"
    shopt -s dotglob
    mv "$source"/* "$target/"
    shopt -u dotglob
    rmdir "$source" 2>/dev/null || true
}

delete_dummy_pods() {
    kubectl get pods --all-namespaces \
        -o custom-columns='NS:.metadata.namespace,NAME:.metadata.name' --no-headers 2>/dev/null | \
        awk '$2 ~ "^kaapana-migration-dummy-" {print $1, $2}' | while read -r ns name; do
            kubectl delete pod "$name" -n "$ns" --wait=false || true
        done
}

# ============================================================================
# PostgreSQL 17 -> 18 major-version upgrade
#
# 0.7 bumps the shared postgres image to 18.4-alpine. PostgreSQL refuses to
# start on a data directory written by an older major version, so every
# persisted PG17 cluster (keycloak + the service DBs + dcm4che) must be dumped
# and reloaded into a fresh PG18 cluster before the 0.7 services start.
#
# The platform is DOWN during migration (no postgres Deployments to talk to),
# so this runs entirely via helper pods that mount the fast-data-dir PVC and
# operate on the on-disk cluster directories under FAST_DATA_DIR. The original
# PG17 cluster is preserved as <cluster>_pg17_bak; nothing is deleted.
#
# No plaintext DB passwords are needed: the dump runs under a temporary
# trust-auth pg_hba, and pg_dumpall carries role password *hashes* through.
#
# NOTE: hostpath layouts only (guarded by the STORAGE_PROVIDER check above).
# ============================================================================
PG17_IMAGE="docker.io/postgres:17-alpine"
PG18_IMAGE="docker.io/postgres:18-alpine"
FAST_PVC="fast-data-dir-pvc"
MY_NAMESPACE="$(cat /var/run/secrets/kubernetes.io/serviceaccount/namespace 2>/dev/null || echo migration)"
# Verbose per-pod output (PG server logs, dump/restore chatter) goes here instead of stdout.
PG_LOGFILE="${FAST_DATA_DIR:-/tmp}/migration_0.6_to_0.7_pg.log"

wait_pod_done() { # namespace pod
    local ns=$1 pod=$2 ph
    for _ in $(seq 1 300); do
        ph=$(kubectl get pod -n "$ns" "$pod" -o jsonpath='{.status.phase}' 2>/dev/null || echo "")
        if [[ "$ph" == "Succeeded" || "$ph" == "Failed" ]]; then echo "$ph"; return 0; fi
        sleep 4
    done
    echo "Timeout"
}

run_pg_pod() { # name image script
    local name=$1 image=$2 script=$3 phase
    kubectl delete pod -n "$MY_NAMESPACE" "$name" --ignore-not-found --force --grace-period=0 >/dev/null 2>&1 || true
    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata: {name: $name, namespace: $MY_NAMESPACE}
spec:
  restartPolicy: Never
  containers:
  - name: c
    image: $image
    securityContext: {runAsUser: 0}
    resources: {requests: {memory: 256Mi}, limits: {memory: 3Gi}}
    command: ["sh","-ec"]
    args:
    - |
$(printf '%s\n' "$script" | sed 's/^/      /')
    volumeMounts: [{name: pv, mountPath: /pv}]
  volumes: [{name: pv, persistentVolumeClaim: {claimName: $FAST_PVC}}]
EOF
    phase=$(wait_pod_done "$MY_NAMESPACE" "$name")
    { echo "===== $name ($phase) ====="; kubectl logs -n "$MY_NAMESPACE" "$name" 2>&1; } >> "$PG_LOGFILE"
    echo "  [$name] $phase"
    kubectl delete pod -n "$MY_NAMESPACE" "$name" --ignore-not-found >/dev/null 2>&1
    [[ "$phase" == "Succeeded" ]]
}

upgrade_one_cluster() { # rel target-subdir
    # rel = cluster dir relative to FAST_DATA_DIR (the dir that holds PG_VERSION).
    # target-subdir = where the PG18 cluster must live so the 0.7 deployment finds it:
    #   "18/docker" for the shared postgres chart (subPath data, default PG18 PGDATA)
    #   "."         for dcm4che (explicit PGDATA at the mount root)
    local rel=$1 tgt=$2
    local leaf; leaf=$(basename "$rel")                       # data | postgres-dcm4che
    local tag; tag=$(basename "$(dirname "$rel")"); tag=${tag%-pvc-*}   # e.g. admin-keycloak-pv-claim
    echo "--- upgrading PG17 cluster: $rel (target=$tgt) ---"

    # DUMP (idempotent: skip if a prior run already produced the dump + backup).
    # Superuser is auto-detected under trust auth (pg_dumpall carries password hashes).
    run_pg_pod "pg17dump-$tag" "$PG17_IMAGE" "
D=/pv/$rel
if [ -f \"\$D/../dumpall.sql\" ] && [ -d \"\$D/../${leaf}_pg17_bak\" ]; then echo already-dumped; echo DUMP_DONE; exit 0; fi
[ -f \"\$D/PG_VERSION\" ] || { echo no-cluster; exit 3; }
[ \"\$(cat \$D/PG_VERSION)\" = 17 ] || { echo not-17; exit 4; }
rm -rf \"\$D/18\" \"\$D/postmaster.pid\"
printf 'local all all trust\nhost all all 127.0.0.1/32 trust\nhost all all ::1/128 trust\n' > /tmp/hba.conf
chown 70:70 /tmp/hba.conf; chmod 700 \"\$D\"; chown -R 70:70 \"\$D\"
G=\"\$(command -v su-exec || command -v gosu) postgres\"
\$G pg_ctl -D \"\$D\" -w -t 120 -o \"-c hba_file=/tmp/hba.conf -c listen_addresses=127.0.0.1 -c unix_socket_directories=/tmp -c ssl=off\" start
SU=\"\"
for c in postgres keycloak kaapanauser root pacs; do
  real=\$(\$G psql -h 127.0.0.1 -U \"\$c\" -d template1 -tAc \"select rolname from pg_roles where rolsuper and rolcanlogin order by oid limit 1\" 2>/dev/null | tr -d '[:space:]')
  [ -n \"\$real\" ] && { SU=\"\$real\"; break; }
done
[ -n \"\$SU\" ] || { echo no-superuser-found; exit 6; }
echo \"superuser: \$SU\"
\$G pg_dumpall -h 127.0.0.1 -U \"\$SU\" > \"\$D/../dumpall.sql\"
\$G pg_ctl -D \"\$D\" -w stop
echo \"dump lines: \$(wc -l < \$D/../dumpall.sql)\"
mv \"\$D\" \"\$D/../${leaf}_pg17_bak\"
mkdir \"\$D\"; chown 70:70 \"\$D\"; chmod 700 \"\$D\"
echo DUMP_DONE
" || { echo "  DUMP FAILED for $rel"; return 1; }

    # RESTORE into a fresh PG18 cluster at the target layout, in place.
    run_pg_pod "pg18restore-$tag" "$PG18_IMAGE" "
D=/pv/$rel; BAK=\"\$D/../${leaf}_pg17_bak\"
[ -f \"\$D/../dumpall.sql\" ] || { echo no-dump; exit 5; }
export PGDATA=\"\$D/$tgt\"
find \"\$D\" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
mkdir -p \"\$PGDATA\"; chown -R 70:70 \"\$D\"; chmod 700 \"\$D\" \"\$PGDATA\"
G=\"\$(command -v su-exec || command -v gosu) postgres\"
\$G initdb -U postgres --auth-local=trust --auth-host=trust
\$G pg_ctl -D \"\$PGDATA\" -w -t 120 -o \"-c listen_addresses=127.0.0.1 -c unix_socket_directories=/tmp -c ssl=off\" start
\$G psql -h 127.0.0.1 -U postgres -d postgres -v ON_ERROR_STOP=0 -f \"\$D/../dumpall.sql\" > /tmp/restore.log 2>&1 || true
ERR=\$(grep -c 'ERROR:' /tmp/restore.log || true); echo \"restore ERROR lines: \$ERR\"
grep 'ERROR:' /tmp/restore.log | grep -v 'already exists' | head -20 || true
[ -f \"\$BAK/pg_hba.conf\" ] && { cp \"\$BAK/pg_hba.conf\" \"\$PGDATA/pg_hba.conf\"; chown 70:70 \"\$PGDATA/pg_hba.conf\"; echo restored-pg_hba; }
\$G pg_ctl -D \"\$PGDATA\" -w stop
echo RESTORE_DONE
" || { echo "  RESTORE FAILED for $rel"; return 1; }

    echo "--- $rel upgraded to PG18 (backup kept at $(dirname "$rel")/${leaf}_pg17_bak) ---"
}

upgrade_postgres_clusters() {
    echo "### PostgreSQL 17 -> 18 upgrade (auto-discovery under $FAST_DATA_DIR) ###"
    # Kaapana DB clusters are dynamically provisioned, so their on-disk locations
    # are uuid dirs (<ns>-<pvc>-pvc-<uuid>/{data,postgres-dcm4che}), not fixed
    # paths. Discover every PG17 cluster by scanning for PG_VERSION, and upgrade
    # in place (the DB PVCs keep their namespace/dir across the 0.6->0.7 upgrade).
    local pgv cluster ver bn tgt rel found=0
    while IFS= read -r pgv; do
        [ -n "$pgv" ] || continue
        cluster=$(dirname "$pgv")
        ver=$(cat "$pgv" 2>/dev/null | tr -d '[:space:]')
        [ "$ver" = "17" ] || { echo "skip (PG${ver:-?}): $cluster"; continue; }
        bn=$(basename "$cluster")
        case "$bn" in
            data)             tgt="18/docker" ;;
            postgres-dcm4che) tgt="." ;;
            *) echo "skip (unrecognized cluster layout '$bn'): $cluster"; continue ;;
        esac
        found=1
        rel="${cluster#"$FAST_DATA_DIR"/}"
        upgrade_one_cluster "$rel" "$tgt"
    done <<EOF
$(find "$FAST_DATA_DIR" -maxdepth 3 -type f -name PG_VERSION -not -path '*_pg17_bak*' 2>/dev/null)
EOF
    [ "$found" = 1 ] || echo "No PG17 clusters found under $FAST_DATA_DIR (nothing to upgrade)."
}

cleanup() {
    local exit_code=$?
    delete_dummy_pods || true
    if [[ $exit_code -eq 0 ]]; then
        echo "Migration 0.6.x -> 0.7.x completed successfully"
    else
        echo "Migration 0.6.x -> 0.7.x completed with errors (exit code: $exit_code)"
    fi
    exit $exit_code
}
trap cleanup EXIT

main() {
    # PostgreSQL major-version upgrade must run regardless of the admin-project
    # namespace move below (it operates on the on-disk DB clusters directly).
    upgrade_postgres_clusters

    if ! kubectl get namespace "$OLD_NAMESPACE" >/dev/null 2>&1; then
        echo "Old namespace $OLD_NAMESPACE not found - nothing else to migrate."
        exit 0
    fi

    ensure_namespace "$NEW_NAMESPACE"

    local failures=0
    for pvc_name in "${!PVC_SIZE[@]}"; do
        echo "--- Migrating PVC $pvc_name ---"

        if ! kubectl get pvc "$pvc_name" -n "$OLD_NAMESPACE" >/dev/null 2>&1; then
            echo "PVC $pvc_name not present in $OLD_NAMESPACE, skipping."
            continue
        fi
        if kubectl get pvc "$pvc_name" -n "$NEW_NAMESPACE" >/dev/null 2>&1; then
            echo "PVC $pvc_name already exists in $NEW_NAMESPACE, skipping (idempotent)."
            continue
        fi

        create_pvc "$pvc_name" "$NEW_NAMESPACE" "${PVC_SIZE[$pvc_name]}"
        bind_pvc_with_dummy_pod "$pvc_name" "$NEW_NAMESPACE"

        old_path=$(get_pv_hostpath "$pvc_name" "$OLD_NAMESPACE") || {
            echo "ERROR: could not resolve old hostPath for $pvc_name"
            failures=$((failures + 1))
            continue
        }
        new_path=$(get_pv_hostpath "$pvc_name" "$NEW_NAMESPACE") || {
            echo "ERROR: could not resolve new hostPath for $pvc_name"
            failures=$((failures + 1))
            continue
        }

        move_data "$old_path" "$new_path"
    done

    if [[ "$failures" -gt 0 ]]; then
        echo "ERROR: $failures PVC(s) failed to migrate"
        exit 1
    fi
}

main
