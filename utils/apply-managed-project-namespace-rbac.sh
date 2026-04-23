#!/bin/bash
set -euo pipefail

# Managed Kubernetes namespace bootstrap for externally created project namespaces.
#
# Run this script after creating a new `project-*` namespace outside of Kaapana,
# for example in Rancher, and before creating or initializing that project from
# the Kaapana UI.
#
# In managed Kubernetes setups without cluster-wide RBAC, Kaapana components such
# as `kube-helm` cannot bootstrap themselves into a brand-new namespace. This
# script applies the required namespace-local RBAC so Kaapana can access and use
# the new namespace.
#
# The Role and RoleBindings below intentionally mirror the managed-cluster RBAC from:
#   - platforms/kaapana-admin-chart/templates/service_account.yaml
#   - platforms/kaapana-platform-chart/deps/services-namespace/templates/service_account.yaml
#
# After you add the same namespaces to `EXTRA_MANAGED_NAMESPACES` in
# `kaapanactl.sh` and redeploy, the chart-managed RBAC will take over and this
# script does not need to be rerun for those namespaces.

PROJECT_NAMESPACES=(
  "project-test"
)

ADMIN_NAMESPACE="idai-admin"
SERVICES_NAMESPACE="idai-services"
ROLE_NAME="kaapana-admin-ns"

if command -v kubectl >/dev/null 2>&1; then
    KUBE="kubectl"
else
    KUBE="microk8s.kubectl"
fi

function ensure_namespace_exists() {
    local namespace="$1"

    if ! "$KUBE" get namespace "$namespace" >/dev/null 2>&1; then
        echo "Namespace '$namespace' does not exist. Create it first, then rerun this script."
        exit 1
    fi
}

function apply_namespace_rbac() {
    local namespace="$1"

    echo "Applying Kaapana managed-cluster RBAC bootstrap in namespace '$namespace'..."

    "$KUBE" apply -f - <<EOF
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: ${ROLE_NAME}
  namespace: ${namespace}
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
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: ${ROLE_NAME}
subjects:
- kind: ServiceAccount
  name: kaapana-kube-admin
  namespace: ${SERVICES_NAMESPACE}
EOF
}

for namespace in "${PROJECT_NAMESPACES[@]}"; do
    ensure_namespace_exists "$namespace"
    apply_namespace_rbac "$namespace"
done

echo "Managed-cluster RBAC bootstrap applied successfully."
