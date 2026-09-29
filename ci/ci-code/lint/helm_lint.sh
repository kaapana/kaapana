#!/bin/bash
set -euf -o pipefail

cd "$(git rev-parse --show-toplevel)"

KUBECONFORM_VERSION="${KUBECONFORM_VERSION:-0.7.0}"
TOOLS_DIR="${KAAPANA_CI_TOOLS:-$HOME/.cache/kaapana-ci}"

export PATH="$TOOLS_DIR/bin:$PATH"

if ! command -v kubeconform >/dev/null; then
    mkdir -p "$TOOLS_DIR/bin"
    curl -fsSL "https://github.com/yannh/kubeconform/releases/download/v$KUBECONFORM_VERSION/kubeconform-linux-amd64.tar.gz" \
        | tar -xz -C "$TOOLS_DIR/bin" kubeconform
fi

if ! (cd / && python -c 'import build_cli.cli' 2>/dev/null); then
    python -m pip install -q -e build_cli
fi

log_level="${HELM_LINT_LOG_LEVEL:-WARN}"
if [[ -n "${CI:-}" ]]; then
    git fetch --tags --quiet
    log_level="${HELM_LINT_LOG_LEVEL:-INFO}"
fi

set +e
kaapana-build --lint-only --enable-linting "$@" --kaapana-dir "$PWD" --build-dir build/helm-lint \
    --log-level "$log_level"
status=$?
mkdir -p helm-reports
cp -r build/helm-lint/junit/. helm-reports/ 2>/dev/null
exit "$status"
