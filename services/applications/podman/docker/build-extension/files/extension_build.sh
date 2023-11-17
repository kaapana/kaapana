#!/bin/bash
set -euf -o pipefail

POSITIONAL=()
while [[ $# -gt 0 ]]
do
    key="$1"

    case $key in

        -h|--help)
            echo -e "build extension in container";
            exit 0
        ;;

        -kv|--kaapana-version)
            KAAPANA_VERSION="$2"
            echo -e "KAAPANA_VERSION set to: $KAAPANA_VERSION";
            shift # past argument
            shift # past value
        ;;

    esac
done

echo building base images...

# TODO: currently can't be run in the container due to permission issues, try kaniko as well for future work
podman build -t local-only/base-python-cpu:latest /kaapana/app/kaapana/data-processing/base-images/base-python-cpu
podman build -t local-only/base-python-gpu:latest /kaapana/app/kaapana/data-processing/base-images/base-python-gpu
podman build -t local-only/base-installer:latest /kaapana/app/kaapana/services/utils/base-installer

echo successfuly built base images

echo setting kaapana_build_version to $KAAPANA_VERSION

sed -i 's/"kaapana_build_version": "0.0.0-latest"/"kaapana_build_version": "'$KAAPANA_VERSION'"/g' /kaapana/app/extension_config.json

echo building images for extension
extensionctl build image extension_config.json

echo generating helm chart
extensionctl build chart extension_config.json