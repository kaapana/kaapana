#!/bin/bash
set -euf -o pipefail

cd "$(git rev-parse --show-toplevel)"

KUBECONFORM_VERSION="${KUBECONFORM_VERSION:-0.7.0}"
KUBE_LINTER_VERSION="${KUBE_LINTER_VERSION:-0.8.3}"
TOOLS_DIR="${KAAPANA_CI_TOOLS:-$HOME/.cache/kaapana-ci}"

export PATH="$TOOLS_DIR/bin:$PATH"

if ! command -v kubeconform >/dev/null; then
    mkdir -p "$TOOLS_DIR/bin"
    curl -fsSL "https://github.com/yannh/kubeconform/releases/download/v$KUBECONFORM_VERSION/kubeconform-linux-amd64.tar.gz" \
        | tar -xz -C "$TOOLS_DIR/bin" kubeconform
fi

if [[ "$(kube-linter version 2>/dev/null || true)" != "$KUBE_LINTER_VERSION" ]]; then
    mkdir -p "$TOOLS_DIR/bin"
    curl -fsSL "https://github.com/stackrox/kube-linter/releases/download/v$KUBE_LINTER_VERSION/kube-linter-linux.tar.gz" \
        | tar -xz -C "$TOOLS_DIR/bin" kube-linter
fi

enforce_advisory=()
if [[ "${1:-}" == "--strict" ]]; then
    shift
    enforce_advisory=(--enforce-advisory)
fi

if ! (cd / && python -c 'import build_cli.cli' 2>/dev/null); then
    python -m pip install -q -e build_cli
fi

log_level="${HELM_LINT_LOG_LEVEL:-WARN}"
if [[ -n "${CI:-}" ]]; then
    git fetch --tags --quiet
    log_level="${HELM_LINT_LOG_LEVEL:-INFO}"
fi

changed=()
for file in "$@"; do
    changed+=(--changed-file "$file")
done

set +e
kaapana-build --lint-only --enable-linting ${changed[@]+"${changed[@]}"} ${enforce_advisory[@]+"${enforce_advisory[@]}"} \
    --kaapana-dir "$PWD" --build-dir build/helm-lint --log-level "$log_level"
status=$?
mkdir -p helm-reports
cp -r build/helm-lint/junit/. helm-reports/ 2>/dev/null
cp build/helm-lint/code-quality/kube-linter.json gl-code-quality-report.json 2>/dev/null || echo "[]" > gl-code-quality-report.json
exit "$status"
