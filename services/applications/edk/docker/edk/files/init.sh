#!/bin/bash
set -euf -o pipefail

clone_repo() {
  local branch=$1
  echo "cloning repo from branch $branch"

  # rm "kaapana" folder if exists
  if [ -d "kaapana" ]; then
    echo "Deleting existing 'kaapana' folder"
    rm -rf "kaapana"
  fi

  # clone repo from branch
  if git clone -b "$branch" --single-branch https://github.com/kaapana/kaapana; then
    return 0
  else
    return 1
  fi
}

# clone repo, try with normal branch name first, if fails add feature/ prefix
if ! clone_repo "$KAAPANA_BUILD_BRANCH"; then
  echo "git clone failed with branch '$KAAPANA_BUILD_BRANCH'. Overwrite it with a valid branch name by running 'export KAAPANA_BUILD_BRANCH=<branch>' and try again"
fi

# check out the ref that the current platform is built from.
# KAAPANA_BUILD_VERSION follows `git describe` (<tag>-<count>-g<hash>) for normal
# builds, but can also be a rolling tag such as `0.7.0-latest` (--version-latest
# builds), which carries no commit hash.
cd "$KAAPANA_REPO_PATH"
git fetch --tags --quiet
if [[ "$KAAPANA_BUILD_VERSION" =~ -g([0-9a-f]+)$ ]]; then
  target="${BASH_REMATCH[1]}"
else
  target="$KAAPANA_BUILD_VERSION"
fi
if git rev-parse --verify --quiet "${target}^{commit}" >/dev/null; then
  echo "Checking out '$target' (from KAAPANA_BUILD_VERSION='$KAAPANA_BUILD_VERSION')"
  git checkout --quiet "$target"
else
  echo "WARNING: could not resolve KAAPANA_BUILD_VERSION='$KAAPANA_BUILD_VERSION' to a git ref."
  echo "         Staying on branch '$KAAPANA_BUILD_BRANCH' HEAD; this may differ from the running platform."
fi
cd ..

# copy example DAG from repo to /dag folder
cp -r $KAAPANA_REPO_PATH/templates_and_examples/examples/processing-pipelines/pyradiomics-feature-extractor /kaapana/app/dag/

# build base images
BASE_PYTHON_CPU="$KAAPANA_REPO_PATH/data-processing/base-images/base-python-cpu"
echo "Building base-python-cpu..."
/usr/bin/bash /kaapana/app/build_image.sh --dir $BASE_PYTHON_CPU --image-name base-python-cpu --image-version latest

BASE_PYTHON_GPU="$KAAPANA_REPO_PATH/data-processing/base-images/base-python-gpu"
echo "Building base-python-gpu..."
/usr/bin/bash /kaapana/app/build_image.sh --dir $BASE_PYTHON_GPU --image-name base-python-gpu --image-version latest

BASE_INSTALLER="$KAAPANA_REPO_PATH/services/utils/base-installer"
echo "Building base-installer..."
/usr/bin/bash /kaapana/app/build_image.sh --dir $BASE_INSTALLER --image-name base-installer --image-version latest