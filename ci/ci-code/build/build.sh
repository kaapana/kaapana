#!/usr/bin/env bash
set -euo pipefail
set -x   # verbose logging

export http_proxy="$HTTP_PROXY"
export https_proxy="$HTTPS_PROXY"

echo "Build command line flags: $BUILD_ARGUMENTS"

# --- Install Python requirements ---
pip install -r "$KAAPANA_DIR/build-scripts/requirements.txt"


# --- Adjust exit_on_error if flags set ---
if [[ "$BUILD_ARGUMENTS" =~ -vs|--vulnerability-scan|-cc|--configuration-check ]]; then
  export EXIT_ON_ERROR="false"
fi

# --- Docker logins ---
set +x
echo "$REGISTRY_TOKEN" | docker login "$REGISTRY_URL" -u "$REGISTRY_USER" --password-stdin
echo "$DOCKER_IO_PASSWORD" | docker login docker.io -u "$DOCKER_IO_USER" --password-stdin

export REGISTRY_USER=$REGISTRY_USER
export REGISTRY_PW=$REGISTRY_TOKEN
set -x

# --- Start build process ---
set +e
python3 "$KAAPANA_DIR/build-scripts/cli.py" \
    --default-registry $REGISTRY_URL \
    $BUILD_ARGUMENTS 
BUILD_RC=$?
set -e

# --- Collect artifacts ---
cp "$KAAPANA_DIR/build/build.log" "$ARTIFACTS_DIR/"

SECURITY_REPORT_DIR="$KAAPANA_DIR/build/security-reports"
if [[ -d "$SECURITY_REPORT_DIR" ]]; then
  cp -r "$SECURITY_REPORT_DIR" "$ARTIFACTS_DIR/"
fi

# --- Fail if build failed ---
if [[ $BUILD_RC -ne 0 ]]; then
  echo "Build failed ❌"
  exit 1
fi

echo "Build completed ✅"
