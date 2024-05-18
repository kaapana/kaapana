#!/bin/bash
set -euf -o pipefail

echo "KAAPANA_BUILD_BRANCH"
echo "$KAAPANA_BUILD_BRANCH"

clone_repo() {
  local branch=$1
  echo "cloning repo from branch $branch"
  if git clone -b "$branch" --single-branch https://github.com/kaapana/kaapana; then
    return 0
  else
    return 1
  fi
}

if ! clone_repo "$KAAPANA_BUILD_BRANCH"; then
  echo "git clone failed, retrying with 'feature/' prefix"
  clone_repo "feature/$KAAPANA_BUILD_BRANCH"
fi

KAAPANA_COMMIT_HASH=$(echo $KAAPANA_BUILD_VERSION | sed 's/.*-g//')
git checkout $KAAPANA_COMMIT_HASH
