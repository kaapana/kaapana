#!/bin/bash
set -euf -o pipefail

cd "$(git rev-parse --show-toplevel)"

mode="${1:-}"
if [[ "$mode" != "validate" && "$mode" != "lint" ]]; then
    echo "usage: $0 validate [<file> ...] | lint" >&2
    exit 2
fi
shift

KUBECONFORM_VERSION="${KUBECONFORM_VERSION:-0.7.0}"
KUBE_LINTER_VERSION="${KUBE_LINTER_VERSION:-0.8.3}"
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

if [[ "$mode" == "lint" ]]; then
    if [[ "$(kube-linter version 2>/dev/null || true)" != "$KUBE_LINTER_VERSION" ]]; then
        mkdir -p "$TOOLS_DIR/bin"
        curl -fsSL "https://github.com/stackrox/kube-linter/releases/download/v$KUBE_LINTER_VERSION/kube-linter-linux.tar.gz" \
            | tar -xz -C "$TOOLS_DIR/bin" kube-linter
    fi

    kaapana-build --lint-only --no-linting --kaapana-dir "$PWD" --build-dir build/helm-lint --log-level "$log_level"

    rm -rf build/helm-lint/rendered
    while IFS= read -r -d '' chart; do
        chart_dir="$(dirname "$chart")"
        helm template "$(basename "$chart_dir")" "./$chart_dir" --values build_cli/build_cli/configs/fake-values.yaml \
            --output-dir "build/helm-lint/rendered/$(basename "$chart_dir")" >/dev/null || true
    done < <(find build/helm-lint -mindepth 3 -maxdepth 3 -name Chart.yaml -print0)

    kube-linter lint --config ci/ci-code/lint/kube-linter-quality.yaml --format json build/helm-lint/rendered \
        > build/helm-lint/kube-linter.json || true
    python ci/ci-code/lint/kube_linter_report.py build/helm-lint/kube-linter.json build/helm-lint/rendered \
        > gl-code-quality-report.json
    exit 0
fi

changed=()
for file in "$@"; do
    changed+=(--changed-file "$file")
done

set +e
kaapana-build --lint-only --enable-linting ${changed[@]+"${changed[@]}"} --kaapana-dir "$PWD" --build-dir build/helm-lint \
    --log-level "$log_level"
status=$?
mkdir -p helm-reports
cp -r build/helm-lint/junit/. helm-reports/ 2>/dev/null
exit "$status"
