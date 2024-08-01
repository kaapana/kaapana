## Build Extension pyradiomics-feature-extractor in `/dag` folder

`./build_extension.sh --dir /kaapana/app/dag/pyradiomics-feature-extractor`


## Build Helm chart

`./build_chart.sh --dir /kaapana/app/dag/pyradiomics-feature-extractor/extension/pyradiomics-workflow`


## Build images without specifying a version to use `KAAPANA_BUILD_VERSION` by default:

`./build_image.sh --dir /kaapana/app/dag/pyradiomics-feature-extractor/processing-containers/pyradiomics-feature-extractor`


## Build `base-python-gpu` image with version `latest`. Option `--no-import` will skip importing the base image into microk8s ctr:

`./build_image.sh --dir $KAAPANA_REPO_PATH/data-processing/base-images/base-python-gpu --image-name base-python-gpu --image-version latest --no-import`
