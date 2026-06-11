#!/bin/bash
# One-time migration script for installations upgrading to the kaapana-service client_credentials setup.
# Creates the kaapana-service Keycloak client and assigns realm-management roles if not already present.
#
# Required env vars:
#   ADMIN_PASSWORD     — Keycloak admin password
#   KEYCLOAK_URL       — e.g. https://<hostname>/auth  (no trailing slash)
#   ADMIN_NAMESPACE    — Kubernetes namespace for admin resources (default: kaapana-admin)
#   ADMIN_USERNAME     — Keycloak admin username (default: admin)

set -euo pipefail

KEYCLOAK_URL="${KEYCLOAK_URL:?KEYCLOAK_URL must be set (e.g. https://<hostname>/auth)}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:?ADMIN_PASSWORD must be set}"
ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"
ADMIN_NAMESPACE="${ADMIN_NAMESPACE:-kaapana-admin}"
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

echo "--- Checking if client '$CLIENT_ID' already exists..."
EXISTING=$(curl -sf \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  "$KEYCLOAK_URL/admin/realms/kaapana/clients?clientId=$CLIENT_ID" \
  | jq -r '.[0].id')

if [ -n "$EXISTING" ] && [ "$EXISTING" != "null" ]; then
  echo "Client '$CLIENT_ID' already exists (UUID: $EXISTING). Nothing to do."
  exit 0
fi

echo "--- Reading client secret from Kubernetes Secret '$SECRET_NAME'..."
CLIENT_SECRET=$(kubectl get secret "$SECRET_NAME" -n "$ADMIN_NAMESPACE" \
  -o jsonpath="{.data.$SECRET_KEY}" | base64 -d)

if [ -z "$CLIENT_SECRET" ]; then
  echo "ERROR: Secret '$SECRET_NAME/$SECRET_KEY' not found in namespace '$ADMIN_NAMESPACE'." >&2
  echo "Run 'helm upgrade' first so the Secret is created, then re-run this script." >&2
  exit 1
fi

echo "--- Creating client '$CLIENT_ID'..."
curl -sf -X POST \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  "$KEYCLOAK_URL/admin/realms/kaapana/clients" \
  -d "{
    \"clientId\": \"$CLIENT_ID\",
    \"secret\": \"$CLIENT_SECRET\",
    \"enabled\": true,
    \"protocol\": \"openid-connect\",
    \"clientAuthenticatorType\": \"client-secret\",
    \"serviceAccountsEnabled\": true,
    \"publicClient\": false,
    \"standardFlowEnabled\": false,
    \"implicitFlowEnabled\": false,
    \"directAccessGrantsEnabled\": false,
    \"bearerOnly\": false
  }"

echo "--- Fetching service account user for '$CLIENT_ID'..."
CLIENT_UUID=$(curl -sf \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  "$KEYCLOAK_URL/admin/realms/kaapana/clients?clientId=$CLIENT_ID" \
  | jq -r '.[0].id')

SERVICE_ACCOUNT_USER_ID=$(curl -sf \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  "$KEYCLOAK_URL/admin/realms/kaapana/clients/$CLIENT_UUID/service-account-user" \
  | jq -r '.id')

echo "--- Fetching realm-management client ID..."
REALM_MGMT_ID=$(curl -sf \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  "$KEYCLOAK_URL/admin/realms/kaapana/clients?clientId=realm-management" \
  | jq -r '.[0].id')

echo "--- Assigning realm-management roles to service account..."
for ROLE in "manage-users" "query-users" "query-groups" "view-realm"; do
  ROLE_REP=$(curl -sf \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    "$KEYCLOAK_URL/admin/realms/kaapana/clients/$REALM_MGMT_ID/roles/$ROLE")

  curl -sf -X POST \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    "$KEYCLOAK_URL/admin/realms/kaapana/users/$SERVICE_ACCOUNT_USER_ID/role-mappings/clients/$REALM_MGMT_ID" \
    -d "[$ROLE_REP]"

  echo "  Assigned: $ROLE"
done

echo "--- Migration complete. Client '$CLIENT_ID' created with required roles."
echo "--- Restart affected deployments if they are already running the new version:"
echo "    kubectl rollout restart deployment/kaapana-backend deployment/access-information-interface -n <services-namespace>"
