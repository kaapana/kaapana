#!/bin/bash
# Reattach surviving Kaapana data to a fresh cluster. After an OS reinstall, a
# `kaapanactl.sh install --uninstall`, or deleted PVCs, the hostpath directories
# <data dir>/<namespace>-<claim>-pvc-<uuid> are still on disk, but a deploy would
# provision empty volumes next to them. This script recreates the namespaces and
# claims with Helm ownership metadata and binds every claim to a hand-made
# PersistentVolume that points at its surviving directory, so the next normal
# deploy adopts them. Nothing on disk is moved or deleted.
#
# Run BEFORE deploying, on an empty cluster (no Helm releases). Needs kubectl and
# jq, no root. Static binding works without the Kaapana StorageClasses and
# without pulling any image, so no kaapanactl.sh flags are involved.

set -euo pipefail

STORAGE_CLASS_FAST="kaapana-hostpath-fast-data-dir"
STORAGE_CLASS_SLOW="kaapana-hostpath-slow-data-dir"

FAST_DATA_DIR=""
SLOW_DATA_DIR=""
PLATFORM_PREFIX=""
NO_PREFIX=false
ADMIN_RELEASE_NAME="kaapana-admin-chart"
PLATFORM_RELEASE_NAME="kaapana-platform-chart"
SERVICES_NAMESPACE="services"
ADMIN_NAMESPACE="admin"
EXTENSIONS_NAMESPACE="extensions"
HELM_NAMESPACE="default"
VOLUME_SLOW_DATA="100Gi"
NODE_NAME=""
CLAIMS_FILE=""
DRY_RUN=false

usage() {
    cat <<EOF
Usage: $0 --fast-dir DIR --slow-dir DIR (--platform-prefix PREFIX | --no-prefix) [options]

Recreates namespaces and PVCs for the Kaapana data directories that survived a
lost cluster and binds them to their existing hostpath directories. Run it on
an empty cluster, then deploy the platform as usual.

Required:
  --fast-dir DIR               FAST_DATA_DIR of the previous deployment
  --slow-dir DIR               SLOW_DATA_DIR of the previous deployment
  --platform-prefix PREFIX     PLATFORM_PREFIX of the previous deployment; project
                               namespaces are <prefix>-project-*
  --no-prefix                  instead of a prefix, for 0.6.x data whose project
                               namespaces are bare project-*

Options (defaults match kaapanactl.sh):
  --admin-release-name NAME    Helm release of the admin chart (default: kaapana-admin-chart)
  --platform-release-name NAME Helm release of the platform chart (default: kaapana-platform-chart)
  --services-namespace NS      (default: services)
  --admin-namespace NS         (default: admin)
  --extensions-namespace NS    (default: extensions)
  --helm-namespace NS          namespace of the admin chart release (default: default)
  --volume-slow-data SIZE      size of the slow-data claims (default: 100Gi)
  --claims-file FILE           extra claims to recover, one per line:
                                 <namespace>/<claim> <class> <size> <release> <release-namespace>
                               <class> is fast, slow or a StorageClass name; "project/<claim>"
                               matches every project namespace; # starts a comment.
                               Meant for extension claims, which the platform table does not
                               know - a distribution can generate the file from its charts.
  --node NAME                  pin the volumes to this node (multi-node clusters)
  --dry-run                    print the manifests instead of applying them
  -h, --help

Environment:
  KUBECTL                      kubectl command to use (default: microk8s.kubectl, then kubectl)
EOF
}

die() {
    echo "ERROR: $*" >&2
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --fast-dir) FAST_DATA_DIR="$2"; shift 2 ;;
        --slow-dir) SLOW_DATA_DIR="$2"; shift 2 ;;
        --platform-prefix) PLATFORM_PREFIX="$2"; shift 2 ;;
        --no-prefix) NO_PREFIX=true; shift ;;
        --admin-release-name) ADMIN_RELEASE_NAME="$2"; shift 2 ;;
        --platform-release-name) PLATFORM_RELEASE_NAME="$2"; shift 2 ;;
        --services-namespace) SERVICES_NAMESPACE="$2"; shift 2 ;;
        --admin-namespace) ADMIN_NAMESPACE="$2"; shift 2 ;;
        --extensions-namespace) EXTENSIONS_NAMESPACE="$2"; shift 2 ;;
        --helm-namespace) HELM_NAMESPACE="$2"; shift 2 ;;
        --volume-slow-data) VOLUME_SLOW_DATA="$2"; shift 2 ;;
        --claims-file) CLAIMS_FILE="$2"; shift 2 ;;
        --node) NODE_NAME="$2"; shift 2 ;;
        --dry-run) DRY_RUN=true; shift ;;
        -h|--help) usage; exit 0 ;;
        *) die "unknown argument: $1 (see --help)" ;;
    esac
done

[[ -n "$FAST_DATA_DIR" && -n "$SLOW_DATA_DIR" ]] \
    || die "--fast-dir and --slow-dir are required (see --help)"
# The prefix decides which project directories are recognised, and a forgotten
# prefix would silently skip every project of a 0.7.x site - so "none" has to be
# said explicitly.
if [[ "$NO_PREFIX" == true ]]; then
    [[ -z "$PLATFORM_PREFIX" ]] || die "--no-prefix and --platform-prefix exclude each other"
else
    [[ -n "$PLATFORM_PREFIX" ]] || die "--platform-prefix PREFIX or --no-prefix is required (see --help)"
fi
for dir in "$FAST_DATA_DIR" "$SLOW_DATA_DIR"; do
    [[ -d "$dir" ]] || die "not a directory: $dir"
done
command -v jq >/dev/null 2>&1 || die "jq is required but not installed"

KUBECTL="${KUBECTL:-}"
if [[ -z "$KUBECTL" ]]; then
    KUBECTL="kubectl"
    command -v microk8s.kubectl >/dev/null 2>&1 && KUBECTL="microk8s.kubectl"
fi
# KUBECTL may carry arguments ("microk8s kubectl"), so it is expanded unquoted on purpose.
kube() {
    # shellcheck disable=SC2086
    $KUBECTL "$@"
}

# Claims the platform charts create, keyed "<namespace>/<claim>" ("project/<claim>"
# for the per-project namespaces), with the StorageClass and size the chart
# requests on this version. Sizes have to match: a claim cannot shrink, and
# hostpath cannot grow, so Helm fails to adopt a claim of a different size.
# The class cannot be read off the directory when fast and slow dir are the
# same path, which is the default. Directories of claims not listed here (e.g.
# extension apps, owned by their own Helm release) are reported and left alone.
declare -A CLAIM_SPEC
define_known_claims() {
    local s="$SERVICES_NAMESPACE" a="$ADMIN_NAMESPACE" name
    # kaapana_database subcharts: <appName>-pv-claim, 10Gi (postgres-chart/values.yaml)
    for name in access-information-interface dicom-web-filter airflow notification-service \
                kaapana-backend data-api workflow-api extension-manager; do
        CLAIM_SPEC["$s/$name-pv-claim"]="$STORAGE_CLASS_FAST|10Gi"
    done
    # global.dynamicVolumes of the platform service charts (services/*/values.yaml)
    for name in opensearch os-certs loki prometheus; do
        CLAIM_SPEC["$s/$name-pv-claim"]="$STORAGE_CLASS_FAST|10Gi"
    done
    for name in ctp-data dcm4che uploads af-logs; do
        CLAIM_SPEC["$s/$name-pv-claim"]="$STORAGE_CLASS_FAST|100Gi"
    done
    for name in data-api-artifacts models workflow-data; do
        CLAIM_SPEC["$s/$name-pv-claim"]="$STORAGE_CLASS_FAST|200Gi"
    done
    for name in af-plugins dags; do
        CLAIM_SPEC["$s/$name-pv-claim"]="$STORAGE_CLASS_FAST|1Gi"
    done
    for name in extensions extensions-tmp; do
        CLAIM_SPEC["$s/$name-pv-claim"]="$STORAGE_CLASS_SLOW|10Gi"
    done
    for name in dcm4chee-standalone dcm4chee-dicom minio; do
        CLAIM_SPEC["$s/$name-pv-claim"]="$STORAGE_CLASS_SLOW|$VOLUME_SLOW_DATA"
    done
    # admin chart: keycloak database, TLS material, kube-helm's extension store
    for name in keycloak tls extensions; do
        CLAIM_SPEC["$a/$name-pv-claim"]="$STORAGE_CLASS_FAST|10Gi"
    done
    # project-namespace chart, one set per <prefix>-project-* namespace
    CLAIM_SPEC["project/models-pv-claim"]="$STORAGE_CLASS_FAST|200Gi"
    CLAIM_SPEC["project/workflow-data-pv-claim"]="$STORAGE_CLASS_FAST|200Gi"
    CLAIM_SPEC["project/tensorboard-pv-claim"]="$STORAGE_CLASS_FAST|10Gi"
}

# Extension claims are owned by the extension's own Helm release, not by the
# platform release of their namespace, so a --claims-file row carries the
# release as well. Rows override the built-in table for the same key.
declare -A CLAIM_OWNER
load_claims_file() {
    local line key class size release release_ns extra lineno=0
    [[ -n "$CLAIMS_FILE" ]] || return 0
    [[ -r "$CLAIMS_FILE" ]] || die "cannot read --claims-file $CLAIMS_FILE"
    while IFS= read -r line || [[ -n "$line" ]]; do
        lineno=$((lineno + 1))
        line="${line%%#*}"
        [[ -z "${line//[[:space:]]/}" ]] && continue
        read -r key class size release release_ns extra <<< "$line"
        [[ "$key" == */* && -n "$release_ns" && -z "$extra" ]] \
            || die "$CLAIMS_FILE:$lineno: expected '<namespace>/<claim> <class> <size> <release> <release-namespace>'"
        case "$class" in
            fast) class="$STORAGE_CLASS_FAST" ;;
            slow) class="$STORAGE_CLASS_SLOW" ;;
        esac
        CLAIM_SPEC["$key"]="$class|$size"
        CLAIM_OWNER["$key"]="$release|$release_ns"
    done < "$CLAIMS_FILE"
}

# Helm release that owns a namespace and its claims, as "<release>|<release namespace>".
# Helm only adopts pre-existing resources whose ownership annotations name the
# release that is about to install them; a wrong owner fails the deploy.
owner_of_namespace() {
    case "$1" in
        "$ADMIN_NAMESPACE") echo "$ADMIN_RELEASE_NAME|$HELM_NAMESPACE" ;;
        "$SERVICES_NAMESPACE"|"$EXTENSIONS_NAMESPACE") echo "$PLATFORM_RELEASE_NAME|$ADMIN_NAMESPACE" ;;
        # Project namespaces are installed by kube-helm as a release named like the
        # namespace, in the admin namespace (access-information-interface kubehelm.py).
        *) echo "$1|$ADMIN_NAMESPACE" ;;
    esac
}

# Splits a directory name "<namespace>-<claim>-pvc-<uuid>" into
# "<namespace>|<claim>|<CLAIM_SPEC key>". Namespaces and claims both contain
# dashes, so the split goes by the known namespace names. Project namespaces
# are [<prefix>-]project-<id>, and a 0.6.x id is the project name, dashes
# included - so project dirs are split at the claim names the project-namespace
# chart creates (the "project/..." entries of CLAIM_SPEC), not at the id. Bare
# project-* dirs (0.6.x, or --no-prefix) are accepted alongside the prefixed form.
parse_dir_name() {
    local stem ns project_ns="project-.+"
    [[ -n "$PLATFORM_PREFIX" ]] && project_ns="(${PLATFORM_PREFIX}-)?${project_ns}"
    [[ "$1" =~ ^(.+)-pvc-[0-9a-f-]+$ ]] || return 1
    stem="${BASH_REMATCH[1]}"
    if [[ "$stem" =~ ^(${project_ns})-(models|workflow-data|tensorboard)-pv-claim$ ]]; then
        ns="${BASH_REMATCH[1]}"
        echo "$ns|${stem#"$ns-"}|project/${stem#"$ns-"}"
        return 0
    fi
    for ns in "$SERVICES_NAMESPACE" "$ADMIN_NAMESPACE" "$EXTENSIONS_NAMESPACE"; do
        if [[ "$stem" == "$ns-"* ]]; then
            echo "$ns|${stem#"$ns-"}|$ns/${stem#"$ns-"}"
            return 0
        fi
    done
    return 1
}

apply_manifest() {
    if [[ "$DRY_RUN" == true ]]; then
        echo "---"
        cat
    else
        kube apply -f - >/dev/null
    fi
}

ensure_namespace() {
    local ns="$1" owner release release_ns
    owner="$(owner_of_namespace "$ns")"
    release="${owner%%|*}"
    release_ns="${owner##*|}"
    apply_manifest <<EOF
apiVersion: v1
kind: Namespace
metadata:
  name: $ns
  labels:
    app.kubernetes.io/managed-by: Helm
  annotations:
    meta.helm.sh/release-name: $release
    meta.helm.sh/release-namespace: $release_ns
    helm.sh/resource-policy: keep
EOF
}

# Collected for the report at the end, so the outcome is readable without
# scrolling through the per-directory output.
RECOVERED_LIST=()
SKIPPED_LIST=()
skip() {
    echo "  skipped $1: $2"
    SKIPPED_LIST+=("$1: $2")
}

recover_dir() {
    local dir="$1" base ns="" claim="" key="" spec class size
    local pv="" phase="" pv_size="" pv_class="" owner release release_ns node_affinity=""
    base="$(basename "$dir")"

    IFS='|' read -r ns claim key < <(parse_dir_name "$base") \
        || { skip "$base" "directory name not recognised"; return 0; }
    spec="${CLAIM_SPEC[$key]:-}"
    [[ -n "$spec" ]] || { skip "$base" "not a platform claim (extension or unknown owner), left in place - see --claims-file"; return 0; }
    IFS='|' read -r class size <<< "$spec"

    # A PV that still points at this directory (Retain class, cluster survived)
    # is reused; only the claim it belonged to has to be recreated.
    IFS=$'\t' read -r pv phase pv_size pv_class < <(jq -r --arg path "$dir" \
        '.items[] | select(.spec.hostPath.path == $path)
         | [.metadata.name, .status.phase, .spec.capacity.storage, .spec.storageClassName // ""] | @tsv' \
        <<< "$PV_JSON") || true
    if [[ -n "$pv" && "$phase" == "Bound" ]]; then
        skip "$base" "PV $pv is already bound"
        return 0
    fi
    if kube get pvc "$claim" -n "$ns" >/dev/null 2>&1; then
        skip "$base" "claim $ns/$claim already exists, left as is"
        return 0
    fi

    ensure_namespace "$ns"
    # The namespace always belongs to the platform; the claim may belong to an extension.
    owner="${CLAIM_OWNER[$key]:-$(owner_of_namespace "$ns")}"
    release="${owner%%|*}"
    release_ns="${owner##*|}"

    if [[ -n "$pv" ]]; then
        # Released PVs keep the uid of the deleted claim in claimRef; a claim only
        # binds once that uid is gone and namespace/name point at the new claim.
        size="${pv_size:-$size}"
        class="${pv_class:-$class}"
        if [[ "$DRY_RUN" == true ]]; then
            echo "--- would patch pv/$pv claimRef -> $ns/$claim"
        else
            kube patch pv "$pv" --type merge -p \
                "{\"spec\":{\"claimRef\":{\"namespace\":\"$ns\",\"name\":\"$claim\",\"uid\":null,\"resourceVersion\":null}}}" \
                >/dev/null
        fi
    else
        pv="$base"
        if [[ -n "$NODE_NAME" ]]; then
            node_affinity="
  nodeAffinity:
    required:
      nodeSelectorTerms:
      - matchExpressions:
        - key: kubernetes.io/hostname
          operator: In
          values: [\"$NODE_NAME\"]"
        fi
        # Retain on the PV itself: deleting the claim later releases the volume
        # but never removes the directory, whatever the StorageClass says.
        apply_manifest <<EOF
apiVersion: v1
kind: PersistentVolume
metadata:
  name: $pv
spec:
  capacity:
    storage: $size
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain
  storageClassName: $class
  claimRef:
    namespace: $ns
    name: $claim
  hostPath:
    path: $dir
    type: Directory$node_affinity
EOF
    fi

    # volumeName makes the binding static: the PV controller binds a named volume
    # at once, even for WaitForFirstConsumer classes and without the class existing.
    apply_manifest <<EOF
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: $claim
  namespace: $ns
  labels:
    app.kubernetes.io/managed-by: Helm
  annotations:
    meta.helm.sh/release-name: $release
    meta.helm.sh/release-namespace: $release_ns
    helm.sh/resource-policy: keep
spec:
  storageClassName: $class
  volumeName: $pv
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: $size
EOF
    echo "  recovered $ns/$claim <- $dir"
    RECOVERED_LIST+=("$ns/$claim <- $base")
}

# Helm release secrets in the two release namespaces are the sign of a deployed
# platform; adopting namespaces under a running release would rewrite its
# ownership. Only those two are checked: the storage class release
# (kaapana-system) and the GPU operator survive an undeploy on purpose.
for ns in "$HELM_NAMESPACE" "$ADMIN_NAMESPACE"; do
    if kube get secrets -n "$ns" -l owner=helm -o name 2>/dev/null | grep -q .; then
        die "Helm releases exist in namespace $ns. Recovery only runs on an undeployed platform - undeploy first."
    fi
done

define_known_claims
load_claims_file
PV_JSON="$(kube get pv -o json 2>/dev/null || echo '{"items":[]}')"

mapfile -t DIRS < <(find "$FAST_DATA_DIR" "$SLOW_DATA_DIR" -mindepth 1 -maxdepth 1 -type d -name '*-pvc-*' | sort -u)

# Two directories for the same claim means the host carries volumes of more
# than one platform lifetime. The uuid in the name carries no order, so picking
# one would be a coin flip; stop before anything is applied and let the
# operator move the obsolete directories away.
declare -A SEEN
for dir in "${DIRS[@]}"; do
    parsed="$(parse_dir_name "$(basename "$dir")")" || continue
    IFS='|' read -r ns claim _ <<< "$parsed"
    key="$ns/$claim"
    if [[ -n "${SEEN[$key]:-}" ]]; then
        die "more than one directory for claim $key:
  - ${SEEN[$key]}
  - $dir
Move the directories of obsolete platform lifetimes out of the data directories and run again."
    fi
    SEEN[$key]="$dir"
done

echo "Recovering Kaapana claims from $FAST_DATA_DIR and $SLOW_DATA_DIR"
[[ "$DRY_RUN" == true ]] && echo "(dry run - nothing is applied)"
for dir in "${DIRS[@]}"; do
    recover_dir "$dir"
done

echo
echo "Recovered (${#RECOVERED_LIST[@]}):"
[[ ${#RECOVERED_LIST[@]} -eq 0 ]] || printf '  %s\n' "${RECOVERED_LIST[@]}"
echo "Skipped (${#SKIPPED_LIST[@]}):"
[[ ${#SKIPPED_LIST[@]} -eq 0 ]] || printf '  %s\n' "${SKIPPED_LIST[@]}"
[[ ${#DIRS[@]} -gt 0 ]] || echo "No *-pvc-* directories found - are --fast-dir/--slow-dir the previous data directories?"
[[ "$DRY_RUN" == true ]] || echo "Now deploy the platform as usual; the deploy adopts the recovered namespaces and claims."
