#!/bin/bash
set -euf -o pipefail

echo "KAAPANA_BUILD_BRANCH"
echo "$KAAPANA_BUILD_BRANCH"

# clone Kaapana
git clone -b $KAAPANA_BUILD_BRANCH --single-branch https://github.com/kaapana/kaapana
KAAPANA_COMMIT_HASH=$(echo $KAAPANA_BUILD_VERSION | sed 's/.*-g//')
git checkout $KAAPANA_COMMIT_HASH