# EDK

Extension Development Kit for Kaapana. You can use this environment to develop custom extensions. Below you will find some useful commands to run different types of build scripts based on your needs.

Start by running the first `./build_extension.sh` command to build and push the new extension pyradiomics-feature-extractor in your Kaapana instance. When the script is finished you should be able to see a new entry under Extensions view, just make sure to change Kind, Version and Resources filters to "All" in order to see the new extension.

If you want to understand more about how extension development works and how to take more advantage of the underlying technologies, refer to our development guide at https://kaapana.readthedocs.io/en/stable/development_guide


## Build Extension pyradiomics-feature-extractor in `/dag` folder

`./build_extension.sh --dir /kaapana/app/dag/pyradiomics-feature-extractor`

This command builds all container images (searching for all `Dockerfile` files) under this path and pushes to the local registry. Also packages the Helm chart (searches for `Chart.yaml` file) and makes it available as an extension under the Extensions tab in the platform.


## Build container image

`./build_image.sh --dir /kaapana/app/dag/pyradiomics-feature-extractor/processing-containers/pyradiomics-feature-extractor`

Builds the container image under the path by creating a separate kaniko pod, and pushes the image to the local registry. By default it does not put the image inside microk8s runtime.

If you want to use an image in the local registry in an operator, you need to change the `{DEFAULT_REGISTRY}` parameter in image tag to `localhost:32000`. For example in the PyradiomicsExtractorOperator file you can see it as `image=localhost:32000/pyradiomics-extract-features:{KAAPANA_BUILD_VERSION}`. `DEFAULT_REGISTRY` refers to the registry url from which the platform is deployed. You can still keep `{KAAPANA_BUILD_VERSION}` at the end since the image is also built with the same version as your Kaapana instance.

Arguments:

```
--dir             Path to the context directory (required), Dockerfile is expected to be under this path
--dockerfile      Path to the Dockerfile (optional, if empty, it defaults to <dir>/Dockerfile)
--image-name      Name of the Docker image (optional, if not provided, extracted from Dockerfile LABEL IMAGE)
--tar             Export container from the registry as a tar file under $VOLUME_PATH
--import          Import container inside microk8s ctr, also generates a tar file
```


## Build Helm chart

`./build_chart.sh --dir /kaapana/app/dag/pyradiomics-feature-extractor/extension/pyradiomics-workflow`


## Build `base-python-gpu` image with version `latest`

Option `--import` will create a tar file import the base image into microk8s ctr

`./build_image.sh --dir $KAAPANA_REPO_PATH/data-processing/base-images/base-python-gpu --image-name base-python-gpu --image-version latest --no-import`


## TODO
- extend build helm chart docs
- add `How to develop your scripts`
- add `./build_images.sh`
- 