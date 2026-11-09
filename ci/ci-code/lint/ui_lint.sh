#!/bin/bash
set -euf -o pipefail

cd "$(git rev-parse --show-toplevel)"

case "${1:-}" in
validate)
    eslint_config=()
    ;;
lint)
    eslint_config=(--config ci/ci-code/lint/eslint-quality.config.mjs)
    ;;
*)
    echo "usage: $0 validate|lint [<file> ...]" >&2
    exit 2
    ;;
esac
mode="$1"
shift

if [[ ! -f node_modules/.package-lock.json || package-lock.json -nt node_modules/.package-lock.json ]]; then
    npm ci --no-audit --no-fund
fi

if [[ $# -gt 0 ]]; then
    npx eslint ${eslint_config[@]+"${eslint_config[@]}"} --fix --no-warn-ignored "$@"
    exit
fi

files=()
while IFS= read -r -d '' f; do
    [[ -f "$f" ]] && files+=("$f")
done < <(git ls-files -z -- '*.js' '*.mjs' '*.cjs' '*.jsx' '*.ts' '*.mts' '*.tsx' '*.vue')

if [[ "$mode" == "validate" ]]; then
    npx eslint --no-warn-ignored "${files[@]}"
    exit
fi

ESLINT_CODE_QUALITY_REPORT=gl-code-quality-report.json \
    npx eslint "${eslint_config[@]}" --format gitlab --no-warn-ignored "${files[@]}" >/dev/null ||
    [[ $? -eq 1 ]]
