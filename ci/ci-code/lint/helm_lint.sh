#!/bin/bash
set -euf -o pipefail

cd "$(git rev-parse --show-toplevel)"

if ! (cd / && python -c 'import build_cli.cli' 2>/dev/null); then
    python -m pip install -q -e build_cli
fi

exec kaapana-build --lint-only --enable-linting --kaapana-dir "$PWD" --build-dir build/helm-lint \
    --log-level "${HELM_LINT_LOG_LEVEL:-WARN}"
