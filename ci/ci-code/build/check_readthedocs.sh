#!/bin/bash
set -euf -o pipefail

TOKEN=$KAAPANA_READTHEDOCS_TOKEN
COMMIT=$CI_COMMIT_SHA

curl -sf -H "Authorization: Token $TOKEN" \
    https://readthedocs.org/api/v3/projects/kaapana/builds/ -o builds.json

# Newest completed "latest" build for this commit; builds still running have
# success == null and are skipped.
result=$(jq -r --arg commit "$COMMIT" \
    '[.results[] | select(.version == "latest" and .commit == $commit and .success != null)][0].success' \
    builds.json)

case "$result" in
    true)
        echo "Build for ${COMMIT} on https://readthedocs.org/projects/kaapana/ succeeded!"
        exit 0
        ;;
    false)
        echo "Build for ${COMMIT} on https://readthedocs.org/projects/kaapana/ failed!"
        exit 1
        ;;
    *)
        echo "No build found for ${COMMIT} on https://readthedocs.org/projects/kaapana/!"
        exit 1
        ;;
esac
