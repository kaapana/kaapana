#!/bin/bash
set -euf -o pipefail

cd "$(git rev-parse --show-toplevel)"

if [[ "${1:-}" != "format" ]]; then
    echo "usage: $0 format [<file> ...]" >&2
    exit 2
fi
shift

if [[ ! -f node_modules/.package-lock.json || package-lock.json -nt node_modules/.package-lock.json ]]; then
    npm ci --no-audit --no-fund
fi

if [[ $# -gt 0 ]]; then
    npx prettier --write --ignore-unknown "$@"
    exit
fi

files=()
while IFS= read -r -d '' f; do
    [[ -f "$f" ]] && files+=("$f")
done < <(git ls-files -z -- '*.js' '*.mjs' '*.cjs' '*.jsx' '*.ts' '*.mts' '*.tsx' '*.vue' '*.md' '*.json' '*.yaml' '*.yml')

npx prettier --check "${files[@]}"
