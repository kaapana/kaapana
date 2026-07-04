#!/bin/bash

set -euo pipefail

# Reconcile AII project metadata and Kubernetes project namespaces after reinstall/recover.
# Behavior:
# 1) Reads authoritative project metadata from AII.
# 2) Normalizes Helm ownership metadata on project-* namespaces.
# 3) Reconciles the project-namespace Helm release for every known project.
# 4) Waits until all expected project namespaces exist in Kubernetes.
# 5) Synchronizes system-user-password from services namespace to admin/project namespaces.
# 6) Synchronizes registry-secret from services namespace to project namespaces.
# 7) Validates required project PVCs and bootstrap secrets for all project-* namespaces, including project-admin.
#
# Optional environment overrides:
#   SERVICES_NAMESPACE=services
#   ADMIN_NAMESPACE=admin
#   WAIT_TIMEOUT_SECONDS=180
#   KUBE=microk8s.kubectl|kubectl
#   HELM=microk8s.helm|helm
#   PROJECT_BOOTSTRAP_INVENTORY_CONFIGMAP=project-bootstrap-inventory
#   PROJECT_NAMESPACE_TEMPLATE_RELEASE=project-admin
#   REQUIRED_PROJECT_PVCS_CSV=tensorboard-pv-claim,models-pv-claim
#   REQUIRED_PROJECT_SECRETS_CSV=registry-secret,system-user-password

SERVICES_NAMESPACE="${SERVICES_NAMESPACE:-services}"
ADMIN_NAMESPACE="${ADMIN_NAMESPACE:-admin}"
WAIT_TIMEOUT_SECONDS="${WAIT_TIMEOUT_SECONDS:-180}"
AIRFLOW_CONTAINER="${AIRFLOW_CONTAINER:-webserver}"
PROJECT_BOOTSTRAP_INVENTORY_CONFIGMAP="${PROJECT_BOOTSTRAP_INVENTORY_CONFIGMAP:-project-bootstrap-inventory}"
# Namespace prefix of the platform. Current kaapana creates project namespaces
# as <prefix>-project-<id>; legacy installs used bare project-<id>. All
# project-namespace matching below accepts both forms so pre-prefix data can
# still be reconciled. Pass via the PLATFORM_PREFIX environment variable.
PLATFORM_PREFIX="${PLATFORM_PREFIX:-}"
if [[ -n "${PLATFORM_PREFIX}" ]]; then
    PROJECT_NS_REGEX="^(${PLATFORM_PREFIX}-)?project-"
    PROJECT_ADMIN_NS="${PLATFORM_PREFIX}-project-admin"
else
    PROJECT_NS_REGEX="^project-"
    PROJECT_ADMIN_NS="project-admin"
fi
# Keep a conservative fallback list for recovery situations where no
# authoritative project release can be queried from Helm yet.
DEFAULT_REQUIRED_PROJECT_PVCS=("tensorboard-pv-claim" "models-pv-claim" "workflow-data-pv-claim")
DEFAULT_REQUIRED_PROJECT_SECRETS=("registry-secret" "system-user-password" "project-user-credentials" "oidc-client-secret")
REQUIRED_PROJECT_PVCS=("${DEFAULT_REQUIRED_PROJECT_PVCS[@]}")
REQUIRED_PROJECT_SECRETS=("${DEFAULT_REQUIRED_PROJECT_SECRETS[@]}")

if [[ -n "${KUBE:-}" ]]; then
    :
elif command -v microk8s.kubectl >/dev/null 2>&1; then
    KUBE="microk8s.kubectl"
else
    KUBE="kubectl"
fi

if [[ -n "${HELM:-}" ]]; then
    :
elif command -v microk8s.helm >/dev/null 2>&1; then
    HELM="microk8s.helm"
else
    HELM="helm"
fi

if ! command -v jq >/dev/null 2>&1; then
    echo "ERROR: jq is required but not installed."
    exit 1
fi

if ! command -v "${HELM}" >/dev/null 2>&1; then
    echo "ERROR: Helm client not found: ${HELM}"
    exit 1
fi

# Split a comma-separated override into one trimmed item per line.
csv_to_lines() {
    local csv="$1"
    local item=""
    IFS=',' read -r -a _csv_items <<< "${csv}"
    for item in "${_csv_items[@]}"; do
        item="${item#"${item%%[![:space:]]*}"}"
        item="${item%"${item##*[![:space:]]}"}"
        [[ -n "${item}" ]] && printf '%s\n' "${item}"
    done
}

helm_release_exists() {
    local release_name="$1"
    ${HELM} status "${release_name}" -n "${ADMIN_NAMESPACE}" >/dev/null 2>&1
}

# Pick a project release whose manifest can serve as the authoritative
# bootstrap template for reconciliation.
discover_template_project_release() {
    local release_name=""

    # Allow operators to point reconciliation at a known-good project release,
    # then fall back to the namespaces discovered from AII metadata.
    if [[ -n "${PROJECT_NAMESPACE_TEMPLATE_RELEASE:-}" ]] && helm_release_exists "${PROJECT_NAMESPACE_TEMPLATE_RELEASE}"; then
        printf '%s\n' "${PROJECT_NAMESPACE_TEMPLATE_RELEASE}"
        return 0
    fi

    while IFS= read -r release_name; do
        [[ -z "${release_name}" ]] && continue
        if helm_release_exists "${release_name}"; then
            printf '%s\n' "${release_name}"
            return 0
        fi
    done <<< "${EXPECTED_NAMESPACES:-}"

    return 1
}

get_template_release_manifest_json() {
    local release_name="$1"

    # Convert the rendered Helm manifest into structured JSON so the bootstrap
    # inventory can be queried with jq instead of brittle text parsing.
    ${HELM} get manifest "${release_name}" -n "${ADMIN_NAMESPACE}" 2>/dev/null \
        | ${KUBE} apply --dry-run=client -f - -o json 2>/dev/null
}

# Read the chart-published bootstrap PVC inventory from the template release.
derive_required_project_pvcs_from_inventory_manifest() {
    local manifest_json="$1"

    printf '%s\n' "${manifest_json}" | jq -r --arg configmap_name "${PROJECT_BOOTSTRAP_INVENTORY_CONFIGMAP}" '
        .items[]
        | select(.kind == "ConfigMap" and .metadata.name == $configmap_name)
        | .data.requiredProjectPvcs // ""
    ' | awk 'NF { print $0 }' | sort -u
}

derive_required_project_secrets_from_inventory_manifest() {
    local manifest_json="$1"

    # Read the chart-published bootstrap secret inventory from the template
    # release instead of treating every Secret in the manifest as required.
    printf '%s\n' "${manifest_json}" | jq -r --arg configmap_name "${PROJECT_BOOTSTRAP_INVENTORY_CONFIGMAP}" '
        .items[]
        | select(.kind == "ConfigMap" and .metadata.name == $configmap_name)
        | .data.requiredProjectSecrets // ""
    ' | awk 'NF { print $0 }' | sort -u
}

# Resolve the bootstrap contract used for strict validation.
# Preference order:
# 1) explicit CSV overrides,
# 2) bootstrap inventory from an in-cluster project release,
# 3) conservative defaults for recovery/bootstrap scenarios.
initialize_required_project_resources() {
    local template_release=""
    local manifest_json=""

    if [[ -n "${REQUIRED_PROJECT_PVCS_CSV:-}" ]]; then
        mapfile -t REQUIRED_PROJECT_PVCS < <(csv_to_lines "${REQUIRED_PROJECT_PVCS_CSV}")
    else
        template_release="$(discover_template_project_release || true)"
        if [[ -n "${template_release}" ]]; then
            manifest_json="$(get_template_release_manifest_json "${template_release}" || true)"
            if [[ -n "${manifest_json}" ]]; then
                mapfile -t REQUIRED_PROJECT_PVCS < <(derive_required_project_pvcs_from_inventory_manifest "${manifest_json}")
            fi
        fi
    fi

    if [[ -n "${REQUIRED_PROJECT_SECRETS_CSV:-}" ]]; then
        mapfile -t REQUIRED_PROJECT_SECRETS < <(csv_to_lines "${REQUIRED_PROJECT_SECRETS_CSV}")
    elif [[ -n "${manifest_json}" ]]; then
        mapfile -t REQUIRED_PROJECT_SECRETS < <(derive_required_project_secrets_from_inventory_manifest "${manifest_json}")
    fi

    if [[ ${#REQUIRED_PROJECT_PVCS[@]} -eq 0 ]]; then
        REQUIRED_PROJECT_PVCS=("${DEFAULT_REQUIRED_PROJECT_PVCS[@]}")
    fi

    if [[ ${#REQUIRED_PROJECT_SECRETS[@]} -eq 0 ]]; then
        REQUIRED_PROJECT_SECRETS=("${DEFAULT_REQUIRED_PROJECT_SECRETS[@]}")
    fi
}

echo "======================================================"
echo "Reconciling project namespaces from AII metadata"
echo "======================================================"
echo "Kube client: ${KUBE}"
echo "Helm client: ${HELM}"
echo "Services namespace: ${SERVICES_NAMESPACE}"
echo "Admin namespace: ${ADMIN_NAMESPACE}"
echo "Airflow container: ${AIRFLOW_CONTAINER}"
echo ""

AIRFLOW_POD="$(
    ${KUBE} -n "${SERVICES_NAMESPACE}" get pod -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' \
    | { grep '^airflow-webserver' || true; } \
    | head -n1
)"

if [[ -z "${AIRFLOW_POD}" ]]; then
    echo "ERROR: Could not find airflow-webserver pod in namespace '${SERVICES_NAMESPACE}'"
    exit 1
fi

echo "Using pod: ${AIRFLOW_POD}"
echo ""

# Delay resource discovery until AII has told us which project namespaces
# should exist, so we can reuse those release names when selecting a template.
get_aii_projects_json() {
    ${KUBE} -n "${SERVICES_NAMESPACE}" exec -i "${AIRFLOW_POD}" -c "${AIRFLOW_CONTAINER}" -- python - "${SERVICES_NAMESPACE}" <<'PY'
import json
import sys

import requests
from kaapanapy.helper import get_project_user_access_token

services_namespace = sys.argv[1]
base_url = f"http://aii-service.{services_namespace}.svc:8080"
token = get_project_user_access_token()
headers = {
    "x-forwarded-access-token": token,
    "Content-Type": "application/json",
}

response = requests.get(f"{base_url}/projects", headers=headers, timeout=30)
if response.status_code >= 400:
    body = response.text.strip().replace("\n", " ")
    raise RuntimeError(
        f"GET {base_url}/projects failed with status={response.status_code}, body={body}"
    )
response.raise_for_status()
projects = response.json()

if not isinstance(projects, list):
    raise RuntimeError(f"Unexpected response from {base_url}/projects: {type(projects)}")

print(json.dumps(projects))
PY
}

reconcile_project_namespace_releases() {
    ${KUBE} -n "${SERVICES_NAMESPACE}" exec -i "${AIRFLOW_POD}" -c "${AIRFLOW_CONTAINER}" -- python - "${SERVICES_NAMESPACE}" <<'PY'
import json
import os
import sys

import requests
from kaapanapy.helper import get_project_user_access_token

services_namespace = sys.argv[1]
kube_helm_url = "http://kube-helm-service.admin.svc:5000/kube-helm-api/helm-install-chart"
aii_base_url = f"http://aii-service.{services_namespace}.svc:8080"
build_version = os.environ.get("KAAPANA_BUILD_VERSION")
token = get_project_user_access_token()
headers = {
    "x-forwarded-access-token": token,
    "Content-Type": "application/json",
}

if not build_version:
    raise RuntimeError("KAAPANA_BUILD_VERSION is not set in the Airflow container.")

response = requests.get(f"{aii_base_url}/projects", headers=headers, timeout=30)
response.raise_for_status()
projects = response.json()
if not isinstance(projects, list):
    raise RuntimeError(
        f"Unexpected response from {aii_base_url}/projects: {type(projects)}"
    )

count = 0
for project in projects:
    project_id = project.get("id")
    name = project.get("name") or ""
    namespace = project.get("kubernetes_namespace") or ""
    if not project_id or not name or not namespace:
        continue

    # AII itself passes project.short_id as the "project" extension param
    # (see aii projects/kubehelm.py); mirror that so the reconciled manifest
    # is identical to an AII-installed one (avoids helm diff/ownership churn).
    short_id = project.get("short_id") or (
        namespace.split("project-", 1)[-1] if "project-" in namespace else name
    )

    # Reconcile the per-project chart directly through kube-helm instead of
    # replaying AII project creation. The POST /projects route is not a safe
    # recovery surface for existing projects because it re-runs non-idempotent
    # side effects after the duplicate project row is detected.
    # NOTE: kube-helm may answer HTTP 200 for releases it SKIPS (e.g. a
    # release in failed state is "blocked", not installed); the helm-status
    # verification step after this function catches those cases.
    payload = {
        "name": "project-namespace",
        "release_name": namespace,
        "version": build_version,
        "extension_params": {
            "project": short_id,
            "project_namespace": namespace,
            "namespace": namespace,
            "project_id": project_id,
        },
    }
    reconcile_response = requests.post(kube_helm_url, json=payload, timeout=300)
    if reconcile_response.status_code >= 400:
        response_body = reconcile_response.text.strip().replace("\n", " ")
        print(
            f"project-chart-reconcile-failed name={name} "
            f"namespace={namespace} "
            f"status={reconcile_response.status_code} body={response_body}",
            file=sys.stderr,
        )
    reconcile_response.raise_for_status()
    count += 1
    print(
        f"reconciled project={name} namespace={namespace}"
    )

print(f"reconciled_projects={count}")
PY
}

# Retry the first AII read for fresh installs where the pod is running but the
# application has not started accepting connections yet.
wait_for_aii_projects_json() {
    local output_file=""
    local error_file=""
    local error_summary=""
    local deadline=$((SECONDS + WAIT_TIMEOUT_SECONDS))
    local attempt=0

    output_file="$(mktemp)"
    error_file="$(mktemp)"

    while true; do
        attempt=$((attempt + 1))
        if get_aii_projects_json >"${output_file}" 2>"${error_file}"; then
            # Keep polling while the list is a valid but EMPTY array: on a
            # fresh install the init-projects job seeds AII asynchronously to
            # the airflow-webserver rollout we waited on, so an early read
            # legitimately returns []. Only a non-empty list is final.
            if jq -e 'type == "array" and length > 0' "${output_file}" >/dev/null 2>&1; then
                cat "${output_file}"
                rm -f "${output_file}" "${error_file}"
                return 0
            fi
            if (( SECONDS >= deadline )); then
                # Still empty at the deadline: return the (valid) response and
                # let the caller decide - this must not look like a fetch error.
                cat "${output_file}"
                rm -f "${output_file}" "${error_file}"
                return 0
            fi
            echo "Waiting for AII to be seeded with projects (attempt ${attempt}): project list still empty" >&2
            sleep 5
            continue
        fi

        error_summary="$(tail -q -n 1 "${error_file}" "${output_file}" 2>/dev/null | tail -n 1)"
        if (( SECONDS >= deadline )); then
            echo "ERROR: Timed out waiting for AII /projects to become reachable." >&2
            if [[ -n "${error_summary}" ]]; then
                echo "Last error: ${error_summary}" >&2
            fi
            rm -f "${output_file}" "${error_file}"
            return 1
        fi

        echo "Waiting for AII /projects (attempt ${attempt}): ${error_summary}" >&2
        sleep 5
    done
}

normalize_aii_projects_json() {
    local projects_json="$1"
    # $project_admin_ns: prefixed admin-project namespace fallback for AII
    # versions that do not report kubernetes_namespace for the admin project.
    printf '%s\n' "${projects_json}" | jq -c --arg project_admin_ns "${PROJECT_ADMIN_NS}" '
        map(
            select((.name // "") != "")
            | {
                name: .name,
                description: (.description // ""),
                external_id: .external_id,
                default: (.default // false),
                kubernetes_namespace: (
                    if (.name == "admin" and (.kubernetes_namespace // "") == "")
                    then $project_admin_ns
                    else (.kubernetes_namespace // "")
                    end
                )
            }
        )
    '
}

derive_expected_project_namespaces() {
    local projects_json="$1"
    # Accept both prefixed (<prefix>-project-*) and legacy (project-*) names.
    printf '%s\n' "${projects_json}" \
    | jq -r --arg ns_regex "${PROJECT_NS_REGEX}" '.[] | select((.kubernetes_namespace // "") != "" and (.kubernetes_namespace | test($ns_regex))) | .kubernetes_namespace' \
    | sort -u
}

ensure_project_namespace_helm_metadata() {
    local namespace="$1"
    cat <<EOF | ${KUBE} apply -f - >/dev/null
apiVersion: v1
kind: Namespace
metadata:
  name: ${namespace}
  labels:
    app.kubernetes.io/managed-by: Helm
  annotations:
    meta.helm.sh/release-name: ${namespace}
    meta.helm.sh/release-namespace: ${ADMIN_NAMESPACE}
    helm.sh/resource-policy: keep
EOF
}

set_namespaced_resource_helm_ownership() {
    local namespace="$1"
    local resource_kind="$2"
    local resource_name="$3"

    ${KUBE} -n "${namespace}" label "${resource_kind}" "${resource_name}" app.kubernetes.io/managed-by=Helm --overwrite >/dev/null 2>&1 || true
    ${KUBE} -n "${namespace}" annotate "${resource_kind}" "${resource_name}" \
        meta.helm.sh/release-name="${namespace}" \
        meta.helm.sh/release-namespace="${ADMIN_NAMESPACE}" \
        --overwrite >/dev/null 2>&1 || true
}

adopt_existing_project_resources() {
    local namespace="$1"

    # Project PVCs are long-lived and are frequently recreated/recovered before
    # the project-namespace release exists. Ensure they are adopted by the
    # per-project Helm release so helm-install can import them.
    while IFS= read -r pvc_name; do
        [[ -z "${pvc_name}" ]] && continue
        set_namespaced_resource_helm_ownership "${namespace}" "pvc" "${pvc_name}"
        ${KUBE} -n "${namespace}" annotate pvc "${pvc_name}" helm.sh/resource-policy=keep --overwrite >/dev/null 2>&1 || true
    done < <(${KUBE} -n "${namespace}" get pvc -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' 2>/dev/null || true)

    # Network policies and these fixed secret names are managed by the
    # project-namespace chart and can also block helm import if ownership drifted.
    while IFS= read -r np_name; do
        [[ -z "${np_name}" ]] && continue
        set_namespaced_resource_helm_ownership "${namespace}" "networkpolicy" "${np_name}"
    done < <(${KUBE} -n "${namespace}" get networkpolicy -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' 2>/dev/null || true)

    for secret_name in "${REQUIRED_PROJECT_SECRETS[@]}"; do
        if ${KUBE} -n "${namespace}" get secret "${secret_name}" >/dev/null 2>&1; then
            set_namespaced_resource_helm_ownership "${namespace}" "secret" "${secret_name}"
        fi
    done

    if ${KUBE} -n "${namespace}" get limitrange default-resource-limits >/dev/null 2>&1; then
        set_namespaced_resource_helm_ownership "${namespace}" "limitrange" "default-resource-limits"
    fi

    if ${KUBE} -n "${namespace}" get job create-project-user >/dev/null 2>&1; then
        set_namespaced_resource_helm_ownership "${namespace}" "job" "create-project-user"
    fi
}

PROJECTS_JSON="$(wait_for_aii_projects_json)"

if [[ -z "${PROJECTS_JSON}" ]]; then
    echo "ERROR: AII /projects returned an empty response."
    exit 1
fi

if ! printf '%s\n' "${PROJECTS_JSON}" | jq -e 'type == "array"' >/dev/null; then
    echo "ERROR: AII /projects did not return a JSON array."
    exit 1
fi

PROJECTS_JSON="$(normalize_aii_projects_json "${PROJECTS_JSON}")"
EXPECTED_NAMESPACES="$(derive_expected_project_namespaces "${PROJECTS_JSON}")"

if [[ -z "${EXPECTED_NAMESPACES}" ]]; then
    # Do NOT fail the deploy here: a fresh platform whose init-projects job
    # has not seeded AII within the timeout would otherwise abort an
    # otherwise-healthy install. After a data recovery an empty AII is a real
    # problem - but one this script cannot repair either; surface it loudly
    # and let the operator re-run reconciliation once AII is populated.
    echo "WARNING: AII returned no project namespaces within the timeout."
    echo "WARNING: Skipping project namespace reconciliation and strict checks."
    echo "WARNING: If projects are expected (e.g. after a recovery), re-run:"
    echo "WARNING:   PLATFORM_PREFIX=${PLATFORM_PREFIX} SERVICES_NAMESPACE=${SERVICES_NAMESPACE} ADMIN_NAMESPACE=${ADMIN_NAMESPACE} bash $0"
    exit 0
fi

initialize_required_project_resources
echo "Required project PVCs: ${REQUIRED_PROJECT_PVCS[*]}"
echo "Required project secrets: ${REQUIRED_PROJECT_SECRETS[*]}"
echo ""

echo "Normalizing Helm ownership metadata on existing project namespaces..."
while IFS= read -r ns; do
    [[ -z "${ns}" ]] && continue
    [[ "${ns}" =~ ${PROJECT_NS_REGEX} ]] || continue
    ensure_project_namespace_helm_metadata "${ns}"
    adopt_existing_project_resources "${ns}"
done <<< "${EXPECTED_NAMESPACES}"
echo "Project namespace metadata normalization complete."
echo ""

reconcile_project_namespace_releases

# Re-read AII metadata after project chart reconciliation so subsequent waits/checks always use the
# final authoritative state.
PROJECTS_JSON="$(wait_for_aii_projects_json)"
if ! printf '%s\n' "${PROJECTS_JSON}" | jq -e 'type == "array"' >/dev/null; then
    echo "ERROR: AII /projects did not return a JSON array after chart reconciliation."
    exit 1
fi
PROJECTS_JSON="$(normalize_aii_projects_json "${PROJECTS_JSON}")"
EXPECTED_NAMESPACES="$(derive_expected_project_namespaces "${PROJECTS_JSON}")"

if [[ -z "${EXPECTED_NAMESPACES}" ]]; then
    echo "ERROR: AII returned no project-* namespaces after chart reconciliation."
    exit 1
fi

# kube-helm answers HTTP 200 even when it SKIPS a release (e.g. an existing
# release in failed state is "blocked" instead of reinstalled), so a
# successful reconcile round does not guarantee healthy releases. Verify the
# helm status of every expected project release explicitly.
echo "Verifying helm state of the project namespace releases..."
UNHEALTHY_RELEASES=()
while IFS= read -r ns; do
    [[ -z "${ns}" ]] && continue
    [[ "${ns}" =~ ${PROJECT_NS_REGEX} ]] || continue
    release_state="$(${HELM} status "${ns}" -n "${ADMIN_NAMESPACE}" -o json 2>/dev/null | jq -r '.info.status // "missing"' || echo "missing")"
    if [[ "${release_state}" != "deployed" ]]; then
        UNHEALTHY_RELEASES+=("${ns}=${release_state}")
    fi
done <<< "${EXPECTED_NAMESPACES}"

if [[ ${#UNHEALTHY_RELEASES[@]} -gt 0 ]]; then
    echo "ERROR: Project namespace releases are not in 'deployed' state after reconciliation:"
    printf '  %s\n' "${UNHEALTHY_RELEASES[@]}"
    echo "HINT: Inspect with: ${HELM} status <release> -n ${ADMIN_NAMESPACE}"
    echo "HINT: A release stuck in failed/pending state may need: ${HELM} uninstall <release> -n ${ADMIN_NAMESPACE} && re-run this script."
    exit 1
fi
echo "All project namespace releases are deployed."
echo ""

VALID_SYSTEM_PASSWORD_B64="$(
    ${KUBE} get secret -n "${SERVICES_NAMESPACE}" system-user-password -o jsonpath='{.data.system-user-password}'
)"

if [[ -z "${VALID_SYSTEM_PASSWORD_B64}" ]]; then
    echo "ERROR: services/system-user-password is empty or missing."
    exit 1
fi

VALID_REGISTRY_DOCKERCONFIG_B64="$(
    ${KUBE} get secret -n "${SERVICES_NAMESPACE}" registry-secret -o jsonpath='{.data.\.dockerconfigjson}'
)"

if [[ -z "${VALID_REGISTRY_DOCKERCONFIG_B64}" ]]; then
    echo "ERROR: services/registry-secret is empty or missing."
    exit 1
fi

# Keep admin password in sync before project chart (re)installs copy it.
if ${KUBE} get secret -n "${ADMIN_NAMESPACE}" system-user-password >/dev/null 2>&1; then
    ${KUBE} patch secret system-user-password -n "${ADMIN_NAMESPACE}" --type=merge -p "{\"data\":{\"system-user-password\":\"${VALID_SYSTEM_PASSWORD_B64}\"}}" >/dev/null
else
    cat <<EOF | ${KUBE} apply -f - >/dev/null
apiVersion: v1
kind: Secret
metadata:
  name: system-user-password
  namespace: ${ADMIN_NAMESPACE}
type: Opaque
data:
  system-user-password: ${VALID_SYSTEM_PASSWORD_B64}
EOF
fi

echo ""
echo "Waiting for expected project namespaces to exist..."

declare -a MISSING_NAMESPACES
end_time=$((SECONDS + WAIT_TIMEOUT_SECONDS))

while true; do
    MISSING_NAMESPACES=()

    while IFS= read -r ns; do
        [[ -z "${ns}" ]] && continue
        if ! ${KUBE} get namespace "${ns}" >/dev/null 2>&1; then
            MISSING_NAMESPACES+=("${ns}")
        fi
    done <<< "${EXPECTED_NAMESPACES}"

    if [[ ${#MISSING_NAMESPACES[@]} -eq 0 ]]; then
        break
    fi

    if (( SECONDS >= end_time )); then
        echo "ERROR: Timed out waiting for namespaces:"
        printf '  - %s\n' "${MISSING_NAMESPACES[@]}"
        exit 1
    fi

    sleep 2
done

echo "All expected project namespaces are present."
echo ""

# Synchronize system-user-password across all project namespaces to avoid Keycloak 401s
# in KubernetesExecutor task pods that run in project-* namespaces.
while IFS= read -r ns; do
    [[ -z "${ns}" ]] && continue
    [[ "${ns}" =~ ${PROJECT_NS_REGEX} ]] || continue

    if ${KUBE} get secret -n "${ns}" system-user-password >/dev/null 2>&1; then
        ${KUBE} patch secret system-user-password -n "${ns}" --type=merge -p "{\"data\":{\"system-user-password\":\"${VALID_SYSTEM_PASSWORD_B64}\"}}" >/dev/null
    else
        cat <<EOF | ${KUBE} apply -f - >/dev/null
apiVersion: v1
kind: Secret
metadata:
  name: system-user-password
  namespace: ${ns}
type: Opaque
data:
  system-user-password: ${VALID_SYSTEM_PASSWORD_B64}
EOF
    fi
done <<< "${EXPECTED_NAMESPACES}"

echo "Synchronized system-user-password in admin and project namespaces."

# Synchronize registry pull secret across all project namespaces so project jobs can
# pull private images immediately after reconciliation.
while IFS= read -r ns; do
    [[ -z "${ns}" ]] && continue
    [[ "${ns}" =~ ${PROJECT_NS_REGEX} ]] || continue

    if ${KUBE} get secret -n "${ns}" registry-secret >/dev/null 2>&1; then
        ${KUBE} patch secret registry-secret -n "${ns}" --type=merge -p "{\"data\":{\".dockerconfigjson\":\"${VALID_REGISTRY_DOCKERCONFIG_B64}\"}}" >/dev/null
    else
        cat <<EOF | ${KUBE} apply -f - >/dev/null
apiVersion: v1
kind: Secret
metadata:
  name: registry-secret
  namespace: ${ns}
type: kubernetes.io/dockerconfigjson
data:
  .dockerconfigjson: ${VALID_REGISTRY_DOCKERCONFIG_B64}
EOF
    fi
done <<< "${EXPECTED_NAMESPACES}"

echo "Synchronized registry-secret in project namespaces."

# Strictly verify that all project namespaces contain the required bootstrap
# PVCs and secrets. This turns namespace drift into a deploy-time failure
# instead of letting later workflow pods fail with Pending/ImagePullBackOff.
if [[ -n "${EXPECTED_NAMESPACES}" ]]; then
    declare -a MISSING_PVC_REFS
    declare -a MISSING_SECRET_REFS
    validation_deadline=$((SECONDS + WAIT_TIMEOUT_SECONDS))

    while true; do
        MISSING_PVC_REFS=()
        MISSING_SECRET_REFS=()

        while IFS= read -r ns; do
            [[ -z "${ns}" ]] && continue
            for pvc_name in "${REQUIRED_PROJECT_PVCS[@]}"; do
                if ! ${KUBE} get pvc -n "${ns}" "${pvc_name}" >/dev/null 2>&1; then
                    MISSING_PVC_REFS+=("${ns}/${pvc_name}")
                fi
            done

            for secret_name in "${REQUIRED_PROJECT_SECRETS[@]}"; do
                if ! ${KUBE} get secret -n "${ns}" "${secret_name}" >/dev/null 2>&1; then
                    MISSING_SECRET_REFS+=("${ns}/${secret_name}")
                fi
            done
        done <<< "${EXPECTED_NAMESPACES}"

        if [[ ${#MISSING_PVC_REFS[@]} -eq 0 && ${#MISSING_SECRET_REFS[@]} -eq 0 ]]; then
            break
        fi

        if (( SECONDS >= validation_deadline )); then
            if [[ ${#MISSING_PVC_REFS[@]} -gt 0 ]]; then
                echo "ERROR: Missing required project PVCs after reconciliation:"
                printf '  - %s\n' "${MISSING_PVC_REFS[@]}"
            fi

            if [[ ${#MISSING_SECRET_REFS[@]} -gt 0 ]]; then
                echo "ERROR: Missing required project secrets after reconciliation:"
                printf '  - %s\n' "${MISSING_SECRET_REFS[@]}"
            fi

            if printf '%s\n' "${MISSING_PVC_REFS[@]}" | grep -qx "${PROJECT_ADMIN_NS}/tensorboard-pv-claim"; then
                echo "HINT: ${PROJECT_ADMIN_NS}/tensorboard-pv-claim is missing."
                echo "      The project-admin project-namespace release was likely not restored or did not reconcile."
                echo "      Re-run reconciliation after kube-helm/init-projects are healthy."
            fi

            if printf '%s\n' "${MISSING_SECRET_REFS[@]}" | grep -qx "${PROJECT_ADMIN_NS}/project-user-credentials"; then
                echo "HINT: ${PROJECT_ADMIN_NS}/project-user-credentials is missing."
                echo "      The project-admin chart install may have failed or is still pending."
                echo "      Re-run reconciliation after kube-helm/init-projects are healthy."
            fi

            if printf '%s\n' "${MISSING_SECRET_REFS[@]}" | grep -qx "${PROJECT_ADMIN_NS}/oidc-client-secret"; then
                echo "HINT: ${PROJECT_ADMIN_NS}/oidc-client-secret is missing."
                echo "      Project-scoped workload auth will fail until the project-namespace chart is reconciled."
            fi

            exit 1
        fi

        sleep 2
    done
else
    echo "No project-* namespaces found in AII metadata; skipping strict project namespace checks."
fi

echo ""
${KUBE} get ns | grep -E "${PROJECT_NS_REGEX}" || true
echo "======================================================"
