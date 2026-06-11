#!/bin/bash
# Rotates the client secret of the kaapana-service Keycloak client.
# Run this whenever the client secret needs to be cycled.
#
# Required env vars:
#   ADMIN_PASSWORD     — Keycloak admin password
#   KEYCLOAK_URL       — e.g. https://<hostname>/auth  (no trailing slash)
#   ADMIN_NAMESPACE    — Kubernetes namespace for admin resources (default: kaapana-admin)
#   SERVICES_NAMESPACE — Kubernetes namespace for platform services (default: kaapana)
#   ADMIN_USERNAME     — Keycloak admin username (default: admin)

set -euo pipefail

KEYCLOAK_URL="${KEYCLOAK_URL:?KEYCLOAK_URL must be set (e.g. https://<hostname>/auth)}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:?ADMIN_PASSWORD must be set}"
ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"
ADMIN_NAMESPACE="${ADMIN_NAMESPACE:-kaapana-admin}"
SERVICES_NAMESPACE="${SERVICES_NAMESPACE:-kaapana}"
CLIENT_ID="kaapana-service"
SECRET_NAME="kaapana-service-password"
SECRET_KEY="kaapana-service-password"

echo "--- Fetching admin token..."
ADMIN_TOKEN=$(curl -sf -X POST \
  "$KEYCLOAK_URL/realms/master/protocol/openid-connect/token" \
  -d "client_id=admin-cli" \
  -d "username=$ADMIN_USERNAME" \
  -d "password=$ADMIN_PASSWORD" \
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

echo "--- Updating Kubernetes Secret in namespace '$ADMIN_NAMESPACE'..."
kubectl patch secret "$SECRET_NAME" \
  -n "$ADMIN_NAMESPACE" \
  --type='json' \
  -p="[{\"op\":\"replace\",\"path\":\"/data/$SECRET_KEY\",\"value\":\"$ENCODED_SECRET\"}]"

echo "--- Updating Kubernetes Secret in namespace '$SERVICES_NAMESPACE'..."
kubectl patch secret "$SECRET_NAME" \
  -n "$SERVICES_NAMESPACE" \
  --type='json' \
  -p="[{\"op\":\"replace\",\"path\":\"/data/$SECRET_KEY\",\"value\":\"$ENCODED_SECRET\"}]"

echo "--- Triggering rolling restart of affected deployments..."
kubectl rollout restart deployment/kaapana-backend -n "$SERVICES_NAMESPACE"
kubectl rollout restart deployment/access-information-interface -n "$SERVICES_NAMESPACE"

kubectl rollout status deployment/kaapana-backend -n "$SERVICES_NAMESPACE" --timeout=120s
kubectl rollout status deployment/access-information-interface -n "$SERVICES_NAMESPACE" --timeout=120s

echo "--- Rotation complete."
