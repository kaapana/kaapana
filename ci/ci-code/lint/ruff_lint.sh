#!/bin/bash
set -euf -o pipefail

cd "$(git rev-parse --show-toplevel)"

RUFF_VERSION="${RUFF_VERSION:-0.16.4}"
TOOLS_DIR="${KAAPANA_CI_TOOLS:-$HOME/.cache/kaapana-ci}"

grep -q "rev: v$RUFF_VERSION" .pre-commit-config.yaml

export PATH="$TOOLS_DIR/ruff/bin:$PATH"

if [[ "$(ruff --version 2>/dev/null || true)" != "ruff $RUFF_VERSION" ]]; then
    python -m pip install --quiet --no-cache-dir --target "$TOOLS_DIR/ruff" "ruff==$RUFF_VERSION"
fi

case "${1:-}" in
format)
    ruff format --check --diff .
    ;;
validate)
    ruff check --output-format=full .
    ;;
lint)
    ruff check --config ci/ci-code/lint/ruff-quality.toml --output-format=gitlab --exit-zero . > gl-code-quality-report.json
    ruff check --config ci/ci-code/lint/ruff-quality.toml --statistics --exit-zero .
    ;;
*)
    echo "usage: $0 format|validate|lint" >&2
    exit 2
    ;;
esac
