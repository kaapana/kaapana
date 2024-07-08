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

# clone repo
if ! clone_repo "$KAAPANA_BUILD_BRANCH"; then
  echo "git clone failed, retrying with 'feature/' prefix"
  clone_repo "feature/$KAAPANA_BUILD_BRANCH"
  sleep 2
fi

# change to commit hash that the current platform is built from
cd $KAAPANA_REPO_PATH
KAAPANA_COMMIT_HASH=$(echo $KAAPANA_BUILD_VERSION | sed 's/.*-g//')
git fetch
git checkout $KAAPANA_COMMIT_HASH
cd ..

# copy example DAG from repo to /dag folder
cp -r $KAAPANA_REPO_PATH/templates_and_examples/examples/processing-pipelines/pyradiomics-feature-extractor /kaapana/app/dag/

# build base images
BASE_PYTHON_CPU="$KAAPANA_REPO_PATH/data-processing/base-images/base-python-cpu"
echo "Building base-python-cpu..."
/usr/bin/bash /kaapana/app/build_image.sh --dir $BASE_PYTHON_CPU --image-name base-python-cpu --image-version latest --no-import

BASE_PYTHON_GPU="$KAAPANA_REPO_PATH/data-processing/base-images/base-python-gpu"
echo "Building base-python-gpu..."
/usr/bin/bash /kaapana/app/build_image.sh --dir $BASE_PYTHON_GPU --image-name base-python-gpu --image-version latest --no-import

BASE_INSTALLER="$KAAPANA_REPO_PATH/services/utils/base-installer"
echo "Building base-installer..."
/usr/bin/bash /kaapana/app/build_image.sh --dir $BASE_INSTALLER --image-name base-installer --image-version latest --no-import