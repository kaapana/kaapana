#!/usr/bin/env bash
set -euo pipefail
set -x   # verbose logging, except around secrets (none here)

DOCS_DIR="$KAAPANA_DIR/docs"

# --- Install Python requirements ---
pip3 install -r "$DOCS_DIR/requirements.txt"

# --- Build documentation ---
set +e
pushd "$DOCS_DIR" >/dev/null
make html >"$ARTIFACTS_DIR/build_documentation_html.log" 2>&1
BUILD_RC=$?
popd >/dev/null
set -e

# --- Fail if build command failed ---
if [[ $BUILD_RC -ne 0 ]]; then
  echo "❌ Building the documentation failed"
  exit 1
fi

# --- Check logs for errors ---
if grep -q "ERROR" "$ARTIFACTS_DIR/build_documentation_html.log"; then
  echo "❌ ERROR found in build_documentation_html.log"
  exit 1
fi

echo "✅ Documentation built successfully"
