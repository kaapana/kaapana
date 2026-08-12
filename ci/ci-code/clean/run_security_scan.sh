#!/usr/bin/env bash
set -Eeuo pipefail

# Full security scan + consolidation + report pipeline: runs ContainerScanner /
# OfflinePackagesScanner (build_cli) via `kaapana-build --scan-only`, then merges
# their raw output into reports/*.json + reports/interactive_report.html.
#
# This is the ONE place that logic lives — ci/pipeline/security.yml's
# security_scan job calls this same script (whether it lands on the shared
# runner pool or a runner you registered yourself, tagged build-runner; see
# ci/README.md), and you can also run it by hand for a pure-local scan with
# no CI involved at all. Either way, it's the same reports/ output.
#
# Required env: REGISTRY_URL, and REGISTRY_PW or REGISTRY_TOKEN — registry to
#   pull the images to scan from.
# Optional env: DOCKER_IO_USER / DOCKER_IO_PASSWORD — docker.io login, avoids
#   rate limits (pulling the trivy image, scanning snaps).
# kaapana-build flags: pass as arguments, e.g. --vulnerability-scan
#   --offline-packages-scan; if none are given, falls back to $SCAN_ARGS, then
#   to "--vulnerability-scan --offline-packages-scan".
#
# Usage (pure local, no CI):
#   export REGISTRY_URL=registry.example.com REGISTRY_PW=<token>
#   ./ci/ci-code/clean/run_security_scan.sh --vulnerability-scan --create-sboms
#
# Output (only produced for scans that actually ran):
#   reports/consolidated_vulnerability_scan.json   (--vulnerability-scan / --offline-packages-scan)
#   reports/interactive_report.html                (same)
#   reports/gl-container-scanning-report.json      (same — GitLab Security tab format)
#   reports/consolidated_misconfiguration_check.json (--configuration-check)
#   reports/consolidated_sbom.json                 (--create-sboms)

if [ "$#" -gt 0 ]; then
  SCAN_ARGS=("$@")
else
  # shellcheck disable=SC2206 # word-splitting is intentional here
  SCAN_ARGS=(${SCAN_ARGS:-${CI_EXEC_SECURITY_SCAN_ARGUMENTS:---vulnerability-scan --offline-packages-scan}})
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

command -v kaapana-build >/dev/null || {
  echo "ERROR: kaapana-build not found on PATH. Install it: pip install -e $REPO_ROOT/build_cli" >&2
  exit 1
}
: "${REGISTRY_URL:?REGISTRY_URL is required}"
REGISTRY_PW="${REGISTRY_PW:-${REGISTRY_TOKEN:-}}"
: "${REGISTRY_PW:?REGISTRY_PW or REGISTRY_TOKEN is required}"

pip show jsonschema >/dev/null 2>&1 || pip install --quiet jsonschema

if [[ -n "${DOCKER_IO_USER:-}" ]]; then
  echo "${DOCKER_IO_PASSWORD:?DOCKER_IO_PASSWORD required when DOCKER_IO_USER is set}" \
    | docker login docker.io -u "$DOCKER_IO_USER" --password-stdin
fi

set +e
export REGISTRY_PW
kaapana-build --scan-only "${SCAN_ARGS[@]}" --default-registry "$REGISTRY_URL" --kaapana-dir "$REPO_ROOT"
SCAN_EXIT_CODE=$?
set -e

SEC_DIR="$REPO_ROOT/security-reports"
REPORTS_DIR="$REPO_ROOT/reports"
mkdir -p "$REPORTS_DIR"

if [[ -f "$SEC_DIR/consolidated_vulnerability_report.json" ]]; then
  mv "$SEC_DIR/consolidated_vulnerability_report.json" "$REPORTS_DIR/consolidated_vulnerability_scan.json"
  python3 "$REPO_ROOT/ci/ci-code/clean/create_vulnerability_report.py" \
    "$REPORTS_DIR/consolidated_vulnerability_scan.json" \
    "$REPORTS_DIR/gl-container-scanning-report.json" \
    --output json
  python3 "$REPO_ROOT/ci/ci-code/clean/create_vulnerability_report.py" \
    "$REPORTS_DIR/consolidated_vulnerability_scan.json" \
    "$REPORTS_DIR/interactive_report.html" \
    --output html
fi

if [[ -f "$SEC_DIR/consolidated_misconfiguration_report.json" ]]; then
  mv "$SEC_DIR/consolidated_misconfiguration_report.json" "$REPORTS_DIR/consolidated_misconfiguration_check.json"
fi

if [[ -f "$SEC_DIR/consolidated_sbom_report.json" ]]; then
  mv "$SEC_DIR/consolidated_sbom_report.json" "$REPORTS_DIR/consolidated_sbom.json"
fi

echo "Reports published to: $REPORTS_DIR"
exit $SCAN_EXIT_CODE
