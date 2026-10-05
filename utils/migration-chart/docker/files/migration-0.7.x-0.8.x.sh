#!/bin/bash
set -eu -o pipefail

FAST_DATA_DIR="${1:-${FAST_DATA_DIR}}"
STORAGE_PROVIDER="${STORAGE_PROVIDER}"

PG18_IMAGE="docker.io/postgres:18-alpine"
FAST_PVC="fast-data-dir-pvc"
MY_NAMESPACE="$(cat /var/run/secrets/kubernetes.io/serviceaccount/namespace 2>/dev/null || echo migration)"
PG_LOGFILE="${FAST_DATA_DIR}/migration_0.7_to_0.8_pg.log"

read -r -d '' EXTENSION_MANAGER_SQL <<'SQL' || true
DO $$
DECLARE
    fk_name text;
BEGIN
    IF to_regclass('public.extensions') IS NULL OR to_regclass('public.registries') IS NULL THEN
        RAISE NOTICE 'extension-manager tables not found, nothing to migrate';
        RETURN;
    END IF;
    ALTER TABLE extensions ALTER COLUMN repository_id DROP NOT NULL;
    FOR fk_name IN
        SELECT conname FROM pg_constraint
        WHERE conrelid = 'extensions'::regclass
          AND confrelid = 'registries'::regclass
          AND contype = 'f'
          AND confdeltype <> 'n'
    LOOP
        EXECUTE format('ALTER TABLE extensions DROP CONSTRAINT %I', fk_name);
    END LOOP;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'extensions'::regclass
          AND confrelid = 'registries'::regclass
          AND contype = 'f'
    ) THEN
        ALTER TABLE extensions ADD CONSTRAINT extensions_repository_id_fkey
            FOREIGN KEY (repository_id) REFERENCES registries (id) ON DELETE SET NULL;
    END IF;
END $$;
SQL

echo "### Starting migration 0.7.x -> 0.8.x ###"
echo "Using STORAGE_PROVIDER: ${STORAGE_PROVIDER}"

if [[ "$STORAGE_PROVIDER" != "microk8s.io/hostpath" ]]; then
    echo "Storage provider is not hostpath. The extension-manager schema change is only implemented for hostpath."
    echo "Apply it manually on the extension-manager database:"
    echo "$EXTENSION_MANAGER_SQL"
    exit 0
fi

wait_pod_done() {
    local ns=$1 pod=$2 ph
    for _ in $(seq 1 300); do
        ph=$(kubectl get pod -n "$ns" "$pod" -o jsonpath='{.status.phase}' 2>/dev/null || echo "")
        if [[ "$ph" == "Succeeded" || "$ph" == "Failed" ]]; then echo "$ph"; return 0; fi
        sleep 4
    done
    echo "Timeout"
}

run_pg_pod() {
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
    resources: {requests: {memory: 256Mi}, limits: {memory: 1Gi}}
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

migrate_extension_manager_db() {
    local rel=$1
    local sql_b64
    sql_b64=$(printf '%s\n' "$EXTENSION_MANAGER_SQL" | base64 -w0)
    echo "--- detaching extensions from removed repositories: $rel ---"
    run_pg_pod "extension-manager-schema" "$PG18_IMAGE" "
D=/pv/$rel
[ -f \"\$D/PG_VERSION\" ] || { echo no-cluster; exit 3; }
[ \"\$(cat \$D/PG_VERSION)\" = 18 ] || { echo not-18; exit 4; }
rm -f \"\$D/postmaster.pid\"
printf 'local all all trust\nhost all all 127.0.0.1/32 trust\nhost all all ::1/128 trust\n' > /tmp/hba.conf
chown 70:70 /tmp/hba.conf
echo '$sql_b64' | base64 -d > /tmp/migration.sql
G=\"\$(command -v su-exec || command -v gosu) postgres\"
\$G pg_ctl -D \"\$D\" -w -t 120 -o \"-c hba_file=/tmp/hba.conf -c listen_addresses=127.0.0.1 -c unix_socket_directories=/tmp -c ssl=off\" start
STATUS=0
\$G psql -h 127.0.0.1 -U postgres -d postgres -v ON_ERROR_STOP=1 -f /tmp/migration.sql || STATUS=\$?
\$G pg_ctl -D \"\$D\" -w stop
[ \"\$STATUS\" = 0 ] || { echo SQL_FAILED; exit \"\$STATUS\"; }
echo SCHEMA_DONE
"
}

main() {
    local pgv rel found=0
    for pgv in "$FAST_DATA_DIR"/*-extension-manager-pv-claim-pvc-*/data/18/docker/PG_VERSION; do
        [ -f "$pgv" ] || continue
        found=1
        rel="$(dirname "$pgv")"
        rel="${rel#"$FAST_DATA_DIR"/}"
        if ! migrate_extension_manager_db "$rel"; then
            echo "ERROR: extension-manager schema migration failed for $rel (see $PG_LOGFILE)"
            exit 1
        fi
    done
    [ "$found" = 1 ] || echo "No extension-manager database found under $FAST_DATA_DIR (nothing to migrate)."
    echo "Migration 0.7.x -> 0.8.x completed successfully"
}

main
