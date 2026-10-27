#!/bin/bash
set -euo pipefail

# Creates a Kaapana project on a cluster deployed with RESTRICTED_RBAC=true.
#
# Without cluster-wide permissions Kaapana can't create the namespace of a new project
# (<platform prefix>-project-<first 8 characters of the project id>) and can't grant its
# service accounts access to it. This script guides through all steps:
#
#   1. asks for the project name and generates the project id,
#   2. names the namespace that has to be created on the cluster (e.g. in Rancher) and waits for it,
#   3. applies the Roles/RoleBindings of Kaapana's service accounts in that namespace,
#   4. creates the project with this id through the access-information-interface,
#   5. adds the namespace to the running Traefik and portal-api,
#   6. asks to check the project in the UI and names the EXTRA_MANAGED_NAMESPACES entry
#      that keeps the namespace managed at the next deployment.
#
# The Roles and RoleBindings mirror the restricted-RBAC templates of:
#   - platforms/kaapana-admin-chart/templates/service_account.yaml
#   - platforms/kaapana-platform-chart/deps/services-namespace/templates/service_account.yaml
#   - services/base/portal-api/portal-api-chart/templates/rbac.yaml
#
# Usage: ./utils/create-restricted-rbac-project.sh
# PLATFORM_PREFIX, ADMIN_NAMESPACE and SERVICES_NAMESPACE can be set in the environment to skip the questions.

ROLE_NAME="kaapana-admin-ns"
AII_LOCAL_PORT="${AII_LOCAL_PORT:-18080}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BOLD='\033[1m'
NC='\033[0m'

if command -v kubectl >/dev/null 2>&1; then
    KUBE="kubectl"
else
    KUBE="microk8s.kubectl"
fi

for tool in curl jq; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo -e "${RED}'$tool' is required but not installed.${NC}"
        exit 1
    fi
done

function fail() {
    echo -e "${RED}$1${NC}"
    exit 1
}

# Reads an answer into the variable $1; $3 is the default for an empty answer.
function ask() {
    local var="$1" prompt="$2" default="${3:-}" answer
    if [ -n "$default" ]; then
        read -r -p "$prompt [$default]: " answer
        answer="${answer:-$default}"
    else
        read -r -p "$prompt: " answer
    fi
    printf -v "$var" '%s' "$answer"
}

# Waits until the user answers yes; any other answer repeats the question, "abort" exits.
function wait_for_yes() {
    local answer
    while true; do
        read -r -p "$1 [yes/abort]: " answer
        case "${answer,,}" in
            y | yes) return 0 ;;
            abort) echo "Aborted."; exit 1 ;;
        esac
    done
}

# A namespace is usable once its "default" ServiceAccount can be read: this works with namespace-scoped
# rights only, while listing or getting namespaces usually needs cluster-wide permissions.
function namespace_exists() {
    "$KUBE" -n "$1" get serviceaccount default >/dev/null 2>&1
}

# Prints the first of the given namespaces that contains deployment $1, or nothing.
function find_namespace_with_deployment() {
    local deployment="$1" namespace
    shift
    for namespace in "$@"; do
        if "$KUBE" -n "$namespace" get deployment "$deployment" >/dev/null 2>&1; then
            echo "$namespace"
            return
        fi
    done
}

# Calls the API of the access-information-interface through the port-forward; leaves the response body
# in AII_BODY and the HTTP status in AII_STATUS.
function aii_request() {
    local method="$1" path="$2" data="${3:-}" response
    response=$(curl -s -w '\n%{http_code}' -X "$method" "http://localhost:${AII_LOCAL_PORT}${path}" \
        -H 'Content-Type: application/json' ${data:+-d "$data"})
    AII_STATUS="${response##*$'\n'}"
    AII_BODY="${response%$'\n'*}"
}

function start_aii_port_forward() {
    "$KUBE" -n "$SERVICES_NAMESPACE" port-forward svc/aii-service "${AII_LOCAL_PORT}:8080" >/dev/null 2>&1 &
    PORT_FORWARD_PID=$!
    trap 'kill "$PORT_FORWARD_PID" 2>/dev/null || true' EXIT
    for _ in $(seq 1 30); do
        if curl -s -o /dev/null "http://localhost:${AII_LOCAL_PORT}/projects"; then
            return
        fi
        sleep 1
    done
    fail "Could not reach the access-information-interface via 'kubectl port-forward svc/aii-service' in '$SERVICES_NAMESPACE'."
}

# Appends namespace $2 to the comma-separated value of every argument "--<$1>=..." of the Traefik container.
function add_namespace_to_traefik() {
    local namespace="$1" index args new_args
    index=$("$KUBE" -n "$ADMIN_NAMESPACE" get deployment traefik -o json \
        | jq '.spec.template.spec.containers | map(.name) | index("traefik")')
    args=$("$KUBE" -n "$ADMIN_NAMESPACE" get deployment traefik -o json | jq -c ".spec.template.spec.containers[$index].args")
    new_args=$(echo "$args" | jq -c --arg ns "$namespace" 'map(
        if test("^--providers\\.kubernetes(ingress|crd)\\.namespaces=") and (split("=")[1] | split(",") | index($ns) | not)
        then . + "," + $ns else . end)')
    if [ "$args" = "$new_args" ]; then
        echo "Traefik already watches '$namespace'."
        return
    fi
    "$KUBE" -n "$ADMIN_NAMESPACE" patch deployment traefik --type=json \
        -p "[{\"op\": \"replace\", \"path\": \"/spec/template/spec/containers/$index/args\", \"value\": $new_args}]"
    "$KUBE" -n "$ADMIN_NAMESPACE" rollout status deployment traefik --timeout=300s
}

function add_namespace_to_portal_api() {
    local namespace="$1" current
    current=$("$KUBE" -n "$SERVICES_NAMESPACE" get deployment portal-api -o json \
        | jq -r '[.spec.template.spec.containers[] | select(.name == "portal-api") | .env[]? | select(.name == "INGRESS_NAMESPACES") | .value][0] // ""')
    if [ -z "$current" ]; then
        echo "portal-api lists the ingresses of all namespaces, nothing to change."
        return
    fi
    if [[ ",$current," == *",$namespace,"* ]]; then
        echo "portal-api already reads the ingresses of '$namespace'."
        return
    fi
    "$KUBE" -n "$SERVICES_NAMESPACE" set env deployment/portal-api -c portal-api "INGRESS_NAMESPACES=${current},${namespace}"
    "$KUBE" -n "$SERVICES_NAMESPACE" rollout status deployment portal-api --timeout=300s
}

# Prints the annotation $2 of object $1 in the services namespace.
function services_annotation() {
    "$KUBE" -n "$SERVICES_NAMESPACE" get "$1" -o jsonpath="{.metadata.annotations.${2//./\\.}}" 2>/dev/null
}

function apply_namespace_rbac() {
    local namespace="$1"
    # The admin and platform charts create these objects in every managed namespace. With Helm's ownership metadata
    # the next deployment, with the namespace in EXTRA_MANAGED_NAMESPACES, adopts them instead of failing.
    local admin_release platform_release release_namespace
    admin_release=$(services_annotation "role/${ROLE_NAME}" meta.helm.sh/release-name)
    platform_release=$(services_annotation rolebinding/kaapana-services-ns meta.helm.sh/release-name)
    release_namespace=$(services_annotation rolebinding/kaapana-services-ns meta.helm.sh/release-namespace)
    if [ -z "$admin_release" ] || [ -z "$platform_release" ] || [ -z "$release_namespace" ]; then
        echo -e "${RED}Helm releases of Kaapana not found in namespace '$SERVICES_NAMESPACE'. Is Kaapana deployed?${NC}"
        exit 1
    fi

    echo "Applying Kaapana managed-cluster RBAC bootstrap in namespace '$namespace'..."

    "$KUBE" apply -f - <<EOF
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: ${ROLE_NAME}
  namespace: ${namespace}
  labels:
    app.kubernetes.io/managed-by: Helm
  annotations:
    meta.helm.sh/release-name: ${admin_release}
    meta.helm.sh/release-namespace: ${release_namespace}
rules:
- apiGroups: [""]
  resources:
    - pods
    - services
    - endpoints
    - secrets
    - configmaps
    - persistentvolumeclaims
    - events
    - serviceaccounts
  verbs: ["get", "list", "watch"]
- apiGroups: [""]
  resources:
    - pods
    - services
    - secrets
    - configmaps
    - persistentvolumeclaims
    - events
    - serviceaccounts
  verbs: ["create", "update", "patch", "delete"]
- apiGroups: [""]
  resources:
    - pods/log
  verbs: ["get"]
- apiGroups: [""]
  resources:
    - pods/exec
  verbs: ["get", "create"]
- apiGroups: ["apps"]
  resources:
    - deployments
    - replicasets
    - statefulsets
    - daemonsets
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["batch"]
  resources:
    - jobs
    - cronjobs
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["networking.k8s.io"]
  resources:
    - ingresses
    - networkpolicies
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["autoscaling"]
  resources:
    - horizontalpodautoscalers
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["policy"]
  resources:
    - poddisruptionbudgets
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["rbac.authorization.k8s.io"]
  resources:
    - roles
    - rolebindings
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["discovery.k8s.io"]
  resources:
    - endpointslices
  verbs: ["get", "list", "watch"]
- apiGroups: ["traefik.io"]
  resources:
    - middlewares
    - middlewaretcps
    - ingressroutes
    - traefikservices
    - ingressroutetcps
    - ingressrouteudps
    - tlsoptions
    - tlsstores
    - serverstransports
    - serverstransporttcps
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: kaapana-admin-ns
  namespace: ${namespace}
  labels:
    app.kubernetes.io/managed-by: Helm
  annotations:
    meta.helm.sh/release-name: ${admin_release}
    meta.helm.sh/release-namespace: ${release_namespace}
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: ${ROLE_NAME}
subjects:
- kind: ServiceAccount
  name: kaapana-kube-admin
  namespace: ${ADMIN_NAMESPACE}
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: kaapana-kube-dashboard-ns
  namespace: ${namespace}
  labels:
    app.kubernetes.io/managed-by: Helm
  annotations:
    meta.helm.sh/release-name: ${admin_release}
    meta.helm.sh/release-namespace: ${release_namespace}
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: ${ROLE_NAME}
subjects:
- kind: ServiceAccount
  name: kaapana-kube-dashboard
  namespace: ${ADMIN_NAMESPACE}
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: kaapana-services-ns
  namespace: ${namespace}
  labels:
    app.kubernetes.io/managed-by: Helm
  annotations:
    meta.helm.sh/release-name: ${platform_release}
    meta.helm.sh/release-namespace: ${release_namespace}
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: ${ROLE_NAME}
subjects:
- kind: ServiceAccount
  name: kaapana-kube-admin
  namespace: ${SERVICES_NAMESPACE}
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: ingress-reader-portal-api
  namespace: ${namespace}
  labels:
    app.kubernetes.io/managed-by: Helm
  annotations:
    meta.helm.sh/release-name: ${platform_release}
    meta.helm.sh/release-namespace: ${release_namespace}
rules:
- apiGroups: ["networking.k8s.io"]
  resources: ["ingresses"]
  verbs: ["list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: ingress-reader-portal-api-binding
  namespace: ${namespace}
  labels:
    app.kubernetes.io/managed-by: Helm
  annotations:
    meta.helm.sh/release-name: ${platform_release}
    meta.helm.sh/release-namespace: ${release_namespace}
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: ingress-reader-portal-api
subjects:
- kind: ServiceAccount
  name: portal-api
  namespace: ${SERVICES_NAMESPACE}
EOF
}

echo -e "${BOLD}Create a Kaapana project on a cluster with restricted RBAC${NC}"
echo "Cluster: kubeconfig context '$("$KUBE" config current-context 2>/dev/null || echo unknown)'"
echo

if [ -z "${PLATFORM_PREFIX:-}" ]; then
    ask PLATFORM_PREFIX "Platform prefix of the deployment (--platform-prefix)"
fi
[ -n "$PLATFORM_PREFIX" ] || fail "The platform prefix is required."
if [ -z "${ADMIN_NAMESPACE:-}" ]; then
    ask ADMIN_NAMESPACE "Admin namespace" "$(find_namespace_with_deployment traefik "${PLATFORM_PREFIX}-admin" admin)"
fi
if [ -z "${SERVICES_NAMESPACE:-}" ]; then
    ask SERVICES_NAMESPACE "Services namespace" "$(find_namespace_with_deployment portal-api "${PLATFORM_PREFIX}-services" services)"
fi
"$KUBE" -n "$ADMIN_NAMESPACE" get deployment traefik >/dev/null 2>&1 \
    || fail "No Traefik deployment in admin namespace '$ADMIN_NAMESPACE'."
"$KUBE" -n "$SERVICES_NAMESPACE" get service aii-service >/dev/null 2>&1 \
    || fail "No aii-service in services namespace '$SERVICES_NAMESPACE'."

start_aii_port_forward

echo
ask PROJECT_NAME "Project name"
[ -n "$PROJECT_NAME" ] || fail "The project name is required."
aii_request GET /projects
[ "$AII_STATUS" = "200" ] || fail "Could not list the projects (HTTP $AII_STATUS): $AII_BODY"
if echo "$AII_BODY" | jq -e --arg name "$PROJECT_NAME" 'any(.[]; .name == $name)' >/dev/null; then
    fail "A project named '$PROJECT_NAME' already exists."
fi
ask PROJECT_DESCRIPTION "Project description" "$PROJECT_NAME"

if command -v uuidgen >/dev/null 2>&1; then
    PROJECT_ID=$(uuidgen)
else
    PROJECT_ID=$(cat /proc/sys/kernel/random/uuid)
fi
PROJECT_ID="${PROJECT_ID,,}"
PROJECT_NAMESPACE="${PLATFORM_PREFIX}-project-${PROJECT_ID:0:8}"

echo
echo -e "Project id:        ${BOLD}${PROJECT_ID}${NC}"
echo -e "Project namespace: ${BOLD}${PROJECT_NAMESPACE}${NC}"
echo
echo -e "${YELLOW}Create the namespace '${PROJECT_NAMESPACE}' on the cluster now (e.g. in Rancher, in the same"
echo -e "Rancher project as the namespaces '${ADMIN_NAMESPACE}' and '${SERVICES_NAMESPACE}').${NC}"
while true; do
    wait_for_yes "Has the namespace '${PROJECT_NAMESPACE}' been created?"
    if namespace_exists "$PROJECT_NAMESPACE"; then
        break
    fi
    echo -e "${RED}Namespace '${PROJECT_NAMESPACE}' is not accessible yet.${NC}"
done

echo
echo "Granting Kaapana's service accounts access to '${PROJECT_NAMESPACE}'..."
apply_namespace_rbac "$PROJECT_NAMESPACE"

echo
echo "Creating the project '${PROJECT_NAME}'..."
PAYLOAD=$(jq -cn --arg id "$PROJECT_ID" --arg name "$PROJECT_NAME" --arg description "$PROJECT_DESCRIPTION" \
    '{id: $id, name: $name, description: $description}')
aii_request POST /projects "$PAYLOAD"
[ "$AII_STATUS" = "200" ] || fail "Creating the project failed (HTTP $AII_STATUS): $AII_BODY
See the logs of the access-information-interface (namespace '$SERVICES_NAMESPACE') and kube-helm (namespace '$ADMIN_NAMESPACE')."
[ "$(echo "$AII_BODY" | jq -r '.id')" = "$PROJECT_ID" ] \
    || fail "The project was created with another id than ${PROJECT_ID}: $AII_BODY"

echo "Waiting for the project to be registered for Airflow workflows..."
for _ in $(seq 1 60); do
    MANAGED=$("$KUBE" -n "$SERVICES_NAMESPACE" get configmap airflow-managed-namespaces -o jsonpath='{.data.namespaces}' 2>/dev/null || true)
    if [[ ",$MANAGED," == *",$PROJECT_NAMESPACE,"* ]]; then
        break
    fi
    sleep 5
done
if [[ ",$MANAGED," != *",$PROJECT_NAMESPACE,"* ]]; then
    echo -e "${YELLOW}'${PROJECT_NAMESPACE}' is not yet in the ConfigMap airflow-managed-namespaces; check the"
    echo -e "create-project-user job in '${PROJECT_NAMESPACE}'.${NC}"
fi

echo
echo "Adding '${PROJECT_NAMESPACE}' to Traefik and portal-api, so that applications of the project are reachable..."
add_namespace_to_traefik "$PROJECT_NAMESPACE"
add_namespace_to_portal_api "$PROJECT_NAMESPACE"

echo
echo -e "${YELLOW}Open Kaapana in the browser, go to 'Projects' and check that '${PROJECT_NAME}' is listed."
echo -e "Users are assigned to the project there as usual.${NC}"
wait_for_yes "Is the project '${PROJECT_NAME}' listed?"

echo
echo -e "${GREEN}Project '${PROJECT_NAME}' is ready.${NC}"
echo
echo -e "${YELLOW}${BOLD}Add the namespace to EXTRA_MANAGED_NAMESPACES (comma-separated) in load_kaapana_config of kaapanactl.sh:${NC}"
echo
echo "    EXTRA_MANAGED_NAMESPACES=\"<existing entries,>${PROJECT_NAMESPACE}\""
echo
echo "The changes to Traefik and portal-api made by this script last only until the next deployment. With this"
echo "entry, the next deployment keeps the project's access rights, Traefik and the portal menu configured."
