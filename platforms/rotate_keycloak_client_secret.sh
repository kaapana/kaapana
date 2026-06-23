#!/bin/bash
# Rotates the client secret of the kaapana-service Keycloak client.
# Run this whenever the client secret needs to be cycled.
#
# Required env vars:
#   ADMIN_PASSWORD     - Keycloak admin password
#   KEYCLOAK_URL       - e.g. https://<hostname>/auth  (no trailing slash)
#   ADMIN_NAMESPACE    - Kubernetes namespace for admin resources (default: admin)
#   SERVICES_NAMESPACE - Kubernetes namespace for platform services (default: services)
#   ADMIN_USERNAME     - Keycloak admin username (default: admin)

set -euo pipefail

KEYCLOAK_URL="${KEYCLOAK_URL:?KEYCLOAK_URL must be set (e.g. https://<hostname>/auth)}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:?ADMIN_PASSWORD must be set}"
ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"
ADMIN_NAMESPACE="${ADMIN_NAMESPACE:-admin}"
SERVICES_NAMESPACE="${SERVICES_NAMESPACE:-services}"
CLIENT_ID="kaapana-service"
SECRET_NAME="kaapana-service-password"
SECRET_KEY="kaapana-service-password"

echo "--- Fetching admin token..."
# The password is piped via stdin (--data-urlencode @-) so it never appears in
# the process argument list (ps / /proc/<pid>/cmdline).
ADMIN_TOKEN=$(printf '%s' "$ADMIN_PASSWORD" | curl -sf -X POST \
  "$KEYCLOAK_URL/realms/master/protocol/openid-connect/token" \
  -d "client_id=admin-cli" \
  --data-urlencode "username=$ADMIN_USERNAME" \
  --data-urlencode "password@-" \
  -d "grant_type=password" \
  | jq -r '.access_token')

echo "--- Resolving client UUID for '$CLIENT_ID'..."
CLIENT_UUID=$(curl -sf \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  "$KEYCLOAK_URL/admin/realms/kaapana/clients?clientId=$CLIENT_ID" \
  | jq -r '.[0].id')

if [ -z "$CLIENT_UUID" ] || [ "$CLIENT_UUID" = "null" ]; then
  echo "ERROR: Client '$CLIENT_ID' not found in Keycloak realm 'kaapana'." >&2
  exit 1
fi

echo "--- Generating new client secret..."
NEW_SECRET=$(curl -sf -X POST \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  "$KEYCLOAK_URL/admin/realms/kaapana/clients/$CLIENT_UUID/client-secret" \
  | jq -r '.value')

ENCODED_SECRET=$(echo -n "$NEW_SECRET" | base64 -w 0)

# Patch every namespace that holds the secret: admin (source), services, and all
# project namespaces. Project namespaces are separate Helm releases that received a
# copy via lookup, so they must be re-synced here or they keep the stale secret.
echo "--- Discovering all namespaces containing secret '$SECRET_NAME'..."
NAMESPACES=$(kubectl get secret "$SECRET_NAME" --all-namespaces \
  -o jsonpath='{range .items[*]}{.metadata.namespace}{"\n"}{end}')

if [ -z "$NAMESPACES" ]; then
  echo "ERROR: Secret '$SECRET_NAME' not found in any namespace." >&2
  exit 1
fi

for NS in $NAMESPACES; do
  echo "--- Updating Kubernetes Secret in namespace '$NS'..."
  kubectl patch secret "$SECRET_NAME" \
    -n "$NS" \
    --type='json' \
    -p="[{\"op\":\"replace\",\"path\":\"/data/$SECRET_KEY\",\"value\":\"$ENCODED_SECRET\"}]"
done

echo "--- Triggering rolling restart of affected deployments..."
kubectl rollout restart deployment/kaapana-backend -n "$SERVICES_NAMESPACE"
kubectl rollout restart deployment/access-information-interface -n "$SERVICES_NAMESPACE"

kubectl rollout status deployment/kaapana-backend -n "$SERVICES_NAMESPACE" --timeout=120s
kubectl rollout status deployment/access-information-interface -n "$SERVICES_NAMESPACE" --timeout=120s

echo "--- Rotation complete."
