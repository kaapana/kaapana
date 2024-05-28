* Build `base-python-gpu` image with version `latest`
`./build_image.sh --dir $KAAPANA_REPO_PATH/data-processing/base-images/base-python-gpu --image-name base-python-gpu --image-version latest`

* Build without specifying a version to use `KAAPANA_BUILD_VERSION` by default
`./build_image.sh --dir $KAAPANA_REPO_PATH/dag/pyradiomics-feature-extractor --image-name pyradiomics-feature-extractor`

