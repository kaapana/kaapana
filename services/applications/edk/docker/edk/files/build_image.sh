#!/bin/bash

# default vals
dockerfile=""
context_path=""
image_name=""

# parse args, order doesn't matter, --dir and --image-name have to be provided
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --dir) context_path="$2"; shift ;;
        --dockerfile) dockerfile="$2"; shift ;;
        --image-name) image_name="$2"; shift ;;
        *) echo "Unknown argument: $1"; exit 1 ;;
    esac
    shift
done

# check if context_path is empty
if [ -z "$context_path" ]; then
    echo "ERROR: Context path is required. Use --dir <context-path>"
    exit 1
fi

# if --dockerfile is empty it will be generated as <context_path>/Dockerfile
if [ -z "$dockerfile" ]; then
    dockerfile="$context_path/Dockerfile"
fi

# check if image-name is empty
if [ -z "$image_name" ]; then
    echo "Error: Image name is required. Use --image-name <imagename>"
    exit 1
fi

# image version if KAAPANA_BUILD_VERSION of the platform by default
image_version="${KAAPANA_BUILD_VERSION}"

# run python script for starting kaniko builder pod, this might take some time to finish as it builds and pushes the image to local registry
python3 /kaapana/app/utils/create_kaniko_pod.py kaniko-builder-pod.yml --dockerfile "$dockerfile" --context "$context_path" --image_name "$image_name" --image_version "$image_version"

# run skopeo command to copy from local reg to a tarball
skopeo copy --tls-verify=false docker://$LOCAL_REGISTRY_URL/$image_name:$image_version oci-archive:/kaapana/app/edk-data/$image_name.tar:$REGISTRY_URL/$image_name:$image_version

# TODO: send req to kube-helm /import-container endpoint for importing container tar into ctr 