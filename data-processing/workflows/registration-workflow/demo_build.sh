#!/bin/bash
# Builds and pushes every processing-container of the classification-workflow.
# Tag = `git describe --tags` output. Registry/credentials come from the repo's .env.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
ENV_FILE="$REPO_ROOT/.env"
CONTAINERS_DIR="$SCRIPT_DIR/processing-containers"

if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: .env not found at $ENV_FILE" >&2
    exit 1
fi
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

if [ -z "${DEFAULT_REGISTRY:-}" ]; then
    echo "ERROR: DEFAULT_REGISTRY is not set in $ENV_FILE" >&2
    exit 1
fi

# VERSION="$(git -C "$REPO_ROOT" describe --tags --always)"
VERSION="0.7.0-latest"
echo "Registry: $DEFAULT_REGISTRY"
echo "Version tag: $VERSION"

if [ -n "${REGISTRY_USER:-}" ] && [ -n "${REGISTRY_PW:-}" ]; then
    docker login "$DEFAULT_REGISTRY" --username "$REGISTRY_USER" --password "$REGISTRY_PW"
fi

for dir in "$CONTAINERS_DIR"/*/; do
    dir="${dir%/}"
    dockerfile="$dir/Dockerfile"
    if [ ! -f "$dockerfile" ]; then
        continue
    fi

    image="$(sed -n 's/^LABEL IMAGE=["'"'"']\?\([^"'"'"']*\)["'"'"']\?.*/\1/p' "$dockerfile" | head -n1)"
    if [ -z "$image" ]; then
        echo "ERROR: no LABEL IMAGE found in $dockerfile" >&2
        exit 1
    fi

    tag="$DEFAULT_REGISTRY/$image:$VERSION"
    echo "=== Building $tag ==="
    docker build -f "$dockerfile" -t "$tag" "$dir"

    echo "=== Pushing $tag ==="
    docker push "$tag"
done

echo "DONE"