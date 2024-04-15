#!/bin/bash

SOURCE_REMOTE="origin"
ARCHIVE_REPO="git@codebase.helmholtz.cloud:kaapana/kaapana-archive.git"
BRANCH="$1"

if [ -z "$BRANCH" ]; then
  echo "Usage: $(basename "$0") branch-to-move"
fi

echo "Branch $BRANCH will be moved to from $SOURCE_REMOTE to $ARCHIVE_REPO"
while true; do
  read -r -p "Proceed? (y/n) " yn
  case $yn in
    [Yy]* ) break;;
    [Nn]* ) exit;;
    * ) echo "Please answer yes or no.";;
  esac
done

set -e
set -x
echo "Pushing branch $SOURCE_REMOTE/$BRANCH to $ARCHIVE_REPO"
git push "$ARCHIVE_REPO" "refs/remotes/$SOURCE_REMOTE/$BRANCH:refs/heads/$BRANCH"
echo "Removing branch from origin"
git push --delete "$SOURCE_REMOTE" "$BRANCH"
echo "$BRANCH was moved to $ARCHIVE_REPO sucessfully"