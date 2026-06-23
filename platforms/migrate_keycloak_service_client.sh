#!/bin/bash
# One-time migration helper for installations upgrading to the two-client Keycloak setup.
#
# Manual equivalent of the keycloak-bootstrap + keycloak-setup jobs:
#   1. Creates the kaapana-admin client in the MASTER realm (service account + master
#      'admin' role). This is the only persisted credential; afterwards redeploys work
#      without the admin password.
#   2. Creates the kaapana-service client in the kaapana realm with the minimal
#      realm-management roles (WITHOUT manage-clients).
#
# Normally the bootstrap/setup jobs do this automatically on deploy. Use this script
# only when you need to bootstrap by hand.
#
# Required env vars:
#   ADMIN_PASSWORD     - Keycloak admin password
#   KEYCLOAK_URL       - e.g. https://<hostname>/auth  (no trailing slash)
#   ADMIN_NAMESPACE    - Kubernetes namespace for admin resources (default: admin)
#   ADMIN_USERNAME     - Keycloak admin username (default: admin)

set -euo pipefail

KEYCLOAK_URL="${KEYCLOAK_URL:?KEYCLOAK_URL must be set (e.g. https://<hostname>/auth)}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:?ADMIN_PASSWORD must be set}"
ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"
ADMIN_NAMESPACE="${ADMIN_NAMESPACE:-admin}"

ADMIN_CLIENT_ID="kaapana-admin"
ADMIN_SECRET_NAME="kaapana-admin-password"
SERVICE_CLIENT_ID="kaapana-service"
SERVICE_SECRET_NAME="kaapana-service-password"

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

read_secret() {
  local name="$1"
  local value
  value=$(kubectl get secret "$name" -n "$ADMIN_NAMESPACE" \
    -o jsonpath="{.data.$name}" | base64 -d)
  if [ -z "$value" ]; then
    echo "ERROR: Secret '$name/$name' not found in namespace '$ADMIN_NAMESPACE'." >&2
    echo "Run 'helm upgrade' first so the Secret is created, then re-run this script." >&2
    exit 1
  fi
  echo "$value"
}

create_client() {
  # create_client <realm> <clientId> <secret>
  local realm="$1" client_id="$2" secret="$3" existing
  existing=$(curl -sf -H "Authorization: Bearer $ADMIN_TOKEN" \
    "$KEYCLOAK_URL/admin/realms/$realm/clients?clientId=$client_id" | jq -r '.[0].id')
  local payload="{
    \"clientId\": \"$client_id\",
    \"secret\": \"$secret\",
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
  # The payload carries the client secret; send it via stdin (--data @-) so it
  # stays out of the process argument list.
  if [ -z "$existing" ] || [ "$existing" = "null" ]; then
    echo "--- Creating client '$client_id' in realm '$realm'..."
    curl -sf -X POST -H "Authorization: Bearer $ADMIN_TOKEN" -H "Content-Type: application/json" \
      "$KEYCLOAK_URL/admin/realms/$realm/clients" --data @- <<<"$payload"
  else
    echo "--- Client '$client_id' already exists in realm '$realm' (UUID: $existing) - updating."
    curl -sf -X PUT -H "Authorization: Bearer $ADMIN_TOKEN" -H "Content-Type: application/json" \
      "$KEYCLOAK_URL/admin/realms/$realm/clients/$existing" --data @- <<<"$payload"
  fi
}

service_account_user_id() {
  # service_account_user_id <realm> <clientId>
  local realm="$1" client_id="$2" uuid
  uuid=$(curl -sf -H "Authorization: Bearer $ADMIN_TOKEN" \
    "$KEYCLOAK_URL/admin/realms/$realm/clients?clientId=$client_id" | jq -r '.[0].id')
  curl -sf -H "Authorization: Bearer $ADMIN_TOKEN" \
    "$KEYCLOAK_URL/admin/realms/$realm/clients/$uuid/service-account-user" | jq -r '.id'
}

# --- 1. Bootstrap the kaapana-admin client in the master realm -----------------
ADMIN_CLIENT_SECRET=$(read_secret "$ADMIN_SECRET_NAME")
create_client "master" "$ADMIN_CLIENT_ID" "$ADMIN_CLIENT_SECRET"

echo "--- Granting master 'admin' realm role to kaapana-admin service account..."
ADMIN_SA_USER_ID=$(service_account_user_id "master" "$ADMIN_CLIENT_ID")
ADMIN_ROLE_REP=$(curl -sf -H "Authorization: Bearer $ADMIN_TOKEN" \
  "$KEYCLOAK_URL/admin/realms/master/roles/admin")
curl -sf -X POST -H "Authorization: Bearer $ADMIN_TOKEN" -H "Content-Type: application/json" \
  "$KEYCLOAK_URL/admin/realms/master/users/$ADMIN_SA_USER_ID/role-mappings/realm" \
  -d "[$ADMIN_ROLE_REP]"

# --- 2. Create the kaapana-service client in the kaapana realm ------------------
SERVICE_CLIENT_SECRET=$(read_secret "$SERVICE_SECRET_NAME")
create_client "kaapana" "$SERVICE_CLIENT_ID" "$SERVICE_CLIENT_SECRET"

SERVICE_SA_USER_ID=$(service_account_user_id "kaapana" "$SERVICE_CLIENT_ID")
REALM_MGMT_ID=$(curl -sf -H "Authorization: Bearer $ADMIN_TOKEN" \
  "$KEYCLOAK_URL/admin/realms/kaapana/clients?clientId=realm-management" | jq -r '.[0].id')

echo "--- Assigning minimal realm-management roles to kaapana-service service account..."
for ROLE in "manage-users" "query-users" "query-groups" "view-realm"; do
  ROLE_REP=$(curl -sf -H "Authorization: Bearer $ADMIN_TOKEN" \
    "$KEYCLOAK_URL/admin/realms/kaapana/clients/$REALM_MGMT_ID/roles/$ROLE")
  curl -sf -X POST -H "Authorization: Bearer $ADMIN_TOKEN" -H "Content-Type: application/json" \
    "$KEYCLOAK_URL/admin/realms/kaapana/users/$SERVICE_SA_USER_ID/role-mappings/clients/$REALM_MGMT_ID" \
    -d "[$ROLE_REP]"
  echo "  Assigned: $ROLE"
done

echo "--- Migration complete. kaapana-admin (master) and kaapana-service (kaapana) are set up."
echo "--- Restart affected deployments if they are already running the new version:"
echo "    kubectl rollout restart deployment/kaapana-backend deployment/access-information-interface -n <services-namespace>"
