#!/usr/bin/env bash
set -euo pipefail

########################################
# Logging helpers
########################################
log()      { printf '[%(%Y-%m-%dT%H:%M:%S%z)T] [%s] %s\n' -1 "$1" "$2"; }
log_info() { log "INFO"  "$*"; }
log_ok()   { log " OK "  "$*"; }
log_fail() { log "FAIL" "$*"; }

########################################
# Args
########################################
if [ "$#" -ne 6 ]; then
  echo "Usage: $0 <container-registry-url> <container-registry-username> <container-registry-password> <target-dir> <platform-version> <image-name>" >&2
  exit 1
fi

CONTAINER_REGISTRY_URL="${1:-}"
CONTAINER_REGISTRY_USERNAME="${2:-}"
CONTAINER_REGISTRY_PASSWORD="${3:-}"
TARGET_DIR="${4:-}"
PLATFORM_VERSION="${5:-}"
IMAGE_NAME="${6:-}"

ACTION="pull"
PAYLOAD_DIGEST="${PAYLOAD_DIGEST:-}"   # set to sha256:... to skip auto-detect

REGISTRY="${CONTAINER_REGISTRY_URL%%/*}"
REPO="${CONTAINER_REGISTRY_URL#*/}/${IMAGE_NAME}"

log_info "Preparing to pull ${REPO}:${PLATFORM_VERSION} from ${REGISTRY}"
mkdir -p "$TARGET_DIR"

########################################
# 1) Auth challenge
########################################
log_info "Requesting auth challenge"
AUTH_HEADER="$(curl -sI "https://${REGISTRY}/v2/" | tr -d '\r' | grep -i '^WWW-Authenticate:')"
REALM="$(printf '%s\n' "$AUTH_HEADER"   | sed -E 's/.*realm="([^"]+)".*/\1/')"
SERVICE="$(printf '%s\n' "$AUTH_HEADER" | sed -E 's/.*service="([^"]+)".*/\1/')"
log_ok   "Auth challenge processed (realm=${REALM}, service=${SERVICE})"

########################################
# 2) Token
########################################
log_info "Requesting bearer token"
SCOPE="repository:${REPO}:${ACTION}"
TOKEN="$(curl -s -u "${CONTAINER_REGISTRY_USERNAME}:${CONTAINER_REGISTRY_PASSWORD}" \
  "${REALM}?service=${SERVICE}&scope=${SCOPE}" \
  | sed -nE 's/.*"token":"([^"]+)".*/\1/p')"

if [ -z "$TOKEN" ]; then
  log_fail "Failed to obtain token"
  exit 1
fi
auth_header="Authorization: Bearer ${TOKEN}"
log_ok "Token acquired"

########################################
# 3) Manifest
########################################
log_info "Pulling manifest for ${PLATFORM_VERSION}"
ACCEPT='application/vnd.docker.distribution.manifest.v2+json, application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.list.v2+json, application/vnd.oci.image.index.v1+json'
MAN_RAW="${TARGET_DIR}/manifest.json"

curl -sSf -H "$auth_header" -H "Accept: $ACCEPT" \
  "https://${REGISTRY}/v2/${REPO}/manifests/${PLATFORM_VERSION}" > "$MAN_RAW"
log_ok "Manifest saved to ${MAN_RAW}"

########################################
# 4) Collect layer digests
########################################
log_info "Parsing manifest for layer digests"
mapfile -t layer_digests < <(
  awk '
    /"layers"/ {in_layers=1}
    in_layers && /"digest"/ {
      if (match($0, /sha256:[0-9a-f]+/)) {
        print substr($0, RSTART + 7, RLENGTH - 7)
      }
    }
  ' "$MAN_RAW"
)


if [ ${#layer_digests[@]} -eq 0 ]; then
  log_fail "No layer digests found"
  exit 1
fi
log_ok "Found ${#layer_digests[@]} layer(s)"

########################################
# 5) Download & extract layers
########################################
for dig in "${layer_digests[@]}"; do
  log_info "Downloading layer $dig"
  curl -sSfL -H "$auth_header" -H "Accept: application/octet-stream" \
    "https://${REGISTRY}/v2/${REPO}/blobs/sha256:${dig}" \
  | tar --no-same-owner -xzf - -C "$TARGET_DIR"
  log_ok "Layer $dig extracted"
done

log_ok "All layers extracted to ${TARGET_DIR}"
