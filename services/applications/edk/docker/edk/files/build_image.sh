#!/bin/bash

# default vals
dockerfile=""
context_path=""
image_name=""
image_version=""
no_import=""

# help message
print_help() {
    echo "Usage: $0 --dir <context-path> --image-name <imagename> [--dockerfile <dockerfile>] [--image-version <imageversion>] [--no-import]"
    echo
    echo "Arguments:"
    echo "  --dir             Path to the context directory (required)"
    echo "  --dockerfile      Path to the Dockerfile (optional, defaults to <context-path>/Dockerfile)"
    echo "  --image-name      Name of the Docker image (optional, if not provided, extracted from Dockerfile LABEL IMAGE)"
    echo "  --image-version   Version of the Docker image (optional, defaults to KAAPANA_BUILD_VERSION)"
    echo "  --no-import       Skip importing container inside microk8s ctr"
    echo "  --help            Display this help message"
    echo
}

# parse args, order doesn't matter, --dir has to be provided
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --dir) context_path="$2"; shift ;;
        --dockerfile) dockerfile="$2"; shift ;;
        --image-name) image_name="$2"; shift ;;
        --image-version) image_version="$2"; shift ;;
        --no-import) no_import="true"; shift ;;
        --help) print_help; exit 0 ;;
        *) echo "Unknown argument: $1"; print_help; exit 1 ;;
    esac
    shift
done

# check if context_path is empty
if [ -z "$context_path" ]; then
    echo "ERROR: Context path is required. Use --dir <context-path>"
    print_help
    exit 1
fi

# if --dockerfile is empty it will be generated as <context_path>/Dockerfile
if [ -z "$dockerfile" ]; then
    dockerfile="$context_path/Dockerfile"
fi

# if --image-name is empty, take it from Dockerfile LABEL IMAGE="<name>"
if [ -z "$image_name" ]; then
    if [ -f "$dockerfile" ]; then
        image_name=$(grep -oP 'LABEL IMAGE="\K[^"]+' "$dockerfile")
        if [ -z "$image_name" ]; then
            echo "ERROR: Image name is required. Use --image-name <imagename> or ensure Dockerfile has LABEL IMAGE=\"<name>\""
            print_help
            exit 1
        else
            echo "INFO: Image name extracted from Dockerfile: $image_name"
        fi
    else
        echo "ERROR: Dockerfile not found at $dockerfile"
        exit 1
    fi
fi

# if --image-version is empty use KAAPANA_BUILD_VERSION
if [ -z "$image_version" ]; then
    image_version="$KAAPANA_BUILD_VERSION"
fi

# update the Dockerfile to replace "FROM local-only/..." with "FROM $LOCAL_REGISTRY_URL/..."
if [ -f "$dockerfile" ]; then
    if grep -q "^FROM local-only/" "$dockerfile"; then
        sed -i "s|^FROM local-only/|FROM $LOCAL_REGISTRY_URL/|g" "$dockerfile"
        if grep -q "^FROM $LOCAL_REGISTRY_URL/" "$dockerfile"; then
            echo "SUCCESS: Dockerfile updated successfully."
        else
            echo "ERROR: Dockerfile update failed."
            exit 1
        fi
    else
        echo "INFO: No 'FROM local-only/...' line found in Dockerfile."
    fi
else
    echo "ERROR: Dockerfile not found at $dockerfile"
    exit 1
fi

# run python script for starting kaniko builder pod, this might take some time to finish as it builds and pushes the image to local registry
python3 /kaapana/app/utils/create_kaniko_pod.py /kaapana/app/utils/kaniko-builder-pod.yml --dockerfile "$dockerfile" --context "$context_path" --image_name "$image_name" --image_version "$image_version"

# run skopeo command to copy from local reg to a tarball
skopeo copy --tls-verify=false docker://$LOCAL_REGISTRY_URL/$image_name:$image_version oci-archive:/kaapana/minio/edk-to-minio/$image_name.tar:$REGISTRY_URL/$image_name:$image_version

# check if --no-import is passed
if [ "$no_import" != "true" ]; then
    # send req to kube-helm /import-container endpoint for importing container tar into ctr
    echo "Importing container tar into ctr..."
    curl -G "$KUBE_HELM_URL/import-container" --data-urlencode "filename=$image_name.tar"
    # TODO: rm .tar file if import is successful
else
    echo "Skipping import."
fi
