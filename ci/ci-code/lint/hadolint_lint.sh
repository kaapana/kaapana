#!/bin/bash
set -euf -o pipefail

cd "$(git rev-parse --show-toplevel)"

HADOLINT_VERSION="${HADOLINT_VERSION:-2.15.1}"
TOOLS_DIR="${KAAPANA_CI_TOOLS:-$HOME/.cache/kaapana-ci}"

grep -A1 hadolint-py .pre-commit-config.yaml | grep -q "rev: v$HADOLINT_VERSION"

export PATH="$TOOLS_DIR/bin:$PATH"

if [[ "$(hadolint --version 2>/dev/null || true)" != *"$HADOLINT_VERSION"* ]]; then
    mkdir -p "$TOOLS_DIR/bin"
    curl -fsSL "https://github.com/hadolint/hadolint/releases/download/v$HADOLINT_VERSION/hadolint-linux-x86_64" -o "$TOOLS_DIR/bin/hadolint"
    chmod +x "$TOOLS_DIR/bin/hadolint"
fi

mapfile -d '' dockerfiles < <(git ls-files -z -- '*Dockerfile')

case "${1:-}" in
validate)
    hadolint "${dockerfiles[@]}"
    ;;
lint)
    hadolint --config ci/ci-code/lint/hadolint-quality.yaml --no-fail -f gitlab_codeclimate "${dockerfiles[@]}" > gl-code-quality-report.json
    hadolint --config ci/ci-code/lint/hadolint-quality.yaml --no-fail "${dockerfiles[@]}"
    ;;
*)
    echo "usage: $0 validate|lint" >&2
    exit 2
    ;;
esac
