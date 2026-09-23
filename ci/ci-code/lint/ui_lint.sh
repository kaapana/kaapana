#!/bin/bash
set -euf -o pipefail

cd "$(git rev-parse --show-toplevel)"

if [[ ! -f node_modules/.package-lock.json || package-lock.json -nt node_modules/.package-lock.json ]]; then
    npm ci --no-audit --no-fund
fi

status=0

if [[ $# -gt 0 ]]; then
    npx eslint --fix --no-warn-ignored "$@" || status=1
    npx prettier --write --ignore-unknown "$@" || status=1
    exit $status
fi

files=()
while IFS= read -r -d '' f; do
    [[ -f "$f" ]] && files+=("$f")
done < <(git ls-files -z -- '*.ts' '*.mts' '*.tsx' '*.vue')

ESLINT_CODE_QUALITY_REPORT=gl-code-quality-report.json \
    npx eslint --config ci/eslint-quality.config.mjs --format gitlab --no-warn-ignored "${files[@]}" >/dev/null ||
    [[ $? -eq 1 ]] || status=1
npx eslint --no-warn-ignored "${files[@]}" || status=1
npx prettier --check "${files[@]}" || status=1

exit $status
